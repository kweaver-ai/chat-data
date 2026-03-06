import asyncio
import re
import time, json
from datetime import datetime


from pydantic import BaseModel
from regex import search

from app.logs.logger import logger
from app.cores.data_comprehension.dc_api import DataComprehensionAPI
from app.cores.cognitive_assistant.qa_api import FindNumberAPI
from app.cores.prompt.manage.ad_service import PromptServices
from app.cores.prompt.manage.payload_prompt import prompt_map


from app.cores.data_comprehension.dc_model import *
from app.cores.data_comprehension.dc_error import (DataCatalogInfoError, DataCataLogMountResourceError,
    DepartmentResponsibilitiesError,DataCataLogOfDepartmentError,DataExploreError)
from app.cores.text2sql.t2s_error import (FrontendColumnError, Text2SQLError)

data_func = DataComprehensionAPI()
llm_func = FindNumberAPI()
# ad = PromptServices()

# 检查字典中的键字符串是否包含 "|" 字符
def contains_pipe(input_dict):
    for key in input_dict.keys():
        if '|' in key:
            return True
    return False


def extract_id_from_pipe_str(input_string):
    """
    Extracts the first part of a string before the first pipe character.

    Summary:
    This function takes an input string and returns the substring that
    appears before the first pipe ('|') character. If no pipe character
    is found, it returns None.

    Args:
        input_string (str): The string from which to extract the ID.

    Returns:
        Optional[str]: The extracted ID or None if no pipe character is found.
    """
    match = re.match(r'([^|]+)\|', input_string)
    if match:
        return match.group(1)
    return None

# 复合表达的结果处理
def refine_complex_expression_results(text:dict, table_information):
    # def control_fhbd(text: json, table_information):
    logger.info(f'复合表达结果后处理开始：\n, 表名：{text}, 表字段：{table_information}')
    answer = {}
    catalog_infos = []
    for i in table_information:
        for id in text["table_id"]:
            if id == i["id"]:
                catalog_info = {
                    "id": i["id"],
                    "code": i['code'],
                    "title": i['name'],
                    "description": i['description']
                }
                catalog_infos.append(catalog_info)
    answer["comprehension"] = text["explain"]
    answer["catalog_infos"] = catalog_infos
    return answer

# 业务维度等
def refine_results_extract_id(text: dict):
# def refine_ywwd_results(text: json):
    # def control_ywwd_(text: json):
    answer = []
    # lines=text.split('\n')
    for key, value in text.items():
        res = re.findall(r"'(.*?)'", value)
        if len(res) == 1:
            column_info = {
                "id": extract_id_from_pipe_str(key),
                "name_cn": res[0],
                "data_type": ""
            }
        else:
            continue
        answer.append({"comprehension": value, "column_info": column_info})
    return answer

def refine_results_general(text: dict):
# def refine_ywwd_results(text: json):
    # def control_ywwd_(text: json):
    answer = []
    # lines=text.split('\n')
    for key, value in text.items():
        res = re.findall(r"'(.*?)'", value)
        if len(res) == 1:
            column_info = {
                "id": key,
                "name_cn": res[0],
                "data_type": ""
            }
        else:
            continue
        answer.append({"comprehension": value, "column_info": column_info})
    return answer


