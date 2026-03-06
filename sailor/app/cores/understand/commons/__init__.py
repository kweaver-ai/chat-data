"""
@File: __init__.py
@Date:2024-08-06
@Author : Danny.gao
@Desc:
"""

from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.understand.commons._api import LLMServices

ad_service = PromptServices()
llm_func = LLMServices()

from app.cores.understand.commons.get_samples import get_one_sample

from app.cores.understand.commons.post_kafka import Kafka_Producer
from app.cores.understand.commons.redis_processor import Redis_Processor

kafka_producer = Kafka_Producer()
redis_processor = Redis_Processor()





