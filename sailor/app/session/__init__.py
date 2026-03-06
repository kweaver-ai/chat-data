from langchain_core.chat_history import BaseChatMessageHistory
from typing import Any
from abc import ABC, abstractmethod


class BaseChatHistorySession(ABC):

    @abstractmethod
    def get_chat_history(
            self, session_id: str,
    ) -> BaseChatMessageHistory:
        raise NotImplementedError

    @abstractmethod
    def _add_chat_history(self, session_id: str, chat_history: BaseChatMessageHistory):
        # Add chat_qa session
        raise NotImplementedError

    @abstractmethod
    def delete_chat_history(self, session_id: str):
        raise NotImplementedError

    @abstractmethod
    def clean_session(self):
        raise NotImplementedError
