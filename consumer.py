import os
import time
import dotenv
import asyncio
import logging
import signal
import sys
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient
from prompt_processor import PromptProcessor

dotenv.load_dotenv()

import json

# Configure logging FIRST, before any other operations
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Set these as environment variables for security
SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')
BATCH_SIZE = 10  # Number of messages to receive in a batch

# Graceful shutdown configuration
SHUTDOWN_TIMEOUT = int(os.getenv('SHUTDOWN_TIMEOUT', '30'))  # seconds
shutdown_event = asyncio.Event()

def validate_environment_variables():
    """
    Validate all required environment variables at startup.
    Raises ValueError with clear message if any variables are missing.
    """
    required_vars = {
        'SERVICE_BUS_CONNECTION_STR': SERVICE_BUS_CONNECTION_STR,
        'SERVICE_BUS_QUEUE_NAME': QUEUE_NAME,
        'AI_MODEL_NAME': os.getenv('AI_MODEL_NAME'),
        'AI_API_KEY': os.getenv('AI_API_KEY'),
        'AI_ENDPOINT': os.getenv('AI_ENDPOINT'),
        'API_VERSION': os.getenv('API_VERSION')
    }
    
    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        logger.critical("Please ensure all required environment variables are set before starting the application.")
        raise ValueError(error_msg)
    
    logger.info("All required environment variables are present")
    return {var_name: var_value for var_name, var_value in required_vars.items()}

# Validate environment variables at startup
try:
    env_vars = validate_environment_variables()
except ValueError as e:
    logger.critical(f"Environment validation failed: {e}")
    raise

def setup_signal_handlers():
    """
    Setup signal handlers for graceful shutdown.
    """
    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Handle SIGTERM (Docker/Kubernetes stop)
    signal.signal(signal.SIGTERM, signal_handler)
    # Handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Signal handlers configured for graceful shutdown")

async def safe_abandon_message(receiver, message):
    """
    Safely abandon a message with proper exception handling.
    Ensures the consumer continues working even if abandon fails.
    """
    try:
        await receiver.abandon_message(message)
        logger.info("Message abandoned successfully")
    except Exception as abandon_error:
        logger.error(f"Failed to abandon message (this won't stop the consumer): {abandon_error}")

async def safe_complete_message(receiver, message):
    """
    Safely complete a message with proper exception handling.
    """
    try:
        await receiver.complete_message(message)
        logger.info("Message completed successfully")
    except Exception as complete_error:
        logger.error(f"Failed to complete message: {complete_error}")
        await safe_abandon_message(receiver, message)

async def process_message_async(message, receiver, model_name, api_key, endpoint, api_version):
    try:
        body_bytes = b"".join(message.body)
        content = json.loads(body_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON message: {e}")
        await safe_abandon_message(receiver, message)
        return

    # Use context manager to ensure proper cleanup
    try:
        async with PromptProcessor(model_name, api_key, endpoint, api_version) as prompt_processor:
            result = await prompt_processor.process_payload(content)
            logger.info(f"Evaluation result: {result}")
            await safe_complete_message(receiver, message)
    except Exception as processing_error:
        logger.error(f"Failed to process message: {processing_error}")
        await safe_abandon_message(receiver, message)

async def cleanup_completed_tasks(tasks):
    """
    Clean up completed tasks and handle their results/exceptions.
    Returns the updated task set with completed tasks removed.
    """
    if not tasks:
        return tasks
    
    # Get completed tasks without waiting
    done, pending = await asyncio.wait(tasks, timeout=0, return_when=asyncio.ALL_COMPLETED)
    
    # Handle results/exceptions from completed tasks
    for task in done:
        try:
            # This will raise an exception if the task failed
            await task
        except Exception as task_error:
            logger.error(f"Task completed with error: {task_error}")
    
    return pending

async def wait_for_available_slot(tasks, max_concurrent_tasks):
    """
    Wait for at least one task to complete when we hit the concurrency limit.
    Returns the updated task set with completed tasks cleaned up.
    """
    if len(tasks) < max_concurrent_tasks:
        return tasks
    
    # Wait for at least one task to complete
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    
    # Handle results/exceptions from completed tasks
    for task in done:
        try:
            await task
        except Exception as task_error:
            logger.error(f"Task completed with error: {task_error}")
    
    return pending

async def graceful_shutdown_tasks(tasks, timeout=SHUTDOWN_TIMEOUT):
    """
    Gracefully shutdown all running tasks within the specified timeout.
    
    Args:
        tasks: Set of asyncio tasks to shutdown
        timeout: Maximum time to wait for tasks to complete (seconds)
    
    Returns:
        bool: True if all tasks completed gracefully, False if timeout occurred
    """
    if not tasks:
        logger.info("No tasks to shutdown")
        return True
    
    logger.info(f"Gracefully shutting down {len(tasks)} tasks (timeout: {timeout}s)")
    
    try:
        # Wait for all tasks to complete within timeout
        done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED)
        
        # Handle completed tasks
        for task in done:
            try:
                await task
                logger.debug("Task completed successfully during shutdown")
            except Exception as task_error:
                logger.warning(f"Task completed with error during shutdown: {task_error}")
        
        # Handle tasks that didn't complete in time
        if pending:
            logger.warning(f"{len(pending)} tasks did not complete within {timeout}s, cancelling them")
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug("Task cancelled successfully")
                except Exception as task_error:
                    logger.warning(f"Error during task cancellation: {task_error}")
            return False
        else:
            logger.info("All tasks completed gracefully")
            return True
            
    except Exception as shutdown_error:
        logger.error(f"Error during graceful shutdown: {shutdown_error}")
        return False

