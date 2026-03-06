import json
import re
from datetime import datetime
from typing import Any

import pandas as pd
import sqlparse
from sql_metadata import Parser
from sql_metadata.compat import get_query_tables

from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.prompt.text2sql import *

from app.cores.text2sql.t2s_config import MySQLKeyword
from app.cores.text2sql.t2s_error import Text2SQLError
from app.logs.logger import logger
from config import settings
from app.models.code_table_model import *


class RuleCheck:
    def __init__(self):
        pass

    async def add_quotes(self, sql: str, tables: list, en2types: dict, table=None) -> str:
        sets: list = sql.split()
        for item in sets:
            if item in tables:
                table = item
                break
        assert table is not None, Text2SQLError(reason="生成了一个错误的SQL")
        #  zkn
        en2type = en2types[table]
        sets, delete = await self.sub_add_quotes(sets, en2type)
        sql = " ".join([item for idx, item in enumerate(sets) if idx not in delete])
        sets: list = sql.split()
        sets = await self.delete_comment(sets)
        sql = " ".join(sets).rstrip("AND")

        return sql

    @staticmethod
    async def delete_comment(sets: list):
        del_id = []
        for index, chunk in enumerate(sets):
            if chunk == "--":
                if sets[index + 1] == "--":
                    del_id.append(index)
                else:
                    del_id += [index, index + 1]
        sets = [chunk for idx, chunk in enumerate(sets) if idx not in del_id]

        return sets

    @staticmethod
    def check_str(idx, sets):
        ## zkn
        if "))" in sets[idx + 1]:
            sets[idx + 1] = f"'{sets[idx + 1].rstrip(')')}'))"
        if ")" in sets[idx + 1]:
            sets[idx + 1] = f"'{sets[idx + 1].rstrip(')')}')"
        elif sets[idx] in MySQLKeyword.BETWEEN:
            sets[idx + 1] = f"'{sets[idx + 1]}'"
            sets[idx + 3] = f"'{sets[idx + 3]}'"
        else:
            sets[idx + 1] = f"'{sets[idx + 1]}'"
        return sets

    @staticmethod
    def check_date(idx, item, sets):
        # DATE 'DATE(2024-05-10') LIMIT 10
        if "DATE(" in sets[idx + 1]:
            sets[idx + 1] = sets[idx + 1].lstrip("DATE(").rstrip(")")
        if ")" in sets[idx + 1]:
            sets[idx + 1] = f"DATE '{sets[idx + 1].rstrip(')')}')"
        else:
            sets[idx + 1] = f"DATE '{sets[idx + 1]}'"
            if item in MySQLKeyword.BETWEEN and idx + 3 < len(sets):
                if "DATE(" in sets[idx + 3]:
                    sets[idx + 3] = sets[idx + 3].lstrip("DATE(").rstrip(")")
                if ")" in sets[idx + 3]:
                    sets[idx + 3] = f"DATE '{sets[idx + 3].rstrip(')')}')"
                else:
                    sets[idx + 3] = f"DATE '{sets[idx + 3]}'"
        return sets

    @staticmethod
    def check_as(idx, sets):
        if sets[idx + 1][-1] == ",":
            sets[idx + 1] = f'"{sets[idx + 1][:-1]}",'
        else:
            sets[idx + 1] = f'"{sets[idx + 1]}"'
        return sets

    @staticmethod
    def check_order_by(idx, sets):
        sets[idx + 1] = f'"{sets[idx + 1]}"'
        return sets

    @staticmethod
    def check_in(idx, sets):
        for jdx in range(idx + 1, len(sets)):
            if ")" in sets[jdx] and "(" in sets[jdx]:
                sets[jdx] = f"('{sets[jdx].lstrip('(').rstrip(')')}')"
                break
            elif ")" not in sets[jdx]:
                if "(" in sets[jdx]:
                    sets[jdx] = f"('{sets[jdx].lstrip('(').rstrip(',')}',"
                else:
                    sets[jdx] = f"'{sets[jdx].rstrip(',')}',"
            else:
                sets[jdx] = f"'{sets[jdx].rstrip(')')}')"
                break
        return sets

    async def sub_add_quotes(self, sets, en2type):
        delete = []
        # 6 删除 sql 中与问题不相关的 筛选条件
        for idx, item in enumerate(sets):
            if idx + 1 < len(sets):
                if "SELECT" in sets[idx + 1]:
                    continue
                elif idx + 2 < len(sets) and "SELECT" in sets[idx + 2]:
                    continue
                if item in MySQLKeyword.SYMBOLS:
                    try:
                        try:
                            kind = en2type[sets[idx - 1].split(".")[-1].lstrip("(")]
                        except Exception as e:
                            en2type = {key.lower(): value for key, value in en2type.items()}
                            kind = en2type[sets[idx - 1].split(".")[-1].lstrip("(")]
                    except Exception as e:
                        for k, v in en2type.items():
                            if k in sets[idx - 1]:
                                kind = v
                                break
                    if kind in MySQLKeyword.STR:
                        sets = self.check_str(idx, sets)
                    elif kind in MySQLKeyword.DATE:
                        sets = self.check_date(idx, item, sets)
                elif item in MySQLKeyword.AS:
                    sets = self.check_as(idx, sets)
                elif item in MySQLKeyword.BY and sets[idx - 1] in MySQLKeyword.ORDER and sets[idx + 1] not in en2type:
                    sets = self.check_order_by(idx, sets)
                elif item in MySQLKeyword.IN:
                    sets = self.check_in(idx, sets)
        return sets, delete

    @staticmethod
    def extract_sql(sql: str) -> str:
        patterns = [r'```sql(.*?)```', r'```(.*?)```']
        for pattern in patterns:
            match = re.findall(pattern, sql, re.DOTALL)
            if match:
                return match[-1]
        patterns = [r'SELECT.*?;', ]
        for pattern in patterns:
            match = re.search(pattern, sql, re.DOTALL)
            if match:
                sql = match.group()
        return sql

    @staticmethod
    def check_limit(sql: str, config: dict) -> str:
        limit = config["sql_limit"]
        if sql.endswith("WHERE") or sql.endswith("where"):
            sql = sql.replace("WHERE", "").replace("where", "")
        if "limit" not in sql and "LIMIT" not in sql:
            sql += " LIMIT {}".format(limit)
        return sql

    @staticmethod
    async def check_table_name(sql: str, tables: list) -> Any:
        used_table = []
        sets = sql.split()
        for table in tables:
            if table not in sql:
                cache_char01 = ".".join(table.split(".")[1:])
                cache_char02 = table.split(".")[-1]
                if cache_char01 in sql:
                    for s in sets:
                        if cache_char01 == s:
                            sql = sql.replace(".".join(table.split(".")[1:]), table)
                            used_table.append(table)
                elif cache_char02 in sql:
                    for s in sets:
                        if cache_char02 == s:
                            sql = sql.replace(table.split(".")[-1], table)
                            used_table.append(table)
            else:
                for s in sets:
                    if s == table:
                        used_table.append(table)
        return sql, used_table

    @staticmethod
    async def delete_quotes(sql: str) -> str:
        sql = sql.replace("`", "").replace("'", "").replace(";", "").replace('"', "")
        return sql


