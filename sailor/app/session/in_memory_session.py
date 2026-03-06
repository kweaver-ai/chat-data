from typing import Any

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from app.session import BaseChatHistorySession


class InMemoryChatSession(BaseChatHistorySession):

    def __init__(self):
        self.message_history_session = {}
        self.agent_logs = {}  # 存储agent日志的字典

    def get_chat_history(
            self, session_id: str,
    ) -> BaseChatMessageHistory:
        if session_id in self.message_history_session:
            return self.message_history_session[session_id]
        else:
            self._add_chat_history(session_id, ChatMessageHistory())
            return self.message_history_session[session_id]

    def _add_chat_history(self, session_id: str, chat_history: BaseChatMessageHistory):
        self.message_history_session[session_id] = chat_history

    def delete_chat_history(self, session_id: str):
        if not self.message_history_session.pop(session_id, None):
            raise "%s not found in message_history_session" % session_id

    def clean_session(self):
        self.message_history_session = {}
        self.agent_logs = {}

    def add_agent_logs(
            self,
            session_id: str,
            logs: dict,
            expire_time: int = None  # in_memory 不需要过期时间
    ) -> Any:
        """存储 agent 日志到内存"""
        self.agent_logs[session_id] = logs

    def get_agent_logs(
            self,
            session_id: str
    ) -> dict | list:
        """获取 agent 日志"""
        return self.agent_logs.get(session_id, {})