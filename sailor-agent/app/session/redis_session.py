import json
import logging
import os
import redis
from redis.sentinel import Sentinel
import re
from abc import ABC
from typing import Any

from langchain.schema import HumanMessage, SystemMessage, BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage
from typing import Union, Awaitable

# from af_agent.settings import get_settings
from data_retrieval.settings import get_settings as get_settings2
from app.logs.logger import logger
from config import get_settings
# from af_agent.logs.logger import logger

settings = get_settings()
empty = ""
from data_retrieval.sessions.base import BaseChatHistorySession



retrieval_settings = get_settings2()


class RedisHistorySession(BaseChatHistorySession):

    def __init__(
            self,
            history_num_limit=retrieval_settings.AGENT_SESSION_HISTORY_NUM_LIMIT,
            history_max=retrieval_settings.AGENT_SESSION_HISTORY_MAX
    ):
        try:
            logger.info(f"初始化 RedisHistorySession，配置: host={settings.REDIS_HOST}, "
                       f"port={settings.REDIS_PORT}, db={settings.REDIS_DB}, "
                       f"connect_type={settings.REDIS_CONNECT_TYPE}"
                        f'redis_passwd={settings.REDIS_PASSWORD}'
                        f'redis_sentinel_passwd={settings.REDIS_SENTINEL_PASSWORD}')
            self.client = RedisConnect().connect()
            # 测试连接
            self.client.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
        self.history_num_limit = history_num_limit
        self.history_max = history_max

    @staticmethod
    def unescape_quotes(s):
        # 替换转义的双引号
        s = re.sub(r'\\\\\"', '\"', s)
        # 替换多层转义的双引号
        while '\\\"' in s:
            s = s.replace('\\\"', '\"')
        return s

    def get_history_num(
            self,
            session_id: str
    ) -> Union[Awaitable[int], int]:
        if not session_id.startswith("agent"):
            session_id = "agent" + session_id

        num = self.client.hlen(session_id)

        return num

    def get_chat_history(
            self,
            session_id: str
    ) -> str | BaseChatMessageHistory | Any:
        if not session_id.startswith("agent"):
            session_id = "agent" + session_id
        chat_message_history = ChatMessageHistory()
        history = self.client.hgetall(session_id)
        history = {
            k.decode('utf-8'): v.decode('utf-8')
            for k, v in history.items()
        }
        sort_history = {
            k: history[k]
            for k in sorted(history)
        }

        if sort_history:
            last_key_of_sort_history = list(sort_history.keys())[-1]
            for k, v in sort_history.items():
                v = self.unescape_quotes(v)
                # if len(v) > self.history_max:
                #     self.history_num_limit = 1
                if "human" in k:
                    chat_message_history.add_message(HumanMessage(v))
                elif "system" in k:
                    chat_message_history.add_message(SystemMessage(v))
                elif "ai" in k:
                    chat_message_history.add_message(AIMessage(v))
                else:
                    if k == last_key_of_sort_history:
                        chat_message_history.add_message(AIMessage(v))
        chat_message_history.messages = chat_message_history.messages[-self.history_num_limit:]

        idx, total_len = max(-self.history_num_limit, -len(chat_message_history.messages)), 0

        for i in range(-1, idx, -1):
            total_len += len(chat_message_history.messages[i].content)
            if total_len > self.history_max:
                idx = i
                break

        chat_message_history.messages = chat_message_history.messages[idx:]

        # for message in chat_message_history.messages:
        #     if len(message.content) > self.history_max:
        #         if_message_big_than_message = True
        #         break
        # if if_message_big_than_message:
        #     chat_message_history.messages = chat_message_history.messages[-1:]

        logger.info(
            f"session id {session_id}, chat_message_history num {len(chat_message_history.messages)}"
            f"检查最近 {self.history_num_limit} 历史记录总长度是否超过 {self.history_max}：获取到了最近{-idx}条数据")

        return chat_message_history

    # TODO: 优化成 BaseMessage，然后继承 add_chat_history
    def add_chat_history(
            self,
            session_id: str,
            types: str,
            content: str,
            expire_time: int = settings.REDIS_SESSION_EXPIRE_TIME
    ):
        session_id = "agent" + session_id
        # chat_message_history = self.get_history_num(session_id)
        nums = str(self.get_history_num(session_id) + 1)
        nums = (4 - len(nums)) * "0" + nums
        if isinstance(content, dict):
            logger.info("chat history save dict {}".format(content))
            content = json.dumps(content)
        if types == "human":
            self.client.hset(session_id, f"{nums}:human", content)
        elif types == "ai":
            self.client.hset(session_id, f"{nums}:ai", content)
        elif types == "system":
            self.client.hset(session_id, f"{nums}:system", content)
        else:
            self.client.hset(session_id, f"{nums}:middle", content)

        self.client.expire(session_id, expire_time)

    def add_agent_logs(
            self,
            session_id: str,
            logs: dict,
            expire_time: int = settings.REDIS_SESSION_EXPIRE_TIME
    ) -> Any:
        try:
            logger.info(f"准备写入 Redis，session_id: {session_id}, expire_time: {expire_time}")
            logger.debug(f"写入的数据: {logs}")
            result = self.client.setex(
                name=session_id,
                time=expire_time,
                value=json.dumps(logs, ensure_ascii=False),
            )
            logger.info(f"Redis 写入成功，session_id: {session_id}, result: {result}")
            return result
        except Exception as e:
            logger.error(f"Redis 写入失败，session_id: {session_id}, 错误: {e}")
            logger.error(f"Redis 配置信息 - host: {settings.REDIS_HOST}, port: {settings.REDIS_PORT}, "
                        f"db: {settings.REDIS_DB}, connect_type: {settings.REDIS_CONNECT_TYPE}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise

    # TODO: 直接返回 get_chat_history
    def get_agent_logs(
            self,
            session_id: str
    ) -> dict | list:
        """获取历史记录"""
        history = self.client.get(session_id)
        if history is None:
            history = {}
        else:
            history = json.loads(history)
        return history

    def clean_session(self):
        """ empty"""
        pass

    def _add_chat_history(
            self,
            session_id: str,
            chat_history: BaseChatMessageHistory
    ):
        """ empty"""
        pass

    def delete_chat_history(
            self,
            session_id: str
    ):
        """ empty"""
        pass

    def add_working_context(
            self,
            session_id: str,
            working_context: dict
    ):
        """ empty"""
        pass

    def get_working_context(
            self,
            session_id: str
    ):
        """ empty"""
        pass

    def save_report_middle_result(self,
                                  report_type_id: str,
                                  report_hash_key: str,
                                  metric_data: str,
                                  expire_time: int = settings.REDIS_SESSION_EXPIRE_TIME
                                  ):
        # self.client.setex(
        #     name=report_type_id,
        #     time=expire_time,
        #     value=metric_data,
        # )
        self.client.hset(report_type_id, report_hash_key, metric_data)
        self.client.expire(report_type_id, expire_time)

    def get_report_middle_result(self,
                                 report_type_id: str,
                                 ):
        result = self.client.hgetall(report_type_id)
        if result is None:
            result = ""

        return result

    def save_result(self, key: str, content: str, expire_time: int = settings.REDIS_SESSION_EXPIRE_TIME):
        # self.client.hset(report_id, "report_content")
        self.client.setex(
            name=key,
            time=expire_time,
            value=content,
        )

    def get_result(self, key: str):
        # self.client.hset(report_id, "report_content")
        return self.client.get(key)


class RedisConnect:
    def __init__(self):
        settings = get_settings()
        self.redis_cluster_mode = settings.REDIS_CONNECT_TYPE
        self.db = settings.REDIS_DB
        self.master_name = settings.REDIS_MASTER_NAME
        self.sentinel_user_name = settings.REDIS_SENTINEL_USER_NAME

        self.host = settings.REDIS_HOST
        # self.host = '10.4.109.216'
        self.sentinel_host = settings.REDIS_SENTINEL_HOST

        self.port = settings.REDIS_PORT
        self.sentinel_port = settings.REDIS_SENTINEL_PORT

        self.password = settings.REDIS_PASSWORD
        self.sentinel_password = settings.REDIS_SENTINEL_PASSWORD

    def connect(self):
        if self.redis_cluster_mode == "master-slave":
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
            )
            client = redis.StrictRedis(connection_pool=pool)
            return client
        if self.redis_cluster_mode == "sentinel":
            sentinel = Sentinel(
                [(self.sentinel_host, self.sentinel_port)],
                password=self.sentinel_password,
                sentinel_kwargs={
                    "password": self.sentinel_password,
                    "username": self.sentinel_user_name
                }
            )
            client = sentinel.master_for(
                self.master_name,
                password=self.sentinel_password,
                username=self.sentinel_user_name,
                db=self.db
            )
            return client


if __name__ == "__main__":
    pass
