# -*- coding: utf-8 -*-
# @Author:  Lareina.guo@aishu.cn
# @Date: 2024-6-7
import json
from typing import Any, List

from app.api.af_api import Services
from app.api.error import AfDataSourceError, VirEngineError, FrontendColumnError, FrontendSampleError
from app.datasource.db_base import DataSource
from app.logs.logger import logger
from data_retrieval.datasource.dimension_reduce import DimensionReduce
from app.session.redis_session import RedisConnect


class AFDataCatalog(DataSource):
    """AF catalog data source
    Connect af catalog database with read-only mode
    """
    data_catalog_list: list = []
    user_id: str
    user: str = "admin"
    token: str
    headers: Any
    service: Any = None
    dimension_reduce: Any = None
    dimension_reduce_type: str = "default"  # default 默认为向量匹配， opensearch opensearch搜索， llm 大模型
    dimension_reduce_kg_id: str = ""
    dimension_reduce_kg_type: str = "data_catalog"
    dimension_reduce_app_id: str = ""
    field_entity_name: str = ""
    base_url: str = ""
    redis_client: Any = None

    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.headers = {"Authorization": self.token}
        self.data_catalog_list = self.data_catalog_list
        self.service = Services(base_url=self.base_url)
        self.dimension_reduce = DimensionReduce()
        self.redis_client = RedisConnect().connect()

    def get_rule_base_params(self):
        # 数据目录规则
        return []

    def test_connection(self):
        return True

    def set_tables(self, tables: List[str]):
        self.data_catalog_list = tables

    def get_tables(self) -> List[str]:
        return self.data_catalog_list

    def query(self, query: str, as_gen=True, as_dict=True) -> dict:
        # TODO: 数据目录查询
        return {}

    def get_columns_by_id(self, data_catalog_id: str) -> dict:
        data_catalog_fields = self.service.get_data_catalog_fields_by_id(data_catalog_id, headers=self.headers)

        columns = []

        total_count = data_catalog_fields.get("total_count", 0)

        fields = data_catalog_fields.get("columns", [])
        for field in fields:
            columns.append({
                "business_name": field.get("business_name", ""),
                "technical_name": field.get("technical_name", ""),
                "field_id": field.get("id", ""),
            })

        while len(columns) < total_count:
            data_catalog_fields = self.service.get_data_catalog_fields_by_id(data_catalog_id, headers=self.headers, offset=len(columns) + 1)
            fields = data_catalog_fields.get("columns", [])
            for field in fields:
                columns.append({
                    "business_name": field.get("business_name", ""),
                    "technical_name": field.get("technical_name", ""),
                    "field_id": field.get("id", ""),
                })

        return columns

    def get_metadata(self, identities=None) -> list:
        details = []
        try:
            for data_catalog_id in self.data_catalog_list:
                data_catalog_detail = self.service.get_data_catalog_detail_by_id(data_catalog_id, headers=self.headers)
                columns = self.get_columns_by_id(data_catalog_id)                
                details.append({
                    "id": data_catalog_id,
                    "name": data_catalog_detail.get("name", ""),
                    "description": data_catalog_detail.get("description", ""),
                    "columns": columns,
                })
        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e
        return details

    def get_sample(
        self,
        identities=None,
        num: int = 5,
        as_dict: bool = False
    ) -> list:
        # 数据目录暂不支持获取样例数据
        return {}

    def get_meta_sample_data(self, input_query="", data_catalog_limit=5, dimension_num_limit=30, with_sample=True, extract_info=dict(), with_white_policy=True, with_desensitization=True)->dict:
        details = []
        logger.info("get meta sample data query {} dimension_num_limit {}".format(input_query, dimension_num_limit))
        try:
            data_catalog_infos = {}
            for data_catalog_id in self.data_catalog_list:
                data_catalog_detail = self.service.get_data_catalog_detail_by_id(data_catalog_id, headers=self.headers)
                data_catalog_infos[data_catalog_id] = data_catalog_detail

            # 数据目录直接返回
            # TODO: 数据目录降维, 获取样例数据
            reduced_data_catalog = self.dimension_reduce.datasource_reduce(
                input_query,
                data_catalog_infos,
                data_catalog_limit,
                datasource_type="data_catalog"
            )
            column_infos = {}
            for k, v in reduced_data_catalog.items():
                columns = self.get_columns_by_id(k)
                reduced_columns = self.dimension_reduce.indicator_reduce(
                    input_query,
                    input_analysis_dimensions=columns,
                    num=dimension_num_limit,
                )

                column_infos[k] = reduced_columns

            for k, v in reduced_data_catalog.items():
                details.append({
                    "id": k,
                    "name": v.get("name", ""),
                    "description": v.get("description", ""),
                    "columns": column_infos[k]
                })
            
        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e

        result = {
            "detail": details,
        }
        return result

    def get_meta_sample_data_v2(self, input_query="", data_catalog_limit=5, dimension_num_limit=30) -> dict:
        details = []
        logger.info("get meta sample data query {} dimension_num_limit {}".format(input_query, dimension_num_limit))
        try:
            data_catalog_infos = {}
            for data_catalog_id in self.data_catalog_list:
                data_catalog_detail = self.service.get_data_catalog_detail_by_id(data_catalog_id, headers=self.headers)
                data_catalog_infos[data_catalog_id] = data_catalog_detail

            # 数据目录直接返回
            # TODO: 数据目录降维, 获取样例数据
            # reduced_data_catalog = self.dimension_reduce.datasource_reduce(
            #     input_query,
            #     data_catalog_infos,
            #     data_catalog_limit,
            #     datasource_type="data_catalog"
            # )
            column_infos = {}
            for k, v in data_catalog_infos.items():
                columns = self.get_columns_by_id(k)

                column_infos[k] = columns

            for k, v in data_catalog_infos.items():
                details.append({
                    "id": k,
                    "name": v.get("name", ""),
                    "description": v.get("description", ""),
                    "department_id": v.get("department_id", ""),
                    "department": v.get("department", ""),
                    "info_system_id": v.get("info_system_id", ""),
                    "info_system": v.get("info_system", ""),
                    "columns": column_infos[k]
                })

        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e

        result = {
            "detail": details,
        }
        return result

    def query_correction(self, query: str) -> str:
        return query

    def close(self):
        pass

    def get_description(self) -> list[dict[str, str]]:
        descriptions = []
        try:
            for data_catalog_id in self.data_catalog_list:
                detail = self.service.get_data_catalog_detail_by_id(data_catalog_id, headers=self.headers)
                description = {}
                description.update({"name": detail.get("name", "")})
                description.update({"description": detail.get("description", "")})
                descriptions.append(description)
        except FrontendColumnError as e:
            logger.error(e)
        except FrontendSampleError as e:
            logger.error(e)
        return descriptions

