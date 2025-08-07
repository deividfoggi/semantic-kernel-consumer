import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.storage.blob import BlobServiceClient
import sys

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blob_client import AzureBlobTemplateClient


class TestAzureBlobTemplateClient:
    """Test suite for AzureBlobTemplateClient class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear environment variables to ensure clean state
        env_vars_to_clear = [
            'AZURE_STORAGE_CONNECTION_STRING',
            'AZURE_STORAGE_ACCOUNT_URL',
            'PROMPT_TEMPLATE_CONTAINER_NAME',
            'PROMPT_TEMPLATE_BLOB_NAME'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_init_with_connection_string_and_container_name(self, mock_from_connection_string):
        """Test initialization with connection string and explicit container name."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_from_connection_string.return_value = mock_blob_service
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        
        # Verify
        mock_from_connection_string.assert_called_once_with('fake_connection_string')
        assert client.blob_service_client == mock_blob_service
        mock_blob_service.get_container_client.assert_called_once_with('test-container')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_init_with_connection_string_and_env_container(self, mock_from_connection_string):
        """Test initialization with connection string and container name from environment."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_from_connection_string.return_value = mock_blob_service
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        os.environ['PROMPT_TEMPLATE_CONTAINER_NAME'] = 'env-container'
        
        # Execute
        client = AzureBlobTemplateClient()
        
        # Verify
        mock_from_connection_string.assert_called_once_with('fake_connection_string')
        mock_blob_service.get_container_client.assert_called_once_with('env-container')

    @patch('blob_client.DefaultAzureCredential')
    @patch('blob_client.BlobServiceClient')
    def test_init_with_managed_identity(self, mock_blob_service_client, mock_default_credential):
        """Test initialization with managed identity (DefaultAzureCredential)."""
        # Setup
        mock_credential = Mock()
        mock_default_credential.return_value = mock_credential
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_blob_service_client.return_value = mock_blob_service
        os.environ['AZURE_STORAGE_ACCOUNT_URL'] = 'https://test.blob.core.windows.net'
        os.environ['PROMPT_TEMPLATE_CONTAINER_NAME'] = 'test-container'
        
        # Execute
        client = AzureBlobTemplateClient()
        
        # Verify
        mock_default_credential.assert_called_once()
        mock_blob_service_client.assert_called_once_with(
            account_url='https://test.blob.core.windows.net',
            credential=mock_credential
        )
        mock_blob_service.get_container_client.assert_called_once_with('test-container')

    def test_init_no_container_name_raises_error(self):
        """Test that initialization without container name raises ValueError."""
        # Setup - no environment variables set
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Container name must be provided"):
            AzureBlobTemplateClient()

    @patch('blob_client.DefaultAzureCredential')
    def test_init_managed_identity_import_error(self, mock_default_credential):
        """Test initialization handles import error for DefaultAzureCredential."""
        # Setup
        mock_default_credential.side_effect = ImportError("azure-identity not installed")
        os.environ['AZURE_STORAGE_ACCOUNT_URL'] = 'https://test.blob.core.windows.net'
        os.environ['PROMPT_TEMPLATE_CONTAINER_NAME'] = 'test-container'
        
        # Execute & Verify
        with pytest.raises(ImportError):
            AzureBlobTemplateClient()

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_success_with_blob_name(self, mock_from_connection_string):
        """Test successful template retrieval with explicit blob name."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        mock_download_result = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value = mock_download_result
        mock_download_result.content_as_text.return_value = "test template content"
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        result = client.get_template(blob_name='test-template.yaml')
        
        # Verify
        assert result == "test template content"
        mock_container_client.get_blob_client.assert_called_once_with('test-template.yaml')
        mock_blob_client.download_blob.assert_called_once()
        mock_download_result.content_as_text.assert_called_once_with(encoding='utf-8')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_success_with_env_blob_name(self, mock_from_connection_string):
        """Test successful template retrieval with blob name from environment."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        mock_download_result = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value = mock_download_result
        mock_download_result.content_as_text.return_value = "env template content"
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        os.environ['PROMPT_TEMPLATE_BLOB_NAME'] = 'env-template.yaml'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        result = client.get_template()
        
        # Verify
        assert result == "env template content"
        mock_container_client.get_blob_client.assert_called_once_with('env-template.yaml')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_no_blob_name_raises_error(self, mock_from_connection_string):
        """Test that get_template without blob name raises ValueError."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_from_connection_string.return_value = mock_blob_service
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        
        # Verify
        with pytest.raises(ValueError, match="Template blob name must be provided"):
            client.get_template()

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_blob_not_found(self, mock_from_connection_string):
        """Test handling of ResourceNotFoundError when blob doesn't exist."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        
        # Verify
        with pytest.raises(FileNotFoundError, match="Template blob 'missing.yaml' not found"):
            client.get_template(blob_name='missing.yaml')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_azure_error(self, mock_from_connection_string):
        """Test handling of general AzureError during blob download."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.side_effect = AzureError("Azure service error")
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        
        # Verify
        with pytest.raises(AzureError, match="Azure service error"):
            client.get_template(blob_name='test.yaml')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_unexpected_error(self, mock_from_connection_string):
        """Test handling of unexpected errors during blob download."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.side_effect = RuntimeError("Unexpected error")
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        
        # Verify
        with pytest.raises(RuntimeError, match="Unexpected error"):
            client.get_template(blob_name='test.yaml')

    @patch('blob_client.BlobServiceClient.from_connection_string')
    def test_get_template_encoding_handling(self, mock_from_connection_string):
        """Test that the template is correctly decoded with UTF-8 encoding."""
        # Setup
        mock_blob_service = Mock(spec=BlobServiceClient)
        mock_container_client = Mock()
        mock_blob_client = Mock()
        mock_download_result = Mock()
        
        mock_from_connection_string.return_value = mock_blob_service
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value = mock_download_result
        mock_download_result.content_as_text.return_value = "UTF-8 content with special chars: ñáéíóú"
        
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
        
        # Execute
        client = AzureBlobTemplateClient(container_name='test-container')
        result = client.get_template(blob_name='utf8-template.yaml')
        
        # Verify
        assert result == "UTF-8 content with special chars: ñáéíóú"
        mock_download_result.content_as_text.assert_called_once_with(encoding='utf-8')


# Fixtures for reuse across tests
@pytest.fixture
def mock_blob_service_client():
    """Fixture providing a mocked BlobServiceClient."""
    with patch('blob_client.BlobServiceClient.from_connection_string') as mock:
        mock_service = Mock(spec=BlobServiceClient)
        mock.return_value = mock_service
        yield mock_service


# Example of parameterized test for different scenarios
@pytest.mark.parametrize("container_name,expected_container", [
    ("explicit-container", "explicit-container"),
    (None, "env-container"),  # When using environment variable
])
def test_container_name_scenarios(container_name, expected_container, mock_blob_service_client):
    """Test different ways of providing container name."""
    # Setup environment if needed
    if container_name is None:
        os.environ['PROMPT_TEMPLATE_CONTAINER_NAME'] = expected_container
    
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'fake_connection_string'
    
    # Execute
    if container_name:
        client = AzureBlobTemplateClient(container_name=container_name)
    else:
        client = AzureBlobTemplateClient()
    
    # Verify
    mock_blob_service_client.get_container_client.assert_called_once_with(expected_container)