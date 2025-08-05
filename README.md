# Semantic Kernel Consumer

This project demonstrates a Python-based consumer for Azure Service Bus and Azure Blob Storage, designed to process messages and retrieve prompt templates securely for LLM Inference using an injected AI service in Semantic Kernel. It follows best practices for logging, error handling, and configuration.

## Features
- Consumes messages from Azure Service Bus (using local emulator or Azure)
- Retrieves prompt templates from Azure Blob Storage (using local emulator or Azure)
- Uses environment variables for configuration and secrets
- Consistent logging across all modules
- **Flexible AI Service Injection:** Easily swap or configure the AI service used by Semantic Kernel (see below)

## Service Injection in Semantic Kernel
This project uses a flexible approach to inject AI services into Semantic Kernel. The `PromptProcessor` class receives deployment and authentication details, and internally creates an `AzureOpenAIProvider` (or any compatible provider). This provider is injected into the `KernelWrapper`, which then configures the Semantic Kernel instance. This design allows you to:
- Swap out the AI provider (e.g., use Azure OpenAI, OpenAI, or another compatible service)
- Pass different deployment names, API keys, or endpoints via environment variables or arguments
- Extend the project to support additional AI services with minimal code changes

See `prompt_processor.py` and `kernel.py` for details on how providers are injected and used.

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
- `OPENAI_MODEL_NAME` (OpenAI model deployment name)
- `AI_API_KEY` (OpenAI API key)
- `AI_ENDPOINT` (OpenAI endpoint, if required)

## Usage

### 1. Start Local Emulators
- **Start Azurite for Blob Storage:**
 - The easiest way is to use the Azurite extension in VS Code and click the "[Azurite Blob Service]" in the status bar
 - Start your Service Bus emulator (a Docker container) or use Azure Service Bus Explorer for local development.
 - Use the Azure Storage Explorer to connect to your blob storage local emulator, create a container named "prompt_templates", create a new file essay.yaml, paste the following content and upload it into the container:

```
name: EvaluateEssay
template: |
  <message role="system">
    You are an expert essay evaluator. Your task is to evaluate the quality of an essay based on the provided criteria.
  </message>
  <message role="user">
    Evaluate the following essay based on each of the skills provided:
      {{ skills_list }}
    For each skill, provide a result in the format:
    {
      "skill": "<skill_name>",
      "comments": "<evaluation_result>",
      "result"
    }
    This is the essay to evaluate:
    {{essay}}
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

### 3. Send Test Messages
To emulate sending messages to the queue (for local testing):
```sh
python local_test/send_message.py
```
This script sends a sample message to the Service Bus queue for processing.

## Project Structure
- `main.py` — Entry point; runs the message consumer
- `receive_message.py` — Handles Service Bus message processing
- `prompt_processor.py` — Processes messages using prompt templates and injects AI services into Semantic Kernel
- `kernel.py` — Handles AI provider injection and Semantic Kernel configuration
- `blob_client.py` — Handles Blob Storage access
- `local_test/send_message.py` — Utility to send test messages

## Notes
- Ensure all required environment variables are set before running the scripts.
- The project is designed to work both locally (with emulators) and in Azure.
- Logging output will appear in the console for all scripts.
- You can easily extend or swap the AI service used by modifying the provider injection in `prompt_processor.py` and `kernel.py`.

---

For more details, see the source code and comments in each file.
