import asyncio
import json
import random
from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.prompt.text2sql import *
from app.cores.text2sql.t2s_api import Services
from app.cores.text2sql.t2s_error import *
from app.cores.text2sql.t2s_reshape import Reshape
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.logs.logger import logger
from app.models.rule_model import *
from app.models.table_model import *
from jinja2 import Template
from app.retriever.base import RetrieverAPI
from typing import List

# 内置模型长度设置
model_max_token_map = {
    "deepseek-chat": 8000,
    "deepseek-r1-250120": 16000,
    "deepseek-v3-241226": 4096,
    "deepseek-r1-distill-qwen-32b-250120": 8000,
    "DeepSeek-R1-Distill-Qwen-32B": 4096,
    "DeepSeek-R1-Distill-Llama-8B": 4096,
    "qwen32b-distill-r1": 4096
}

class SampleGenerate(Services, Reshape):
    def __init__(
        self,
        # a_appid: str,
        header: dict,
    ):
        super().__init__()
        # self.appid = a_appid
        self.headers = header
        self.ad_prompt_service = PromptServices()

    async def construct_rule_info_prompt(self, one_rule_info: RuleDetailModel) -> str:
        # 构造编码规则信息的prompt
        RULE_TYPE_TO_NAME = {"CUSTOM": "自定义编码规则", "REGEX": "正则表达式"}
        rule_info_prompt = CODE_RULE_INFO_TEMPLATE.format(code_rule_name=one_rule_info.name,
                                                          code_rule_standard_type=RULE_TYPE_TO_NAME[
                                                              one_rule_info.rule_type])
        if one_rule_info.regex:
            # 编码规则为正则，直接拼接正则表达式信息
            rule_info_prompt += RE_INFO_TEMPLATE.format(re=one_rule_info.regex)
        elif one_rule_info.custom:
            # 编码规则为自定义编码，拼接所有分段编码规则信息
            segment_rule_info_promnt = ""
            segment_place_sum = 0  # 计算当前分段位置
            for a_segment_rule in one_rule_info.custom:
                if a_segment_rule.segment_length == 1:
                    segment_rule_info_promnt += ONE_CODE_RULE_PLACE_EQUALS_ONE_INFO_TEMPLATE.format(
                        present_place_number=segment_place_sum + 1)
                elif a_segment_rule.segment_length > 1:
                    segment_rule_info_promnt += ONE_CODE_RULE_PLACE_GREATER_THAN_ONE_INFO_TEMPLATE.format(
                        present_place_start_number=segment_place_sum + 1,
                        present_place_end_number=segment_place_sum + a_segment_rule.segment_length)
                segment_rule_info_promnt += ONE_CODE_RULE_DESCRIPTION_TEMPLATE.format(
                    code_rule_name=a_segment_rule.name,
                    code_rule_type=SELF_DEFINE_RULE_TYPE_INT_TO_NAME[
                        a_segment_rule.type])
                # 特殊分段编码类型进行额外的信息拼接
                if a_segment_rule.type == TIME:
                    segment_rule_info_promnt += ONE_CODE_RULE_DATA_TIME_TYPE_INFO_TEMPLATE.format(
                        data_time_format=a_segment_rule.value)
                elif a_segment_rule.type == CONSTANT_STRING:
                    segment_rule_info_promnt += ONE_CODE_RULE_STRING_TYPE_INFO_TEMPLATE.format(
                        string=a_segment_rule.value)
                elif a_segment_rule.type == CODE_TABLE:
                    code_table_detail = await self.get_code_table_detail_by_id(a_segment_rule.value,
                                                                               self.headers)
                    code_table_info_prompt = await self.construct_code_table_info_prompt(code_table_detail)
                    segment_rule_info_promnt += code_table_info_prompt
                segment_place_sum += a_segment_rule.segment_length
            rule_info_prompt += SELFDEFINE_CODE_RULE_INFO_TEMPLATE.format(
                rules=segment_rule_info_promnt)
        return rule_info_prompt

    async def construct_column_info_prompt(self, one_column_detail_info: ColumnDetailModel):
        # 构建单个字段信息的prompt
        # 字段基础信息
        # code_table_infos = {}  # 存储码表信息

        one_column_info_prompt = COLUMN_DETAIL_START_INFO_TEMPLATE.format(
            column_en=one_column_detail_info.technical_name, column_cn=one_column_detail_info.business_name)
        if one_column_detail_info.primary_key:
            one_column_info_prompt += MAIN_KEY

        # zkn 字段直接关联了码表，
        if one_column_detail_info.code_table_id:
            logger.info("字段直接关联了码表：获取码表信息")
            code_table_info_detail = await self.get_code_table_detail_by_id(
                one_column_detail_info.code_table_id,
                self.headers)
            code_table_info_prompt, code_table_enum = await self.construct_code_table_info_prompt(code_table_info_detail)
            # code_table_infos[one_column_detail_info.technical_name] = code_table_enum
            one_column_info_prompt += code_table_info_prompt
            one_column_info_prompt = COLUMN_DETAIL_INFO_TEMPLATE.format(
                column_en=one_column_detail_info.technical_name, column_detail_info=one_column_info_prompt)
            return one_column_info_prompt, code_table_enum

        # 字段关联数据标准时的信息
        if one_column_detail_info.standard_code:  # zkn 字段关联了数据标准
            column_standard_info = await self.get_standard_detail_by_code(one_column_detail_info.standard_code,
                                                                          self.headers)

            # zkn 修改 bug，提前判断标准关联了码表，如果关联了码表，则不再调用编码规则接口
            if column_standard_info.dict_id:  # 标准关联了码表
                logger.info("字段关联了标准, 没有关联码表，获取标准中的码表信息")
                # zkn 码表信息
                code_table_info_detail = await self.get_code_table_detail_by_id(column_standard_info.dict_id,
                                                                                self.headers)
                code_table_info_prompt, code_table_enum = await self.construct_code_table_info_prompt(code_table_info_detail)
                # code_table_infos[one_column_detail_info.technical_name] = code_table_enum
                one_column_info_prompt += code_table_info_prompt
                one_column_info_prompt = COLUMN_DETAIL_INFO_TEMPLATE.format(
                    column_en=one_column_detail_info.technical_name, column_detail_info=one_column_info_prompt)
                return one_column_info_prompt, code_table_enum
            elif column_standard_info.rule_id:  # 标准关联了编码规则
                rule_info_detail = await self.get_rule_detail_by_id(column_standard_info.rule_id, self.headers)
                rule_info_prompt = await self.construct_rule_info_prompt(rule_info_detail)
                one_column_info_prompt += rule_info_prompt
                one_column_info_prompt = COLUMN_DETAIL_INFO_TEMPLATE.format(
                    column_en=one_column_detail_info.technical_name, column_detail_info=one_column_info_prompt)
                return one_column_info_prompt, {}

            # 字段关联数据标准的基础信息，
            # zkn 标准名称，标准类型，标准说明
            one_column_info_prompt += DATA_STANDARD_INFO_TEMPLATE.format(
                standard_name=column_standard_info.name_cn,
                standard_type=column_standard_info.std_type_name,
                standard_description=column_standard_info.description)
            if column_standard_info.data_type == 1:  # 标准的数据类型为字符型
                one_column_info_prompt += COLUMN_LENGTH_INFO_TEMPLATE.format(
                    data_length=column_standard_info.data_length)
            elif column_standard_info.data_type == 0:  # 标准的数据类型为数字型
                one_column_info_prompt += NUMBER_OF_DECIMAL_PLACES_INFO_TEMPLATE.format(
                    place=column_standard_info.data_length)
                if column_standard_info.data_precision > 0:
                    one_column_info_prompt += DECIMAL_NUMBER_INFO_TEMPLATE.format(
                        decimal_precision=column_standard_info.data_precision)

        one_column_info_prompt = COLUMN_DETAIL_INFO_TEMPLATE.format(
            column_en=one_column_detail_info.technical_name, column_detail_info=one_column_info_prompt)
        return one_column_info_prompt, {}

    async def construct_columns_detail_info(self, a_view_id):
        # 构造数据表建表语句schema以及字段详细信息
        retriever = RetrieverAPI()
        try:
            detail = await retriever.get_view_detail(a_view_id, self.headers)
        except Text2SQLError as e:
            e.reason = f"寻找id为：\n{a_view_id}\n的逻辑视图失败。"
            raise DataViewError(e) from e
        source = {
            "index": a_view_id,
            "source": detail["view_source_catalog_name"][:-8],
            "schema": "default",
            "title": detail["technical_name"],
        }
        columns = await self.get_view_column_by_id(a_view_id, self.headers)
        schema, _, _ = await self.get_view_schema_of_table(source, columns)
        columns = [ColumnDetailModel.model_validate(a_column) for a_column in
                   columns["fields"]]
        view_info = await self.get_view_info_by_id(a_view_id, self.headers)

        column_prompts = []
        code_table_infos = {}
        # zkn 字段详细信息prompt
        for a_column in columns:
            one_column_info_prompt, code_table_info = await self.construct_column_info_prompt(a_column)
            column_prompts.append(one_column_info_prompt)
            if code_table_info:
                code_table_infos[a_column.technical_name] = code_table_info




        # column_prompts, code_table_infos = [await self.construct_column_info_prompt(a_column) for a_column in columns]

        # zkn 字段详细信息prompt
        columns_detail_info_promt = VIEW_COLUMN_DETAIL_INFO_TEMPLATE.format(view_name_cn=view_info.business_name,
                                                                            view_description=view_info.description,
                                                                            columns_detail_info="".join(
                                                                                column_prompts))
        return schema, columns_detail_info_promt , code_table_infos

    async def generate_sample(self, input_view_id: str, samples_size: int, max_retry: int = 2) -> List[ColumnModel]:
        # 样例生成函数
        # input:
        #   input_view_id:视图id
        #   samples_size:希望生成几个样例
        _, sample_generate_prompt_id = await self.ad_prompt_service.from_anydata(self.appid,
                                                                                 SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME)
        _, sample_generate_with_samples_prompt_id = await self.ad_prompt_service.from_anydata(self.appid,
                                                                                              SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME)
        input_prompt_template = await self.ad_prompt_service.get_prompt(prompt_id=sample_generate_prompt_id,
                                                                        appid=self.appid)
        if not input_prompt_template:
            e = NoPromptTemplateError(Text2SQLError())
            e.status = 500
            e.reason = "没有从AD取到input_prompt_template"
            raise e
        input_prompt_template = input_prompt_template.replace(
            "{{", "{").replace("}}", "}")
        input_with_samples_prompt_template = await self.ad_prompt_service.get_prompt(
            prompt_id=sample_generate_with_samples_prompt_id, appid=self.appid)
        if not input_with_samples_prompt_template:
            e = NoPromptTemplateError(Text2SQLError())
            e.status = 500
            e.reason = "没有从AD取到input_with_samples_prompt_template"
            raise e
        input_with_samples_prompt_template = input_with_samples_prompt_template.replace(
            "{{", "{").replace("}}", "}")
        logger.info("模型名称为：" + self.model_name)
        model_max_length = await self.ad_prompt_service.get_model_max_tokens_length(model_name=self.model_name,
                                                                                    appid=self.appid)

        # model_max_length = model_info.get("max_tokens_length", 20000)
        if not model_max_length:
            model_max_length = 20000  # 拿不到模型服务最大长度时，默认答案空间为20000
            logger.info("拿不到模型服务最大token数，设置模型服务默认值为：" + str(model_max_length))
        model_info_list = await  self.ad_prompt_service.get_model_list(model_name=self.model_name,
                                                                  appid=self.appid)
        # if len(model_info_list) == 0:
        #     raise Exception("模型不存在")

        model_info = [m_info for m_info in model_info_list if m_info["model_name"] == self.model_name]
        # m = model_info[0]["model_series"]
        if len(model_info) > 0 and model_info[0]["model_series"] == "deepseek":
            _model_max_length = model_max_token_map.get(model_info[0]["model"])
            if _model_max_length is None:
                logger.info("内部最大token数配置没配置模型：{}".format(model_info[0]["model"]))
            else:
                logger.info("模型：{} 最大tokens为 {}".format(model_info[0]["model"], _model_max_length))
                model_max_length = _model_max_length

        logger.info("模型服务最大token数为：" + str(model_max_length))

        schema, column_detail_info_prompt, code_table_infos = await self.construct_columns_detail_info(input_view_id)

        # zkn 第三个参数为字段详细信息prompt
        async def generate_samples(a_schema, the_samples_size, a_column_detail_info_prompt):

            generate_sample_param = {"schema": a_schema, "sample_size": str(the_samples_size),
                                     "column_detail_info": a_column_detail_info_prompt}
            # 动态配置模型服务的答案生成空间，该空间长度 = 模型最大窗口长度 - 输入的tokens数
            input_prompt = input_prompt_template.format(schema=a_schema, sample_size=str(the_samples_size),
                                                        column_detail_info=a_column_detail_info_prompt)
            input_tokens_count = \
                await self.ad_prompt_service.tokens_count(input_text=input_prompt, model_name=self.model_name,
                                                          appid=self.appid)
            max_generate_tokens = model_max_length - input_tokens_count - \
                100  # 模型最大上下文空间 - 输入token数 - 100 作为答案空间
            logger.info("无样例时答案生成窗口为:" + str(max_generate_tokens))
            try:
                # zkn  尝试调用模型去生成样例
                a_sample_text_to_parse = await self.exec_prompt_by_llm(generate_sample_param, self.appid,
                                                                       prompt_id=sample_generate_prompt_id,
                                                                       max_tokens=max_generate_tokens)
            except LLMExecError as e:
                e.reason = "大模型生成失败。"
                raise e
            if not a_sample_text_to_parse:
                e = LLMExecError
                e.reason = "大模型生成服务没有返回非空内容。"
                raise e
            return a_sample_text_to_parse

        async def generate_samples_with_samples(a_schema, the_samples_size, a_column_detail_info_prompt, samples):
            generate_sample_param = {"schema": a_schema, "sample_size": str(the_samples_size),
                                     "column_detail_info": a_column_detail_info_prompt, "samples": samples}

            # 动态配置模型服务的答案生成空间，该空间长度 = 模型最大窗口长度 - 输入的tokens数
            input_with_samples_prompt = input_with_samples_prompt_template.format(schema=a_schema,
                                                                                  sample_size=str(
                                                                                      the_samples_size),
                                                                                  column_detail_info=a_column_detail_info_prompt,
                                                                                  samples=samples)
            input_tokens_count = \
                await self.ad_prompt_service.tokens_count(input_text=input_with_samples_prompt,
                                                          model_name=self.model_name,
                                                          appid=self.appid)
            max_generate_tokens = model_max_length - input_tokens_count - \
                100  # 模型最大上下文空间 - 输入token数 - 100 作为答案空间
            logger.info("有样例时答案生成窗口为:" + str(max_generate_tokens))
            try:
                a_sample_text_to_parse = await self.exec_prompt_by_llm(generate_sample_param, self.appid,
                                                                       sample_generate_with_samples_prompt_id,
                                                                       max_tokens=max_generate_tokens)
            except LLMExecError as e:
                e.reason = "大模型生成失败。"
                raise e
            if not a_sample_text_to_parse:
                e = LLMExecError
                e.reason = "大模型生成服务没有返回非空内容。"
                raise e
            return a_sample_text_to_parse

        def parser(text_to_parse: str):
            logger.info("正在解析大模型原始生成结果:\n" + str(text_to_parse))
            pattern = re.compile(r'''SAMPLES_START([\s\S]*)SAMPLES_END''')
            parse_result = pattern.findall(text_to_parse)
            if parse_result:
                return parse_result[0]
            else:
                e = SampleParseError(Text2SQLError())
                e.reason = "未能从大模型生成结果中找到样例部分的字符串。"
                raise e

        def reshape_result(result_to_reshape: list, code_table_infos: dict) -> List[List[ColumnModel]]:
            samples_list = []
            columns_list = []
            for a_sample in result_to_reshape:
                for k, v in a_sample.items():
                    column_description = code_table_infos.get(k, {}).get(v, "")
                    columns_list.append(ColumnModel(
                        column_name=k, column_value=v, column_description=column_description))
                samples_list.append(columns_list)
                columns_list = []
            return samples_list

        legal_checked_result = []
        tried_turns = 1
        remain_samples_to_generate = samples_size
        while remain_samples_to_generate > 0 and tried_turns <= max_retry:
            # 尝试生成样例
            logger.info("尝试第" + str(tried_turns) + "次生成。")
            try:
                if tried_turns == 1:
                    sample_text_to_parse = await generate_samples(schema, remain_samples_to_generate,
                                                                  column_detail_info_prompt)
                else:  # 为了确保不生成重复样例，多次生成需参照之前已生成样例规避
                    samples_string = "[\n" + ",\n\t".join(
                        [str(one_sample) for one_sample in legal_checked_result]) + "]"
                    sample_text_to_parse = await generate_samples_with_samples(schema, remain_samples_to_generate,
                                                                               column_detail_info_prompt,
                                                                               samples_string)
            except Exception:
                e = SampleGenerateError(Text2SQLError())
                e.reason = "样例生成失败"
                raise e
            parsed_res = parser(sample_text_to_parse)
            res = []
            try:
                logger.info("尝试将大模型生成的样例数据字符串进行JSON解析:\n" + parsed_res)
                res = json.loads(parsed_res)
            except Exception:
                logger.info("对生成的样例字符串进行JSON解析失败，待JSON解析字符串为:\n" + parsed_res)
                logger.info("尝试一次只生成一个样例，然后使用多次生成达到期望的样例数，可能会大幅度增加样例生成耗时")
                for i in range(remain_samples_to_generate):
                    if res:
                        sample_text_to_parse = await generate_samples_with_samples(schema, 1,
                                                                                   column_detail_info_prompt, str(res))
                    else:  # 为了确保不生成重复样例，多次生成需参照之前已生成样例规避
                        sample_text_to_parse = await generate_samples(schema, 1,
                                                                      column_detail_info_prompt)
                    parsed_res = parser(sample_text_to_parse)
                    try:
                        res += json.loads(parsed_res)
                    except Exception:
                        e = SampleGenerateError(Text2SQLError())
                        e.reason = "单次单条生成依然失败，放弃生成。可能视图或字段过于复杂。"
                        raise e
            # 检查生成的样例字段名是否与视图一致,把非法的去掉，再生成一次与去掉的非法样例数量相同的样例补充进去
            columns = await self.get_view_column_by_id(input_view_id, self.headers)
            input_view_columns_names = set([ColumnDetailModel.model_validate(a_column).technical_name for a_column in
                                            columns["fields"]])
            illegal_sample_number = 0
            legal_sample_number = 0
            for one_sample in res:
                raw_generated_column_names = set(one_sample.keys())
                if not raw_generated_column_names == input_view_columns_names:
                    illegal_sample_number += 1
                    continue
                legal_checked_result.append(one_sample)
                legal_sample_number += 1
            remain_samples_to_generate = illegal_sample_number
            logger.info("第" + str(tried_turns) + "次生成了" + str(
                legal_sample_number) + "个字段名合法样例，期望生成" + str(
                samples_size) + "个字段名合法样例,还需生成" + str(
                remain_samples_to_generate) + "个合法样例,还可以重试" + str(max_retry - tried_turns) + "次")
            tried_turns += 1
        if tried_turns == max_retry and remain_samples_to_generate > 0:
            logger.info("注意，由于最大只能尝试重新生成" + str(max_retry) + "次，本次希望生成" + str(
                samples_size) + "个样例，实际生成了" + str(len(legal_checked_result)) + "个样例。")
        final_result = reshape_result(legal_checked_result, code_table_infos)
        logger.info("最后成功生成了" + str(len(final_result)) + "个样例")
        return final_result

    async def generate_sample_v2(self, input_view_id: str, samples_size: int, user_id: str, max_retry: int = 2) -> List[ColumnModel]:
        # 样例生成函数
        # input:
        #   input_view_id:视图id
        #   samples_size:希望生成几个样例
        # _, sample_generate_prompt_id = await self.ad_prompt_service.from_anydata(self.appid,
        #                                                                          SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME)
        # _, sample_generate_with_samples_prompt_id = await self.ad_prompt_service.from_anydata(self.appid,
        #                                                                                       SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME)
        # input_prompt_template = await self.ad_prompt_service.get_prompt(prompt_id=sample_generate_prompt_id,
        #                                                                 appid=self.appid)
        # if not input_prompt_template:
        #     e = NoPromptTemplateError(Text2SQLError())
        #     e.status = 500
        #     e.reason = "没有从AD取到input_prompt_template"
        #     raise e
        # input_prompt_template = input_prompt_template.replace(
        #     "{{", "{").replace("}}", "}")
        input_prompt_template = SAMPLE_GENERATE_PROMPT_TEMPLATE
        input_with_samples_prompt_template = SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE
        # input_with_samples_prompt_template = await self.ad_prompt_service.get_prompt(
        #     prompt_id=sample_generate_with_samples_prompt_id, appid=self.appid)
        # if not input_with_samples_prompt_template:
        #     e = NoPromptTemplateError(Text2SQLError())
        #     e.status = 500
        #     e.reason = "没有从AD取到input_with_samples_prompt_template"
        #     raise e
        # input_with_samples_prompt_template = input_with_samples_prompt_template.replace(
        #     "{{", "{").replace("}}", "}")
        logger.info("模型名称为：" + self.model_name)
        model_max_length = 20000
        # model_max_length = await self.ad_prompt_service.get_model_max_tokens_length(model_name=self.model_name,
        #                                                                             appid=self.appid)
        #
        # # model_max_length = model_info.get("max_tokens_length", 20000)
        # if not model_max_length:
        #     model_max_length = 20000  # 拿不到模型服务最大长度时，默认答案空间为20000
        #     logger.info("拿不到模型服务最大token数，设置模型服务默认值为：" + str(model_max_length))
        # model_info_list = await  self.ad_prompt_service.get_model_list(model_name=self.model_name,
        #                                                           appid=self.appid)
        # if len(model_info_list) == 0:
        #     raise Exception("模型不存在")

        # model_info = [m_info for m_info in model_info_list if m_info["model_name"] == self.model_name]
        # # m = model_info[0]["model_series"]
        # if len(model_info) > 0 and model_info[0]["model_series"] == "deepseek":
        #     _model_max_length = model_max_token_map.get(model_info[0]["model"])
        #     if _model_max_length is None:
        #         logger.info("内部最大token数配置没配置模型：{}".format(model_info[0]["model"]))
        #     else:
        #         logger.info("模型：{} 最大tokens为 {}".format(model_info[0]["model"], _model_max_length))
        #         model_max_length = _model_max_length

        # logger.info("模型服务最大token数为：" + str(model_max_length))

        schema, column_detail_info_prompt, code_table_infos = await self.construct_columns_detail_info(input_view_id)

        # zkn 第三个参数为字段详细信息prompt
        async def generate_samples(a_schema, the_samples_size, a_column_detail_info_prompt):

            generate_sample_param = {"schema": a_schema, "sample_size": str(the_samples_size),
                                     "column_detail_info": a_column_detail_info_prompt}
            try:

                tpl = Template(input_prompt_template)
            except Exception as e:
                logger.error("模板解析错误：" + str(e))

            content = tpl.render(schema=a_schema, sample_size=str(the_samples_size),
                                                        column_detail_info=a_column_detail_info_prompt)
            # # 动态配置模型服务的答案生成空间，该空间长度 = 模型最大窗口长度 - 输入的tokens数
            # input_prompt = input_prompt_template.format(schema=a_schema, sample_size=str(the_samples_size),
            #                                             column_detail_info=a_column_detail_info_prompt)
            # input_tokens_count = \
            #     await self.ad_prompt_service.tokens_count(input_text=input_prompt, model_name=self.model_name,
            #                                               appid=self.appid)
            input_tokens_count = len(content)
            max_generate_tokens = model_max_length - input_tokens_count - \
                100  # 模型最大上下文空间 - 输入token数 - 100 作为答案空间
            logger.info("无样例时答案生成窗口为:" + str(max_generate_tokens))
            try:
                # zkn  尝试调用模型去生成样例
                # a_sample_text_to_parse = await self.exec_prompt_by_llm(generate_sample_param, self.appid,
                #                                                        prompt_id=sample_generate_prompt_id,
                #                                                        max_tokens=max_generate_tokens)
                api = FindNumberAPI()
                prompt_rendered_msg = [{
                    "role": "user",
                    "content": content
                }]
                x_account_type = "user"
                x_account_id = user_id
                logger.info("x_account_id {}".format(x_account_id))
                a_sample_text_to_parse = await api.exec_prompt_by_llm_dip_understand(prompt_rendered_msg,
                                                                                     x_account_id,
                                                                                     x_account_type,
                                                                                     max_generate_tokens)
            except LLMExecError as e:
                e.reason = "大模型生成失败。"
                raise e
            if not a_sample_text_to_parse:
                e = LLMExecError
                e.reason = "大模型生成服务没有返回非空内容。"
                raise e
            return a_sample_text_to_parse

        async def generate_samples_with_samples(a_schema, the_samples_size, a_column_detail_info_prompt, samples):
            generate_sample_param = {"schema": a_schema, "sample_size": str(the_samples_size),
                                     "column_detail_info": a_column_detail_info_prompt, "samples": samples}

            tpl = Template(input_with_samples_prompt_template)
            content = tpl.render(schema=a_schema,
                                                                                  sample_size=str(
                                                                                      the_samples_size),
                                                                                  column_detail_info=a_column_detail_info_prompt,
                                                                                  samples=samples)

            # # 动态配置模型服务的答案生成空间，该空间长度 = 模型最大窗口长度 - 输入的tokens数
            # input_with_samples_prompt = input_with_samples_prompt_template.format(schema=a_schema,
            #                                                                       sample_size=str(
            #                                                                           the_samples_size),
            #                                                                       column_detail_info=a_column_detail_info_prompt,
            #                                                                       samples=samples)
            # input_tokens_count = \
            #     await self.ad_prompt_service.tokens_count(input_text=input_with_samples_prompt,
            #                                               model_name=self.model_name,
            #                                               appid=self.appid)
            input_tokens_count = len(content)
            max_generate_tokens = model_max_length - input_tokens_count - \
                100  # 模型最大上下文空间 - 输入token数 - 100 作为答案空间
            logger.info("有样例时答案生成窗口为:" + str(max_generate_tokens))
            try:
                # a_sample_text_to_parse = await self.exec_prompt_by_llm(generate_sample_param, self.appid,
                #                                                        sample_generate_with_samples_prompt_id,
                #                                                        max_tokens=max_generate_tokens)
                api = FindNumberAPI()
                prompt_rendered_msg = [{
                    "role": "user",
                    "content": content
                }]
                x_account_type = "user"
                x_account_id = user_id
                a_sample_text_to_parse = await api.exec_prompt_by_llm_dip_understand(prompt_rendered_msg, x_account_id,
                                                                                     x_account_type, max_generate_tokens)
            except LLMExecError as e:
                e.reason = "大模型生成失败。"
                raise e
            if not a_sample_text_to_parse:
                e = LLMExecError
                e.reason = "大模型生成服务没有返回非空内容。"
                raise e
            return a_sample_text_to_parse

        def parser(text_to_parse: str):
            logger.info("正在解析大模型原始生成结果:\n" + str(text_to_parse))
            pattern = re.compile(r'''SAMPLES_START([\s\S]*)SAMPLES_END''')
            parse_result = pattern.findall(text_to_parse)
            if parse_result:
                return parse_result[0]
            else:
                e = SampleParseError(Text2SQLError())
                e.reason = "未能从大模型生成结果中找到样例部分的字符串。"
                raise e

        def reshape_result(result_to_reshape: list, code_table_infos: dict) -> List[List[ColumnModel]]:
            samples_list = []
            columns_list = []
            for a_sample in result_to_reshape:
                for k, v in a_sample.items():
                    column_description = code_table_infos.get(k, {}).get(v, "")
                    columns_list.append(ColumnModel(
                        column_name=k, column_value=v, column_description=column_description))
                samples_list.append(columns_list)
                columns_list = []
            return samples_list

        legal_checked_result = []
        tried_turns = 1
        remain_samples_to_generate = min([50, samples_size])
        while remain_samples_to_generate > 0 and tried_turns <= max_retry:
            # 尝试生成样例
            logger.info("尝试第" + str(tried_turns) + "次生成。")
            try:
                if tried_turns == 1:
                    sample_text_to_parse = await generate_samples(schema, remain_samples_to_generate,
                                                                  column_detail_info_prompt)
                else:  # 为了确保不生成重复样例，多次生成需参照之前已生成样例规避
                    samples_string = "[\n" + ",\n\t".join(
                        [str(one_sample) for one_sample in legal_checked_result]) + "]"
                    sample_text_to_parse = await generate_samples_with_samples(schema, remain_samples_to_generate,
                                                                               column_detail_info_prompt,
                                                                               samples_string)
            except Exception:
                e = SampleGenerateError(Text2SQLError())
                e.reason = "样例生成失败"
                raise e
            parsed_res = parser(sample_text_to_parse)
            res = []
            try:
                logger.info("尝试将大模型生成的样例数据字符串进行JSON解析:\n" + parsed_res)
                res = json.loads(parsed_res)
            except Exception:
                logger.info("对生成的样例字符串进行JSON解析失败，待JSON解析字符串为:\n" + parsed_res)
                logger.info("尝试一次只生成一个样例，然后使用多次生成达到期望的样例数，可能会大幅度增加样例生成耗时")
                for i in range(remain_samples_to_generate):
                    if res:
                        sample_text_to_parse = await generate_samples_with_samples(schema, 1,
                                                                                   column_detail_info_prompt, str(res))
                    else:  # 为了确保不生成重复样例，多次生成需参照之前已生成样例规避
                        sample_text_to_parse = await generate_samples(schema, 1,
                                                                      column_detail_info_prompt)
                    parsed_res = parser(sample_text_to_parse)
                    try:
                        res += json.loads(parsed_res)
                    except Exception:
                        e = SampleGenerateError(Text2SQLError())
                        e.reason = "单次单条生成依然失败，放弃生成。可能视图或字段过于复杂。"
                        raise e
            # 检查生成的样例字段名是否与视图一致,把非法的去掉，再生成一次与去掉的非法样例数量相同的样例补充进去
            columns = await self.get_view_column_by_id(input_view_id, self.headers)
            input_view_columns_names = set([ColumnDetailModel.model_validate(a_column).technical_name for a_column in
                                            columns["fields"]])
            illegal_sample_number = 0
            legal_sample_number = 0
            for one_sample in res:
                raw_generated_column_names = set(one_sample.keys())
                if not raw_generated_column_names == input_view_columns_names:
                    illegal_sample_number += 1
                    continue
                legal_checked_result.append(one_sample)
                legal_sample_number += 1
            remain_samples_to_generate = illegal_sample_number
            logger.info("第" + str(tried_turns) + "次生成了" + str(
                legal_sample_number) + "个字段名合法样例，期望生成" + str(
                samples_size) + "个字段名合法样例,还需生成" + str(
                remain_samples_to_generate) + "个合法样例,还可以重试" + str(max_retry - tried_turns) + "次")
            tried_turns += 1
        if tried_turns == max_retry and remain_samples_to_generate > 0:
            logger.info("注意，由于最大只能尝试重新生成" + str(max_retry) + "次，本次希望生成" + str(
                samples_size) + "个样例，实际生成了" + str(len(legal_checked_result)) + "个样例。")
        if len(legal_checked_result) < samples_size:
            n_legal_checked_result = random_column_data(legal_checked_result, samples_size)
            final_result = reshape_result(n_legal_checked_result, code_table_infos)
        else:

            final_result = reshape_result(legal_checked_result, code_table_infos)
        logger.info("最后成功生成了" + str(len(final_result)) + "个样例")
        return final_result


def random_column_data(input_data, output_data_size):
    column_data_info = {}
    for data in input_data:
        for key, value in data.items():
            if key not in column_data_info:
                column_data_info[key] = []
            column_data_info[key].append(value)
    output_data = []
    for i in range(output_data_size):
        one_data = {}
        for key in column_data_info:
            one_data[key] = random.choice(column_data_info[key])
        output_data.append(one_data)
    return output_data

