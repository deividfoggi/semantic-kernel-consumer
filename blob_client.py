import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
import dotenv

dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Import DefaultAzureCredential at module level for proper mocking in tests
try:
    from azure.identity import DefaultAzureCredential
    _default_credential_available = True
except ImportError:
    DefaultAzureCredential = None
    _default_credential_available = False

class AzureBlobTemplateClient:
    """
    Client for retrieving prompt templates from Azure Blob Storage.
    Uses connection string from environment variable for local dev,
    or managed identity when deployed to Azure.
    Container name can be provided as an argument or via PROMPT_TEMPLATE_CONTAINER_NAME env var.
    """
    def __init__(self, account_name: str = None, container_name: str = None):
        # Get container name from argument or environment
        if container_name is None:
            container_name = os.getenv("PROMPT_TEMPLATE_CONTAINER_NAME")
        if not container_name:
            raise ValueError("Container name must be provided either as an argument or via PROMPT_TEMPLATE_CONTAINER_NAME environment variable.")
        
        self.container_name = container_name
        self.blob_service_client = None
        self.container_client = None
        
        # Get connection string from environment
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
        if connection_string:
            # Use connection string for local development
            logger.info("Using Azure Storage connection string")
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        else:
            # Use managed identity for production
            account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
            if account_url is None and account_name is not None:
                account_url = f"https://{account_name}.blob.core.windows.net"
            
            if account_url is None:
                raise ValueError("Account URL must be provided via AZURE_STORAGE_ACCOUNT_URL environment variable or account_name parameter when not using connection string authentication.")
            
            logger.info("Using Azure managed identity")
            if not _default_credential_available:
                logger.error("Azure identity library not available. Please install azure-identity package.")
                raise ImportError("azure-identity package is required for managed identity authentication")
            
            try:
                credential = DefaultAzureCredential()
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
                self.container_client = self.blob_service_client.get_container_client(self.container_name)
                self.account_name = account_name
            except Exception as e:
                logger.error(f"Failed to authenticate with managed identity: {e}")
                raise

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
            blob_data = blob_client.download_blob().content_as_text(encoding='utf-8')
            logger.info(f"Successfully downloaded blob: {blob_name}")
            return blob_data
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
