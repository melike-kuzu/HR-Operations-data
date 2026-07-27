from __future__ import annotations

from abc import ABC, abstractmethod


class ChatModel(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        question: str,
        context: list[str],
    ) -> str:
        raise NotImplementedError


class NoOpChatModel(ChatModel):
    def generate(
        self,
        *,
        question: str,
        context: list[str],
    ) -> str:
        del question
        return "\n\n".join(context)
