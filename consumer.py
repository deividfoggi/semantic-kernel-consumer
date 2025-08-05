import os
import time
import dotenv
import asyncio
import logging
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

    try:
        prompt_processor = PromptProcessor(model_name, api_key, endpoint, api_version)
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
    
    while retry_count <= max_retries:
        try:
            async with AsyncServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
                receiver = client.get_queue_receiver(queue_name=QUEUE_NAME)
                async with receiver:
                    logger.info("Service Bus consumer started successfully (async)")
                    retry_count = 0
                    tasks = set()
                    
                    while True:
                        try:
                            messages = await receiver.receive_messages(max_message_count=BATCH_SIZE, max_wait_time=5)
                            if not messages:
                                await asyncio.sleep(2)
                                # Clean up any completed tasks during idle time
                                tasks = await cleanup_completed_tasks(tasks)
                                continue
                            
                            for msg in messages:
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
                            logger.error(f"Error receiving messages: {receive_error}")
                            await asyncio.sleep(5)
                            # Clean up tasks during error recovery
                            tasks = await cleanup_completed_tasks(tasks)
                            
        except Exception as connection_error:
            retry_count += 1
            logger.error(f"Service Bus connection failed (attempt {retry_count}/{max_retries + 1}): {connection_error}")
            if retry_count <= max_retries:
                wait_time = min(30, 2 ** retry_count)
                logger.info(f"Retrying connection in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.critical("Max retries exceeded. Service Bus consumer stopping.")
                raise

def run_service_bus_processor():
    asyncio.run(run_service_bus_processor_async())