async def llm_invoke_dip(headers, prompt_name, query, search_configs, data_dict=None, description=None)-> dict:
    """ 调用大模型进行数据理解
        params:
            appid: 应用id
            prompt_name: 提示词模板名称
            query: 待理解的目录名
            data_dict: 待理解的目录项列表
            description: 单位职责
        returns:
            res_load: 大模型返回结果，dict类型
        提示词比如为：
            你是一个数据理解专家,现在某个单位的一张表,这个单位的职责是:
            {{description}}
            表为'{{query}}',表字段如下：{{data_dict}}
    """
    logger.info(
        f'调用大模型进行数据理解开始：\n表名：{query}, \n表字段：{data_dict}, \nprompt_name：{prompt_name}, \n部门职责：{description}')

    start1 = time.ctime()
    start = time.time()
    # 构建prompt_data时进行空值检查
    prompt_data = {'query': str(query)}
    if data_dict is not None:
        prompt_data['data_dict'] = str(data_dict)
    if description is not None:
        prompt_data['description'] = description
    # if description == 'Nothing' and data_dict != 'Nothing':
    #     prompt_data = {'query': str(query), 'data_dict': str(data_dict)}
    # elif description == 'Nothing' and data_dict == 'Nothing':
    #     prompt_data = {'query': str(query)}
    # else:
    #     prompt_data = {'query': query, 'data_dict': str(data_dict), 'description': description}
    # _, prompt_id = await ad.from_anydata(
    #     appid=appid,
    #     name=prompt_name
    # )
    prompt_rendered_msg=[]
    prompt_template = prompt_map.get(prompt_name, "")
    logger.info(f'prompt_template={prompt_template}')
    if prompt_template:
        prompt_rendered = prompt_template
        for prompt_var, value in prompt_data.items():
            logger.info(f'{prompt_var}={value}')
            prompt_rendered = prompt_rendered.replace("{{" + str(prompt_var) + "}}", str(value))
        logger.info(f'prompt_rendered={prompt_rendered}')
        prompt_rendered_msg = [
            {
                "role": "user",
                "content": prompt_rendered
            }
        ]

    try:
        # res = await llm_func.exec_prompt_by_llm(prompt_data, appid, prompt_id)
        # res = await llm_func.exec_prompt_by_llm_dip_private(
        #     prompt_rendered_msg=prompt_data,
        #     search_configs=search_configs,
        #     x_account_id=search_params.subject_id,
        #     x_account_type=search_params.subject_type
        # )
        token = headers.get("Authorization")
        res = await llm_func.exec_prompt_by_llm_dip_external(
            token=token,
            prompt_rendered_msg=prompt_rendered_msg,
            search_configs=search_configs
        )
    except Exception as e:
        logger.warning(f'调用大模型出错，报错信息如下: \n{e}')
        # res = " "
        return {}
    if res:
        logger.info(f'大模型整理结果为：\n{res}')
        sp = res.split("```")
        if len(sp) > 1:
            if sp[1][:4] == 'json':
                a = sp[1][4:]
            else:
                a = sp[1]
            # 如果大模型输出不是json格式，处理异常, 置为空
            try:
                res_load = json.loads(a)
                # 解析结果不一定是dict类型， 也可能是list类型或其他JSON支持的数据类型（如字符串、数字、布尔值或null）。
                # if not isinstance(res_load, dict):
                #     logger.warning("大模型返回结果不是有效的字典格式")
                #     res_load = {}
            except Exception as e:
                logger.info(f'大模型返回json解析出错，结果置为空, 报错信息如下: \n{e}')
                res_load = {}
        else:
            res_load = {}
        end1 = time.ctime()
        end = time.time()
        logger.info(f'开始时间为：{start1}, 结束时间为：{end1}, 调用大模型耗时为：{end - start}')
        return res_load
    else:
        return {}

# 处理探查的结果数据
async def func_data_explore(formview_uuid, headers, id_time, id_space):
    time_list, space_list= [],[]
    # 在调用方处理异常，这里只抛出异常即可
    data_explore_res = await data_func.get_data_explore(
        formview_uuid=formview_uuid,
        headers=headers
    )
    for field in data_explore_res:
        # logger.info(f"数据探查结果为：\n{field}")
        # print("field['field_id']= ",field['field_id'])
        if field['field_id'] in id_time:
            for detail in field['details']:
                if detail['rule_name'] in ["最小值", "最大值"]:
                    time_list.append(eval(detail['result'])[0]['result'])
        if field['field_id'] in id_space:
            for detail in field['details']:
                if detail['rule_name'] == '枚举值分布':
                    # print("枚举值分布：",detail['result'])
                    detail_dict = eval(detail['result'])
                    # print(json.dumps(detail_dict,ensure_ascii=False,indent=4))
                    for rst in eval(detail['result']):
                        space_list.append(rst['key'])
    return time_list, space_list

