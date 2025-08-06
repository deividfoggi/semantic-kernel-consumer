# Semantic Kernel Consumer

This project demonstrates a Python-based consumer for Azure Service Bus and Azure Blob Storage, designed to process messages and retrieve prompt templates securely for LLM Inference using an injected AI service in Semantic Kernel. It follows best practices for logging, error handling, and configuration.

## Features
- Consumes messages from Azure Service Bus (using local emulator or Azure)
- Retrieves prompt templates from Azure Blob Storage (using local emulator or Azure)
- Uses environment variables for configuration and secrets
- Consistent logging across all modules
- **Flexible AI Service Injection:** Easily swap or configure the AI service used by Semantic Kernel (supports Azure OpenAI and Azure AI Inference)
- **Essay Evaluation Plugin:** Built-in plugin for evaluating essays with scoring and approval/rejection logic
- **Graceful Shutdown:** Handles shutdown signals properly with configurable timeout
- **Concurrent Processing:** Supports concurrent message processing with configurable limits
- **Robust Error Handling:** Comprehensive error handling and retry logic

## Service Injection in Semantic Kernel
This project uses a flexible approach to inject AI services into Semantic Kernel through the `KernelFactory` class. The `PromptProcessor` receives deployment and authentication details, and the `KernelFactory` creates the appropriate AI provider based on the `ProviderType` enum (currently supporting `AZURE_OPENAI` and `AZURE_AI_INFERENCE`). The provider is then injected into the kernel instance. This design allows you to:
- Swap out the AI provider (e.g., use Azure OpenAI or Azure AI Inference)
- Pass different deployment names, API keys, endpoints, or API versions via environment variables
- Extend the project to support additional AI services with minimal code changes
- Use different AI services for different use cases

The system also includes a `PostEvaluation` plugin that provides additional evaluation capabilities for essay scoring and approval/rejection logic.

See `prompt_processor.py`, `kernel.py`, and `post_evaluation.py` for details on how providers and plugins are injected and used.

## Prerequisites
- Python 3.8+
- [Azurite](https://github.com/Azure/Azurite) (for local Blob Storage emulation)
- [Azure Service Bus Emulator](https://github.com/Azure/azure-service-bus) (for local Service Bus emulation)
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```

## Environment Variables
Set the following environment variables before running the project:

- `AZURE_STORAGE_CONNECTION_STRING` (for local Blob Storage)
- `AZURE_STORAGE_ACCOUNT_URL` (for managed identity/Azure)
- `PROMPT_TEMPLATE_CONTAINER_NAME` (Blob container name)
- `PROMPT_TEMPLATE_BLOB_NAME` (Blob name for the prompt template)
- `SERVICE_BUS_CONNECTION_STR` (Service Bus connection string)
- `SERVICE_BUS_QUEUE_NAME` (Service Bus queue name)
- `AI_MODEL_NAME` (AI model deployment name)
- `AI_API_KEY` (AI API key)
- `AI_ENDPOINT` (AI endpoint)
- `API_VERSION` (AI API version)
- `SHUTDOWN_TIMEOUT` (Optional: Graceful shutdown timeout in seconds, default: 30)

## Usage

### 1. Start Local Emulators
 - The easiest way to emulate a local blob storage is to use the Azurite extension in VS Code and click the "[Azurite Blob Service]" in the status bar
 - Start your Service Bus emulator (a Docker container) or use Azure Service Bus Explorer for local development.
 - Use the Azure Storage Explorer to connect to your blob storage local emulator, create a container named "prompt_templates", create a new file essay.yaml, paste the following content and upload it into the container:

```yaml
name: EvaluateEssay
template: |
  <message role="system">
    Você é um avaliador de redações especialista. Sua tarefa é avaliar a qualidade de uma redação com base nos critérios fornecidos.
  </message>
  <message role="user">
    Avalie a seguinte redação com base em cada uma das habilidades fornecidas:
      {{ skills_list }}
    Para cada habilidade, forneça um resultado no formato:
    {
      "habilidade": "<nome_da_habilidade>",
      "comentários": "<resultado_da_avaliação>",
      "nota": "<nota>"
    }
    Esta é a redação a ser avaliada:
      {{ essay }}

    SEMPRE SOMENTE AO FINAL da avaliação, você deve usar os resultados de cada habilidade avaliada na função evaluate_skills, e então adicione o resultado da avaliação ao resultado final exatamente como ele é retornado.
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
output_variable:
  evaluation: The evaluation result.
execution_settings:
  service1:
    model_id: gpt-4o
    temperature: 0.6
  service2:
    model_id: gpt-4o-mini
    temperature: 0.4
  default:
    temperature: 0.5
```


### 2. Run the Consumer
To start the message consumer:
```sh
python main.py
```
This will listen for messages on the configured Service Bus queue and process them using the prompt template from Blob Storage.

### 3. Test the Consumer
The consumer will automatically start processing messages when you run:
```sh
python main.py
```

To test the system, you can send messages to your Service Bus queue using Azure Service Bus Explorer, Azure CLI, or any Service Bus client. The expected message format is:
```json
{
  "skills_list": ["skill1", "skill2", "skill3"],
  "essay": "Your essay text here..."
}
```

## Project Structure
- `main.py` — Entry point; runs the message consumer
- `consumer.py` — Handles Service Bus message processing with async support and graceful shutdown
- `prompt_processor.py` — Processes messages using prompt templates and manages AI service injection
- `kernel.py` — Handles AI provider injection and Semantic Kernel configuration via KernelFactory
- `blob_client.py` — Handles Blob Storage access for prompt templates
- `post_evaluation.py` — Plugin for essay evaluation, scoring, and approval/rejection logic
- `tests/` — Unit tests for all modules
- `essay.yaml` — Sample prompt template (in Portuguese) with evaluation logic

## Notes
- Ensure all required environment variables are set before running the scripts.
- The project is designed to work both locally (with emulators) and in Azure.
- Logging output will appear in the console for all scripts.
- The system supports graceful shutdown via SIGTERM/SIGINT signals with configurable timeout.
- Concurrent message processing is supported with a default limit of 10 concurrent tasks.
- The essay evaluation includes both individual skill assessment and overall approval/rejection logic.
- You can easily extend or swap the AI service used by modifying the provider injection in `kernel.py`.
- The PostEvaluation plugin can be extended to support additional evaluation criteria and logic.

---

For more details, see the source code and comments in each file.
