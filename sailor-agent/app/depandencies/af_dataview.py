# -*- coding: utf-8 -*-
# @Author:  Lareina.guo@aishu.cn
# @Date: 2024-6-7
import json
from typing import Any, List, Union
import jieba

from app.api.af_api import Services
from app.api.error import AfDataSourceError, VirEngineError, FrontendColumnError, FrontendSampleError
from app.datasource.db_base import DataSource
from app.logs.logger import logger
# from data_retrieval.parsers.text2sql_parser import RuleBaseSource
# from data_retrieval.datasource.dimension_reduce import DimensionReduce
# from data_retrieval.sessions.redis_session import RedisConnect
from app.utils.stop_word import get_default_stop_words
from config import settings


CREATE_SCHEMA_TEMPLATE = """CREATE TABLE {source}.{schema}.{title}
(
{middle}
);
"""

RESP_TEMPLATE = """根据<strong>"{table}"</strong><i slice_idx=0>{index}</i>，检索到如下数据："""


# 入参原为 resp_column ， 改为 view_fields
def get_view_en2type(view_fields):
    en2type = {}
    column_name = []
    # 一个逻辑视图的所有字段
    for field in view_fields["fields"]:
        # en2type 是字段英文名称（技术名称）为key， 数据类型为value的字典
        en2type[field["technical_name"]] = field["data_type"]
        # column_name 是字段英文名称（技术名称）列表
        column_name.append(f'"{field["technical_name"]}"')
    # table 是数据虚拟化引擎中数据源的名称.逻辑视图的英文名称（技术名称）
    table = view_fields["view_source_catalog_name"] + "." + view_fields["technical_name"]
    # zh_table 是表的中文名称（业务名称）
    zh_table = view_fields["business_name"]
    return en2type, column_name, table, zh_table


# en2type 是字段英文名称（技术名称）为key， 数据类型为value的字典
# column_name 是字段英文名称（技术名称）列表
# table 是数据虚拟化引擎中数据源的名称.逻辑视图的英文名称（技术名称）
# zh_table 是表的中文名称（业务名称）


def get_table_info(table: str) -> dict:
    table_paths = table.split(".")
    if len(table_paths) == 3:
        title = table_paths[2]
        catalog = table_paths[0]
        schema = "default"
    elif len(table_paths) == 4:
        title = table_paths[3]
        catalog = ".".join(table_paths[:2])
        schema = table_paths[2]
    else:
        raise ValueError(f"Invalid table path: {table}")
    return {
        "title": title,
        "view_source_catalog": catalog,
        "schema": schema
    }


def view_source_reshape(asset: dict) -> dict:
    data_source = {
        "index": asset["index"],
        "title": asset["title"],
        "schema": asset["schema"],  # 逻辑全是默认： default
        "source": asset["view_source_catalog"],
    }
    return data_source


# 入参 column 改为 view_fields
def get_view_schema_of_table(source: dict, view_fields: dict, zh_table, description) -> dict:
    # en2cn 是字段英文名称（技术名称）为key， 字段中文名称（业务名称）为value的字典
    res = {}
    en2cn: dict = {}
    middle: str = ""
    for entry in view_fields["fields"]:
        en2cn[entry["technical_name"]] = entry["business_name"]
        middle += "\t{column_en} {column_type} comment '{column_cn}'\n"
        middle = middle.format(
            column_en=entry["technical_name"],
            column_cn=entry["business_name"],
            column_type=entry["original_data_type"],
        )
    schema = CREATE_SCHEMA_TEMPLATE.format(
        title=source["title"],
        schema=source["schema"],
        source=source["source"],
        middle=middle
    ).strip()

    table = "{source}.{schema}.{title}".format(
        title=source["title"],
        schema=source["schema"],
        source=source["source"]
    )

    res["id"] = source["index"]
    res["name"] = zh_table
    res["en_name"] = source["title"]
    res["description"] = description
    res["ddl"] = schema
    res["en2cn"] = en2cn
    return res


def _query_generator(cur, query: str, as_dict):
    res = cur.execute(query)
    headers = [desc[0] for desc in res.description]

    def result_gen():
        for row in res:
            if as_dict:
                yield dict(zip(headers, row))
            yield row

    return headers, result_gen()


def _query(cur, query: str, as_dict):
    res = cur.execute(query)
    headers = [desc[0] for desc in res.description]

    data = res.fetchall()
    if as_dict:
        return headers, [dict(zip(headers, row)) for row in data]

    return headers, data


