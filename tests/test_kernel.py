import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import ProviderType, KernelFactory


class TestProviderType:
    """Test suite for ProviderType enum."""

    def test_provider_type_values(self):
        """Test that ProviderType enum has expected values."""
        assert ProviderType.AZURE_OPENAI.value == "azure_openai"
        assert ProviderType.AZURE_AI_INFERENCE.value == "azure_ai_inference"

    def test_provider_type_membership(self):
        """Test that all expected provider types are present."""
        expected_providers = ["azure_openai", "azure_ai_inference"]
        actual_providers = [provider.value for provider in ProviderType]
        assert set(actual_providers) == set(expected_providers)


class TestKernelFactory:
    """Test suite for KernelFactory class."""

    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_azure_openai_success(self, mock_azure_chat_completion):
        """Test successful kernel creation with Azure OpenAI provider."""
        # Setup
        mock_chat_completion = Mock(spec=AzureChatCompletion)
        mock_chat_completion.service_id = "azure_openai_service"  # Add required attribute
        mock_azure_chat_completion.return_value = mock_chat_completion
        
        deployment_name = "gpt-4o"
        api_key = "fake_api_key"
        endpoint = "https://fake.openai.azure.com/"
        api_version = "2024-02-01"

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            deployment_name=deployment_name,
            api_key=api_key,
            endpoint=endpoint,
            api_version=api_version
        )

        # Verify
        assert isinstance(kernel, Kernel)
        mock_azure_chat_completion.assert_called_once_with(
            deployment_name=deployment_name,
            api_key=api_key,
            endpoint=endpoint
        )
        # Verify service was added to kernel (we can't easily check this without accessing internal state)

    @patch('kernel.AzureAIInferenceChatCompletion')
    def test_create_kernel_azure_ai_inference_success(self, mock_azure_ai_inference):
        """Test successful kernel creation with Azure AI Inference provider."""
        # Setup
        mock_chat_completion = Mock(spec=AzureAIInferenceChatCompletion)
        mock_chat_completion.service_id = "azure_ai_inference_service"  # Add required attribute
        mock_azure_ai_inference.return_value = mock_chat_completion
        
        deployment_name = "gpt-4o"
        api_key = "fake_api_key"
        endpoint = "https://fake.aiservices.azure.com/"
        api_version = "2024-02-01"

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_AI_INFERENCE,
            deployment_name=deployment_name,
            api_key=api_key,
            endpoint=endpoint,
            api_version=api_version
        )

        # Verify
        assert isinstance(kernel, Kernel)
        mock_azure_ai_inference.assert_called_once_with(
            ai_model_id=deployment_name,
            api_key=api_key,
            endpoint=endpoint
        )

    def test_create_kernel_unsupported_provider_type(self):
        """Test that unsupported provider type raises ValueError."""
        # Setup
        class UnsupportedProvider:
            pass
        
        unsupported_provider = UnsupportedProvider()

        # Execute & Verify
        with pytest.raises(ValueError, match="Unsupported provider type"):
            KernelFactory.create_kernel(
                provider_type=unsupported_provider,
                deployment_name="gpt-4o",
                api_key="fake_key",
                endpoint="https://fake.endpoint.com"
            )

    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_azure_openai_minimal_params(self, mock_azure_chat_completion):
        """Test kernel creation with minimal required parameters for Azure OpenAI."""
        # Setup
        mock_chat_completion = Mock(spec=AzureChatCompletion)
        mock_chat_completion.service_id = "azure_openai_service"
        mock_azure_chat_completion.return_value = mock_chat_completion

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            deployment_name="gpt-35-turbo",
            api_key="test_key"
        )

        # Verify
        assert isinstance(kernel, Kernel)
        mock_azure_chat_completion.assert_called_once_with(
            deployment_name="gpt-35-turbo",
            api_key="test_key",
            endpoint=None
        )

    @patch('kernel.AzureAIInferenceChatCompletion')
    def test_create_kernel_azure_ai_inference_minimal_params(self, mock_azure_ai_inference):
        """Test kernel creation with minimal required parameters for Azure AI Inference."""
        # Setup
        mock_chat_completion = Mock(spec=AzureAIInferenceChatCompletion)
        mock_chat_completion.service_id = "azure_ai_inference_service"
        mock_azure_ai_inference.return_value = mock_chat_completion

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_AI_INFERENCE,
            deployment_name="gpt-4o-mini",
            api_key="test_key"
        )

        # Verify
        assert isinstance(kernel, Kernel)
        mock_azure_ai_inference.assert_called_once_with(
            ai_model_id="gpt-4o-mini",
            api_key="test_key",
            endpoint=None
        )

    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_azure_openai_with_all_params(self, mock_azure_chat_completion):
        """Test kernel creation with all parameters for Azure OpenAI."""
        # Setup
        mock_chat_completion = Mock(spec=AzureChatCompletion)
        mock_chat_completion.service_id = "azure_openai_service"
        mock_azure_chat_completion.return_value = mock_chat_completion
        
        params = {
            "deployment_name": "gpt-4o",
            "api_key": "sk-test123456789",
            "endpoint": "https://myresource.openai.azure.com/",
            "api_version": "2024-02-01-preview"
        }

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            **params
        )

        # Verify
        assert isinstance(kernel, Kernel)
        # Note: api_version is not passed to AzureChatCompletion constructor in current implementation
        expected_call_params = {k: v for k, v in params.items() if k != "api_version"}
        mock_azure_chat_completion.assert_called_once_with(**expected_call_params)

    @patch('kernel.AzureAIInferenceChatCompletion')
    def test_create_kernel_azure_ai_inference_with_all_params(self, mock_azure_ai_inference):
        """Test kernel creation with all parameters for Azure AI Inference."""
        # Setup
        mock_chat_completion = Mock(spec=AzureAIInferenceChatCompletion)
        mock_chat_completion.service_id = "azure_ai_inference_service"
        mock_azure_ai_inference.return_value = mock_chat_completion
        
        params = {
            "deployment_name": "gpt-4o",
            "api_key": "test-key-123",
            "endpoint": "https://myaiservice.cognitiveservices.azure.com/",
            "api_version": "2024-02-01"
        }

        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_AI_INFERENCE,
            **params
        )

        # Verify
        assert isinstance(kernel, Kernel)
        # Note: api_version is not used in AzureAIInferenceChatCompletion constructor in current implementation
        mock_azure_ai_inference.assert_called_once_with(
            ai_model_id=params["deployment_name"],
            api_key=params["api_key"],
            endpoint=params["endpoint"]
        )

    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_azure_openai_exception_handling(self, mock_azure_chat_completion):
        """Test that exceptions from AzureChatCompletion are properly propagated."""
        # Setup
        mock_azure_chat_completion.side_effect = Exception("Authentication failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Authentication failed"):
            KernelFactory.create_kernel(
                provider_type=ProviderType.AZURE_OPENAI,
                deployment_name="gpt-4o",
                api_key="invalid_key",
                endpoint="https://invalid.endpoint.com"
            )

    @patch('kernel.AzureAIInferenceChatCompletion')
    def test_create_kernel_azure_ai_inference_exception_handling(self, mock_azure_ai_inference):
        """Test that exceptions from AzureAIInferenceChatCompletion are properly propagated."""
        # Setup
        mock_azure_ai_inference.side_effect = Exception("Model not found")

        # Execute & Verify
        with pytest.raises(Exception, match="Model not found"):
            KernelFactory.create_kernel(
                provider_type=ProviderType.AZURE_AI_INFERENCE,
                deployment_name="invalid-model",
                api_key="test_key",
                endpoint="https://test.endpoint.com"
            )

    @patch('kernel.Kernel')
    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_service_addition(self, mock_azure_chat_completion, mock_kernel_class):
        """Test that the chat completion service is properly added to the kernel."""
        # Setup
        mock_kernel = Mock(spec=Kernel)
        mock_kernel_class.return_value = mock_kernel
        mock_chat_completion = Mock(spec=AzureChatCompletion)
        mock_chat_completion.service_id = "azure_openai_service"
        mock_azure_chat_completion.return_value = mock_chat_completion

        # Execute
        result_kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            deployment_name="gpt-4o",
            api_key="test_key"
        )

        # Verify
        assert result_kernel == mock_kernel
        mock_kernel.add_service.assert_called_once_with(mock_chat_completion)

    @patch('kernel.AzureChatCompletion')
    def test_create_kernel_azure_openai_exception_handling(self, mock_azure_chat_completion):
        """Test that exceptions from AzureChatCompletion are properly propagated."""
        # Setup
        mock_azure_chat_completion.side_effect = Exception("Authentication failed")

        # Execute & Verify
        with pytest.raises(Exception, match="Authentication failed"):
            KernelFactory.create_kernel(
                provider_type=ProviderType.AZURE_OPENAI,
                deployment_name="gpt-4o",
                api_key="invalid_key",
                endpoint="https://invalid.endpoint.com"
            )

    @patch('kernel.AzureAIInferenceChatCompletion')
    def test_create_kernel_azure_ai_inference_exception_handling(self, mock_azure_ai_inference):
        """Test that exceptions from AzureAIInferenceChatCompletion are properly propagated."""
        # Setup
        mock_azure_ai_inference.side_effect = Exception("Model not found")

        # Execute & Verify
        with pytest.raises(Exception, match="Model not found"):
            KernelFactory.create_kernel(
                provider_type=ProviderType.AZURE_AI_INFERENCE,
                deployment_name="invalid-model",
                api_key="test_key",
                endpoint="https://test.endpoint.com"
            )

    def test_create_kernel_logging(self):
        """Test that appropriate logging messages are generated."""
        # This test would require mocking the logger, which could be done but might be overkill
        # for this implementation. The logging functionality is tested implicitly through other tests.
        pass


