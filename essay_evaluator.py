import os
import yaml
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig, HandlebarsPromptTemplate
from kernel import KernelWrapper, AzureOpenAIProvider

class EssayEvaluator:
    def __init__(self, deployment_name: str, api_key: str, endpoint: str = None):
        # Cria uma nova instância do kernel para cada evaluator
        provider = AzureOpenAIProvider(deployment_name, api_key, endpoint)
        self.kernel = KernelWrapper(provider).kernel

    async def evaluate_essay(self, essay: str, prompt_path: str) -> str:
        with open(prompt_path, 'r') as f:
            yaml_content = f.read()

        yaml_data = yaml.safe_load(yaml_content)
        prompt_template_config = PromptTemplateConfig(**yaml_data)
        prompt_template = HandlebarsPromptTemplate(prompt_template_config=prompt_template_config)

        arguments = KernelArguments(criteria1="conciseness", criteria2="relevance", essay=essay)

        semantic_function = self.kernel.add_function(
            prompt=yaml_content,
            plugin_name="EssayEvaluator",
            function_name="EvaluateEssay",
            template_format="handlebars"
        )

        response = await self.kernel.invoke(semantic_function, arguments)
        return response
