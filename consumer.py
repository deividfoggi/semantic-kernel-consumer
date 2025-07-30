import os
import time
import asyncio
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from prompt_processor import PromptProcessor
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
        receiver.abandon_message(message)
        logger.info("Message abandoned successfully")
    except Exception as abandon_error:
        # Log the error but don't let it crash the consumer
        logger.error(f"Failed to abandon message (this won't stop the consumer): {abandon_error}")
        # Optionally, you could implement retry logic here or send to a dead letter queue

def safe_complete_message(receiver, message):
    """
    Safely complete a message with proper exception handling.
    """
    try:
        receiver.complete_message(message)
        logger.info("Message completed successfully")
    except Exception as complete_error:
        logger.error(f"Failed to complete message: {complete_error}")
        # If completion fails, try to abandon the message
        safe_abandon_message(receiver, message)

def process_message(message, model_name, api_key, endpoint):
    try:
        body_bytes = b"".join(message.body)
        content = json.loads(body_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON message: {e}")
        return

    # Create a new KernelWrapper and PromptProcessor for each message
    prompt_processor = PromptProcessor(model_name, api_key, endpoint)
    result = asyncio.run(prompt_processor.process_payload(content))
    logger.info(f"Evaluation result: {result}")


def run_service_bus_processor():
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')
    api_key = os.getenv('OPENAI_API_KEY', 'your-api-key')
    endpoint = os.getenv('OPENAI_ENDPOINT')
    
    retry_count = 0
    max_retries = 3
    
    while retry_count <= max_retries:
        try:
            with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
                receiver = client.get_queue_receiver(queue_name=QUEUE_NAME)
                with receiver:
                    logger.info("Service Bus consumer started successfully")
                    retry_count = 0  # Reset retry count on successful connection
                    
                    while True:
                        try:
                            messages = receiver.receive_messages(max_message_count=BATCH_SIZE, max_wait_time=5)
                            if not messages:
                                # No messages, wait before polling again
                                time.sleep(2)
                                continue
                                
                            for msg in messages:
                                try:
                                    process_message(msg, model_name, api_key, endpoint)
                                    safe_complete_message(receiver, msg)
                                except Exception as processing_error:
                                    logger.error(f"Failed to process message: {processing_error}")
                                    safe_abandon_message(receiver, msg)
                                    
                        except Exception as receive_error:
                            logger.error(f"Error receiving messages: {receive_error}")
                            # Brief pause before trying to receive again
                            time.sleep(5)
                            
        except Exception as connection_error:
            retry_count += 1
            logger.error(f"Service Bus connection failed (attempt {retry_count}/{max_retries + 1}): {connection_error}")
            
            if retry_count <= max_retries:
                wait_time = min(30, 2 ** retry_count)  # Exponential backoff, max 30 seconds
                logger.info(f"Retrying connection in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.critical("Max retries exceeded. Service Bus consumer stopping.")
                raise
