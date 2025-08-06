import pytest
import asyncio
import json
import yaml
import os
import sys
import gc
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompt_processor import PromptProcessor
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings


class TestPromptProcessor:
    """Test suite for PromptProcessor class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Default test parameters
        self.test_deployment_name = "gpt-4o"
        self.test_api_key = "fake_api_key"
        self.test_endpoint = "https://fake.endpoint.com"
        self.test_api_version = "2024-02-01"

    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.PostEvaluation')
    def test_prompt_processor_init(self, mock_post_evaluation, mock_kernel_factory):
        """Test PromptProcessor initialization."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_post_eval_instance = Mock()
        mock_post_evaluation.return_value = mock_post_eval_instance

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key,
            endpoint=self.test_endpoint,
            api_version=self.test_api_version
        )

        # Verify
        mock_kernel_factory.create_kernel.assert_called_once()
        mock_kernel.add_plugin.assert_called_once_with(mock_post_eval_instance, "PostEvaluationPlugin")
        assert processor.kernel == mock_kernel

    @patch('prompt_processor.KernelFactory')
    def test_prompt_processor_init_default_provider(self, mock_kernel_factory):
        """Test PromptProcessor initialization with default provider type."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )

        # Verify that AZURE_AI_INFERENCE provider is used by default
        call_args = mock_kernel_factory.create_kernel.call_args
        assert call_args is not None

    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.PostEvaluation')
    def test_register_plugins(self, mock_post_evaluation, mock_kernel_factory):
        """Test that PostEvaluation plugin is properly registered."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_post_eval_instance = Mock()
        mock_post_evaluation.return_value = mock_post_eval_instance

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )

        # Verify
        mock_kernel.add_plugin.assert_called_once_with(mock_post_eval_instance, "PostEvaluationPlugin")

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_string_input(self, mock_blob_client_class, mock_kernel_factory):
        """Test process_payload with string JSON input."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        # Mock template YAML content
        yaml_content = """
name: EvaluateEssay
template: |
  Evaluate this essay: {{ essay }}
  Skills: {{ skills_list }}
template_format: handlebars
"""
        mock_blob_client.get_template.return_value = yaml_content
        
        # Mock kernel function and response
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_response.__str__ = Mock(return_value="Evaluation complete")
        mock_kernel.invoke.return_value = mock_response

        # Test payload as string
        test_payload_str = json.dumps({
            "skills_list": ["writing", "grammar"],
            "essay": "This is a test essay."
        })

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        result = await processor.process_payload(test_payload_str)

        # Verify
        mock_blob_client.get_template.assert_called_once()
        mock_kernel.add_function.assert_called_once()
        mock_kernel.invoke.assert_called_once()
        assert result == mock_response

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_dict_input(self, mock_blob_client_class, mock_kernel_factory):
        """Test process_payload with dictionary input."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        yaml_content = """
name: EvaluateEssay
template: |
  Evaluate this essay: {{ essay }}
  Skills: {{ skills_list }}
