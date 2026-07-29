import os
import sys

from dotenv import load_dotenv
from openai import AzureOpenAI


load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def main() -> None:
    endpoint = require_env("AZURE_OPENAI_ENDPOINT")
    api_key = require_env("AZURE_OPENAI_API_KEY")
    deployment = require_env(
        "AZURE_OPENAI_CHAT_DEPLOYMENT"
    )

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-10-21",
    )

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a connection test assistant."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Reply with exactly: "
                    "Azure OpenAI connection successful"
                ),
            },
        ],
        temperature=0,
        max_tokens=20,
    )

    answer = response.choices[0].message.content

    print("Connection successful.")
    print(f"Deployment: {deployment}")
    print(f"Response: {answer}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"Connection failed: "
            f"{type(exc).__name__}: {exc}"
        )
        sys.exit(1)