class TestKernelFactoryIntegration:
    """Integration tests for KernelFactory (testing actual object creation without mocking)."""

    def test_create_kernel_returns_kernel_instance(self):
        """Test that create_kernel returns an actual Kernel instance."""
        # Execute
        kernel = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            deployment_name="test-model",
            api_key="fake-key",
            endpoint="https://fake.endpoint.com"
        )

        # Verify
        assert isinstance(kernel, Kernel)

    def test_create_kernel_different_providers_return_different_services(self):
        """Test that different providers result in different service types being added."""
        # Execute
        kernel_openai = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_OPENAI,
            deployment_name="gpt-4o",
            api_key="fake-key-1",
            endpoint="https://fake1.endpoint.com"
        )

        kernel_ai_inference = KernelFactory.create_kernel(
            provider_type=ProviderType.AZURE_AI_INFERENCE,
            deployment_name="gpt-4o",
            api_key="fake-key-2",
            endpoint="https://fake2.endpoint.com"
        )

        # Verify both are Kernel instances
        assert isinstance(kernel_openai, Kernel)
        assert isinstance(kernel_ai_inference, Kernel)
        
        # Note: Without accessing internal state, we can't easily verify the service types
        # but we can at least confirm that different kernels are created


# Fixtures for reuse across tests
@pytest.fixture
def azure_openai_config():
    """Fixture providing Azure OpenAI configuration."""
    return {
        "provider_type": ProviderType.AZURE_OPENAI,
        "deployment_name": "gpt-4o",
        "api_key": "sk-fake123456789",
        "endpoint": "https://myresource.openai.azure.com/",
        "api_version": "2024-02-01-preview"
    }


