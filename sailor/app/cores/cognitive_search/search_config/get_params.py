import json
from typing import Optional

import aiohttp
import requests
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator

from app.logs.logger import logger
from config import settings

if not settings.IF_DEBUG:
    af_configuration_type8_url = settings.AF_CONFIGUATION_CENTER_BY_TYPE.format(num=8)
    af_configuration_type9_url = settings.AF_CONFIGUATION_CENTER_BY_TYPE.format(num=9)
else:
    af_configuration_type8_url = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8133/api/internal/configuration-center/v1/byType-list/8'
    af_configuration_type9_url = f'{settings.DEBUG_URL_ANYFABRIC_HTTP}:8133/api/internal/configuration-center/v1/byType-list/9'


class SearchConfigs(BaseModel):
    sailor_search_if_history_qa_enhance: str = Field(
        default='0',
        description='是否有历史问答对的知识增强, "1":有, "0":无,默认值"0"', )
    sailor_search_if_kecc: str = Field(
        default='0',
        description='是否有基于部门职责的知识增强, "1":有, "0":无,默认值"0"')
    sailor_search_if_auth_in_find_data_qa: str = Field(
        default='1',
        description='''服务超市找数问答中, 是否要限制普通用户只能对有权限的资源进行问答,
       "1":有, "0":无,默认值"1",为保证数据安全,本参数="0"的前提是 direct_qa 参数 
       = "false",否则不允许本参数="0"''')
    direct_qa: str = Field(
        default='false',
        description='''服务超市问答中, 是否开启针对表中具体数据的问答, "true":开启,"false":关闭, 默认值"false"''')
    sailor_vec_min_score_analysis_search: str = Field(
        default='0.5',
        description='')
    sailor_vec_knn_k_analysis_search: str = Field(
        default='10',
        description='')
    sailor_vec_size_analysis_search: str = Field(
        default='10',
        description='')
    sailor_vec_min_score_kecc: str = Field(
        default='0.5',
        description='')  # 部门职责知识图谱向量检索的最小分数, 原`min_score_kecc`变量
    sailor_vec_knn_k_kecc: str = Field(
        default='10',
        description='')  # 部门职责知识图谱向量检索knn算法的`k`值, 应大于等于`size`, 原`limit`变量
    sailor_vec_size_kecc: str = Field(
        default='10',
        description='')  # 部门职责知识图谱向量检索的`size`值
    kg_id_kecc: Optional[str] = Field(
        default=None,
        description='')
    kn_id_catalog: Optional[str] = Field(
        default=None,
        description='')
    sailor_vec_min_score_history_qa: str = Field(
        default='0.7',
        description='')
    sailor_vec_knn_k_history_qa: str = Field(
        default='10',
        description='')
    sailor_vec_size_history_qa: str = Field(
        default='10',
        description='')
    kg_id_history_qa: Optional[str] = Field(
        default=None,
        description='')
    sailor_token_tactics_history_qa: str = Field(
        default='1',
        description='')
    sailor_search_qa_llm_temperature: str = Field(
        default='0',
        description='认知搜索和问答中大模型的参数')
    sailor_search_qa_llm_top_p: str = Field(
        default='1',
        description='认知搜索和问答中大模型的参数')
    sailor_search_qa_llm_presence_penalty: str = Field(
        default='0',
        description='认知搜索和问答中大模型的参数')
    sailor_search_qa_llm_frequency_penalty: str = Field(
        default='0',
        description='认知搜索和问答中大模型的参数')
    sailor_search_qa_llm_max_tokens: str = Field(
        default='8000',
        description='认知搜索和问答中大模型的参数')
    sailor_search_qa_llm_input_len: str = Field(
        default='4000',
        description='认知搜索和问答中大模型的参数')
    # sailor_search_qa_llm_output_len: str = Field(
    #     default='4000',
    #     description='认知搜索和问答中大模型的参数')
    sailor_search_qa_cites_num_limit: str = Field(
        default='50',
        description='分析问答型搜索返回的引用资源数量上限')

    # @field_validator('sailor_search_if_history_qa_enhance')
    # def validate_sailor_search_if_history_qa_enhance(cls, v: str) -> str:
    #     if v not in {'0', '1'}:
    #         raise ValueError('值必须是 "0" 或 "1"')
    #     return v
    #
    # @field_validator('sailor_search_if_kecc')
    # def validate_sailor_search_if_kecc(cls, v: str) -> str:
    #     if v not in {'0', '1'}:
    #         raise ValueError('值必须是 "0" 或 "1"')
    #     return v
    #
    # @field_validator('sailor_search_if_auth_in_find_data_qa')
    # def validate_sailor_search_if_auth_in_find_data_qa(cls, v: str) -> str:
    #     if v not in {'0', '1'}:
    #         raise ValueError('值必须是 "0" 或 "1"')
    #     return v
    #
    # @field_validator('direct_qa')
    # def validate_direct_qa(cls, v: str) -> str:
    #     if v not in {'true', 'false'}:
    #         raise ValueError('值必须是 "true" 或 "false"')
    #     return v

    def refresh(self) -> 'SearchConfigs':
        """刷新当前实例的配置"""
        new_config = SearchConfigs.get_configs()
        # 更新当前实例的字段值
        for field_name, field_value in new_config.dict().items():
            setattr(self, field_name, field_value)
        return self

    @classmethod
    def _fetch_config(cls, url: str, config_type: str, max_retries: int = 3) -> list:
        """获取配置数据的通用函数"""
        for attempt in range(max_retries):
            if attempt > 0:
                logger.warning(f'正在重试获取{config_type}配置...')
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                # HTTP错误（如404, 500等）通常不需要重试
                logger.error(f'获取{config_type}配置HTTP错误: {str(e)}')
                return []
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f'获取{config_type}配置失败(尝试{attempt + 1}/{max_retries}): {str(e)}')
                    # time.sleep(2 ** attempt)
                    continue
                else:
                    logger.error(f'获取{config_type}配置最终失败: {str(e)}')
                    return []
        return []

    @classmethod
    def get_default_configs(cls) -> 'SearchConfigs':
        """获取默认配置实例"""
        return cls()  # 等同于原来的 SearchConfigs()

    # @lru_cache()
    @classmethod
    def get_configs(cls) -> Optional['SearchConfigs']:
        props_default = cls().model_dump()
        props = {}
        # res_type8 = []
        # res_type9 = []
        try:
            res_type8 = cls._fetch_config(af_configuration_type8_url, "type8")
            res_type9 = cls._fetch_config(af_configuration_type9_url, "type9")

            res: list = res_type8 + res_type9
            logger.info(f'AF 获取数据元补全参数字典（原始数据）res_type8：\n{res_type8}')
            logger.info(f'AF 获取数据元补全参数字典（原始数据）res_type9：\n{res_type9}')
            logger.info(f'AF 获取数据元补全参数字典（原始数据）res：\n{res}')

            # 筛选出需要的配置参数
            for item in res:
                param_name = item['key']
                param_value = item['value']
                # value = int(param_value)
                # logger.debug(f'param_name in props.keys() = {param_name in props.keys()}')
                if param_name in props_default:
                    props[param_name] = param_value
                else:
                    continue
            # 如果没有获取到全部配置参数，则抛出异常，后续except中返回默认值
            logger.info(f'len(props)={len(props)}')
            logger.info(f'len(props_default)={len(props_default)}')
            # if len(props) != len(props_default):
            #     raise Exception(f'获取配置参数失败，请检查配置参数是否正确')
            logger.info(f'AF 获取认知搜索配置参数字典结果 =\n{props}')
            return cls(**props)

        except Exception as e:
            logger.error(
                f"AF 获取认知搜索配置参数字典失败: url='{af_configuration_type8_url},\nurl={af_configuration_type9_url}' \nerror info = {str(e)}")
            # 返回None，调用方来处理
            return None

def get_search_configs() -> SearchConfigs:
    return SearchConfigs.get_configs()

# search_configs: SearchConfigs = get_search_configs()

if __name__ == '__main__':
    # import asyncio
    import json
    # default_props = SearchConfigs().model_dump()
    # print(default_props)
    # default_props_json=SearchConfigs().model_dump_json()
    # print(json.dumps(default_props, ensure_ascii=False, indent=4))

    search_configs = get_search_configs()
    # logger.debug(f'search_configs =\n{search_configs}')
    #
    # logger.debug(f"*******************{settings.AF_CONFIGUATION_CENTER_BY_TYPE.format(num=8)}")

    # 示例
    # model = SearchConfigs(sailor_search_if_history_qa_enhance='1')
    # logger.debug(model)
    #
    # # 尝试传入无效值
    # try:
    #     invalid_model = SearchConfigs(sailor_search_if_history_qa_enhance='2')
    # except ValueError as e:
    #     logger.debug(e)


# RESPONSE_CONFIGS = {
#     'sailor_search_if_history_qa_enhance': '0',
#     'sailor_search_if_kecc': '0',
#     'sailor_search_if_auth_in_find_data_qa': '1',
#     'direct_qa':'false',
#     'sailor_vec_min_score_analysis_search':'0.5',
#     'sailor_vec_knn_k_analysis_search':'10',
#     'sailor_vec_size_analysis_search':'10',
#     'sailor_vec_min_score_kecc':'0.5',
#     'sailor_vec_knn_k_kecc':'10',
#     'sailor_vec_size_kecc':'10',
#     'kg_id_kecc':'6839',
#     'sailor_vec_min_score_history_qa':'0.7',
#     'sailor_vec_knn_k_history_qa':'10',
#     'sailor_vec_size_history_qa':'10',
#     'kg_id_history_qa':'19467',
#     'sailor_token_tactics_history_qa':'1',
#     'sailor_search_qa_llm_temperature':'0',
#     'sailor_search_qa_llm_top_p':'1',
#     'sailor_search_qa_llm_presence_penalty':'0',
#     'sailor_search_qa_llm_frequency_penalty':'0',
#     'sailor_search_qa_llm_max_tokens':'8000',
#     'sailor_search_qa_llm_input_len':'4000',
#     'sailor_search_qa_llm_output_len':'4000',
#     'sailor_search_qa_cites_num_limit':'50'
# }