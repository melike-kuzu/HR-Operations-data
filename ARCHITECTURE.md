# Workforce Assistant Architecture

## Query flow

1. UI sends a question to `ChatbotService`.
2. Router selects structured data, skills, profile search, or document search.
3. Structured questions use Parquet/SQL repositories.
4. Profile and document questions use `SearchRepository`.
5. Local development uses `InMemorySearchRepository`.
6. Azure deployment swaps it for `AzureSearchRepository`.
7. Azure OpenAI generation can be added behind the `ChatModel` interface.

## Azure target

- Azure Container Apps: application runtime
- Azure Container Registry: container images
- Azure AI Search: profile/PDF/Excel chunk retrieval
- Azure OpenAI: embeddings and grounded response generation
- Azure Blob Storage: original documents
- Azure Key Vault: secrets
- Application Insights: telemetry
- Azure SQL or private company SQL: structured data
- Container Apps Job or Azure Function: scheduled ingestion/index refresh
