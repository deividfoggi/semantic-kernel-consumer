"""
blob_client.py

A utility module for securely retrieving prompt templates from Azure Blob Storage.
Follows Azure SDK and Python best practices: managed identity, error handling, logging, and configuration.
"""
import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, AzureError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class AzureBlobTemplateClient:
    """
    Client for retrieving prompt templates from Azure Blob Storage.
    Uses connection string from environment variable for local dev,
    or managed identity when deployed to Azure.
    Container name can be provided as an argument or via PROMPT_TEMPLATE_CONTAINER_NAME env var.
    """
    def __init__(self, container_name: str = None):
        # Allow container name from env var if not provided
        if container_name is None:
            container_name = os.getenv("PROMPT_TEMPLATE_CONTAINER_NAME")
            if not container_name:
                logger.error("PROMPT_TEMPLATE_CONTAINER_NAME environment variable is not set and no container_name was provided.")
                raise ValueError("Container name must be provided either as an argument or via PROMPT_TEMPLATE_CONTAINER_NAME environment variable.")
        # Use connection string from env for local dev, otherwise use default creds
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            self.blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            logger.info("Using connection string for Azure Blob Storage authentication.")
        else:
            # Use DefaultAzureCredential for managed identity (requires azure-identity)
            try:
                from azure.identity import DefaultAzureCredential
                self.blob_service_client = BlobServiceClient(
                    account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
                    credential=DefaultAzureCredential()
                )
                logger.info("Using managed identity for Azure Blob Storage authentication.")
            except Exception as e:
                logger.error("Failed to authenticate to Azure Blob Storage: %s", e)
                raise
        self.container_client = self.blob_service_client.get_container_client(container_name)

    def get_template(self, blob_name: str = None) -> str:
        """
        Download and return the contents of a template blob as a string.
        If blob_name is not provided, it is read from the environment variable PROMPT_TEMPLATE_BLOB_NAME.
        Handles errors and logs appropriately.
        """
        if blob_name is None:
            blob_name = os.getenv("PROMPT_TEMPLATE_BLOB_NAME")
            if not blob_name:
                logger.error("PROMPT_TEMPLATE_BLOB_NAME environment variable is not set and no blob_name was provided.")
                raise ValueError("Template blob name must be provided either as an argument or via PROMPT_TEMPLATE_BLOB_NAME environment variable.")
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_data = blob_client.download_blob().readall()
            logger.info(f"Successfully downloaded blob: {blob_name}")
            return blob_data.decode('utf-8')
        except ResourceNotFoundError:
            logger.error(f"Blob not found: {blob_name}")
            raise FileNotFoundError(f"Template blob '{blob_name}' not found.")
        except AzureError as e:
            logger.error(f"Azure error while downloading blob '{blob_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

# Usage example (should be in your main or service code):
# from blob_client import AzureBlobTemplateClient
# client = AzureBlobTemplateClient()  # Uses PROMPT_TEMPLATE_CONTAINER_NAME env var
# template = client.get_template()  # Uses PROMPT_TEMPLATE_BLOB_NAME env var
# print(template)