# 数据理解核心函数
async def func_get_data(inputs, headers, dimension,search_configs):
    # 在handler中已经校验过入参 catalog_id和dimension， 如果为空， 不会执行到这里
    processing_catalog_id = inputs.get('catalog_id', None)
    appid = inputs.get('appid', None)
    department_id_list = []

    # 1. 获取数据资源目录的详情，其中包括 department_id
    # source_department_id 是数据资源的来源部门id，department_id 是目录提供方的部门id， 一般情况下，二者是一致的,  用department_id
    try:
        catalog_information = await data_func.get_data_catalog_info(
            headers=headers,
            catalog_id=processing_catalog_id
        )
        logger.info(f'catalog_information = {catalog_information}')
        # 部门拿到的是数据资源目录提供方的部门id， 如果为空，或者获取失败，则返回空响应
        if catalog_information is None:
            error_msg = f"获取数据资源目录 {processing_catalog_id} 的详情信息 失败！"
            logger.error(error_msg)
            return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
        department_id: str | None = catalog_information.get('department_id', None)
        department_id_list.append(department_id)
        if department_id is None:
            error_msg = f"数据资源目录 {processing_catalog_id} 的部门id为空！"
            logger.error(error_msg)
            return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    except DataCatalogInfoError as e:
        error_msg = "获取数据资源目录详情信息异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    except Exception as e:
        error_msg = "获取数据资源目录详情信息过程中，发生通用类型的异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    # 1.1 获取数据目录挂接的数据资源
    try:
        processing_catalog_mount_resource = await data_func.get_data_catalog_mount_resource(
            headers=headers,
            catalog_id=processing_catalog_id
        )
        mount_resource_list = processing_catalog_mount_resource.get("mount_resource")
        if mount_resource_list:
            for mount_resource in mount_resource_list:
                # '数据资源类型 resource_type 枚举值 1：逻辑视图 2：接口 3:文件资源'
                if mount_resource.get("resource_type") == 1:
                    processing_catalog_mount_formview_uuid = mount_resource.get("resource_id")
        else:
            # mount_resource_list 为空， processing_catalog_mount_formview_uuid = "" 为空字符串， 后续需要注意处理
            logger.warning(f"数据目录 {processing_catalog_id} 挂接的数据资源为空")
    except DataCataLogMountResourceError as e:
        error_msg = "获取数据目录挂接的数据资源异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    except Exception as e:
        error_msg = "获取数据目录挂接的数据资源过程中，发生通用类型的异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )

    # 2. 获取部门的职责
    try:
        department_responsibilities = await data_func.get_department_attributes(
            headers=headers,
            department_id=department_id
        )
        logger.info(f'department_responsibilities = {department_responsibilities}')

        if department_responsibilities is None:
            error_msg = f"数据资源目录 {processing_catalog_id} 的部门职责为空！"
            logger.warning(error_msg)
            # return create_empty_data_comprehension_response(dimension, error_msg)
        if department_responsibilities == '':
            error_msg = f"数据资源目录 {processing_catalog_id} 的部门职责为空！"
            logger.warning(error_msg)
            # 部门职责可能为空字符串，后续处理时要注意
            # return create_empty_data_comprehension_response(dimension, error_msg)
    except DepartmentResponsibilitiesError as e:
        error_msg = "获取部门职责信息异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    except Exception as e:
        error_msg="获取部门职责信息异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )

    # 3. 获取该部门下所有的数据目录id（雪花id，没有uuid）,code,name,description,挂接资源的id（除了指标外都是uuid）对应结果
    try:
        dept_all_catalog_info_list = await data_func.get_basic_search_result(
            headers=headers,
            catalog_id=processing_catalog_id,
            department_id_list=department_id_list,
            size=50
        )
        # dept_all_catalog_info_list = await data_func.get_department_all_data(department_id, headers)
        logger.info(f'获取该部门下所有的数据目录信息以及挂接资源的id：dept_all_catalog_info_list = {dept_all_catalog_info_list}')
        if not dept_all_catalog_info_list:
            logger.warning("部门下没有数据资源")
            # 查询结果可能为空，需要容错处理
    except DataCataLogOfDepartmentError as e:
        error_msg = "获取部门下所有的数据资源信息异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )
    except Exception as e:
        error_msg = "获取部门下所有的数据资源信息过程中，发生通用类型的异常"
        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
        return create_empty_data_comprehension_response(
                dimension=dimension,
                error_str=error_msg
            )

    ##记录表的id,name,description方便后面查找，待传入大模型prompt，
    # processing_catalog_column_id_name_list 表及字段name和id,由于业务维度, catalog_id_name_columns_list 所有表和包含的字段信息,由于复合表达
    catalog_info_no_source_list, processing_catalog_column_id_name_list, catalog_id_name_columns_list = [],[],[]
    #catalog_mount_columnid_and_type_dict 的形式,记录字段的uuid和类型，用于筛选时间范围和空间范围字段//////
    # query_information_dict 记录待探查
    catalog_mount_columnid_and_type_dict, query_information_dict = {},{}
    ##因为数据探查是对逻辑视图进行的， 所以需要查出来目录所挂接逻辑视图的mount_formview_uuid，调用数据探查接口


    # 4. 获取部门下所有数据目录信息项和挂接资源的字段信息

    if dept_all_catalog_info_list:
        for catalog_info in dept_all_catalog_info_list:
            catalog_info_no_source_list.append(
                {
                    "id": catalog_info.get("id", ""),
                    "code": catalog_info.get("code", ""),
                    "name": catalog_info.get("name", ""),
                    'description': catalog_info.get('description', "")
                }
            )

            # 4.1 获取数据资源字段的详细信息
            column_list = []
            # '字段类型 0:数字型 1:字符型 2:日期型 3:日期时间型 5:布尔型 6:其他 7:小数型 8:高精度型 9:时间型'
            try:
                # 获取一个数据目录的信息项列表
                catalog_column_info_list = await data_func.get_catalog_column_details(
                    catalog_id=catalog_info['id'],
                    headers=headers,
                    limit=100
                )
                # logger.info(f'catalog_column_info_list = {catalog_column_info_list}')
                if catalog_column_info_list:
                    for column_info in catalog_column_info_list:
                        column_list.append(column_info['business_name'])
                        # 仅在时间范围和空间范围中起作用， 只需要待理解数据目录的，无需获取部门所有信息项对应的逻辑视图字段id，name信息
                        # catalog_mount_columnid_and_type_dict[column_info['id']] = {
                        #     'source_id': column_info['source_id'],
                        #     'data_type': column_info['data_type']}
                        # 如果是需要理解的目录id
                        if catalog_info['id'] == processing_catalog_id:
                            catalog_mount_columnid_and_type_dict[column_info['id']] = {
                                'source_id': column_info['source_id'],
                                'data_type': column_info['data_type']
                            }
                            processing_catalog_column_id_name_list.append(
                                column_info['id'] + '|' + column_info['business_name']
                            )
                            # processing_catalog_mount_formview_uuid = catalog_info['source_id'][0]
                catalog_id_name_columns_list.append({catalog_info['id'] + '|' + catalog_info['name']: column_list})
                if catalog_info['id'] == processing_catalog_id:
                    query_information_dict = {catalog_info.get('name'): column_list}
            except FrontendColumnError as e:
                logger.warning(f'获取数据资源字段的详细信息异常，报错信息如下: \n{str(e)}')
            except Exception as e:
                logger.warning(f'获取数据资源字段的详细信息过程中，发生通用类型的异常: \n{str(e)}')
    else:
        logger.warning("部门下没有数据资源")
    # 部门下数据目录很多时，要控制上限， 导致待理解目录没有被查出来，
    # 以上的处理会导致待理解的数据目录没有关联上字段数据column_id_name_list， 需要提供以下的保底措施
    if not processing_catalog_column_id_name_list:
        try:
            catalog_column_info_list = await data_func.get_catalog_column_details(
                catalog_id=processing_catalog_id,
                headers=headers,
                limit=100
            )
            if catalog_column_info_list:
                column_name_list_of_processing_catalog = []
                for column_info in catalog_column_info_list:
                    catalog_mount_columnid_and_type_dict[column_info['id']] = {
                        'source_id': column_info['source_id'],
                        'data_type': column_info['data_type']}
                    column_name_list_of_processing_catalog.append(column_info['business_name'])
                    processing_catalog_column_id_name_list.append(
                        column_info['id'] + '|' + column_info['business_name'])
                query_information_dict = {catalog_information.get('name'): column_name_list_of_processing_catalog}
        except FrontendColumnError as e:
            logger.warning(f'获取数据资源字段的详细信息异常，报错信息如下: \n{str(e)}')
        except Exception as e:
            logger.warning(f'获取数据资源字段的详细信息过程中，发生通用类型的异常: \n{str(e)}')
    # logger.info(f"catalog_information = \n{catalog_information}")
    # logger.info(f"department_responsibilities = \n{department_responsibilities}")
    # logger.info(f"dept_all_catalog_info_list = \n{dept_all_catalog_info_list}")
    # logger.info(f"catalog_info_no_source_list = \n{catalog_info_no_source_list}")
    logger.info(f"processing_catalog_column_id_name_list = \n{processing_catalog_column_id_name_list}")
    # logger.info(f"catalog_id_name_columns_list = \n{catalog_id_name_columns_list}")
    # 仅在时间范围和空间范围中起作用， 只需要待理解数据目录的，无需获取部门所有信息项对应的逻辑视图字段id，name信息
    logger.info(f"catalog_mount_columnid_and_type_dict = \n{catalog_mount_columnid_and_type_dict}")
    logger.info(f"query_information_dict = \n{query_information_dict}")
    logger.info(f"processing_catalog_mount_formview_uuid = \n{processing_catalog_mount_formview_uuid}")



    ##分别记录时间范围字段和空间范围字段
    time_field_source_uuid, space_field_source_uuid = [], []
    processing_catalog_name = catalog_information.get("name")

    # 5. 根据不同的数据理解维度， 进行不同的处理
    # 5.1 时间字段用大模型理解， 大模型判断的时间字段中， 如果有日期型或日期时间型，则通过查询探查结果计算时间范围
    if dimension in [TIME_FIELD, TIME_RANGE]:
        # 先用大模型进行时间字段的判断， 并进行时间字段理解
        # 然后再根据数据类型选出大模型输出结果中日期型和日期时间型的字段， 通过数据探查结果得到其最大值，最小值，作为时间范围
        # 时间字段按照探查结果的时间类型来判断，
        # ”时间范围“用探查结果的最大值和最小值，如果探查结果中没有时间字段， 则”时间范围“为空

        logger.info(f"大模型提示词 {TEMPLATE_TIME_FIELD} 入参为："
                    f"\n待理解的目录名称： {processing_catalog_name}"
                    f"\n待理解的目录信息项列表: {processing_catalog_column_id_name_list}"
                    f"\n单位职责：{department_responsibilities}")
        # llm_invoke_dip()内部处理了异常， 如果发生异常，会返回空字典，这里无需再处理异常

        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_TIME_FIELD,
            query=processing_catalog_name,
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        logger.info(f"大模型回答： \n{res_load}")
        if isinstance(res_load, dict):
            time_fields_llm_answer = res_load.get(TIME_FIELD)
        else:
            error_msg = "大模型返回结果的”时间字段理解“为空"
            logger.error(f'{error_msg}')
            time_fields_llm_answer = {}
        logger.info(f'time_fields_llm_answer = {time_fields_llm_answer}')
        # 如果大模型返回结果的”时间字段理解“，是空，或者空字典
        if not time_fields_llm_answer:
            error_msg = "大模型返回结果的”时间字段理解“为空"
            if dimension == TIME_FIELD:
                return {"dimension": dimension, "answer": None, "error_msg": error_msg}
            if dimension == TIME_RANGE:
                return {"dimension": dimension, "answer": [{'start': None, 'end': None}], "error_msg": error_msg}
        # 如果大模型返回结果的”时间字段理解“，不为空，也不是空字典
        else:
            # 输入data_dict都是这种形式 processing_catalog_column_id_name_list =
            if dimension == TIME_FIELD:
                if contains_pipe(time_fields_llm_answer):
                    answer = refine_results_extract_id(time_fields_llm_answer)
                else:
                    answer = refine_results_general(time_fields_llm_answer)
                return {"dimension": dimension, "answer": answer}
            if dimension == TIME_RANGE:
                # 再根据数据类型选出大模型输出结果中日期型和日期时间型的字段，['data_type'] in [2, 3]
                # 这里有个问题， 如果信息项名称是英文，而大模型识别结果解析后拿到的是中文名称
                time_field_id_list=[]
                if contains_pipe(time_fields_llm_answer):
                    for key,value in time_fields_llm_answer.items():
                        time_field_id = extract_id_from_pipe_str(key)
                        time_field_id_list.append(time_field_id)
                else:
                    for key,value in time_fields_llm_answer.items():
                        time_field_id = key
                        time_field_id_list.append(time_field_id)
                logger.info(f'before datatype filter, time_field_id_list = {time_field_id_list}')
                for time_field_id in time_field_id_list:
                    field_info = catalog_mount_columnid_and_type_dict.get(time_field_id)
                    if field_info:
                        field_data_type = field_info.get('data_type')
                        if field_data_type is not None and field_data_type in [2, 3]:
                                time_field_source_uuid.append(field_info['source_id'])
                logger.info(f'time_field_source_uuid = {time_field_source_uuid}')
                # 通过数据探查结果得到其最大值，最小值，作为时间范围
                if len(time_field_source_uuid)>0:
                    try:
                        time_list, _ = await func_data_explore(formview_uuid=processing_catalog_mount_formview_uuid,
                                                               headers=headers,
                                                               id_time=time_field_source_uuid,
                                                               id_space=space_field_source_uuid)
                        logger.info(f"日期时间字段的探查结果列表：\n{time_list}")
                        if time_list:
                            min_date = datetime.strptime(min(time_list), "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")
                            max_date = datetime.strptime(max(time_list), "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")
                            return {"dimension": dimension, "answer": [{'start': min_date, 'end': max_date}]}
                        else:
                            error_msg = "时间字段探查结果为空"
                            return {"dimension": dimension, "answer": [{'start': None, 'end': None}], "error": error_msg}
                    except DataExploreError as e:
                        error_msg = "获取时间字段探查结果异常"
                        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
                        return {"dimension": dimension, "answer": [{'start': None, 'end': None}], "error": error_msg}
                    except Exception as e:
                        error_msg = "获取时间字段探查结果过程中， 发生通用类型的异常"
                        logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
                        return {"dimension": dimension, "answer": [{'start': None, 'end': None}], "error": error_msg}
                else:
                    error_msg="时间字段探查结果为空"
                    return {"dimension": dimension, "answer": [{'start': None, 'end': None}], "error": error_msg}
    # 5.2 空间范围、空间字段理解
    elif dimension in [SPACE_RANGE, SPACE_FIELD]:
        # query = catalog_information.get("name")
        logger.info(f"大模型提示词 {TEMPLATE_SPACE_FIELD} 入参为："
                    f"\n待理解的目录名称： {processing_catalog_name}"
                    f"\n待理解的目录信息项列表: {processing_catalog_column_id_name_list}"
                    f"\n单位职责：{department_responsibilities}")
        # llm_invoke_dip()内部处理了异常， 如果发生异常，会返回空字典，这里无需再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_SPACE_FIELD,
            query=processing_catalog_name,
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs,
        )
        # answer = control_ywwd(res_load['空间维度'])
        logger.info(f"大模型回答： \n{res_load}")
        if isinstance(res_load, dict) and SPACE_FIELD in res_load:
            space_fields_llm_answer = res_load.get(SPACE_FIELD)
        else:
            error_msg = "空间字段理解结果为空"
            logger.error(f'{error_msg}')
            space_fields_llm_answer = {}
        logger.info(f'space_fields_llm_answer = {space_fields_llm_answer}')
        # 如果大模型返回结果的”空间字段理解“，是空，或者空字典
        if not space_fields_llm_answer:
            error_msg = "没有空间字段"
            if dimension == SPACE_FIELD:
                return {"dimension": dimension, "answer": None, "error": error_msg}
            if dimension == SPACE_RANGE:
                return {"dimension": dimension, "answer": None, "error": error_msg}
        # 如果大模型返回结果的”空间字段理解“，不为空，也不是空字典
        else:
            # 大模型判断存在空间字段
            if dimension == SPACE_FIELD:
                # 输入data_dict都是这种形式 processing_catalog_column_id_name_list =

                if contains_pipe(space_fields_llm_answer):
                    answer = refine_results_extract_id(space_fields_llm_answer)
                else:
                    answer = refine_results_general(space_fields_llm_answer)
                logger.info(f'answer = {answer}')
                return {"dimension": dimension,"answer": answer}
            if dimension == SPACE_RANGE:
                # 需要将id解析出来
                space_field_id_list = []
                if contains_pipe(space_fields_llm_answer):
                    for key, value in space_fields_llm_answer.items():
                        space_field_id = extract_id_from_pipe_str(key)
                        space_field_id_list.append(space_field_id)
                else:
                    for key, value in space_fields_llm_answer.items():
                        space_field_id = key
                        space_field_id_list.append(space_field_id)
                logger.info(f'space_field_id_list = {space_field_id_list}')
                for space_field_id in space_field_id_list:
                    field_info = catalog_mount_columnid_and_type_dict.get(space_field_id)
                    # logger.info(f'field_info = {field_info}')
                    if field_info:
                        source_id = field_info.get('source_id')
                        # logger.info(f'source_id = {source_id}')
                        if source_id:
                            space_field_source_uuid.append(source_id)
                    else:
                        error_msg = "数据资源目录空间字段对应挂接资源字段uuid不存在"
                        return {"dimension": dimension, "answer": None, "error": error_msg}

                logger.info(f"数据资源目录空间字段对应挂接资源字段uuid的列表：\n{space_field_source_uuid}" )
                try:
                    _, space_list = await func_data_explore(
                        formview_uuid=processing_catalog_mount_formview_uuid,
                        headers=headers,
                        id_time=time_field_source_uuid,
                        id_space=space_field_source_uuid)
                    logger.info(f"空间字段探查值的列表：\n{space_list}" )
                except DataExploreError as e:
                    error_msg = "获取空间字段探查结果异常"
                    logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
                    return {"dimension": dimension, "answer": None, "error": error_msg}
                except Exception as e:
                    error_msg = "获取空间字段探查结果过程中，发生通用类型的异常"
                    logger.error(f'{error_msg}，报错信息如下: \n{str(e)}')
                    return {"dimension": dimension, "answer": None, "error": error_msg}

                logger.info(
                    f"大模型提示词 {TEMPLATE_SPACE_RANGE} 入参为："
                    f"待判断范围的空间字段探查值列表： {space_list}"
                )
                if space_list:
                    # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
                    res = await llm_invoke_dip(
                        headers=headers,
                        prompt_name=TEMPLATE_SPACE_RANGE,
                        query=space_list,
                        search_configs=search_configs
                    )
                    if isinstance(res, dict):
                        return {"dimension": dimension, "answer": res.get(SPACE_RANGE)}
                    else:
                        error_msg = "大模型返回结果格式错误"
                        logger.error(f'{error_msg}')
                        return {"dimension": dimension, "answer": None, "error": error_msg}
                else:
                    error_msg = "空间字段探查结果为空"
                    return {"dimension": dimension, "answer": None, "error": error_msg}

    # 业务维度
    elif dimension == BUSINESS_DIMENSION:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_BUSINESS_DIMENSION,
            query=processing_catalog_name,
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        # answer = control_ywwd(res_load['业务维度'])
        logger.info(f"大模型回答： \n{res_load}")
        if isinstance(res_load, dict):
            biz_dim = res_load.get(dimension)
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}
        # 如果大模型返回的业务维度理解结果为空或者空字典
        if not biz_dim:
            error_msg = "业务维度理解为空"
            return {"dimension": dimension, "answer": None, "error": error_msg}
        # 如果大模型返回的业务维度理解结果不为空，也不是空字典
        else:
            if contains_pipe(biz_dim):
                answer = refine_results_extract_id(biz_dim)
            else:
                answer = refine_results_general(biz_dim)
        # answer = refine_results_extract_id(res_load['业务维度'])
        return {"dimension": dimension, "answer": answer}

    # 复合表达
    elif dimension == COMPLEX_EXPRESSION:
        answer=[]
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        relation = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_COMPLEX_EXPRESSION,
            # query=catalog_information.get("name"),
            query=query_information_dict,
            data_dict=catalog_id_name_columns_list,
            search_configs=search_configs
        )
        # 正常情况下， 复合表达的大模型理解结果是一个列表，如果发生异常， 返回空字典
        if relation:
            # 对复合表达的大模型理解结果进行处理，构建成结果格式
            for item in relation:
                res = refine_complex_expression_results(item, catalog_info_no_source_list)
                answer.append(res)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "复合表达理解为空"
            return {"dimension": dimension, "answer": None, "error": error_msg}

    # 服务范围
    elif dimension == SERVICE_SCOPE:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_SERVICE_SCOPE,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )

        # answer = control_ywwd(res_load['业务维度'])
        if isinstance(res_load, dict):
            answer = res_load.get(SERVICE_SCOPE)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}


    # 服务领域
    elif dimension == SERVICE_FIELD:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_SERVICE_FIELD,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        # answer = control_ywwd(res_load['业务维度'])
        if isinstance(res_load, dict):
            answer = res_load.get(SERVICE_FIELD)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}


    # 正面支撑
    elif dimension == POSITIVE_SUPPORT:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_POSITIVE,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        # answer = control_ywwd(res_load['业务维度'])
        if isinstance(res_load, dict):
            answer = res_load.get(POSITIVE_SUPPORT)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}



    # 负面支撑
    elif dimension == NEGATIVE_SUPPORT:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_NEGATIVE,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        # answer = control_ywwd(res_load['业务维度'])
        if isinstance(res_load, dict):
            answer = res_load.get(NEGATIVE_SUPPORT)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}

    # 保护控制
    elif dimension == PROTECTION_CONTROL:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_PROTECTION,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        if isinstance(res_load, dict):
            answer = res_load[PROTECTION_CONTROL]
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}

    elif dimension == PROMOTION_DRIVE:
        # llm_invoke_dip()内部已经封装了异常处理，如果发生异常，会返回空字典，这里不需要再处理异常
        res_load = await llm_invoke_dip(
            headers=headers,
            prompt_name=TEMPLATE_PROMOTION,
            query=catalog_information.get("name"),
            data_dict=processing_catalog_column_id_name_list,
            description=department_responsibilities,
            search_configs=search_configs
        )
        if isinstance(res_load, dict):
            answer = res_load.get(PROMOTION_DRIVE)
            return {"dimension": dimension, "answer": answer}
        else:
            error_msg = "大模型返回结果格式错误"
            logger.error(f'{error_msg}')
            return {"dimension": dimension, "answer": None, "error": error_msg}
        # answer = control_ywwd(res_load['业务维度'])



    # 所有维度一次性理解
    # elif dimension == ALL_DIMENSIONS:
    #     relation = await llm_invoke(appid=appid,
    #                             prompt_name=TEMPLATE_COMPLEX_EXPRESSION,
    #                             query=query_information_dict,
    #                             data_dict=catalog_id_name_columns_list
    #                             )
    #     res_load = await llm_invoke(appid=appid,
    #                             prompt_name=TEMPLATE_ALL_DIMENSIONS,
    #                             query=catalog_information.get("name"),
    #                             data_dict=processing_catalog_column_id_name_list,
    #                             description=department_responsibilities)
    #     comprehension = []
    #     for key, value in res_load.items():
    #         data_json = {}
    #         data_json["dimension"] = key
    #         if key == BUSINESS_DIMENSION:
    #             # data_json["answer"] = control_ywwd(res_load['业务维度'])
    #             data_json["answer"] = refine_results_extract_id(res_load[BUSINESS_DIMENSION])
    #
    #         elif key == "时间字段理解":
    #             for id in res_load['时间字段理解'].keys():
    #                 if id in catalog_mount_columnid_and_type_dict.keys() and catalog_mount_columnid_and_type_dict[id]['data_type'] in [2, 3]:
    #                     time_field_source_uuid.append(catalog_mount_columnid_and_type_dict[id]['source_id'])
    #             # data_json["answer"] = control_ywwd(res_load['时间字段理解'])
    #             data_json["answer"] = refine_results_extract_id(res_load['时间字段理解'])
    #         elif key == "空间字段理解":
    #             for id in res_load['空间字段理解'].keys():
    #                 if id in catalog_mount_columnid_and_type_dict.keys():
    #                     space_field_source_uuid.append(catalog_mount_columnid_and_type_dict[id]['source_id'])
    #             # data_json["answer"] = control_ywwd(res_load['空间字段理解'])
    #             data_json["answer"] = refine_results_extract_id(res_load['空间字段理解'])
    #         else:
    #             data_json["answer"] = value
    #         comprehension.append(data_json)
    #     try:
    #         time_list,space_list=await func_data_explore(processing_catalog_mount_formview_uuid, headers, time_field_source_uuid, space_field_source_uuid)
    #         if not time_list:
    #             logger.info('未获取数据探查的时间')
    #             comprehension.append({"dimension": "时间范围", "answer": [{'start': None, 'end': None}]})
    #         else:
    #             comprehension.append(
    #                 {"dimension": "时间范围", "answer": [{'start': min(time_list), 'end': max(time_list)}]})
    #         if not space_list:
    #             logger.info('未获取数据探查的地点')
    #             comprehension.append({"dimension": "空间范围", "answer": None})
    #         else:
    #             res = await llm_invoke(appid=appid,
    #                                prompt_name=TEMPLATE_SPACE_RANGE,
    #                                query=space_list)
    #             comprehension.append(
    #                 {"dimension": "空间范围", "answer": res['空间范围']})
    #     except Exception as e:
    #         logger.error(f'获取数据探查接口出错，报错信息如下: \n{str(e)}')
    #         comprehension.append({"dimension": "时间范围", "answer": [{'start': None, 'end': None}]})
    #         comprehension.append({"dimension": "空间范围", "answer": None})
    #     answer = []
    #     for i in relation:
    #         res = refine_complex_expression_results(i, catalog_info_no_source_list)
    #         answer.append(res)
    #     comprehension.append({"dimension": "复合表达", "answer": answer})
    #     return {
    #         "catalog_id": catalog_id,
    #         "comprehension": comprehension
    #     }
    # else:
    #     if dimension in prompt_map.keys():
    #         res_load = await llm_invoke(appid=appid,
    #                                 prompt_name=prompt_map[dimension],
    #                                 query=catalog_information.get("name"),
    #                                 data_dict=processing_catalog_column_id_name_list,
    #                                 description=department_responsibilities)
    #
    #         return {"dimension": dimension, "answer": res_load[dimension]}
    else:
        return f"数据理解维度 '{dimension}' 不支持"

