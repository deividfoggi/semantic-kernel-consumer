from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

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
