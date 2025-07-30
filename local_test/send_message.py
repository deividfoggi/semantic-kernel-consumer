import os
import json
import uuid
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')

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

def send_message_to_queue(message_body):
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            message = ServiceBusMessage(message_body)
            sender.send_messages(message)
            logger.info(f"Sent message: {message_body}")

if __name__ == "__main__":
    # a json payload to be sent to the queue
    payload = {
        "id": str(uuid.uuid4()),
        "essay": "The Brazil has been discovered by Pedro Alvares Cabral in 1500. It is a country with a rich history and diverse culture. It is known for its beautiful landscapes, vibrant cities, and passionate people.",
        "skills_list": [
            {
                "name": "coesao",
                "description": "Avalia a coesão textual do ensaio.",
                "score": "1 a 10"
            },
            {
                "name": "vocabulario",
                "description": "Avalia o uso do vocabulário no ensaio.",
                "score": "1 a 10"
            },
            {
                "name": "ortografia",
                "description": "Avalia a ortografia utilizada no ensaio.",
                "score": "1 a 10"
            }
        ]
    }
    test_message = json.dumps(payload)
    send_message_to_queue(test_message)