# 包装了func_get_data(), handler调用这个函数
# async def get_data_comprehension(request, catalog_id, dimension):
async def get_data_comprehension(authorization, catalog_id, dimension, search_configs):
    headers = {"Authorization": authorization}
    # appid = ad.get_appid()

    # if not appid:
    #     error_msg = "获取ad appid失败！无法进行数据理解！"
    #     logger.error(error_msg)
    #     return create_empty_data_comprehension_response(
    #         dimension=dimension,
    #         error_str=error_msg
    #     )

    inputs = {'catalog_id': catalog_id}
    dc_rst = await func_get_data(
        inputs=inputs,
        headers=headers,
        dimension=dimension,
        search_configs=search_configs
    )

    if not dc_rst:
        error_msg = "数据理解结果为空！"
        logger.error(error_msg)
        return create_empty_data_comprehension_response(
            dimension=dimension,
            error_str=error_msg
        )
    logger.info(f'数据理解结果 =\n{json.dumps(dc_rst, ensure_ascii=False, indent=4)}')
    return dc_rst

if __name__ == '__main__':
    async def main():
        from app.utils.password import get_authorization
        # class DataComprehensionParams(BaseModel):
        #     catalog_id: str
        #     dimension: str

        authorization = get_authorization("https://10.4.109.85", "liberly", "")

        # catalog_id='555633979462576600'  # 没有探查结果
        catalog_id = '555633151808956888'  # 有日期型和空间型探查结果
        # res = await get_data_comprehension(authorization, catalog_id, "复合表达")
        # res = await get_data_comprehension(authorization, catalog_id, "业务维度")
        # res = await get_data_comprehension(authorization, catalog_id, "服务范围")
        # res = await get_data_comprehension(authorization, catalog_id, "服务领域")
        # res = await get_data_comprehension(authorization, catalog_id, "正面支撑")
        # res = await get_data_comprehension(authorization, catalog_id, "负面支撑")
        # res = await get_data_comprehension(authorization, catalog_id, "保护控制")
        # res = await get_data_comprehension(authorization, catalog_id, "促进推动")
        res = await get_data_comprehension(authorization, catalog_id, TIME_RANGE)
        # res = await get_data_comprehension(authorization, catalog_id, TIME_FIELD)
        # res = await get_data_comprehension(authorization, catalog_id, SPACE_RANGE)
        # res = await get_data_comprehension(authorization, catalog_id, SPACE_FIELD)
        # print(json.dumps(res,ensure_ascii=False, indent=4))

        # appid = 'OIZ6_KHCKIk-ASpNLg5'
        # prompt_name='comprehension_template_yywd'
        # prompt, prompt_id = await ad.from_anydata(appid, prompt_name)
        # print(prompt)
        # print(prompt_id)

    asyncio.run(main())

    # input_string="555633980000037336|送达方式"
    # rst=extract_id_from_pipe_str(input_string)
    # print(rst)