class Reshape(RuleCheck):
    def __init__(self):
        super().__init__()

    @staticmethod
    async def assets_reshape(ori_assets: dict) -> list:
        assets = []
        for items in ori_assets["entries"]:
            assets.append(
                {
                    "index": items["id"],
                    "title": items["raw_title"],
                    "schema": items["raw_schema_name"],
                    "source": items["raw_data_source_name"],
                    "description": items["raw_description"],
                }
            )
        return assets

    @staticmethod
    async def source_reshape(asset) -> dict:
        print("----source_reshape---> common")
        print()
        print(asset)
        data_source = {
            "index": asset["index"],
            "source_id": asset["source"],
            "schema": asset["schema"],
            "title": asset["technical_name"],
        }
        return data_source

    @staticmethod
    async def view_source_reshape(asset: dict) -> dict:
        data_source = {
            "index": asset["index"],
            "title": asset["title"],
            "schema": "default",  # 逻辑全是默认： default
            "source": asset["view_source_catalog_name"][:-8],
        }
        return data_source

    @staticmethod
    async def get_schema_of_table(source: dict, column: dict) -> tuple:
        en2cn: dict = {}
        middle: str = ""
        for entry in column["fields"]:
            en2cn[entry["technical_name"]] = entry['business_name']
            middle += "{column_en} {column_type} comment '{column_cn}'\n"
            middle = middle.format(
                column_en=entry["technical_name"],
                column_cn=entry["business_name"],
                column_type=MySQLKeyword.MAP_TYPE.get(entry["data_type"], entry["data_type"]),  # 可能不需要映射了
            )

        schema = CREATE_SCHEMA_TEMPLATE.format(
            title=source["title"],
            schema=source["schema"],
            source=source["source_id"],
            middle=middle[: -2]
        )
        table = "{source}.{schema}.{title}".format(
            title=source["title"],
            schema=source["schema"],
            source=source["source_id"]
        )

        return schema, en2cn, table

    @staticmethod
    async def construct_code_table_info_prompt(one_code_table_info: CodeTableDetailModel):
        # 输入一个砝表详情信杯，构造有关这个砝表信杯的prompt
        value_set_info_prompt = ""
        code_table_enum = {}
        for a_value_info in one_code_table_info.enums:
            # zkn 码表值信息
            value_set_info_prompt += ENUM_VALUE_TEMPLATE.format(enum_value_name=a_value_info.value,
                                                                enum_value=a_value_info.code)
            code_table_enum[a_value_info.code] = a_value_info.value

            # if a_value_info.description:
            #     value_set_info_prompt += ENUM_VALUE_DESCRIPTION_TEMPLATE.format(
            #         enum_value_description=a_value_info.description)
            # else:
            #     value_set_info_prompt += "\n"

        # zkn 码表信息汇总
        code_table_info_prompt = ENUM_SET_INFO_TEMPLATE.format(enum_set_name=one_code_table_info.ch_name,
                                                               enum_value_set=value_set_info_prompt)
        return code_table_info_prompt, code_table_enum

    @staticmethod
    async def get_view_schema_of_table(source: dict, column: dict) -> tuple:
        en2cn: dict = {}
        middle: str = ""
        for entry in column["fields"]:
            en2cn[entry["technical_name"]] = entry["business_name"]
            middle += "{column_en} {column_type} comment '{column_cn}'\n"
            middle = middle.format(
                column_en=entry["technical_name"],
                column_cn=entry["business_name"],
                column_type=entry["original_data_type"],
            )
        schema = CREATE_SCHEMA_TEMPLATE.format(
            title=source["title"],
            schema=source["schema"],
            source=source["source"],
            middle=middle[: -2]
        )
        table = "{source}.{schema}.{title}".format(
            title=source["title"],
            schema=source["schema"],
            source=source["source"]
        )

        return schema, en2cn, table

    @staticmethod
    async def get_prompt_resp_sql(query, table):
        template = GENERATE_SQL_CONCLUSION_TEMPLATE
        prompt = template.replace("{{UserQuestion}}", query).replace("{{Table}}", table)
        logger.info(f"prompt: \n{prompt}")
        return prompt

    @staticmethod
    def find_related_examples(
        words: list,
        values: list | dict,
    ):
        if isinstance(values, dict):
            found_words = {}
            for word in words:
                for key, value in values.items():
                    if word in value or word in key:
                        found_words[key] = f"comment '{value}'"
            sample_num = int(settings.CODE_VALUE_NUM)
            if len(found_words) > sample_num:
                found_words = {key: found_words[key] for key in list(found_words.keys())[:sample_num]}
            else:
                for key, value in values.items():
                    if len(found_words) < sample_num:
                        found_words[key] = f"comment '{value}'"
                    else:
                        break
        else:
            found_words = []
            for word in words:
                for value in values:
                    if value is not None and word in value:
                        found_words.append(value)

            sample_num = settings.SAMPLE_NUM
            if len(found_words) > sample_num:
                found_words = found_words[:int(sample_num)]
            else:
                found_words += values[:int(sample_num - len(found_words))]

        return found_words

    def build_explore_sample(
        self,
        idx: int,
        words: list,
        detail: tuple,
        samples: list | dict
    ):
        if detail[7][idx]["ret_flag"] != 3:
            if isinstance(samples, dict):
                samples = json.dumps(samples, ensure_ascii=False, indent=3)
            else:
                samples = json.dumps(samples[0], ensure_ascii=False, indent=3)
            return samples
        if isinstance(samples, list):
            samples = samples[0]
        logger.info("使用探查结果构建样例")
        column_report = detail[7][idx]["data"]["explore_details"]
        # 字段类型 0 数字型，1 字符型，2 日期型，3 日期时间型，4 时间戳型，5 布尔型，6 二进制，99其他
        sample = {}
        reported_column = [x["field_name_en"].lower() for x in column_report]
        for i, key in enumerate(samples.keys()):
            if key not in reported_column:
                sample[key] = samples[key]
                continue
            msg = column_report[reported_column.index(key)]
            if msg["field_type"] in [0, 1]:
                values = []
                for info in msg["details"]:
                    if info["rule_id"] == "Group":
                        if msg["params"] != "":
                            params = json.loads(msg["params"])
                            values = {x[0]: params.get(x[0], "") for x in json.loads(info["result"]) if
                                      x[0] is not None}
                        else:
                            if info["result"] != "null":
                                values = [x[0] for x in json.loads(info["result"])]
                            else:
                                values = [samples.get(key)]
                if len(values) > settings.SAMPLE_NUM:
                    values = self.find_related_examples(words, values)
                sample[msg["field_name_en"]] = values

            if msg["field_type"] in [2, 3, 4, 5]:
                values = [x["result"] for x in msg["details"] if x["rule_id"] in ["Min", "Max"]]
                sample[msg["field_name_en"]] = values
        sample = json.dumps(sample, ensure_ascii=False, indent=4)

        return sample

    async def get_catalog_prompt(self, assets: list, detail: tuple, query: str = "", appid="", words=[]) -> tuple:
        ddl_and_sample = ""
        logger.info(f"分词结果: \n{words}")
        for idx, items in enumerate(zip(assets, detail[0], detail[3])):  # detail[0]: ddl, detail[3]: samples
            try:
                # samples = items[2]['entries'][: 1]
                samples = {
                    columns["name"]: data
                    for data, columns in zip(items[2]["data"][0], items[2]["columns"])
                }
                samples = self.build_explore_sample(idx, words, detail, samples)
                logger.info(f"{items[0]['title']}的样例数据：\n{samples}")
            except json.decoder.JSONDecodeError:
                samples = ""
            except TypeError:
                samples = ""
            ddl_and_sample += f"这是第{idx + 1}张表：{items[0]['title']}，{items[0]['description']}：\n" \
                              f"{items[1]}\n" \
                              f"这是第{idx + 1}张表各字段的部分样例数据:\n" \
                              f"{samples}\n"

        _, prompt_id = await PromptServices().from_anydata(appid, "text2sql")
        params = {
            "ddl_and_sample": ddl_and_sample,
            "query": query,
            "error_code": "",
            "background": str(datetime.now().date())
        }

        return prompt_id, params

    async def get_view_prompt(self, assets: list, detail: tuple, query: str = "", appid="", words=[]) -> tuple:
        ddl_and_sample = ""
        logger.info(f"分词结果: \n{words}")
        for idx, items in enumerate(zip(assets, detail[0], detail[3])):  # detail[0]: ddl, detail[3]: samples
            try:
                samples = {
                    columns["name"]: data
                    for data, columns in zip(items[2]["data"][0], items[2]["columns"])
                }
                samples = self.build_explore_sample(idx, words, detail, samples)
                logger.info(f"{items[0]['resource_name']}的样例数据：\n{samples}")
            except json.decoder.JSONDecodeError:
                samples = ""
            except TypeError:
                samples = ""
            except Exception:
                samples = ""

            ddl_and_sample += f"这是第{idx + 1}张表：{items[0]['resource_name']}，{items[0]['description']}：\n" \
                              f"{items[1]}\n" \
                              f"这是第{idx + 1}张表各字段的部分样例数据:\n" \
                              f"{samples}\n"

        _, prompt_id = await PromptServices().from_anydata(appid, "text2sql")
        params = {
            "ddl_and_sample": ddl_and_sample,
            "query": query,
            "error_code": "",
            "background": str(datetime.now().date())
        }

        return prompt_id, params

    @staticmethod
    async def process_spaces(sql: str, detail, used_tables) -> str:
        # 当字段中存在空格时，加 双引号
        def contains_chinese(s):
            return bool(re.search(r'[\u4e00-\u9fff]', s))

        for table in used_tables:
            files = detail.get(table, None)
            if files is not None:
                for key, value in files.items():
                    if " " in key and key in sql:
                        sql = sql.replace(key, f'"{key}"')
                    if key in sql and contains_chinese(key):
                        sql = sql.replace(key, f'"{key}"')
            sql = sql.replace('""', '"').replace("''", "'")

        return sql

    @staticmethod
    async def add_space(ori_sql: str):
        sql = ""
        for chunk in ori_sql.split():
            flag = False
            if "AND" in chunk and chunk != "AND":
                sql += "AND" + " " + chunk[3:] + " "
                flag = True
            if "WHERE" in chunk and chunk != "WHERE":
                sql += "WHERE" + " " + chunk[5:] + " "
                flag = True
            if not flag:
                sql += chunk + " "
        return sql

    @staticmethod
    async def show_auth_column(sql: str, column: dict, used_table: str):
        if "*" in sql:
            fields = ', '.join(column[used_table[0]])  # 通过used_table[0]去控制只用一张表，在多表有问题
            sql = sql.replace("*", fields)
        return sql

    async def check_sql(self, sql: str, detail: tuple, config={}) -> str:
        logger.info("大模型直接生成的SQL: \n{}".format(sql))
        try:
            sql = self.extract_sql(sql)
            sql = await self.add_space(sql)
            sql = await self.delete_quotes(sql)
            sql, used_table = await self.check_table_name(sql, detail[2])
            sql = await self.add_quotes(sql, detail[2], detail[5])
            sql = await self.process_spaces(sql, detail[1], used_table)
            sql = self.check_limit(sql, config)
            # sql = await self.check_column(sql, detail[5])
            sql = sql.replace(";", "")
            sql = self.format_sql(sql)
        except Exception as e:
            print(e)
            pass
        logger.info("进行很多校验以后的SQL，同时整理了以下SQL: \n{}".format(sql))
        return sql

    @staticmethod
    def table_to_markdown(
        sql: str,
        table: dict,
        detail: tuple,
        index: int = 0
    ) -> tuple:
        """返回三种格式：
            1. 完整 markdown 格式，用于前端展示数据
            2. 包含 5 条数据的 markdown 格式，用于一致性校验
            3. 包含 5 条数据的 json 格式，用于一致性校验
        """
        try:
            parser = Parser(sql)
            query_tables = get_query_tables(sql)
            columns_select = parser.columns_dict.get("select")
            column2table = {}   # 构建每一个字段到所属表的映射，如果字段长度为1，默认只有一张表
            for items in columns_select:
                column_split = items.rsplit(".", maxsplit=1)
                if len(column_split) > 1:
                    column2table[column_split[1]] = column_split[0]
                else:
                    column2table[column_split[-1]] = column_split[-1]

            columns = []
            for column in table["columns"]:
                # column_table: str = column2table[column["name"]]   #  实际的表名 xxx.xxx.xxx
                column_table: str = column2table.get(column["name"], None)   #  实际的表名 xxx.xxx.xxx
                if column_table is None:
                    column_name = column["name"]
                else:
                    if len(column_table.split(".")) > 1:
                        en2cn = detail[1].get(column_table, None)
                    else: #  xxx
                        en2cn = detail[1].get(query_tables[0], None)
                    column_alias = en2cn.get(column["name"], "")
                    column_name = f'{column["name"]}/{column_alias}'
                if column["type"] == "unknown":
                    column_name += "（无权限）"
                columns.append(column_name)
                if columns[-1].endswith("/"):
                    columns[-1] = columns[-1][:-1]
        except Exception as e:
            columns = [column["name"] for column in table["columns"]]
        df = pd.DataFrame(data=table["data"], columns=columns)
        df.fillna("null", inplace=True)

        five_row_markdown = []
        if not df.empty:
            five_row_markdown = df.iloc[0: 5].to_markdown()

        five_row_json = {
            "columns": table["columns"],
            "data": table["data"][:5]
        }

        # 通过disable_numparse 禁用科学计数法 通过
        markdown = df.to_markdown(
            index=False,
            disable_numparse=True
        )
        logger.info("Table: \n{}".format(df))
        df2json = df.to_json(force_ascii=False)

        return markdown, five_row_json, five_row_markdown, df2json

    @staticmethod
    async def get_dict_en2type(resp_column):
        en2type = {}
        column_name = []
        for entry in resp_column["fields"]:
            en2type[entry["technical_name"]] = entry["data_type"]
            column_name.append(entry["technical_name"])
        return en2type, column_name

    @staticmethod
    async def get_view_en2type(resp_column):
        en2type = {}
        column_name = []
        for field in resp_column["fields"]:
            en2type[field["technical_name"]] = field["data_type"]

            column_name.append(f'"{field["technical_name"]}"')
        return en2type, column_name

    @staticmethod
    def get_infos_of_res(cites: dict, sql: str, cn2en: dict) -> tuple[Any, Any]:
        table = ""
        text = "根据"
        cites_tables = []
        if cites is not None:
            for key, value in cn2en.items():  # sql 中使用了哪些表
                if value in sql:
                    cites_tables.append(key)
            for index, table in enumerate(cites):  # 找到使用的表及其位置
                if table in cites_tables:
                    text += f"<strong>'{table}'</strong><i slice_idx=0>{index + 1}</i>,"

        text += "检索到如下数据："
        return text, table

    @staticmethod
    def format_sql(sql) -> str:
        sql = sqlparse.format(sql, reindent=True, keyword_case="upper")
        return sql

    @staticmethod
    def check_punctuation(
        query: str
    ) -> str:
        query = query.replace(";", "")
        query = query.replace("`", "")
        chunks = query.split()
        parser = Parser(query)
        columns_aliases_names = parser.columns_aliases_names
        for i, chunk in enumerate(chunks):
            if chunk in columns_aliases_names:
                if '"' in chunk:
                    continue
                else:
                    chunk = chunk.replace("'", "")
                    chunks[i] = f'"{chunk}"'

        return " ".join(chunks)

    @staticmethod
    def check_table(query: str, ori_tables: list) -> str:
        tables = get_query_tables(query)
        one_dim_tables = [msg.split(".")[-1] for msg in ori_tables]
        two_dim_tables = [msg.split(".")[-2] + "." + msg.split(".")[-1] for msg in ori_tables]
        chunks = query.split()
        for table in tables:
            if table not in ori_tables:
                try:
                    index = one_dim_tables.index(table)
                except ValueError:
                    index = two_dim_tables.index(table)
                # 如果直接 replace 可能会替换错误，因为字段可能包含表名：'SELECT penaltiestype, COUNT(*) AS count FROM penalties GROUP BY penaltiestype LIMIT 10'
                for i, chunk in enumerate(chunks):
                    if chunk == table:
                        chunks[i] = ori_tables[index]
                # query = query.replace(table, ori_tables[index])
        query = " ".join(chunks)
        return query

    @staticmethod
    def check_as_new(
        query: str
    ) -> str:
        parser = Parser(query)
        alias_or_name = parser.columns_aliases_names
        print(alias_or_name)
        chunks = query.split()
        for i, chunk in enumerate(chunks):
            if chunk in alias_or_name:
                if '"' not in chunk:
                    chunk = chunk.replace("'", "")
                    chunks[i] = f'"{chunk}"'

        return " ".join(chunks)

    def get_column_type(
        self,
        column: str,
        query: str,
        en2types: dict
    ) -> str:
        column = column.replace("'", "").replace('"', "")
        column_length = len(column.split("."))
        if column_length == 2:  # f1.data
            tables = Parser(query).tables_aliases
            tables_aliases = column.rsplit(".", 1)[0]
            aim_table = tables.get(tables_aliases)
        else:  # data
            if column_length == 4:  # vdm.default.xxx.data
                aim_table = column.rsplit(".", 1)[0]
            else:
                aim_table = get_query_tables(query)[0]  # data 单表

        en2type = en2types.get(aim_table)
        column_type = en2type.get(column.split(".")[-1])

        return column_type

    def check_in_new(
        self,
        query: str,
        en2types: dict
    ) -> str:

        keyword = "IN"
        date = "DATE"
        chunks = query.split()
        if keyword not in chunks:
            return query

        index = chunks.index(keyword)
        column_type = self.get_column_type(
            chunks[index - 1],
            query,
            en2types
        )
        if column_type not in MySQLKeyword.DATE:
            return query
        for i, chunk in enumerate(chunks[index + 1:]):
            if date in chunk:
                return query
            if MySQLKeyword.SELECT in chunk:
                return query

            new_chunk = ""
            for char in chunk:
                if char in ["(", ")"]:
                    new_chunk += char
                else:
                    if date in new_chunk:
                        new_chunk += char
                    else:
                        new_chunk += date + " " + char
            chunks[i + index + 1] = new_chunk
            if ")" in chunk:
                break

        return " ".join(chunks)

    def find_from_index(
        self,
        sql: str
    ) -> int:
        sql_lower = sql.lower()
        from_pos = sql_lower.find('from ')
        if from_pos == 0:
            return from_pos
        elif from_pos > 0:
            if sql_lower[from_pos - 1] in [' ', "\t", "\n"]:
                return from_pos
            else:
                return self.find_from_index(sql[from_pos + 1:])
        else:
            return -1

    async def check_column(
        self,
        sql,
        en2types,
    ) -> str:
        columns_list = []
        for k, v in en2types.items():
            columns_list += list(v)


        if sql.count('SELECT') > 1:
            return sql
        keywords = [
            '*', "(", ")", 'FROM', 'SELECT', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN',
            'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN', 'ON', 'USING', 'GROUP BY', 'HAVING', 'ORDER BY', 'DISTINCT',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CASE WHEN ... THEN ... ELSE ... END', 'COALESCE',
            'ISNULL', 'NULLIF', 'IIF', 'CONCAT', '||', 'SUBSTRING', 'SUBSTR', 'TRIM', 'LTRIM', 'RTRIM', 'LENGTH',
            'CHAR_LENGTH', 'BYTE_LENGTH', 'CAST', 'CONVERT', 'FORMAT', 'TO_CHAR', 'TO_DATE', 'ROW_NUMBER', 'RANK',
            'DENSE_RANK', 'LEAD', 'LAG', 'FIRST_VALUE', 'LAST_VALUE', 'NTILE', 'PERCENT_RANK', 'CUME_DIST', 'TOP',
            'LIMIT', 'FETCH FIRST n ROWS ONLY', 'UNION', 'UNION ALL',
            'INTERSECT', 'EXCEPT', 'MINUS',
        ]
        from_pos = self.find_from_index(sql)
        clause = sql[7:from_pos]
        for word in keywords:
            if word in clause:
                return sql
        parser = Parser(sql)
        columns_dict = parser.columns_dict

        where = columns_dict.get("where")
        select = columns_dict.get("select")
        tables_aliases = {
            value: key
            for key, value in parser.tables_aliases.items()
        }
        column_aliases = {
            value: key
            for key, value in parser.columns_aliases.items()
        }
        print("tables_aliases", tables_aliases)
        print("column_aliases", column_aliases)
        if where:
            for column in where:
                if column not in select:
                    select.append(column)

        new_sql = "SELECT "
        for column in select:
            cache = column.rsplit(".", maxsplit=1)
            real_column = cache[-1]
            if len(cache) > 1:
                imag_column = tables_aliases[cache[0]]
                if imag_column in ["WHERE", "JOIN", "ON"]:
                    imag_column = cache[0]
                real_column = f"{imag_column}.{real_column}"
            cache = column_aliases.get(column)
            if real_column in columns_list:
                if cache:
                    new_sql += real_column + f' AS "{cache}", '
                else:
                    new_sql += real_column + ", "
        new_sql = new_sql.rstrip(", ")
        new_sql += " " + sql[from_pos:]
        logger.info(f"带上过滤字段以后的SQL：\n{self.format_sql(new_sql)}")
        return new_sql

    # def check_column_new(self):

    async def check_sql_v3(
        self,
        sql: str,
        detail: tuple,
        config: dict
    ) -> str:
        logger.info("大模型直接生成的SQL: \n{}".format(sql))
        try:
            sql = self.extract_sql(sql)
            sql = self.check_punctuation(sql)
            sql = self.check_limit(sql, config)
            sql = self.check_as_new(sql)
            sql = self.check_table(sql, detail[2])
            sql = self.check_in_new(sql, detail[5])
            # sql = self.check_column_new(sql, detail[5])
            format_sql = self.format_sql(sql, )
            logger.info("简单校验过后的SQL: \n{}".format(format_sql))
        except Exception as e:
            print(e)

        return sql
