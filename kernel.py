from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
import logging
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class ProviderType(Enum):
    AZURE_OPENAI = "azure_openai"
    AZURE_AI_INFERENCE = "azure_ai_inference"

class KernelFactory:
    @staticmethod
    def create_kernel(provider_type: ProviderType, deployment_name: str, api_key: str, endpoint: str = None) -> Kernel:
        """Create a kernel with the specified AI provider."""
        kernel = Kernel()
        
        if provider_type == ProviderType.AZURE_OPENAI:
            chat_completion = AzureChatCompletion(
                deployment_name=deployment_name,
                api_key=api_key,
                endpoint=endpoint
            )
            kernel.add_service(chat_completion)
            logger.info(f"Created kernel with Azure OpenAI provider: {deployment_name}")
            
        elif provider_type == ProviderType.AZURE_AI_INFERENCE:
            chat_completion = AzureAIInferenceChatCompletion(
                ai_model_id=deployment_name,
                api_key=api_key,
                endpoint=endpoint
            )
            kernel.add_service(chat_completion)
            logger.info(f"Created kernel with Azure AI Inference provider: {deployment_name}")
            
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        return kernel