class AFDataSource(DataSource):
    """AF data source
    Connect af database with read-only mode
    """
    view_list: list = []
    user_id: str
    user: str = "admin"
    # password: str
    # af_ip: str
    token: str
    headers: Any
    service: Any = None
    dimension_reduce: Any = None
    dimension_reduce_type: str = "default"  # default 默认为向量匹配， opensearch opensearch搜索， llm 大模型
    dimension_reduce_kg_id: str = ""
    dimension_reduce_kg_type: str = "resource"
    dimension_reduce_app_id: str = ""
    field_entity_name: str = ""
    base_url: str = ""
    model_data_view_fields: dict = None  # 主题模型、专题模型字段，筛选专用
    special_data_view_fields: dict = None  # 指定字段
    redis_client: Any = None

    def __init__(
            self,
            **kwargs
    ):
        super().__init__(**kwargs)

        # self.token = get_authorization(self.af_ip, self.user, self.password)
        self.headers = {"Authorization": self.token}
        self.view_list = self.view_list

        self.base_url = settings.DATA_VIEW_URL
        self.service = Services(base_url=self.base_url)
        # self.dimension_reduce = DimensionReduce(dimension_reduce_type=self.dimension_reduce_type,
        #                                         dimension_reduce_kg_id=self.dimension_reduce_kg_id,
        #                                         dimension_reduce_kg_type=self.dimension_reduce_kg_type,
        #                                         dimension_reduce_app_id=self.dimension_reduce_app_id,
        #                                         field_entity_name=self.field_entity_name)
        self.model_data_view_fields = self.model_data_view_fields
        self.special_data_view_fields = self.special_data_view_fields

        # if self.redis_client is None:
        #     self.redis_client = RedisConnect().connect()

    def get_rule_base_params(self):
        # tables = []
        # en2types = {}
        # try:
        #     for view_id in self.view_list:
        #         column = self.service.get_view_column_by_id(view_id, headers=self.headers)
        #         totype, column_name, table, zh_table = get_view_en2type(column)
        #         tables.append(table)
        #         en2types[table] = totype
        # except AfDataSourceError as e:
        #     raise FrontendColumnError(e) from e
        # rule_base = RuleBaseSource(tables=tables, en2types=en2types)
        return None

    def get_metadata_async(self, identities: Union[List, str] = None) -> List[Any]:
        """Get meta information
        """
        return []

    def query_async(self, query: str, as_gen=True, as_dict=True) -> dict:
        """Get data from data source
        """
        return {}

    def test_connection(self):
        return True

    def set_tables(self, tables: List[str]):
        self.view_list = tables

    def get_tables(self) -> List[str]:
        return self.view_list

    def query(self, query: str, as_gen=True, as_dict=True) -> dict:
        print(f'虚拟引擎查询语句 query: {query}')
        try:
            table = self.service.exec_vir_engine_by_sql(self.user, self.user_id, query)
        except AfDataSourceError as e:
            raise VirEngineError(e) from e
        return table

    def get_metadata(self, identities=None) -> list:
        details = []
        try:
            for view_id in self.view_list:
                column = self.service.get_view_column_by_id(view_id, headers=self.headers)
                totype, column_name, table, zh_table = get_view_en2type(column)
                asset = get_table_info(table)
                asset["index"] = view_id
                source = view_source_reshape(asset)
                description = self.service.get_view_details_by_id(view_id, headers=self.headers)
                detail = get_view_schema_of_table(source, column, zh_table, description["description"])
                details.append(detail)
        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e
        return details

    def get_sample(
            self,
            identities=None,
            num: int = 5,
            as_dict: bool = False
    ) -> list:
        samples = {}
        try:
            for view in self.view_list:
                if isinstance(view, str):
                    view_id = view
                else:
                    view_id = view["id"]

                column = self.service.get_view_column_by_id(view_id, headers=self.headers)
                totype, column_name, table, zh_table = get_view_en2type(column)
                asset = get_table_info(table)
                asset["index"] = view_id
                source = view_source_reshape(asset)
                sample = self.service.get_view_sample_by_source(source, headers=self.headers)

                id_sample = {
                    columns["name"]: data.strip() if isinstance(data, str) else data
                    for data, columns in zip(sample["data"][0], sample["columns"])
                }
                samples[view_id] = id_sample
        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e
        return samples

    def get_meta_sample_data(self, input_query="", view_limit=5, dimension_num_limit=30, with_sample=True,
                             extract_info=dict()) -> dict:
        details = []
        samples = {}
        logger.info("get meta sample data query {} dimension_num_limit {}".format(input_query, dimension_num_limit))
        try:
            view_infos = {}
            view_white_list_sql_infos = {}  # 白名单筛选sql
            view_desensitization_field_infos = {}  # 字段脱敏
            view_classifier_field_list = {}  # 分类分级
            view_schema_infos = {}  # 表头名字
            for view_id in self.view_list:
                view_infos[view_id] = self.service.get_view_details_by_id(view_id, headers=self.headers)
                try:
                    view_white_list_sql_infos[view_id] = self.service.get_view_white_policy_sql(view_id,
                                                                                                headers=self.headers)
                except AfDataSourceError as e:
                    logger.error(f"get view white list sql info error: {e}")
                try:
                    view_filed_infos = self.service.get_view_field_info(view_id, headers=self.headers)
                    view_valid_list = []
                    view_desensitization_field_info = dict()
                    if "field_list" in view_filed_infos and len(view_filed_infos["field_list"]):
                        view_valid_list = [item["field_id"] for item in view_filed_infos["field_list"]]
                        for item in view_filed_infos["field_list"]:
                            if item.get("field_desensitization_method", "") != "":
                                view_desensitization_field_info[item["field_name"]] = {
                                    "field_desensitization_method": item["field_desensitization_method"],
                                    "field_desensitization_algorithm": item["field_desensitization_algorithm"],
                                    "field_desensitization_middle_bit": item["field_desensitization_middle_bit"],
                                    "field_desensitization_head_bit": item["field_desensitization_head_bit"],
                                    "field_desensitization_tail_bit": item["field_desensitization_tail_bit"],
                                }

                    view_classifier_field_list[view_id] = view_valid_list
                    if view_desensitization_field_info:
                        view_desensitization_field_infos[view_id] = view_desensitization_field_info
                except AfDataSourceError as e:
                    logger.error(f"get desensitization field infos error: {e}")
            reduced_view = self.dimension_reduce.datasource_reduce(input_query, view_infos, view_limit)

            # 降维
            column_infos = {}
            common_filed = []
            words = set()

            first = True
            for view_id in reduced_view.keys():
                column = self.service.get_view_column_by_id(view_id, headers=self.headers)
                column_infos[view_id] = column

                if first:
                    common_filed = [field["technical_name"] for field in column["fields"]]
                    first = False
                    for field in column["fields"]:
                        business_name = field["business_name"]
                        business_name_word = business_name.split("_")
                        for b_word in business_name_word:
                            if b_word in words:
                                continue
                            words.add(b_word)
                            jieba.add_word(b_word, freq=100, tag="n")
                else:
                    n_common_field = []
                    for field in column["fields"]:
                        if field["technical_name"] in common_filed:
                            n_common_field.append(field["technical_name"])
                        business_name = field["business_name"]
                        business_name_word = business_name.split("_")
                        for b_word in business_name_word:
                            if b_word in words:
                                continue
                            words.add(b_word)

                            jieba.add_word(b_word, freq=100, tag="n")
                    common_filed = n_common_field

            query_seg_list = [q_cut.lower() for q_cut in jieba.cut(input_query, cut_all=False) if q_cut.lower().strip()]
            logger.info("query cut result {}".format(query_seg_list))
            stop_set = get_default_stop_words()
            query_seg_list = [q_word for q_word in query_seg_list if q_word not in stop_set]
            logger.info("off stop word query cut result {}".format(query_seg_list))
            if len(reduced_view) < 4:
                common_filed = []

            for view_id, column in column_infos.items():
                o_column_info = [field["technical_name"] for field in column["fields"]]  # 原始字段信息
                # column = self.service.get_view_column_by_id(view_id, headers=self.headers)
                special_fields = []
                # 指定字段必须保留
                if self.special_data_view_fields is not None and view_id in self.special_data_view_fields:
                    special_fields = [field["technical_name"] for field in self.special_data_view_fields[view_id]]
                    logger.info("优先保留字段有{}".format(special_fields))

                # column["fields"] = self.dimension_reduce.data_view_reduce(input_query, column["fields"], dimension_num_limit, common_filed+special_fields, query_seg_list, view_id)
                column["fields"] = self.dimension_reduce.data_view_reduce(input_query=input_query,
                                                                          input_fields=column["fields"],
                                                                          num=dimension_num_limit,
                                                                          input_common_fields=common_filed + special_fields,
                                                                          input_query_seg_list=query_seg_list,
                                                                          input_data_view_id=view_id)

                # 分类分级过滤
                if view_id in view_classifier_field_list and len(view_classifier_field_list[view_id]):
                    n_column_fields = []
                    num_fields = len(column["fields"])
                    for n_field in column["fields"]:
                        if n_field["id"] in view_classifier_field_list[view_id]:
                            n_column_fields.append(n_field)
                    column["fields"] = n_column_fields
                    logger.info("view_id {} 字段数量 {} 分类分级过滤后字段数量 {}".format(view_id, num_fields,
                                                                                          len(n_column_fields)))

                # 主题模型 专题模型筛选
                if self.model_data_view_fields is not None and view_id in self.model_data_view_fields:
                    n_column_fields = []
                    num_fields = len(column["fields"])
                    model_field_ids = {_field["field_id"] for _field in self.model_data_view_fields[view_id]}
                    for n_field in column["fields"]:
                        if n_field["id"] in model_field_ids:
                            n_column_fields.append(n_field)
                    column["fields"] = n_column_fields
                    logger.info("view_id {} 字段数量 {} 模型字段过滤后字段数量 {}".format(view_id, num_fields,
                                                                                          len(n_column_fields)))
                logger.info("view_id {} 字段最后保留字段为 {}".format(view_id, [_filed["technical_name"] for _filed in
                                                                                column["fields"]]))

                totype, column_name, table, zh_table = get_view_en2type(column)
                asset = get_table_info(table)
                asset["index"] = view_id
                source = view_source_reshape(asset)
                description = view_infos[view_id]
                detail = get_view_schema_of_table(source, column, zh_table, description["description"])
                details.append(detail)
                view_schema_infos[view_id] = asset["view_source_catalog"]

                if with_sample:
                    dict_sample = {}
                    # select_field_sql = ",".join([_filed["technical_name"] for _filed in column["fields"]])
                    table = "{source}.{schema}.{title}".format(
                        title=source["title"],
                        schema=source["schema"],
                        source=source["source"]
                    )

                    _sample_state = 0
                    sample = dict()
                    if self.redis_client.exists(table):
                        try:
                            sample_json = self.redis_client.get(table)
                            sample = json.loads(sample_json)

                            sample_columns = [column["name"] for column in sample.get("columns", [])]

                            for sc in sample_columns:
                                if sc not in o_column_info:
                                    _sample_state = 1
                                    break
                            for sc in o_column_info:
                                if sc not in sample_columns:
                                    _sample_state = 1
                                    break
                            if _sample_state == 1:
                                logger.info("table {} 字段发生变化".format(table))
                                sample = dict()
                            else:

                                logger.info("table {} 样例使用缓存".format(table))
                        except Exception as e:
                            _sample_state = 1
                            logger.warn("获取缓存失败")
                            sample = dict()
                    else:
                        _sample_state = 1
                    if _sample_state == 1:
                        select_field_sql = "*"

                        sql = "select {} from {} limit 1".format(select_field_sql, table)
                        logger.info("sample sql {}".format(sql))
                        try:
                            sample = self.service.exec_vir_engine_by_sql(self.user, self.user_id, sql)
                            self.redis_client.setex(table, time=60 * 60 * 24, value=json.dumps(sample))
                        except Exception as e:
                            logger.warn("存缓存失败, {}".format(e))
                            if len(sample) == 0:
                                sample = dict()
                    # logger.info("{}".format(sample))

                    if "data" in sample and len(sample["data"]) > 0:
                        for data, columns in zip(sample["data"][0], sample["columns"]):
                            for field in column["fields"]:
                                if field["technical_name"] == columns["name"]:
                                    # 加 strip 是方式某些字段类型用空格进行填充
                                    dict_sample[field["business_name"]] = data.strip() if isinstance(data,
                                                                                                     str) else data
                                    break

                    samples[view_id] = dict_sample

                    logger.info("get sample data num {}".format(len(dict_sample)))


        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e

        result = {
            "detail": details,
            "view_schema_infos": view_schema_infos
        }

        if view_white_list_sql_infos:
            result["view_white_list_sql_infos"] = view_white_list_sql_infos
        if view_desensitization_field_infos:
            result["view_desensitization_field_infos"] = view_desensitization_field_infos

        if with_sample:
            result["sample"] = samples
        return result

    def get_meta_sample_data_v2(self, input_query):
        details = []
        column_infos = dict()
        view_infos = dict()
        view_schema_infos = dict()

        for view_id in self.view_list:
            view_infos[view_id] = self.service.get_view_details_by_id(view_id, headers=self.headers)
            column = self.service.get_view_column_by_id(view_id, headers=self.headers)
            column_infos[view_id] = column

        for view_id, column in column_infos.items():
            totype, column_name, table, zh_table = get_view_en2type(column)
            asset = get_table_info(table)
            asset["index"] = view_id
            source = view_source_reshape(asset)
            description = view_infos[view_id]
            detail = get_view_schema_of_table(source, column, zh_table, description["description"])
            detail["department_id"] = description.get("department_id", "")
            detail["department"] = description.get("department", "")
            detail["info_system_id"] = description.get("info_system_id", "")
            detail["info_system"] = description.get("info_system", "")
            details.append(detail)
            view_schema_infos[view_id] = asset["view_source_catalog"]

        result = {
            "detail": details,
            "view_schema_infos": view_schema_infos
        }

        return result

    def get_meta_sample_data_v3(self, with_sample=False):
        details = []
        sample_datas = []
        column_infos = dict()
        view_infos = dict()
        view_schema_infos = dict()

        for view_id in self.view_list:

            view_info = self.service.get_view_details_by_id(view_id, headers=self.headers)
            view_info = {
                 "table_id": view_info['datasource_id'],
                 "table_name": view_info['technical_name'],
                 "table_business_name": view_info['business_name'],
                 "table_description": view_info['description'],
                 "fields": [
                     {"field_id": "f001", "field_name": "user_id", "field_business_name": "用户ID",
                      "field_type": "varchar", "field_description": ""}
                 ]
            }
            fields = [

            ]
            columns = self.service.get_view_column_by_id(view_id, headers=self.headers)
            for column in columns["fields"]:
                fields.append({"field_id": column["id"],
                               "field_name": column['technical_name'],
                               "field_business_name": column['business_name'],
                               "field_type": column['data_type'],
                               "field_description": column['comment']})
            view_info["fields"] = fields

            if with_sample:
                sample_data = self.service.get_data_view_sample_data(view_id, headers=self.headers)
                columns = sample_data["columns"]
                data = sample_data["data"][:2]

                sample_rec_data = [{column["name"]:[da[i] for da in data ]}  for i, column in enumerate(columns)]
                sample_datas.append({"table_name":  view_info['table_name'], "sample": sample_rec_data})
            details.append(view_info)

        result = {
            "detail": details,
            "sample": sample_datas
        }

        return result

    def get_data_view_sample(self):
        sample_details = dict()
        for view_id in self.view_list:
            sample_data = self.service.get_data_view_sample_data(view_id, headers=self.headers)
            sample_details[view_id] = sample_data

        return sample_details



    def get_meta_sample_data_4_seeker(self, input_query="", view_limit=5, dimension_num_limit=30, with_sample=True,
                                      extract_info=dict()) -> dict:
        details = []
        samples = {}
        logger.info("get meta sample data query for data seeker {} dimension_num_limit {}".format(input_query,
                                                                                                  dimension_num_limit))
        try:
            view_infos = {}
            # view_white_list_sql_infos = {}  # 白名单筛选sql
            # view_desensitization_field_infos = {}  # 字段脱敏
            # view_classifier_field_list = {}  # 分类分级
            view_schema_infos = {}  # 表头名字
            for view_id in self.view_list:
                # 获取逻辑视图详情
                view_infos[view_id] = self.service.get_view_details_by_id(view_id, headers=self.headers)


            # 降维
            column_infos = {}
            common_filed = []
            words = set()

            first = True
            # for view_id in reduced_view.keys():
            for view_id in view_infos.keys():
                # column ·改名为 view_fields
                view_fields = self.service.get_view_column_by_id(
                    view_id=view_id,
                    headers=self.headers
                )
                #
                column_infos[view_id] = view_fields

            if len(reduced_view) < 4:
                common_filed = []

            for view_id, view_fields in column_infos.items():
                o_column_info = [field["technical_name"] for field in view_fields["fields"]]  # 原始字段信息

                en2type, column_name, table, zh_table = get_view_en2type(
                    view_fields=view_fields
                )
                # asset 结构
                # {
                #     "title": title,
                #     "view_source_catalog": catalog,
                #     "schema": schema
                # }
                asset = get_table_info(
                    table=table
                )
                asset["index"] = view_id
                # source 结构
                # {
                #         "index": asset["index"],
                #         "title": asset["title"],
                #         "schema": asset["schema"],  # 逻辑全是默认： default
                #         "source": asset["view_source_catalog"],
                #     }
                source = view_source_reshape(
                    asset=asset
                )
                description = view_infos[view_id]
                # detail 结构
                # res["id"] = source["index"]
                #     res["name"] = zh_table
                #     res["en_name"] = source["title"]
                #     res["description"] = description
                #     res["ddl"] = schema
                #     res["en2cn"] = en2cn
                detail = get_view_schema_of_table(
                    source=source,
                    view_fields=view_fields,
                    zh_table=zh_table,
                    description=description["description"]
                )

                details.append(detail)

                view_schema_infos[view_id] = asset["view_source_catalog"]

                if with_sample:
                    dict_sample = {}
                    # select_field_sql = ",".join([_filed["technical_name"] for _filed in column["fields"]])
                    table = "{source}.{schema}.{title}".format(
                        title=source["title"],
                        schema=source["schema"],
                        source=source["source"]
                    )

                    _sample_state = 0
                    sample = dict()
                    if self.redis_client.exists(table):
                        try:
                            sample_json = self.redis_client.get(table)
                            sample = json.loads(sample_json)

                            sample_columns = [column["name"] for column in sample.get("columns", [])]

                            for sc in sample_columns:
                                if sc not in o_column_info:
                                    _sample_state = 1
                                    break
                            for sc in o_column_info:
                                if sc not in sample_columns:
                                    _sample_state = 1
                                    break
                            if _sample_state == 1:
                                logger.info("table {} 字段发生变化".format(table))
                                sample = dict()
                            else:

                                logger.info("table {} 样例使用缓存".format(table))
                        except Exception as e:
                            _sample_state = 1
                            logger.warn("获取缓存失败")
                            sample = dict()
                    else:
                        _sample_state = 1
                    if _sample_state == 1:
                        select_field_sql = "*"

                        sql = "select {} from {} limit 1".format(select_field_sql, table)
                        logger.info("sample sql {}".format(sql))
                        try:
                            sample = self.service.exec_vir_engine_by_sql(self.user, self.user_id, sql)
                            self.redis_client.setex(table, time=60 * 60 * 24, value=json.dumps(sample))
                        except Exception as e:
                            logger.warn("存缓存失败, {}".format(e))
                            if len(sample) == 0:
                                sample = dict()
                    # logger.info("{}".format(sample))

                    if "data" in sample and len(sample["data"]) > 0:
                        for data, columns in zip(sample["data"][0], sample["columns"]):
                            for field in column["fields"]:
                                if field["technical_name"] == columns["name"]:
                                    # 加 strip 是方式某些字段类型用空格进行填充
                                    dict_sample[field["business_name"]] = data.strip() if isinstance(data,
                                                                                                     str) else data
                                    break

                    samples[view_id] = dict_sample

                    logger.info("get sample data num {}".format(len(dict_sample)))


        except AfDataSourceError as e:
            raise FrontendColumnError(e) from e

        result = {
            "detail": details,
            "view_schema_infos": view_schema_infos
        }

        # if view_white_list_sql_infos:
        #     result["view_white_list_sql_infos"] = view_white_list_sql_infos
        # if view_desensitization_field_infos:
        #     result["view_desensitization_field_infos"] = view_desensitization_field_infos

        if with_sample:
            result["sample"] = samples
        return result

    def get_sample_data(self, view_id, with_sample=False):
        pass

    def query_correction(self, query: str) -> str:
        return query

    def close(self):
        # self.connection.close()
        pass

    def get_description(self) -> list[dict[str, str]]:
        descriptions = []
        try:
            for view_id in self.view_list:
                detail = self.service.get_view_details_by_id(view_id, headers=self.headers)
                description = {}
                description.update({"name": detail.get("business_name", "")})
                description.update({"description": detail.get("description", "")})
                descriptions.append(description)
        except FrontendColumnError as e:
            logger.error(e)
        except FrontendSampleError as e:
            logger.error(e)
        return descriptions

    def get_catelog(self) -> list[str]:
        text2sql = Services()
        catelogs = []
        try:
            for view_id in self.view_list:
                column = text2sql.get_view_column_by_id(view_id, headers=self.headers)
                totype, column_name, table, zh_table = get_view_en2type(column)
                catelogs.append(table)
        except FrontendColumnError as e:
            logger.error(e)
        return catelogs