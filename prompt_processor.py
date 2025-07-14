import os
import yaml
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig, HandlebarsPromptTemplate
from kernel import KernelWrapper, AzureOpenAIProvider
from blob_client import AzureBlobTemplateClient  # Import the blob client

class PromptProcessor:
    def __init__(self, deployment_name: str, api_key: str, endpoint: str = None):
        # Cria uma nova instância do kernel para cada evaluator
        provider = AzureOpenAIProvider(deployment_name, api_key, endpoint)
        self.kernel = KernelWrapper(provider).kernel

    async def process_payload(self, payload: str) -> str:
        # Fetch template from Azure Blob Storage using environment variables
        blob_client = AzureBlobTemplateClient()
        yaml_content = blob_client.get_template()

        arguments = KernelArguments(criteria1="conciseness", criteria2="relevance", essay=payload)

        semantic_function = self.kernel.add_function(
            prompt=yaml_content,
            plugin_name="EssayEvaluator",
            function_name="EvaluateEssay",
            template_format="handlebars"
        )

        response = await self.kernel.invoke(semantic_function, arguments)
        return response
