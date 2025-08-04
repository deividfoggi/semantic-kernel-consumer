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

# Set these as environment variables for security
SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')
BATCH_SIZE = 10  # Number of messages to receive in a batch

if not SERVICE_BUS_CONNECTION_STR or not QUEUE_NAME:
    raise ValueError("Please set SERVICE_BUS_CONNECTION_STR and SERVICE_BUS_QUEUE_NAME environment variables.")

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def safe_abandon_message(receiver, message):
    """
    Safely abandon a message with proper exception handling.
    Ensures the consumer continues working even if abandon fails.
    """
    try:
        asyncio.create_task(receiver.abandon_message(message))
        logger.info("Message abandoned successfully")
    except Exception as abandon_error:
        logger.error(f"Failed to abandon message (this won't stop the consumer): {abandon_error}")

def safe_complete_message(receiver, message):
    """
    Safely complete a message with proper exception handling.
    """
    try:
        asyncio.create_task(receiver.complete_message(message))
        logger.info("Message completed successfully")
    except Exception as complete_error:
        logger.error(f"Failed to complete message: {complete_error}")
        safe_abandon_message(receiver, message)

async def process_message_async(message, receiver, model_name, api_key, endpoint):
    try:
        body_bytes = b"".join(message.body)
        content = json.loads(body_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON message: {e}")
        await receiver.abandon_message(message)
        return

    prompt_processor = PromptProcessor(model_name, api_key, endpoint)
    try:
        result = await prompt_processor.process_payload(content)
        logger.info(f"Evaluation result: {result}")
        await receiver.complete_message(message)
    except Exception as processing_error:
        logger.error(f"Failed to process message: {processing_error}")
        await receiver.abandon_message(message)


async def run_service_bus_processor_async():
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')
    api_key = os.getenv('OPENAI_API_KEY', 'your-api-key')
    endpoint = os.getenv('OPENAI_ENDPOINT')
    retry_count = 0
    max_retries = 3
    max_concurrent_tasks = 10
    
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
                                continue
                            for msg in messages:
                                # Limit concurrency
                                while len(tasks) >= max_concurrent_tasks:
                                    _done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                                task = asyncio.create_task(process_message_async(msg, receiver, model_name, api_key, endpoint))
                                tasks.add(task)
                            # Clean up finished tasks
                            done, tasks = await asyncio.wait(tasks, timeout=0, return_when=asyncio.ALL_COMPLETED)
                        except Exception as receive_error:
                            logger.error(f"Error receiving messages: {receive_error}")
                            await asyncio.sleep(5)
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
