import os
import yaml
import logging
import json
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig, HandlebarsPromptTemplate
from kernel import KernelWrapper, AzureOpenAIProvider
from blob_client import AzureBlobTemplateClient  # Import the blob client

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class PromptProcessor:
    def __init__(self, deployment_name: str, api_key: str, endpoint: str = None):
        # Cria uma nova instância do kernel para cada evaluator
        provider = AzureOpenAIProvider(deployment_name, api_key, endpoint)
        self.kernel = KernelWrapper(provider).kernel

    async def process_payload(self, payload) -> str:
        # payload is now a JSON object (dict or str)
        if isinstance(payload, str):
            payload = json.loads(payload)
        skills_list = payload.get("skills_list", [])
        essay = payload.get("essay", "")
        # Fetch template from Azure Blob Storage using environment variables
        blob_client = AzureBlobTemplateClient()
        yaml_content = blob_client.get_template()

        arguments = KernelArguments(skills_list=skills_list, essay=essay)

        semantic_function = self.kernel.add_function(
            prompt=yaml_content,
            plugin_name="EssayEvaluator",
            function_name="EvaluateEssay",
            template_format="handlebars"
        )

        response = await self.kernel.invoke(semantic_function, arguments)
        return response
