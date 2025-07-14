from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class AIProviderBase:
    def add_to_kernel(self, kernel: Kernel):
        raise NotImplementedError("Implement in subclass")

class AzureOpenAIProvider(AIProviderBase):
    def __init__(self, deployment_name, api_key, endpoint=None):
        self.deployment_name = deployment_name
        self.api_key = api_key
        self.endpoint = endpoint

    def add_to_kernel(self, kernel: Kernel):
        chat_completion = AzureChatCompletion(
            deployment_name=self.deployment_name,
            api_key=self.api_key,
            endpoint=self.endpoint
        )
        kernel.add_service(chat_completion)
        return kernel

class KernelWrapper:
    def __init__(self, ai_provider: AIProviderBase):
        self.kernel = Kernel()
        ai_provider.add_to_kernel(self.kernel)
