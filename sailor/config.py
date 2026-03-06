# -*- coding: utf-8 -*-

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 加载 .env 文件（如果存在）
# 优先级：环境变量 > .env 文件 > 代码中的默认值
load_dotenv()


class Settings(BaseSettings):
    # 本地调试时， 可以设置本地环境变量 IF_DEBUG， 设置值为 True
    # 生产环境不存在这个环境变量，IF_DEBUG 值为 False
    IF_DEBUG: bool = os.getenv('IF_DEBUG', False)

    DEBUG_URL_ANYFABRIC: str = '10.4.109.85'
    DEBUG_URL_ANYFABRIC_HTTP: str = 'http://' + DEBUG_URL_ANYFABRIC
    DEBUG_URL_ANYFABRIC_HTTPS: str = 'https://' + DEBUG_URL_ANYFABRIC

    DEBUG_URL_GPU: str = 'http://192.168.152.11'  # 本地调试时， 配置 大模型服务器 测试环境的IP

    DEBUG_DIP_GATEWAY: str = '10.4.109.85'
    DEBUG_DIP_GATEWAY_HTTP: str = 'http://' + DEBUG_DIP_GATEWAY
    DEBUG_DIP_GATEWAY_HTTPS: str = 'https://' + DEBUG_DIP_GATEWAY
    DEBUG_DIP_GATEWAY_USER: str = os.getenv('DEBUG_DIP_GATEWAY_USER', '')
    DEBUG_DIP_GATEWAY_TYPE: str = 'user'

    # 用于测试环境中给不同服务器上的 af-sailor 提示词分组
    if IF_DEBUG:
        AF_IP: str = os.getenv("AF_IP", DEBUG_URL_ANYFABRIC_HTTPS)
    else:
        AF_IP: str = os.getenv("AF_IP", "")

    LLM_NAME: str = os.getenv('LLM_NAME', "Tome-pro")

    AF_OPENSEARCH_HOST: str = os.getenv('OPENSEARCH_HOST', DEBUG_URL_ANYFABRIC)
    AF_OPENSEARCH_PORT: str = os.getenv('OPENSEARCH_PORT', '9200')
    AF_OPENSEARCH_USER: str = os.getenv('OPENSEARCH_USER', '')
    # 密码不应硬编码在代码中，必须通过环境变量或 .env 文件提供
    AF_OPENSEARCH_PASS: str = os.getenv('OPENSEARCH_PASS', '')

    ML_EMBEDDING_URL: str = os.getenv('ML_EMBEDDING_URL', DEBUG_URL_GPU + ':8316')
    ML_EMBEDDING_URL_suffix: str = 'v1/embeddings'
    # AD 版本信息
    AD_VERSION: str = os.getenv('AD_VERSION', '3.0.1.3')

    # 智能推荐：获取字典配置、获取AD环境参数、大模型名称
    AF_SVC_URL: str = 'http://configuration-center:8133/api/internal/configuration-center/v1/byType-list/6'
    AD_BASIC_INFOS_URL: str = 'http://af-sailor-service:80/api/internal/af-sailor-service/v1/knowledge/configs'
    # AF_SVC_URL: str = 'http://10.4.134.29:8133/api/internal/configuration-center/v1/byType-list/6'
    # AD_BASIC_INFOS_URL: str = 'http://10.4.134.29:80/api/internal/af-sailor-service/v1/knowledge/configs'
    REC_LLM_NAME: str = os.getenv('RECOMMEND_LLM_NAME', 'L40-Qwen2-72B-Chat')

    # DIP
    DIP_GATEWAY_URL: str = os.getenv('DIP_GATEWAY_URL', DEBUG_DIP_GATEWAY_HTTP)
    DIP_GATEWAY_USER: str = os.getenv('DIP_GATEWAY_USER', DEBUG_DIP_GATEWAY_USER)
    DIP_GATEWAY_USER_TYPE: str = os.getenv('DIP_GATEWAY_USER_TYPE', DEBUG_DIP_GATEWAY_TYPE)

    # retriever中的分数阈值，如果分数都小于阈值，那么就返回第一个， 就不看分数
    CS_FILTER_VALUE: float = os.getenv('CS_FILTER_VALUE', 3.99)
    # 已废弃：QA区分不走大模型的query文字长度，<=5个字，返回搜索列表的结果， 不走大模型， 但是分析问答型搜索算法还是要走一遍向量和大模型调用
    QUERY_LEN_MIN: int = os.getenv('QUERY_LEN_MIN', 6)

    MIN_SCORE: float = os.getenv('MIN_SCORE', 0.85)  # 搜索列表向量召回的分数下限阈值
    SAMPLE_NUM: int = os.getenv('SAMPLE_NUM', 1)  # 探查样例数量
    CODE_VALUE_NUM: int = os.getenv('CODE_VALUE_NUM', 20)  # 码值数量
    OS_NUM: int = os.getenv('OS_NUM', 500)  # 用于辅助排序, 用在"score": settings.OS_NUM - num中
    OS_KEY_NUM: int = os.getenv('OS_KEY_NUM', 1000)  # opensearch关键词搜索返回结果数量限制
    OS_VEC_NUM: int = os.getenv('OS_VEC_NUM', 100)  # opensearch向量搜索返回结果数量限制
    Finally_NUM: int = os.getenv('EN_NUM', 30)  # 图分析最终返回前端数量限制

    ######################################### redis 连接信息
    REDIS_CONNECT_TYPE: str = os.getenv('REDIS_CONNECT_TYPE', 'master-slave')
    REDIS_MASTER_NAME: str = os.getenv('REDIS_MASTER_NAME', 'mymaster')
    REDIS_DB: str = os.getenv('REDIS_DB', '0')

    REDIS_SENTINEL_HOST: str = os.getenv('REDIS_SENTINEL_HOST', 'proton-redis-proton-redis-sentinel.resource')
    REDIS_SENTINEL_PORT: str = os.getenv('REDIS_SENTINEL_PORT', "26379")
    # 密码不应硬编码在代码中，必须通过环境变量或 .env 文件提供
    REDIS_SENTINEL_PASSWORD: str = os.getenv('REDIS_SENTINEL_PASSWORD', '')
    REDIS_SENTINEL_USER_NAME: str = os.getenv('REDIS_SENTINEL_USER_NAME', '')

    REDIS_HOST: str = os.getenv('REDIS_HOST', DEBUG_URL_ANYFABRIC)
    REDIS_PORT: str = os.getenv('REDIS_PORT', '6379')
    # 密码不应硬编码在代码中，必须通过环境变量或 .env 文件提供
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '')

    ######################################### kafka消息：环境变量+常量
    KAFKA_MQ_HOST: str = os.getenv('KAFKA_MQ_HOST', 'kafka-headless.resource:9097')
    KAFKA_HOST: str = KAFKA_MQ_HOST.split(':')[0]
    KAFKA_PORT: str = KAFKA_MQ_HOST.split(':')[-1]
    KAFKA_MECHANISM: str = os.getenv('KAFKA_MQ_MECHANISM', 'PLAIN')
    KAFKA_SECURITY_PROTOCOL: str = 'SASL_PLAINTEXT'
    KAFKA_USERNAME: str = os.getenv('KAFKA_MQ_USERNAME', 'kafkaclient')
    # 密码不应硬编码在代码中，必须通过环境变量或 .env 文件提供
    KAFKA_PASSWORD: str = os.getenv('KAFKA_MQ_PASSWORD', '')
    KAFKA_TOPIC: str = 'af.af-sailor.table_completion'
    KAFKA_PARTITION: int = 0
    KAFKA_EX_TIME: int = 60

    ######################################### 数据元补全：超时时间（以second为单位）、大模型输入/输出长度限制（通过字典配置）
    TABLE_COMPLETION_AF_SVC_URL: str = 'http://configuration-center:8133/api/internal/configuration-center/v1/byType-list/9'
    TABLE_COMPLETION_LLM_NAME: str = os.getenv('TABLE_COMPLETION_LLM_NAME', 'Tome-L')
    TABLE_COMPLETION_REDIS_HASHTABLE_NAME: str = 'af_sailor_table_completion'
    TABLE_COMPLETION_DELTA_CHECK_TIME: int = 60 * 60

    # 鉴权服务

    HYDRA_URL: str = os.getenv('HYDRA_HOST', DEBUG_URL_ANYFABRIC_HTTP + ':4445')

    AF_CONFIGUATION_CENTER_BY_TYPE: str = 'http://configuration-center:8133/api/internal/configuration-center/v1/byType-list/{num}'


@lru_cache
def get_settings():
    return Settings()

settings = get_settings()


if __name__ == '__main__':

    print(settings.model_dump())
    print(settings.model_dump_json())

    print(settings.DEBUG_URL_ANYFABRIC_HTTP)
    print(settings.DEBUG_URL_ANYFABRIC_HTTPS)
    print(settings.DEBUG_URL_AD_HTTPS)

    print(settings.DEBUG_URL_GPU)
