import json
import re
import time

from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.cores.cognitive_assistant.qa_config import select_times
from app.cores.cognitive_assistant.qa_error import Text2SQLError, ConfigurationCenterError
from app.cores.cognitive_assistant.qa_func import get_time, data, get_text, get_table, qa_data_reorganize_to_json
from app.cores.cognitive_assistant.qa_model import AfEdition, QAParamsModelDIP, CognitiveSearchResponseModel
from app.cores.cognitive_assistant.qa_utils import exec_func_of_service
from app.cores.cognitive_search.search_config.get_params import SearchConfigs
from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.prompt.qa import BIG_FLAG, TIMEOUT_ERROR, NO_ANSWER, QUERY_TOO_SHORT, NO_ANSWER_WITH_RESOURCES
from app.cores.text2sql.t2s import Text2SQL
from app.logs.logger import logger
from app.retriever import CognitiveSearch


BD_SYMBOLS = ["，", "。", ",", "."]


def async_timing_decorator(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        resp = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return resp, execution_time

    return wrapper


class QABase(FindNumberAPI):
    up_limit: int = 10000
    time_execute: float = 0
    time_search: float = 0
    time_select: float = 0
    time_service: float = 0
    time_text2sql: float = 0
    time_conclude: float = 0
    plus_flag: bool = False
    timeout_flag: bool = False
    yield_service: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.save_svc_info: list = []
        self.save_cites: list = []

    @staticmethod
    @async_timing_decorator
    async def cognitive_search(request, headers, params: QAParamsModelDIP,
                               search_configs: SearchConfigs) -> CognitiveSearchResponseModel:
        """获取认知搜索结果"""
        search_executor = CognitiveSearch(
            request=request,
            params=params,
            headers=headers,
            search_configs=search_configs
        )
        assets = await search_executor.call()
        # logger.info(f"认知助手从认知搜索拿到的原始结果 CognitiveSearchModel assets = \n{assets}")
        # logger.info(f"认知助手从认知搜索拿到的原始结果 CognitiveSearchModel 对象转换为json格式后 assets = \n{json.dumps(assets.model_dump(), indent=4, ensure_ascii=False)}")
        # logger.info(f"认知助手从认知搜索实际拿到的资产 assets.props =\n{json.dumps(assets.props, indent=4, ensure_ascii=False)}")
        return assets

    async def exec_llm_by_prompt(self, inputs: dict, appid: str, prompt_id: str) -> str:
        """调用大模型获取结果"""
        try:
            response = await self.exec_prompt_by_llm(inputs, appid, prompt_id)
        except Text2SQLError:
            response = ""
        return response

    @async_timing_decorator
    async def select_service(self, props: dict, query: str, appid: str) -> list:
        """从认知搜索结果中提取接口服务"""
        service = props.get("接口服务")

        _, prompt_id = await PromptServices().from_anydata(appid, "select_interface")
        params = {
            "Dataset": json.dumps(service, ensure_ascii=False, indent=3),
            "UserQuestion": query
        }
        logger.info("===================")
        logger.info(f"params = {params}")

        for idx in range(select_times):
            logger.info("第{}次选择接口".format(idx + 1))
            result = await self.exec_llm_by_prompt(
                inputs=params,
                appid=appid,
                prompt_id=prompt_id,

            )
            logger.info(f"select_interface_ori: \n{result}")
            match = re.search(
                pattern=r'\[.*?]',
                string=result,
                flags=re.DOTALL
            )
            result = match.group(0) if match else result

            try:
                result = json.loads(result)
                break
            except json.decoder.JSONDecodeError:
                result = {}
                continue
        del_list = ["", "未提供"]
        if not isinstance(result, list):
            result = [result]
        try:
            # 去除参数为空的条件
            for svc in result:
                param = svc.get("params")
                info = {}
                for k, v in param.items():
                    if v not in del_list:
                        info[k] = v
                svc["params"] = info
        except:
            result = {}

        return result

    def deal_dict_data(self, resp, plus_flag):
        datas = resp.get("data")
        text = "一共检索到{total}条信息，以下为部分数据: {source}"
        if datas:
            total = resp.get("total_count")
            if len(str(resp)) > self.up_limit:  # 超长度
                plus_flag = True
                if isinstance(datas, list):
                    if len(str(datas[0])) < self.up_limit:
                        source = datas[0]
                        source = json.dumps(source, ensure_ascii=False)
                        source = text.format(total=total, source=source)
                    else:
                        source = str(datas)[:self.up_limit]
                else:
                    source = str(datas)
                    if len(source) > self.up_limit:
                        source = source[:self.up_limit]
                        source = text.format(total=total, source=source)
            else:
                source = str(datas)
                source = text.format(total=total, source=source)
        else:
            source = ""
        return source, plus_flag

    @async_timing_decorator
    async def execute_service(self, headers, svc_dict, service, cites) -> tuple:
        """执行接口服务，获取结果"""
        plus_flag = False
        resp_data = []
        for idx, svc in enumerate(service):
            logger.info(f"接口参数: \n{json.dumps(svc, ensure_ascii=False, indent=4)}")
            logger.info(f"第 {idx + 1} 次调用接口")
            resp_func = await exec_func_of_service(
                headers=headers,
                cites=cites, **svc
            )
            if resp_func.get("res") != "":
                resp = resp_func.get("res")
                info = resp_func.get("info")
                en2cn = svc_dict.get(svc["interface_name"]).get("返回参数描述")
                if isinstance(resp, dict):
                    sources, plus_flag = self.deal_dict_data(resp, plus_flag)
                else:
                    resp = str(resp)
                    if len(resp) > self.up_limit:  # 超长度
                        sources = resp[: self.up_limit]
                        plus_flag = True
                    else:
                        sources = resp
                for key, value in en2cn.items():
                    sources = sources.replace(key, str(value))

                resp_data.append(
                    {
                        "from": svc["interface_name"],
                        "data": sources,
                        "info": info
                    }
                )
                if sources == TIMEOUT_ERROR:
                    break

        return resp_data, plus_flag

    @staticmethod
    def add_label(origin, cites):
        """" 查找目标子字符串在原始字符串中的位置"""
        for num, cite in enumerate(cites):
            title = cite.get("title")
            index = origin.find(title)
            if index != -1:
                local = index + len(title)
                target = "<i slice_idx=0>{}</i>".format(num + 1)
                origin = origin[:local] + target + origin[local:]

        return origin

    @staticmethod
    def delete_summary(text: str) -> str:
        last_summary_index = text.rfind("总结")
        if last_summary_index != -1:
            return text[:last_summary_index]
        else:
            return text

    @async_timing_decorator
    async def get_res_search(
        self,
        cites,
        props_cn: dict,
        af_editions: str,
        explanation: list[dict],
        resources: list
    ) -> str:
        """将认知搜索的结果整理为答案,增加数据资源序号"""
        # resources 是指定资源问答中的指定资源
        if resources:
            tag = ""
            for i in range(len(cites)):
                tag += f"<i slice_idx=0>{i + 1}</i>"
            res = NO_ANSWER_WITH_RESOURCES
            res = res.replace("{resources}", tag)
            return res

        if explanation:
            text_map = {
                "index": "基于指标的方式：",
                "view": "基于逻辑视图的方式：",
                "api": "基于接口服务的方式：",
                "catalog": "基于数据目录的方式：",
            }
            props = "根据检索到的资源，可以采取以下方式获取结果："
            if len(explanation) >= 2:
                for item in explanation:
                    # print(item)
                    for key, value in item.items():
                        props += "<br>" + f"{text_map[key]}" + "<br>" + value
            else:
                for key, value in explanation[0].items():
                    props += "<br>" + f"{text_map[key]}" + "<br>" + value
            return props

        if af_editions == AfEdition.CATALOG:
            props = "根据问题，检索到如下数据目录：<br>"
            for idx, prop in enumerate(props_cn.get("数据目录")):
                target = "<i slice_idx=0>{}</i>".format(idx + 1)
                props += f"""{idx + 1}. {prop["中文名"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
        else:
            if not props_cn.get("接口服务") and not props_cn.get("指标分析"):
                props = "根据问题，检索到如下逻辑视图：<br>"
                for idx, prop in enumerate(props_cn.get("逻辑视图")):
                    target = "<i slice_idx=0>{}</i>".format(idx + 1)
                    props += f"""{idx + 1}. {prop["中文名"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
            elif not props_cn.get("逻辑视图") and not props_cn.get("指标分析"):
                props = "根据问题，检索到如下接口服务：<br>"
                for idx, prop in enumerate(props_cn.get("接口服务")):
                    target = "<i slice_idx=0>{}</i>".format(idx + 1)
                    props += f"""{idx + 1}. {prop["中文名"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
            elif not props_cn.get("逻辑视图") and not props_cn.get("接口服务"):
                props = "根据问题，检索到如下指标：<br>"
                for idx, prop in enumerate(props_cn.get("指标分析")):
                    target = "<i slice_idx=0>{}</i>".format(idx + 1)
                    props += f"""{idx + 1}. {prop["名称"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
            else:
                list_cite = [cite["title"] + cite["type"] for cite in cites]
                props = "根据问题，检索到如下资源：<br>"
                if props_cn["逻辑视图"]:
                    props += "逻辑视图：<br>"
                    for idx, prop in enumerate(props_cn.get("逻辑视图")):
                        jdx = list_cite.index(prop["中文名"] + "data_view")
                        target = "<i slice_idx=0>{}</i>".format(jdx + 1)
                        props += f"""{idx + 1}. {prop["中文名"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
                if props_cn["接口服务"]:
                    props += "接口服务：<br>"
                    for idx, prop in enumerate(props_cn.get("接口服务")):
                        jdx = list_cite.index(prop["中文名"] + "interface_svc")
                        target = "<i slice_idx=0>{}</i>".format(jdx + 1)
                        props += f"""{idx + 1}. {prop["中文名"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
                if props_cn["指标分析"]:
                    props += "指标：<br>"
                    for idx, prop in enumerate(props_cn.get("指标分析")):
                        jdx = list_cite.index(prop["名称"] + "indicator")
                        target = "<i slice_idx=0>{}</i>".format(jdx + 1)
                        props += f"""{idx + 1}. {prop["名称"]}{target}：{prop["描述"]}""".rstrip("：") + "<br>"
        if props.endswith("<br>"):
            props = props[:-4]
        props = props.replace("：__NULL__", "")
        logger.info(f"generate_answer_search: \n{props}")

        return props

    @async_timing_decorator
    async def format_service_response(self, save_cites, query: str, exec_result: dict, appid: str) -> tuple:
        """将接口调用的结果整理为答案"""
        name_map = [cell.get("title") for cell in save_cites]
        logger.info(f"generate_answer: \n{json.dumps(exec_result, ensure_ascii=False, indent=3)}")
        index = name_map.index(exec_result.get("from")) + 1

        _, prompt_id = await PromptServices().from_anydata(appid, "conclusion_interface_result")
        params = {
            "UserQuestion": query,
            "Answer": json.dumps(exec_result, ensure_ascii=False, indent=3)
        }

        svc_info = exec_result.get("info")  # 接口的调用信息
        del exec_result["info"]

        text = await self.exec_llm_by_prompt(
            inputs=params,
            appid=appid,
            prompt_id=prompt_id,
        )
        patterns = [
            r'综上所述(.*)$',
            r'根据表格数据(.*)$',
            r'根据表格(.*)$',
            r'根据提供的资源(.*)$',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                text = match.group(1).strip()  # 使用strip()去除可能的前后空白字符
        if text[0] in BD_SYMBOLS:
            text = text[1:]
        text = text + "<i slice_idx=0>{}</i>".format(index)
        text = text.replace("\r\n", "\n")
        text = text.replace("\n", "<br>")
        logger.info(f"generate_answer_conclusion: \n{text}")

        return text, svc_info

    @staticmethod
    @async_timing_decorator
    async def get_res_t2s(headers, params, props, af_editions, config):
        t2s = Text2SQL(
            "admin",
            params.subject_id,
            params.ad_appid,
            headers,
            params.query,
            af_editions=af_editions,
            config=config
        )
        if af_editions == AfEdition.RESOURCE:
            resp_t2s = await t2s.call(props.view_text2sql, props.cites_dict)
            # resp_t2s = await t2s.call(props.view_text2sql, props.props_dict)
        else:
            resp_t2s = await t2s.call(props.tab_text2sql, props.cites_dict)
            # resp_t2s = await t2s.call(props.tab_text2sql, props.props_dict)
        return resp_t2s

    async def yield_text2sql_response(self, headers, params, props, af_editions="", config={}):
        """ 执行text2sql 获取结果"""

        res_t2s, self.time_text2sql = await self.get_res_t2s(
            headers=headers,
            params=params,
            props=props,
            af_editions=params.af_editions,
            config=config
        )

        # for items in self.save_cites:
        #     if items["title"] == res_t2s["cite"]:
        #         items["sql"] = {"sql": res_t2s["sql"]}
        tag = ""
        if str(res_t2s["table"]) == "":
            for i in range(len(props.cites)):
                tag += f"<i slice_idx=0>{i + 1}</i>"
            text = NO_ANSWER
            text = text.replace("{resources}", tag)
            res_t2s["text"] = text

        # # 在 react agent 中 只需要df2json 即可, markdown 表格在 af-sailor-agent 中实现
        # res_t2s["table"] = ""
        yield data(
            status="answer",
            cites=props.cites,
            detail=res_t2s["text"],
            table=res_t2s["table"],
            explain=[{"sql": res_t2s["sql"]}],
            df2json=res_t2s["df2json"]
        )

    async def yield_service_response(self, headers, params, props, text=""):
        """ 执行接口调用获取结果 """
        # 暂时不调用分析问答给的接口参数
        props.select_interface = []
        if props.select_interface:
            service = props.select_interface.get("推荐实例")
            self.time_select = 0.00
        else:
            service, self.time_select = await self.select_service(
                props=props.props,
                query=params.query,
                appid=params.ad_appid
            )
        yield data(status="invoke")
        execute_result, self.time_execute = await self.execute_service(
            headers=headers,
            svc_dict=props.svc_dict,
            cites=props.cites,
            service=service,
        )
        if not execute_result[0]:
            raise Exception("Text2api 执行成功了，但是结果为空，选择不出答案")
        for items in execute_result[0]:

            if items["data"] in ["", [], None, '{"total_count":0,"data":[]}']:
                continue
            elif items["data"] == TIMEOUT_ERROR:
                self.timeout_flag = True
                continue

            detail, times = await self.format_service_response(
                save_cites=props.cites,
                query=params.query,
                exec_result=items,
                appid=params.ad_appid,
            )
            # 添加 url 和 参数 在给前端的文件中
            for item in self.save_cites:
                if item["title"] == items["from"]:
                    detail[1]["title"] = item["title"]

            self.save_svc_info.append(detail[1])  # 存储接口的执行信息
            text += detail[0] + "<br>"
            self.time_service += times

            yield data(
                status="answer",
                cites=self.save_cites,
                detail=text[:-4],
                explain=[detail[1]]
            )
            self.yield_service = True

        self.plus_flag = execute_result[1]

    async def yield_search_response(self, params, props: CognitiveSearchResponseModel, error=False):
        """ 执行认知搜索获取结果 """
        logger.info(f'yield_search_response ...')
        logger.info(f'params = \n{params}')
        logger.info(f'assets = \n{props}')
        # get_res_search()的功能是将认知搜索的结果整理为答案
        resp_search, self.time_conclude = await self.get_res_search(
            cites=props.cites,
            props_cn=props.props, # 包含字段信息
            af_editions=params.af_editions,
            explanation=props.explanation,
            resources=params.resources,
        )
        yield qa_data_reorganize_to_json(
            status="answer",
            cites=props.cites,
            detail=resp_search,
            related_info = props.related_info,
        )
        if error:
            yield qa_data_reorganize_to_json(
                status="answer",
                cites=props.cites,
                detail=resp_search + "<br>" + QUERY_TOO_SHORT
            )

    @staticmethod
    async def yield_big_response(props, last_resp):
        try:
            last_resp = get_text(last_resp)
            table = get_table(last_resp)
            yield data(
                status="answer",
                cites=props.cites,
                detail=last_resp + "<br>" + BIG_FLAG,
                table=table
            )
        except KeyError as e:
            pass
        except json.decoder.JSONDecodeError as e:
            pass

    async def get_timeout_res(self, last_resp):
        if self.timeout_flag:
            try:
                resp = get_text(last_resp)
                resp = resp + "<br><br>"
            except KeyError as e:
                resp = ""
            except json.decoder.JSONDecodeError as e:
                resp = ""
            yield data(
                status="answer",
                cites=self.save_cites,
                detail=resp + "<br>" + TIMEOUT_ERROR
            )

    async def paser_config_dict(
        self,
        num: int | str,
        headers: dict
    ):

        config = await self.get_config_dict(
            num,
            headers=headers
        )
        config_dict = {}
        for item in config:
            config_dict[item["key"]] = item["value"]
        return config_dict


    async def logger_time(self):
        """ 打印出各个工具的时间 """
        run_time = get_time(
            self.time_search,
            self.time_select,
            self.time_execute,
            self.time_conclude,
            self.time_service,
            self.time_text2sql
        )
        logger.info("耗时：\n{}\n".format(json.dumps(run_time, indent=4, ensure_ascii=False)))
