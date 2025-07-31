import os
import yaml
import logging
import json
from semantic_kernel.functions import KernelArguments
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from kernel import KernelWrapper, AzureOpenAIProvider
from blob_client import AzureBlobTemplateClient
from post_evaluation import PostEvaluation

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
        
        # Register the PostEvaluation plugin
        self._register_plugins()

    def _register_plugins(self):
        """Register all plugins that can be called from prompts."""

        self.kernel.add_plugin(
            PostEvaluation(), "PostEvaluationPlugin"
        )
        logger.info("PostEvaluation plugin registered successfully")

    async def process_payload(self, payload) -> str:
        # payload is now a JSON object (dict or str)
        if isinstance(payload, str):
            payload = json.loads(payload)
        
        skills_list = payload.get("skills_list", [])
        essay = payload.get("essay", "")
        
        # Fetch template from Azure Blob Storage
        blob_client = AzureBlobTemplateClient()
        yaml_content = blob_client.get_template()
        
        # Parse the YAML to get the template and execution settings
        template_config = yaml.safe_load(yaml_content)
        template_text = template_config["template"]

        
        # Create function directly from template text
        semantic_function = self.kernel.add_function(
            function_name="evaluate_essay",
            plugin_name="EvaluateEssayPlugin",
            prompt=yaml_content,
            template_format="handlebars"
        )

        # Convert skills_list to JSON string for the function call
        skills_json = json.dumps(skills_list) if isinstance(skills_list, list) else str(skills_list)
        
        arguments = KernelArguments(
            settings=PromptExecutionSettings(function_choice_behavior=FunctionChoiceBehavior.Auto()),
            skills_list=skills_json,
            essay=essay
        )

        response = await self.kernel.invoke(semantic_function, arguments)
        return response
