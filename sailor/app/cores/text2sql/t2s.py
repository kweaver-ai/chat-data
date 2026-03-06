from typing import Any

from app.cores.cognitive_assistant.qa_model import AfEdition
from app.cores.text2sql.t2s_api import Services
from app.cores.text2sql.t2s_error import Text2SQLError, T2SErrno
from app.cores.text2sql.t2s_reshape import Reshape
from app.logs.logger import logger


class Text2SQL(Services, Reshape):
    def __init__(
        self,
        user: str,
        user_id: str,
        appid: str,
        headers: dict,
        question: str,
        af_editions: str,
        config: dict
    ):
        super().__init__()
        self.user = user
        self.appid = appid
        self.headers = headers
        self.question = question
        self.af_editions = af_editions
        self.user_id = user_id
        self.config = config

    async def cognitive_search(
        self
    ) -> list:
        assets = await self.get_assets_by_search(self.query, self.headers, 1)
        if assets["entries"] is None:
            raise Text2SQLError(T2SErrno.COGNITIVE_SEARCH_ERROR)
        assets = await self.assets_reshape(assets)
        return assets

    async def get_assets_detail(
        self,
        assets: list
    ) -> tuple:
        ddl = []  # 存储建表的ddl
        en2cn = {}  # 存储字段英文到中文的映射, key=表名， value=对应的字段中英文
        cn2en = {}  # 存储表名中文到英文的映射，key=中文表名， value=英文表名
        en2type = {}  # 储存字段英文到类型的映射
        tables = []  # 存储表名，数据源-数据库-数据表
        samples = []  # 存储样例
        columns = {}  # 存储每一个表的字段信息，用于行列权限
        bi_report = []  # 存储每一个表的探查结果
        for asset in assets:
            print("-=-=-=-=-=-=")
            print(asset)
            if self.af_editions == AfEdition.CATALOG:
                # 以下两行是为了将通过目录执行SQL转换为通过视图执行SQL
                asset["source"] = f"vdm_{asset['source']}"
                asset["schema"] = "default"
                # common = await self.get_common_by_id(asset["index"], self.headers)
                source = await self.source_reshape(asset)
                # column = await self.get_column_by_id(asset["index"], self.headers)
                # sample = await self.get_samples_by_id(source["index"], self.headers)

                # 迁移所有的 数据目录接口到逻辑视图
                column = await self.get_view_column_by_id(asset["form_view_id"], self.headers)
                totype, column_name = await self.get_dict_en2type(column)
                sample = await self.get_view_sample_by_source(asset, self.headers, types=1)


                detail = await self.get_schema_of_table(source, column)  # schema, en2cn, table
                print("##############")
                print(asset)
                report = await self.get_bi_explore_report(asset["form_view_id"], self.headers)
                cn2en[asset["title"]] = asset["technical_name"]
            else:
                source = await self.view_source_reshape(asset)
                column = await self.get_view_column_by_id(asset["index"], self.headers)
                totype, column_name = await self.get_view_en2type(column)
                sample = await self.get_view_sample_by_source(source, self.headers)
                detail = await self.get_view_schema_of_table(source, column)  # schema, en2cn, table
                report = await self.get_bi_explore_report(asset["index"], self.headers)
                cn2en[asset["resource_name"]] = asset["title"]

            ddl.append(detail[0])
            tables.append(detail[2])
            samples.append(sample)
            en2cn[detail[2]] = detail[1]
            en2type[detail[2]] = totype
            columns[detail[2]] = column_name
            bi_report.append(report)

        return ddl, en2cn, tables, samples, cn2en, en2type, columns, bi_report

    async def get_prompt(
        self,
        assets,
        detail,
        word_chunk
    ):
        if self.af_editions == AfEdition.RESOURCE:
            prompt_id, params = await self.get_view_prompt(
                assets,
                detail,
                self.question,
                self.appid,
                word_chunk
            )
        else:
            prompt_id, params = await self.get_catalog_prompt(
                assets,
                detail,
                self.question,
                self.appid,
                word_chunk
            )
        params["error_code"] = ""
        return prompt_id, params

    def get_verbal(
        self,
        query: str,
        error: str,
        params: dict
    ) -> tuple:
        if error is not None:
            params["error_code"] += (
                f"这是之前的SQL:"
                f"{query}"
                f"反馈信息如下，请你参考："
                f"{error}"
                "同时为你提出如下建议："
                "SQL 不能 出现： 中文字段名 AS 中文别名"
            )
        empty_error = (
            "SQL 执行结果为空，"
            "1. 你需要检查 SQL 中所有的筛选条件， 通过与问题和 表信息做比较，确认过滤条件是否使用恰当；"
            "2. 如果是多表查询，你需要校验关联字段是否满足对你提出的要求中的第 5 条；"
            "3. 检查 SELECT 后面的字段是否出现了 表中不存在的 字段名，或者 错误使用了中文名称；"
            "重新生成 SQL, 你不需要修改其中的 limit 限制"
        )
        return empty_error, params

    async def call(
        self,
        assets: list = None,
        cites: dict = None,
        query: str = None,
        table: dict = None,
        error: str = None
    ) -> Any:
        if assets is None:
            assets = await self.cognitive_search()
        detail = await self.get_assets_detail(assets)
        word_chunk = await self.participle(self.question, self.appid)

        prompt_id, params = await self.get_prompt(
            assets,
            detail,
            word_chunk=word_chunk
        )

        for epoch in range(3):
            logger.info(f"第 {epoch + 1} 次生成SQL...")
            if error is not None:
                _, params = self.get_verbal(
                    query,
                    error,
                    params
                )
            query = await self.exec_prompt_by_llm(
                params,
                appid=self.appid,
                prompt_id=prompt_id
            )
            stop = False
            assume_words = ["假设", "如果", "样例数据"]
            for word in assume_words:
                if word in query:
                    stop = True
                    break
            if stop:
                raise Text2SQLError(reason="sql 中存在假设信息", detail={"sql": query})
            try:
                query = await self.check_sql_v3(
                    query,
                    detail=detail,
                    config=self.config
                )
                try:
                    new_query = await self.check_column(query, detail[5])
                    table = await self.exec_vir_engine_by_sql(
                        self.user,
                        self.user_id,
                        new_query
                    )
                    query = new_query
                    if not table.get("data"):
                        error, _ = self.get_verbal(
                            query,
                            error,
                            params
                        )
                        continue
                    break
                except Exception as e:
                    print("#" * 20, e)

                table = await self.exec_vir_engine_by_sql(
                    self.user,
                    self.user_id,
                    query
                )
                if not table.get("data"):
                    error, _ = self.get_verbal(
                        query,
                        error,
                        params
                    )
                    continue
                break
            except Exception as e:
                print("#" * 20, e)
                if epoch == 0:
                    query = await self.check_sql(
                        query,
                        detail=detail,
                        config=self.config
                    )
                else:
                    query = await self.check_sql_v3(
                        query,
                        detail=detail,
                        config=self.config
                    )
                    try:
                        new_query = await self.check_column(query, detail[5])
                        table = await self.exec_vir_engine_by_sql(
                            self.user,
                            self.user_id,
                            new_query
                        )
                        query = new_query
                        if not table.get("data"):
                            error, _ = self.get_verbal(
                                query,
                                error,
                                params
                            )
                            continue
                        break
                    except Exception as e:
                        print("#" * 20, e)
            try:
                table = await self.exec_vir_engine_by_sql(
                    self.user,
                    self.user_id,
                    query
                )
                if not table.get("data"):
                    error, _ = self.get_verbal(
                        query,
                        error,
                        params
                    )
                    continue
                break
            except Text2SQLError as e:
                error = e.detail

        if table is None:
            raise Text2SQLError()

        table, five_row_json, five_row_markdown, df2json = self.table_to_markdown(
            query,
            table,
            detail=detail
        )
        infos = self.get_infos_of_res(
            cites,
            query,
            cn2en=detail[4]
        )
        if not table:
            return {
                "sql": query,
                "text": infos[0],
                "table": table,
                "cite": infos[1],
                "df2json": df2json,
            }
        try:
            res = await self.check_consistency(
                query,
                self.question,
                five_row_json,
                five_row_markdown,
                appid=self.appid,
            )
        except Exception as e:
            print("一致性校验错误，直接跳过")
            print(e)
            res = {"res": "跳过"}

        if res.get("res") != "no":
            logger.info(f"一致性校验结果{res}: 通过")
            infos = self.get_infos_of_res(cites, query, detail[4])
            return {
                "sql": query,
                "text": infos[0],
                "table": table,
                "cite": infos[1],
                "df2json": df2json,
            }
        raise Text2SQLError()