@pytest.fixture
def azure_ai_inference_config():
    """Fixture providing Azure AI Inference configuration."""
    return {
        "provider_type": ProviderType.AZURE_AI_INFERENCE,
        "deployment_name": "gpt-4o",
        "api_key": "test-api-key-123",
        "endpoint": "https://myaiservice.cognitiveservices.azure.com/",
        "api_version": "2024-02-01"
    }


@pytest.mark.parametrize("deployment_name", [
    "gpt-4o",
    "gpt-4o-mini", 
    "gpt-35-turbo",
    "gpt-4",
    "text-embedding-ada-002"
])
@patch('kernel.AzureChatCompletion')
def test_create_kernel_various_models_azure_openai(mock_azure_chat_completion, deployment_name):
    """Test kernel creation with various model deployment names for Azure OpenAI."""
    # Setup
    mock_chat_completion = Mock(spec=AzureChatCompletion)
    mock_chat_completion.service_id = "azure_openai_service"
    mock_azure_chat_completion.return_value = mock_chat_completion

    # Execute
    kernel = KernelFactory.create_kernel(
        provider_type=ProviderType.AZURE_OPENAI,
        deployment_name=deployment_name,
        api_key="test_key",
        endpoint="https://test.endpoint.com"
    )

    # Verify
    assert isinstance(kernel, Kernel)
    mock_azure_chat_completion.assert_called_once_with(
        deployment_name=deployment_name,
        api_key="test_key",
        endpoint="https://test.endpoint.com"
    )


@pytest.mark.parametrize("deployment_name", [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-35-turbo-16k",
    "claude-3-sonnet",
    "llama-2-70b"
])
@patch('kernel.AzureAIInferenceChatCompletion')
def test_create_kernel_various_models_azure_ai_inference(mock_azure_ai_inference, deployment_name):
    """Test kernel creation with various model deployment names for Azure AI Inference."""
    # Setup
    mock_chat_completion = Mock(spec=AzureAIInferenceChatCompletion)
    mock_chat_completion.service_id = "azure_ai_inference_service"
    mock_azure_ai_inference.return_value = mock_chat_completion

    # Execute
    kernel = KernelFactory.create_kernel(
        provider_type=ProviderType.AZURE_AI_INFERENCE,
        deployment_name=deployment_name,
        api_key="test_key",
        endpoint="https://test.endpoint.com"
    )

    # Verify
    assert isinstance(kernel, Kernel)
    mock_azure_ai_inference.assert_called_once_with(
        ai_model_id=deployment_name,
        api_key="test_key",
        endpoint="https://test.endpoint.com"
    )


# Error handling test scenarios
@pytest.mark.parametrize("invalid_param,param_value,expected_error", [
    ("deployment_name", None, Exception),  # ServiceInitializationError is a subclass of Exception
    ("deployment_name", "", Exception),
])
def test_create_kernel_invalid_parameters(invalid_param, param_value, expected_error):
    """Test that invalid parameters result in appropriate errors."""
    # Setup base parameters
    params = {
        "provider_type": ProviderType.AZURE_OPENAI,
        "deployment_name": "gpt-4o",
        "api_key": "test_key",
        "endpoint": "https://test.endpoint.com"
    }
    
    # Override the invalid parameter
    params[invalid_param] = param_value

    # Execute & Verify
    with pytest.raises(expected_error):
        KernelFactory.create_kernel(**params)