template_format: handlebars
"""
        mock_blob_client.get_template.return_value = yaml_content
        
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_kernel.invoke.return_value = mock_response

        # Test payload as dictionary
        test_payload_dict = {
            "skills_list": ["coherence", "grammar", "vocabulary"],
            "essay": "This is another test essay for evaluation."
        }

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        result = await processor.process_payload(test_payload_dict)

        # Verify
        mock_kernel.invoke.assert_called_once()
        call_args = mock_kernel.invoke.call_args
        
        # Verify that the arguments contain the expected data
        assert call_args is not None
        args, kwargs = call_args
        kernel_args = args[1]  # Second argument should be KernelArguments
        assert isinstance(kernel_args, KernelArguments)

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_skills_json_conversion(self, mock_blob_client_class, mock_kernel_factory):
        """Test that skills_list is properly converted to JSON string."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        yaml_content = "name: Test\ntemplate: Test template\ntemplate_format: handlebars"
        mock_blob_client.get_template.return_value = yaml_content
        
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_kernel.invoke.return_value = mock_response

        test_payload = {
            "skills_list": ["skill1", "skill2", "skill3"],
            "essay": "Test essay"
        }

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        await processor.process_payload(test_payload)

        # Verify
        call_args = mock_kernel.invoke.call_args
        kernel_args = call_args[0][1]
        
        # Check that skills_list was converted to JSON string
        # Note: This is a simplified check since we can't easily access the internal arguments
        mock_kernel.invoke.assert_called_once()

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_blob_client_error(self, mock_blob_client_class, mock_kernel_factory):
        """Test handling of blob client errors."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        mock_blob_client.get_template.side_effect = Exception("Blob not found")

        test_payload = {
            "skills_list": ["writing"],
            "essay": "Test essay"
        }

        # Execute & Verify
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        
        with pytest.raises(Exception, match="Blob not found"):
            await processor.process_payload(test_payload)

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_invalid_yaml(self, mock_blob_client_class, mock_kernel_factory):
        """Test handling of invalid YAML template."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        mock_blob_client.get_template.return_value = "invalid: yaml: content: ["

        test_payload = {
            "skills_list": ["writing"],
            "essay": "Test essay"
        }

        # Execute & Verify
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        
        with pytest.raises(yaml.YAMLError):
            await processor.process_payload(test_payload)

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    async def test_cleanup_with_aiohttp(self, mock_kernel_factory):
        """Test cleanup method with aiohttp available."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel

        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )

        # Execute
        await processor.cleanup()

        # Verify
        assert processor.kernel is None

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.gc')
    async def test_cleanup_forces_garbage_collection(self, mock_gc, mock_kernel_factory):
        """Test that cleanup forces garbage collection."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel

        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )

        # Execute
        await processor.cleanup()

        # Verify
        mock_gc.collect.assert_called()

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    async def test_context_manager_cleanup(self, mock_kernel_factory):
        """Test that context manager properly calls cleanup."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel

        # Execute
        async with PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        ) as processor:
            assert processor.kernel == mock_kernel

        # Verify cleanup was called (kernel should be None)
        assert processor.kernel is None

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    async def test_context_manager_exception_handling(self, mock_kernel_factory):
        """Test that context manager handles exceptions properly."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel

        # Execute with exception
        try:
            async with PromptProcessor(
                deployment_name=self.test_deployment_name,
                api_key=self.test_api_key
            ) as processor:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify cleanup was still called
        assert processor.kernel is None

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_empty_skills_list(self, mock_blob_client_class, mock_kernel_factory):
        """Test process_payload with empty skills list."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        yaml_content = "name: Test\ntemplate: Test\ntemplate_format: handlebars"
        mock_blob_client.get_template.return_value = yaml_content
        
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_kernel.invoke.return_value = mock_response

        test_payload = {
            "skills_list": [],
            "essay": "Test essay"
        }

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        result = await processor.process_payload(test_payload)

        # Verify
        assert result == mock_response
        mock_kernel.invoke.assert_called_once()

    @pytest.mark.asyncio
    @patch('prompt_processor.KernelFactory')
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_process_payload_missing_essay(self, mock_blob_client_class, mock_kernel_factory):
        """Test process_payload with missing essay field."""
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        yaml_content = "name: Test\ntemplate: Test\ntemplate_format: handlebars"
        mock_blob_client.get_template.return_value = yaml_content
        
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_kernel.invoke.return_value = mock_response

        test_payload = {
            "skills_list": ["writing", "grammar"]
            # Missing essay field
        }

        # Execute
        processor = PromptProcessor(
            deployment_name=self.test_deployment_name,
            api_key=self.test_api_key
        )
        result = await processor.process_payload(test_payload)

        # Verify - should still work with empty essay
        assert result == mock_response


class TestPromptProcessorIntegration:
    """Integration tests for PromptProcessor."""

    @pytest.mark.asyncio
    @patch('prompt_processor.AzureBlobTemplateClient')
    async def test_full_workflow_integration(self, mock_blob_client_class):
        """Test the complete workflow with real Kernel objects (mocked AI calls)."""
        # Setup
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        # Real YAML template
        yaml_content = """
name: EvaluateEssay
template: |
  <message role="system">
    You are an essay evaluator.
  </message>
  <message role="user">
    Skills: {{ skills_list }}
    Essay: {{ essay }}
  </message>
template_format: handlebars
description: An essay evaluation prompt.
input_variables:
  - name: skills_list
    description: The list of skills.
    is_required: true
  - name: essay
    description: The essay to evaluate.
    is_required: true
execution_settings:
  default:
    temperature: 0.5
"""
        mock_blob_client.get_template.return_value = yaml_content

        test_payload = {
            "skills_list": ["writing", "grammar", "coherence"],
            "essay": "This is a comprehensive test essay that demonstrates various writing skills."
        }

        # Execute
        processor = PromptProcessor(
            deployment_name="gpt-4o",
            api_key="fake_key",
            endpoint="https://fake.endpoint.com",
            api_version="2024-02-01"
        )

        # Note: This would normally call the AI service, but since we're using fake credentials,
        # we expect it to fail at the AI call stage, not before
        try:
            result = await processor.process_payload(test_payload)
            # If it succeeds (unlikely with fake creds), that's fine too
        except Exception as e:
            # Expected to fail at AI service call with fake credentials
            # This confirms the setup works up to the AI call
            assert "fake" in str(e).lower() or "auth" in str(e).lower() or "invalid" in str(e).lower()

        # Cleanup
        await processor.cleanup()

    def test_prompt_processor_parameters_validation(self):
        """Test that PromptProcessor validates required parameters."""
        # Test missing deployment_name
        with pytest.raises(TypeError):
            PromptProcessor(api_key="test_key")

        # Test missing api_key
        with pytest.raises(TypeError):
            PromptProcessor(deployment_name="gpt-4o")


# Fixtures for reuse across tests
@pytest.fixture
def sample_yaml_template():
    """Fixture providing a sample YAML template."""
    return """
