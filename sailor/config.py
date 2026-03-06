import os
from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "9595"))

    REDIS_CONNECT_TYPE: str = os.getenv("REDIS_CONNECT_TYPE", 'master-slave')
    REDIS_MASTER_NAME: str = os.getenv("REDIS_MASTER_NAME", 'mymaster')
    REDIS_DB: str = os.getenv("REDIS_DB", "0")

    REDIS_SENTINEL_HOST: str = os.getenv("REDIS_SENTINEL_HOST", 'proton-redis-proton-redis-sentinel.resource')
    REDIS_SENTINEL_PORT: str = os.getenv("REDIS_SENTINEL_PORT", "26379")
    REDIS_SENTINEL_PASSWORD: str = os.getenv("REDIS_SENTINEL_PASSWORD", '')
    REDIS_SENTINEL_USER_NAME: str = os.getenv("REDIS_SENTINEL_USER_NAME", '')

    REDIS_HOST: str = os.getenv("REDIS_HOST", 'proton-redis-proton-redis-sentinel.resource')
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", 'password')
    REDIS_SESSION_EXPIRE_TIME: int = 60 * 60 * 24

    AD_GATEWAY_URL: str = os.getenv('AD_GATEWAY_URL', 'https://10.4.134.32:8444')
    AD_GATEWAY_USER: str = os.getenv('AD_GATEWAY_USER', '')
    AD_GATEWAY_PASSWORD: str = os.getenv('AD_GATEWAY_PASSWORD', '')
    # AISHU_READER_LLM: str = os.getenv('AISHU_READER_LLM', "http://192.168.152.11:8303/v1/Qwen2-72B-Chat")
    AISHU_READER_LLM: str = os.getenv('AISHU_READER_LLM', "https://10.4.134.32:8444/api/model-factory/v1/Qwen-72B-Chat")
    FINAL_READER_LLM: str = AISHU_READER_LLM
    if os.getenv('FINAL_READER_LLM') is not None and os.getenv('FINAL_READER_LLM') != "":
        FINAL_READER_LLM = os.getenv('FINAL_READER_LLM', "https://10.4.134.32:8444/api/model-factory/v1/Qwen-72B-Chat")
    LLM_STYLE: str = os.getenv('LLM_STYLE', "OPENAI")


    DPQA_MYSQL_HOST: str = os.getenv("MYSQL_HOST", '10.4.104.59:15236')
    DPQA_MYSQL_USER: str = os.getenv("MYSQL_USERNAME", 'SYSDBA')
    DPQA_MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", 'SYSDBA001')
    DPQA_MYSQL_DATABASE: str = os.getenv("MYSQL_DB", 'af_cognitive_assistant')
    DB_TYPE: str = os.getenv("DB_TYPE","dm8")

    AF_IP: str = os.getenv("AF_IP", "")
    AF_DEBUG_IP: str = os.getenv("AF_DEBUG_IP", "")
    SAILOR_URL: str = os.getenv("SAILOR_URL", "http://af-sailor:9797")
    AF_QA_TIMEOUT: int | str = os.getenv("AF_QA_TIMEOUT", 295)

    # 模型相关配置
    MODEL_TYPE: str = os.getenv("MODEL_TYPE", "openai")
    TOOL_LLM_MODEL_NAME: str = os.getenv("TOOL_LLM_MODEL_NAME", "Tome-pro")
    TOOL_LLM_OPENAI_API_KEY: str = os.getenv("TOOL_LLM_OPENAI_API_KEY", "EMPTY")
    TOOL_LLM_OPENAI_API_BASE: str = os.getenv("TOOL_LLM_OPENAI_API_BASE", "http://mf-model-api:9898/api/private/mf-model-api/v1/")

    CS_FILTER_VALUE: float = os.getenv('CS_FILTER_VALUE', 3.99)
    AD_OPENSEARCH_HOST: str = os.getenv('AD_OPENSEARCH_HOST', '10.4.109.199')
    AD_OPENSEARCH_PORT: str = os.getenv('AD_OPENSEARCH_PORT', '9200')
    AD_OPENSEARCH_USER: str = os.getenv('AD_OPENSEARCH_USER', '')
    AD_OPENSEARCH_PASS: str = os.getenv('AD_OPENSEARCH_PASS', '')
    ML_EMBEDDING_URL: str = os.getenv('ML_EMBEDDING_URL', 'http://192.168.152.11:8316')
    ML_EMBEDDING_URL_suffix: str = 'v1/embeddings'
    # AD 版本信息
    AD_VERSION: str = os.getenv('AD_VERSION', '3.0.0.3')

    # 外部服务
    HYDRA_URL: str = os.getenv('HYDRA_HOST', 'http://hydra-admin:4445')

    # 调试模式
    DEBUG_MODE: bool = os.getenv('DEBUG_MODE', 'False')

    # 启用 rethink 工具
    ENABLE_RETHINK_TOOL: bool = os.getenv('ENABLE_RETHINK_TOOL', 'False')

    # data-view 服务
    DATA_VIEW_URL: str = os.getenv('DATA_VIEW_URL', 'http://data-view:8123')

    # Kafka 配置
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_URI", "kafka-headless.resource:9097")
    KAFKA_DATA_UNDERSTAND_RESULT_TOPIC: str = os.getenv("KAFKA_DATA_UNDERSTAND_RESULT_TOPIC", "data-understanding-responses")
    KAFKA_PASSWORD: str = os.getenv("KAFKA_PASSWORD", "")


    # ADP 服务
    ADP_HOST: str = os.getenv("ADP_HOST", "agent-app")
    ADP_PORT: str = os.getenv("ADP_PORT", "30777")

    XAccountID: str = os.getenv("ADP_X_ACCOUNT_ID", "ceeb84c2-87ca-11f0-af23-e24b42ec8e4f")
    XAccountType: str = os.getenv("ADP_X_ACCOUNT_TYPE", "user")

    ADP_AGENT_KEY: str = os.getenv("ADP_AGENT_KEY", "01KF0EPC3SDWKPKFN3PY0XTRHF")
    ADP_BUSINESS_DOMAIN_ID: str = os.getenv("ADP_BUSINESS_DOMAIN_ID", "bd_public")
    ADP_AGENT_FACTORY_HOST: str = os.getenv("ADP_AGENT_FACTORY_HOST", "http://agent-factory:13020")
    ADP_ONTOLOGY_MANAGER_HOST: str = os.getenv("ADP_ONTOLOGY_MANAGER_HOST", "http://ontology-manager-svc:13014")
    ADP_ONTOLOGY_QUERY_HOST: str = os.getenv("ADP_ONTOLOGY_QUERY_HOST", "http://ontology-query-svc:13018")


    VIR_ENGINE_URL: str = "http://vega-gateway:8099"
    INDICATOR_MANAGEMENT_URL: str = "http://indicator-management:8213"
    AUTH_SERVICE_URL: str = "http://auth-service:8155"
    CATALOG_URL: str =  os.getenv("AF_CATALOG_URL", "http://data-catalog:8153")
    DATA_MODEL_URL:str = os.getenv("DATA_MODEL_URL", "http://mdl-data-model-svc:13020")



class Config:
    TIMES: int = 3
    TIMEOUT: int = 50


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
