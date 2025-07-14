import os
import json
import uuid
from azure.servicebus import ServiceBusClient, ServiceBusMessage

SERVICE_BUS_CONNECTION_STR = os.getenv('SERVICE_BUS_CONNECTION_STR')
QUEUE_NAME = os.getenv('SERVICE_BUS_QUEUE_NAME')

if not SERVICE_BUS_CONNECTION_STR or not QUEUE_NAME:
    raise ValueError("Please set SERVICE_BUS_CONNECTION_STR and SERVICE_BUS_QUEUE_NAME environment variables.")

def send_message_to_queue(message_body):
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STR) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            message = ServiceBusMessage(message_body)
            sender.send_messages(message)
            print(f"Sent message: {message_body}")

if __name__ == "__main__":
    test_message = "In 1500, Portuguese explorer Pedro Álvares Cabral discovered Brazil while sailing to India, ahahahahah. He landed on the coast, claiming the land for Portugal. This marked the beginning of European colonization in South America, shaping Brazil’s culture, language, and history through centuries of exploration, trade, and transformation."
    send_message_to_queue(test_message)
