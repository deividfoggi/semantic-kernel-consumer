import os
import time
import asyncio
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from essay_evaluator import EssayEvaluator

# Set these as environment variables for security
SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')
BATCH_SIZE = 10  # Number of messages to receive in a batch

if not SERVICE_BUS_CONNECTION_STR or not QUEUE_NAME:
    raise ValueError("Please set SERVICE_BUS_CONNECTION_STR and SERVICE_BUS_QUEUE_NAME environment variables.")

def process_message(message, model_name, api_key, endpoint, prompt_path):
    try:
        content = message.body_as_str()
    except AttributeError:
        content = b''.join(message.body).decode('utf-8', errors='replace')
    print(f"Processing message: {content}")

    # Create a new KernelWrapper and EssayEvaluator for each message
    essay_evaluator = EssayEvaluator(model_name, api_key, endpoint)
    result = asyncio.run(essay_evaluator.evaluate_essay(content, prompt_path))
    print(f"Evaluation result: {result}")


def run_service_bus_processor():
    model_name = os.getenv('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')
    api_key = os.getenv('OPENAI_API_KEY', 'your-api-key')
    endpoint = os.getenv('OPENAI_ENDPOINT')
    prompt_path = os.getenv('PROMPT_TEMPLATE_PATH', 'prompt_templates/essay.yaml')
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
        receiver = client.get_queue_receiver(queue_name=QUEUE_NAME)
        with receiver:
            while True:
                messages = receiver.receive_messages(max_message_count=BATCH_SIZE, max_wait_time=5)
                if not messages:
                    # No messages, wait before polling again
                    time.sleep(2)
                    continue
                for msg in messages:
                    try:
                        process_message(msg, model_name, api_key, endpoint, prompt_path)
                        receiver.complete_message(msg)
                    except Exception as e:
                        print(f"Failed to process message: {e}")
                        receiver.abandon_message(msg)
