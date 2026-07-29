from __future__ import annotations

from openai import AzureOpenAI

from workforce_assistant.config.settings import settings
from workforce_assistant.llm.chat_model import ChatModel


class AzureOpenAIChatModel(ChatModel):
    def __init__(self) -> None:
        self._validate_settings()

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01",
        )

    def generate(
        self,
        *,
        question: str,
        context: list[str],
    ) -> str:
        clean_context = [
            item.strip()
            for item in context
            if item and item.strip()
        ]

        if not clean_context:
            return (
                "I could not find relevant information "
                "in the available workforce data."
            )

        context_text = "\n\n---\n\n".join(
            clean_context
        )

        response = self._client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an internal workforce data "
                        "assistant. Answer only from the supplied "
                        "context. Do not invent names, skills, "
                        "availability, project details, dates, or "
                        "numbers. If the context is insufficient, "
                        "say that clearly. When listing consultants, "
                        "remove duplicates and present every relevant "
                        "consultant found in the context. Do not say "
                        "'top results'. Keep the answer clear and "
                        "business-friendly."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Context:\n{context_text}"
                    ),
                },
            ],
        )

        answer = response.choices[0].message.content

        if not answer:
            return (
                "Azure OpenAI returned an empty response."
            )

        return answer.strip()

    @staticmethod
    def _validate_settings() -> None:
        required_settings = {
            "AZURE_OPENAI_ENDPOINT":
                settings.azure_openai_endpoint,
            "AZURE_OPENAI_API_KEY":
                settings.azure_openai_api_key,
            "AZURE_OPENAI_CHAT_DEPLOYMENT":
                settings.azure_openai_chat_deployment,
        }

        missing = [
            name
            for name, value in required_settings.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )