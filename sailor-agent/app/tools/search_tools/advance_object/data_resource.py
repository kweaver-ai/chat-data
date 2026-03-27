# -*- coding: utf-8 -*-
# @Time    : 2026/1/4 11:49
# @Author  : Glen.lv
# @File    : datasource_filter_v2
# @Project : af-agent

import json
import traceback
from io import StringIO
from textwrap import dedent
from typing import Optional, Type, Any, List, Dict, Callable
from collections import OrderedDict
from enum import Enum
import re
import asyncio

import pandas as pd
from app.api.af_api import Services
from app.tools.search_tools.datasource_filter import DataSourceFilterTool
from app.datasource.af_data_catalog import AFDataCatalog
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field, PrivateAttr

from app.logs.logger import logger

from app.depandencies.af_indicator import AFIndicator

from app.utils.llm_utils import estimate_tokens_safe


class DataResource:
    data_view_list: Dict[str, dict] = {}
    metric_list: Dict[str, dict] = {}
    data_catalog_list: Dict[str, dict] = {}
    all_data_resources: List[dict] = []
    data_resource_list_description: str = ""
    invalid_type: str = ""

    batch_size: int = 10  # map-reduce 批次大小，每批处理的数据源数量（回退方案）
    max_tokens_per_chunk: Optional[int] = None  # 每个批次的最大 token 数，如果设置则按 token 数分块
    search_configs: Optional[Any] = None
    data_resource_num_limit: int = -1  # 数据资源数量上限，-1代表不限制
    dimension_num_limit: int = -1  # 字段（维度）数量上限，-1代表不限制

    service: Any = None
    headers: Dict[str, str] = Field(default_factory=dict)  # HTTP 请求头
    query: str = ""
    token: str = ""
    user_id: str = ""

    def __init__(self, *args, **kwargs):
        logger.info(f'*args={args}, \n**kwargs={kwargs}')
        data_resource_list = kwargs.pop("data_resource_list", [])
        data_resource_list_description = kwargs.pop("data_resource_list_description", "")
        # 赋值
        self.data_resource_list_description = data_resource_list_description
        self.max_tokens_per_chunk = kwargs.pop("max_tokens_per_chunk", None)
        self.search_configs = kwargs.pop("search_configs", None)
        self.batch_size = kwargs.pop("batch_size", 10)
        self.data_resource_num_limit = kwargs.pop("data_resource_num_limit", -1)
        self.dimension_num_limit = kwargs.pop("dimension_num_limit", -1)
        self.user_id = kwargs.pop("user_id", "")
        self.headers = {}
        self.token = kwargs.pop("token", "")
        if self.token != "":
            self.headers = {"Authorization": self.token}

        for data_resource in data_resource_list:
            if data_resource["type"] == "data_view":
                self.data_view_list[data_resource["id"]] = data_resource
            elif data_resource["type"] == "indicator":
                self.metric_list[data_resource["id"]] = data_resource
            elif data_resource["type"] == "data_catalog":
                self.data_catalog_list[data_resource["id"]] = data_resource
            else:
                self.invalid_type = data_resource['type']
                break

    def valid(self) -> dict:
        """
        1:校验数据资源是否包含无效类型
        2:校验所有数据资源是否为空
        """
        if not self.invalid_type:
            return {
                "result": f"数据资源类型错误: {self.invalid_type}"
            }
        if not self.data_view_list and not self.metric_list and not self.data_catalog_list:
            return {
                "result": f"没有找到符合要求的数据源"
            }
        return None

    async def init_all_data_resources(self, query: str):
        self.query = query
        all_data_resources = []
        # 为数据视图添加字段信息、样例数据和枚举值
        if len(self.data_view_list) > 0:
            self.all_data_resources += list(self.data_view_list.values())
            logger.info(f'data_view_list={self.data_view_list}')
            await self._enrich_data_view_with_field_info(self.data_view_list)

        # 为指标数据源补充字段列信息
        if len(self.metric_list) > 0:
            self.all_data_resources += list(self.metric_list.values())
            logger.info(f'metric_list={self.metric_list}')
            await  self._enrich_metric_list_with_columns(self.metric_list, query)

        # 为数据目录补充字段列信息
        if len(self.data_catalog_list) > 0:
            self.all_data_resources += list(self.data_catalog_list.values())
            logger.info(f'data_catalog_list={self.data_catalog_list}')
            await self._enrich_data_catalog_list_with_columns(self.data_catalog_list, query)

        self.all_data_resources = all_data_resources

    async def _enrich_data_catalog_list_with_columns(self, data_catalog_list: Dict[str, dict], query: str) -> None:
        catalog_source = AFDataCatalog(
            data_catalog_list=list(data_catalog_list.keys()),
            token=self.token,
            user_id=self.user_id
        )
        catalog_metadata = catalog_source.get_meta_sample_data_v2(
            query,
            self.data_resource_num_limit,
            self.dimension_num_limit,
        )

        for k, v in data_catalog_list.items():
            for detail in catalog_metadata["detail"]:
                if detail["id"] == k:
                    v["columns"] = detail.get("columns", {})
                    break

    async def _enrich_metric_list_with_columns(self, metric_list: Dict[str, dict], query: str) -> None:
        """
        为指标类型的数据源（metric_list）补充字段(columns)信息。

        会调用 AFIndicator.get_details 获取指标的维度信息，并将维度 technical_name -> business_name
        填充到每个指标数据源的 columns 字段中。
        """
        if not metric_list:
            return

        metric_source = AFIndicator(
            indicator_list=list(metric_list.keys()),
            token=self.token,
            user_id=self.user_id
        )
        try:
            metric_metadata = metric_source.get_details(
                input_query=query,
                indicator_num_limit=self.data_resource_num_limit,
                input_dimension_num_limit=self.dimension_num_limit
            )

            for k, v in metric_list.items():
                for detail in metric_metadata.get("details", []):
                    if detail.get("id") == k:
                        v["columns"] = {
                            dimension["technical_name"]: dimension["business_name"]
                            for dimension in detail.get("dimensions", [])
                        }
                        break
        except Exception as e:
            logger.error(f"获取指标元数据失败: {str(e)}")
            # 按原逻辑仅记录错误，不抛出异常

    async def _enrich_data_view_with_field_info(self, data_view_list: Dict[str, dict]) -> None:
        """
        为数据视图列表中的每个视图添加字段信息、样例数据和枚举值到描述中

        Args:
            data_view_list: 数据视图字典，key为视图ID，value为视图信息字典
        """
        # 需要在 description 中加入样例数据和探查结果枚举值
        for hit in data_view_list.values():
            # 挨个查询视图的字段信息
            view_column_info_for_prompt, view_source_catalog_name = await self.service.get_view_column_info_for_prompt(
                idx=hit['id'],
                headers=self.headers
            )
            # 查询视图详情
            view_details = self.service.get_view_details_by_id(
                view_id=hit['id'],
                headers=self.headers
            )

            source, schema = view_source_catalog_name.split('.')
            source_dict = {
                "source": source,  # 数据源在虚拟化引擎中的 catalog, 数据源配置的时候已经固定数据库了
                "schema": schema,  # 固定都是default
                "title": view_details['technical_name']  # 表名
            }
            # 查询视图的样例数据
            sample = await self.service.get_view_sample_by_source(
                source=source_dict,
                headers=self.headers
            )
            # 查询探查结果
            try:
                data_explore_rst = await self.service.get_data_explore(
                    entity_id=hit['id'],
                    headers=self.headers
                )
            except Exception as e:
                logger.warning(f'get_data_explore warning: 探查报告不存在')
                data_explore_rst = []
            if data_explore_rst:
                logger.info(f'data_explore_rst = {data_explore_rst}')

            # 构建字段ID到枚举值的映射
            field_enum_map = {}
            for explore_item in data_explore_rst:
                field_id = explore_item['field_id']
                if explore_item.get('details') and len(explore_item['details']) > 0:
                    result_str = explore_item['details'][0].get('result', '[]')
                    try:
                        enum_data = json.loads(result_str)
                        # 提取枚举值列表（只取key，过滤掉null值）
                        enum_values = [item['key'] for item in enum_data if item.get('key') is not None]
                        if enum_values:  # 只有当枚举值不为空时才添加
                            field_enum_map[field_id] = enum_values
                    except Exception as e:
                        pass

            # 构建技术名称到样例数据的映射
            sample_data = sample['data'][0] if sample.get('data') and len(sample['data']) > 0 else []
            sample_columns = sample.get('columns', [])
            field_sample_map = {}
            for idx, col in enumerate(sample_columns):
                if idx < len(sample_data):
                    field_sample_map[col['name']] = sample_data[idx]

            # 整合字段信息、样例数据和枚举值
            def build_field_info():
                """整合字段信息、样例数据和枚举值"""
                fields_info = []
                for field_info in view_column_info_for_prompt:
                    field_id = field_info['id']
                    technical_name = field_info['technical_name']

                    # 获取样例数据
                    sample_value = field_sample_map.get(technical_name, None)

                    # 获取枚举值
                    enum_values = field_enum_map.get(field_id, None)

                    field_data = {
                        'business_name': field_info['business_name'],
                        'technical_name': technical_name,
                        'comment': field_info['comment'],
                        'data_type': field_info['data_type'],
                        'sample_value': sample_value,
                        'enum_values': enum_values
                    }
                    fields_info.append(field_data)

                return fields_info

            fields_info = build_field_info()

            # 格式化字段信息为长字符串
            def format_to_long_string(fields_info: List[dict], table_description: str = "") -> str:
                """生成长字符串格式的提示词（包含表描述、字段信息、样例数据、枚举值）"""
                # 开始构建字段信息部分
                fields_text = ""

                for idx, field in enumerate(fields_info, 1):
                    # 字段基本信息
                    field_info = f"{field['business_name']}（技术名称：{field['technical_name']}，数据类型：{field['data_type']}"

                    # 添加样例值
                    if field['sample_value'] is not None:
                        sample_str = str(field['sample_value'])
                        # 如果样例值太长，截断
                        if len(sample_str) > 80:
                            sample_str = sample_str[:80] + "..."
                        field_info += f"，样例值：{sample_str}"
                    else:
                        field_info += "，样例值：无"

                    # 添加枚举值（如果有）
                    if field['enum_values']:
                        max_enum_display = 6  # 枚举值最多显示6个，避免过长
                        if len(field['enum_values']) <= max_enum_display:
                            enum_str = '、'.join(map(str, field['enum_values']))
                            field_info += f"，枚举值：{enum_str}（共{len(field['enum_values'])}个）"
                        else:
                            enum_str = '、'.join(map(str, field['enum_values'][:max_enum_display]))
                            field_info += f"，枚举值：{enum_str}等（共{len(field['enum_values'])}个）"

                    field_info += "）"

                    if idx < len(fields_info):
                        fields_text += field_info + "；"
                    else:
                        fields_text += field_info

                # 组合成完整的长字符串
                full_prompt = f"{table_description} 字段信息、样例数据、部分字段的枚举值如下：{fields_text}"

                return full_prompt

            # 获取原始描述
            original_description = hit.get('description', '')
            description_append_fields_info = format_to_long_string(
                fields_info,
                table_description=original_description
            )
            hit['description'] = description_append_fields_info

    def _should_use_map_reduce(self) -> bool:
        """
        根据 token 数和数据源数量，结合 search_configs 与 batch_size，判断是否使用 map-reduce。
        可能会在首次调用时自动设置 max_tokens_per_chunk。
        """
        estimated_tokens = estimate_tokens_safe(str(self.all_data_resources))
        logger.info(f'estimated_tokens = {estimated_tokens}')
        # 如果 search_configs 存在，使用它来计算 max_tokens_per_chunk
        if self.search_configs and hasattr(self.search_configs, 'sailor_search_qa_llm_input_len'):
            logger.info(
                f'search_configs.sailor_search_qa_llm_input_len = {self.search_configs.sailor_search_qa_llm_input_len}'
            )
            calculated_max_tokens = int(self.search_configs.sailor_search_qa_llm_input_len) * 0.8
            # 如果用户没有手动设置 max_tokens_per_chunk，则使用计算出的值
            if self.max_tokens_per_chunk is None:
                self.max_tokens_per_chunk = int(calculated_max_tokens)
                logger.info(f'根据 search_configs 自动设置 max_tokens_per_chunk = {self.max_tokens_per_chunk}')
            use_mapreduce = estimated_tokens > calculated_max_tokens
        else:
            use_mapreduce = False

        # 综合判断是否使用 map-reduce 模式
        return (
                use_mapreduce
                or self.max_tokens_per_chunk is not None
                or (len(self.all_data_resources) > self.batch_size and self.batch_size > 0)
        )

    async def run(self, process_batch: Callable) -> List[dict]:
        """
        使用 map-reduce 模式按批次处理所有数据源，并返回合并后的结果列表。
        """
        log_str = f"数据源数量 ({len(self.all_data_resources)}) 超过批次大小 ({self.batch_size})，使用 map-reduce 模式处理"
        if self.max_tokens_per_chunk is not None:
            log_str = f"使用 map-reduce 模式处理，按 token 数分块 (max_tokens_per_chunk={self.max_tokens_per_chunk})"
        logger.info(log_str)

        # 将数据源列表分成多个批次（按 token 数或数量）
        batches = self._split_into_batches()
        logger.info(f"共分成 {len(batches)} 个批次进行处理")

        # 并行处理所有批次
        batch_tasks = []
        for i, batch in enumerate(batches):
            invoke = process_batch(batch, i, len(batches))
            batch_tasks.append(invoke(self.query, self.data_resource_list_description))

        batch_results = await asyncio.gather(*batch_tasks)

        # Reduce 阶段：合并所有批次的结果
        result_datasource_list: List[dict] = []
        for batch_result in batch_results:
            if batch_result and "result" in batch_result:
                result_datasource_list += self._enrich_results(batch_result["result"])

        logger.info(f"map-reduce 处理完成，共筛选出 {len(result_datasource_list)} 个数据源")
        return result_datasource_list

    def _enrich_results(self, result: List[dict]) -> List[dict]:
        """
        对 map-reduce 处理后的结果进行过滤，保留符合条件的数据源。
        """
        result_datasource_list: List[dict] = []
        if not result:
            return result_datasource_list
        for res in result.get("result", []):
            if res["id"] in self.view_ids:
                # 结果中补充 title
                res["title"] = self.data_view_list[res["id"]].get("title", "")
                result_datasource_list.append(res)
            elif res["id"] in self.metric_ids:
                res["title"] = self.metric_list[res["id"]].get("title", "")
                result_datasource_list.append(res)
            elif res["id"] in self.data_catalog_ids:
                res["title"] = self.data_catalog_list[res["id"]].get("title", "")
                result_datasource_list.append(res)
        return result_datasource_list

    def _split_into_batches(self) -> List[List[Any]]:
        """
        将列表分成多个批次，优先按 token 数分块，失败则回退到按数量分块

        Args:
            data_list: 数据源列表
            query: 用户查询
            data_resource_list_description: 数据源列表描述

        Returns:
            分块后的列表
        """
        if not self._should_use_map_reduce():
            return [self.all_data_resources]

        chunks = []

        if self.max_tokens_per_chunk is not None:
            try:
                # 估算固定 token 数：query + prompt模板 + 输出预留
                # query约100 tokens, data_resource_list_description约500 tokens, prompt约500 tokens, 输出预留1000 tokens
                estimated_fixed_tokens = 2100

                # 获取模型的最大 token 长度（如果有的话）
                model_max_tokens = None
                if self.llm and hasattr(self.llm, 'max_tokens'):
                    model_max_tokens = self.llm.max_tokens
                elif self.llm and hasattr(self.llm, 'model_kwargs') and 'max_tokens' in self.llm.model_kwargs:
                    model_max_tokens = self.llm.model_kwargs.get('max_tokens')

                # 计算可用 token 数
                if model_max_tokens:
                    available_tokens = min(
                        self.max_tokens_per_chunk,
                        int(model_max_tokens) - estimated_fixed_tokens
                    )
                else:
                    available_tokens = self.max_tokens_per_chunk - estimated_fixed_tokens

                # 确保 available_tokens 至少为 100，避免过小的值
                if available_tokens < 100:
                    logger.warning(f'计算出的 available_tokens ({available_tokens}) 过小，使用默认值 1000')
                    available_tokens = 1000

                logger.info(f'max_tokens_per_chunk = {self.max_tokens_per_chunk}')
                logger.info(f'model_max_tokens = {model_max_tokens}')
                logger.info(f'available_tokens = {available_tokens}')

                # 按 token 数分块
                current_chunk = []
                current_chunk_tokens = 0

                for item in self.all_data_resources:
                    # 估算当前项的 token 数
                    item_str = json.dumps(item, ensure_ascii=False, separators=(',', ':'))
                    estimated_tokens = estimate_tokens_safe(item_str)

                    # 如果单个数据项的 token 数就超过了可用 token，仍然添加到当前块（避免无限循环）
                    if estimated_tokens > available_tokens:
                        logger.warning(
                            f'单个数据项的 token 数 ({estimated_tokens}) 超过可用 token ({available_tokens})，仍将添加到当前块')

                    if current_chunk_tokens + estimated_tokens > available_tokens and current_chunk:
                        # 当前块已满，开始新块
                        chunks.append(current_chunk)
                        current_chunk = [item]
                        current_chunk_tokens = estimated_tokens
                    else:
                        current_chunk.append(item)
                        current_chunk_tokens += estimated_tokens

                if current_chunk:
                    chunks.append(current_chunk)

                logger.info(f'按token数分块，共 {len(chunks)} 块，每块约 {available_tokens:.0f} tokens')

            except Exception as e:
                logger.warning(f'按token数分块失败: {e}，回退到按数量分块')
                chunks = [self.all_data_resources[i:i + self.batch_size] for i in
                          range(0, len(self.all_data_resources), self.batch_size)]
        else:
            # 按数量分块
            chunks = [self.all_data_resources[i:i + self.batch_size] for i in
                      range(0, len(self.all_data_resources), self.batch_size)]

        logger.info(f'数据分块完成，共 {len(chunks)} 块，每块约 {len(chunks[0]) if chunks else 0} 个数据项')
        return chunks