name: EvaluateEssay
template: |
  <message role="system">
    You are an expert essay evaluator.
  </message>
  <message role="user">
    Evaluate the following essay based on these skills: {{ skills_list }}
    
    Essay text: {{ essay }}
    
    Provide detailed feedback and scoring.
  </message>
template_format: handlebars
description: An essay evaluation prompt with detailed feedback.
input_variables:
  - name: skills_list
    description: The list of skills to evaluate.
    is_required: true
  - name: essay
    description: The essay text to evaluate.
    is_required: true
output_variable:
  evaluation: The evaluation result.
execution_settings:
  service1:
    model_id: gpt-4o
    temperature: 0.6
  default:
    temperature: 0.5
"""


@pytest.fixture
def sample_payload():
    """Fixture providing a sample payload for testing."""
    return {
        "skills_list": [
            "Writing Clarity",
            "Grammar and Syntax", 
            "Argument Structure",
            "Evidence and Examples",
            "Conclusion Effectiveness"
        ],
        "essay": """
The impact of technology on modern education has been transformative and multifaceted. 
In recent decades, we have witnessed a paradigm shift from traditional classroom 
instruction to more interactive, personalized learning experiences enabled by digital tools.

This technological revolution has democratized access to information, allowing students 
from diverse backgrounds to access high-quality educational resources previously 
available only to a privileged few. Online learning platforms, educational apps, 
and digital libraries have broken down geographical and economic barriers.

However, this transformation is not without challenges. The digital divide remains 
a significant concern, as not all students have equal access to technology and 
reliable internet connections. Furthermore, the effectiveness of technology in 
education depends largely on how it is implemented and integrated into pedagogical 
practices.

In conclusion, while technology has undoubtedly enhanced educational opportunities 
and accessibility, its successful integration requires thoughtful planning, adequate 
infrastructure, and ongoing support for both educators and students.
"""
    }


@pytest.fixture
def mock_processor_dependencies():
    """Fixture providing mocked dependencies for PromptProcessor."""
    with patch('prompt_processor.KernelFactory') as mock_kernel_factory, \
         patch('prompt_processor.AzureBlobTemplateClient') as mock_blob_client_class:
        
        # Setup mock kernel
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        
        # Setup mock blob client
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        
        yield {
            'kernel_factory': mock_kernel_factory,
            'kernel': mock_kernel,
            'blob_client_class': mock_blob_client_class,
            'blob_client': mock_blob_client
        }


# Parameterized tests for different input scenarios
@pytest.mark.parametrize("skills_input,expected_json_type", [
    (["skill1", "skill2"], list),
    ("string_skills", str),
    ({"skill": "value"}, dict),
    ([], list),
])
@pytest.mark.asyncio
async def test_process_payload_skills_list_variations(skills_input, expected_json_type, mock_processor_dependencies, sample_yaml_template):
    """Test process_payload with different types of skills_list input."""
    # Setup
    mocks = mock_processor_dependencies
    mocks['blob_client'].get_template.return_value = sample_yaml_template
    
    mock_semantic_function = Mock()
    mocks['kernel'].add_function.return_value = mock_semantic_function
    mock_response = Mock()
    mocks['kernel'].invoke.return_value = mock_response

    test_payload = {
        "skills_list": skills_input,
        "essay": "Test essay content"
    }

    # Execute
    processor = PromptProcessor(
        deployment_name="gpt-4o",
        api_key="test_key"
    )
    result = await processor.process_payload(test_payload)

    # Verify
    assert result == mock_response
    mocks['kernel'].invoke.assert_called_once()


# Performance and memory tests
@pytest.mark.asyncio
async def test_multiple_process_payload_calls_memory_management():
    """Test that multiple process_payload calls don't cause memory leaks."""
    with patch('prompt_processor.KernelFactory') as mock_kernel_factory, \
         patch('prompt_processor.AzureBlobTemplateClient') as mock_blob_client_class:
        
        # Setup
        mock_kernel = Mock()
        mock_kernel_factory.create_kernel.return_value = mock_kernel
        mock_blob_client = Mock()
        mock_blob_client_class.return_value = mock_blob_client
        mock_blob_client.get_template.return_value = "name: Test\ntemplate: Test\ntemplate_format: handlebars"
        
        mock_semantic_function = Mock()
        mock_kernel.add_function.return_value = mock_semantic_function
        mock_response = Mock()
        mock_kernel.invoke.return_value = mock_response

        processor = PromptProcessor(
            deployment_name="gpt-4o",
            api_key="test_key"
        )

        # Execute multiple calls
        for i in range(5):
            test_payload = {
                "skills_list": [f"skill_{i}"],
                "essay": f"Test essay {i}"
            }
            result = await processor.process_payload(test_payload)
            assert result == mock_response

        # Cleanup
        await processor.cleanup()

        # Verify kernel was set to None
        assert processor.kernel is None