async def run_service_bus_processor_async():
    # Use validated environment variables
    model_name = env_vars['AI_MODEL_NAME']
    api_key = env_vars['AI_API_KEY']
    endpoint = env_vars['AI_ENDPOINT']
    api_version = env_vars['API_VERSION']
    
    retry_count = 0
    max_retries = 3
    max_concurrent_tasks = 10
    
    logger.info(f"Starting Service Bus processor with model: {model_name}")
    logger.info(f"Graceful shutdown timeout: {SHUTDOWN_TIMEOUT}s")
    
    while retry_count <= max_retries and not shutdown_event.is_set():
        try:
            async with AsyncServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
                receiver = client.get_queue_receiver(queue_name=QUEUE_NAME)
                async with receiver:
                    logger.info("Service Bus consumer started successfully (async)")
                    retry_count = 0
                    tasks = set()
                    
                    while not shutdown_event.is_set():
                        try:
                            messages = await receiver.receive_messages(max_message_count=BATCH_SIZE, max_wait_time=5)
                            if not messages:
                                await asyncio.sleep(2)
                                # Clean up any completed tasks during idle time
                                tasks = await cleanup_completed_tasks(tasks)
                                continue
                            
                            # Check for shutdown signal before processing new messages
                            if shutdown_event.is_set():
                                logger.info("Shutdown signal received, stopping message processing")
                                # Abandon all unprocessed messages
                                for msg in messages:
                                    await safe_abandon_message(receiver, msg)
                                break
                            
                            for msg in messages:
                                # Check shutdown signal before processing each message
                                if shutdown_event.is_set():
                                    logger.info("Shutdown signal received, abandoning remaining messages")
                                    await safe_abandon_message(receiver, msg)
                                    continue
                                
                                # Wait for available slot if we're at the limit
                                tasks = await wait_for_available_slot(tasks, max_concurrent_tasks)
                                
                                # Create new task for message processing
                                task = asyncio.create_task(
                                    process_message_async(msg, receiver, model_name, api_key, endpoint, api_version)
                                )
                                tasks.add(task)
                            
                            # Clean up completed tasks after processing batch
                            tasks = await cleanup_completed_tasks(tasks)
                            
                        except Exception as receive_error:
                            if shutdown_event.is_set():
                                logger.info("Shutdown in progress, skipping error recovery")
                                break
                            logger.error(f"Error receiving messages: {receive_error}")
                            await asyncio.sleep(5)
                            # Clean up tasks during error recovery
                            tasks = await cleanup_completed_tasks(tasks)
                    
                    # Graceful shutdown of remaining tasks
                    if tasks:
                        logger.info("Initiating graceful shutdown of in-flight tasks")
                        graceful_complete = await graceful_shutdown_tasks(tasks)
                        if graceful_complete:
                            logger.info("All in-flight tasks completed successfully")
                        else:
                            logger.warning("Some tasks were forcefully cancelled during shutdown")
                    
                    logger.info("Service Bus consumer shutdown completed")
                    return  # Exit the retry loop on graceful shutdown
                    
        except Exception as connection_error:
            if shutdown_event.is_set():
                logger.info("Shutdown signal received during connection error, stopping retries")
                break
                
            retry_count += 1
            logger.error(f"Service Bus connection failed (attempt {retry_count}/{max_retries + 1}): {connection_error}")
            if retry_count <= max_retries:
                wait_time = min(30, 2 ** retry_count)
                logger.info(f"Retrying connection in {wait_time} seconds...")
                
                # Wait with shutdown check
                for _ in range(wait_time):
                    if shutdown_event.is_set():
                        logger.info("Shutdown signal received during retry wait, aborting")
                        return
                    await asyncio.sleep(1)
            else:
                logger.critical("Max retries exceeded. Service Bus consumer stopping.")
                raise

def run_service_bus_processor():
    # Setup signal handlers before starting
    setup_signal_handlers()
    
    try:
        asyncio.run(run_service_bus_processor_async())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Service Bus consumer stopped")
