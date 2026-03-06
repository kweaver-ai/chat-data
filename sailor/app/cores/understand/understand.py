# -*- coding: utf-8 -*-

"""
@Time ：2024/1/15 17:30
@Auth ：Danny.gao
@File ：understand_demo.py
@Desc ：
@Motto：ABC(Always Be Coding)
"""

import datetime
import time
import json
import asyncio
import collections
import json
import uuid

from config import settings
from app.logs.logger import logger
from app.cores.understand.commons import ad_service, llm_func, redis_processor, kafka_producer
from app.cores.understand.commons import get_one_sample
from app.cores.understand.commons.task_params import Task_Status, Task_Info
from app.cores.understand.commons.get_params import af_params_connector
from app.cores.prompt.understand import TABLE_UNDERSTAND_PROMPT, TABLE_UNDERSTAND_ONLY_FOR_TABLE_PROMPT

redis_hashtable_name = settings.TABLE_COMPLETION_REDIS_HASHTABLE_NAME
dtime_format = '%Y-%m-%d %H:%M:%S'


# 保存redis消息
def save_redis(task_info, task_id=None, status=None, request_type=None, reason=None, result=None, time=None):
    if not task_info:
        # 初始化
        task_info = {
            'task_id': task_id,
            'status': status,
            'request_type': request_type,
            'reason': reason,
            'result': result,
            'time': time
        }
    else:
        if status:
            task_info['status'] = status
        if reason:
            task_info['reason'] = reason
        if result:
            task_info['result'] = result

    redis_processor._hmset(hname=redis_hashtable_name, datas={task_id: task_info})
    logger.info(f'task_id={task_id} 补全任务 {status} {reason} ！！')
    return task_info


# kafka发送消息
def post_kafka(task_info, task_id, error=None):
    kafka_info = task_info.copy()

    if error:
        error = f'{error}'
        kafka_info['status'] = Task_Status.FAIL.value
        kafka_info['reason'] = Task_Info.FAIL_ERROR_INFO.value.format(e=error)
        if 'time' in kafka_info:
            kafka_info.pop('time')
        kafka_info = {'res': kafka_info}
        logger.info(f'kafka发送的消息：{kafka_info}')
        kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
        # 每隔10s重试
        for idx in range(5):
            if kafka_status:
                break
            time.sleep(10)
            kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
        if kafka_status:
            redis_processor._hdel(hname=redis_hashtable_name, key=task_id)
        else:
            save_redis(task_info, task_id=task_id, status=Task_Status.FAIL.value, reason=Task_Info.FAIL_ERROR_INFO.value.format(e=error))
    else:
        kafka_info['status'] = Task_Status.SUCCESS.value
        kafka_info['reason'] = Task_Info.SUCCESS_INFO.value
        if 'time' in kafka_info:
            kafka_info.pop('time')
        kafka_info = {'res': kafka_info}
        logger.info(f'kafka发送的消息：{kafka_info}')
        kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
        # 每隔10s重试
        for idx in range(5):
            if kafka_status:
                break
            time.sleep(10)
            kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
        if kafka_status:
            redis_processor._hdel(hname=redis_hashtable_name, key=task_id)
        else:
            save_redis(task_info, task_id=task_id, status=Task_Status.SUCCESS.value, reason=Task_Info.FAIL_SEND_INFO.value)


# 封装completion结果
async def completion(tb_id: str, gen_field_ids: list, completion_info_list: list, field_map_dico: dict) -> dict:
    # 合并所有的字段信息
    assistant_name, assistant_desc = '', ''
    f_dico = {}
    for info in completion_info_list:
        # 表信息
        t_info = info.get('table', {})
        assistant_name = assistant_name if assistant_name else t_info.get('name_cn', '')
        assistant_desc = assistant_desc if assistant_desc else t_info.get('desc', '')
        # 字段信息
        f_info = info.get('columns', [])
        for f in f_info:
            new_id = f.get('id', '')
            f_dico[new_id] = f

    new_cols = []
    for new_id in gen_field_ids:
        f_id = field_map_dico.get(new_id, '')
        if not f_id:
            continue
        info = f_dico.get(new_id, {})
        item = {
            'id': f_id,
            'assistant_name_en': info.get('name_en', ''),
            'assistant_name_cn': info.get('name_cn', ''),
            'assistant_desc': info.get('desc', '')
        }
        new_cols.append(item)

    if gen_field_ids:
        result = {
            'id': tb_id,
            'assistant_name': assistant_name,
            'assistant_desc': assistant_desc,
            'columns': new_cols
        }
    else:
        result = {
            'id': tb_id,
            'assistant_name': assistant_name,
            'assistant_desc': assistant_desc
        }
    return result


# 将原始数据切分成功多次请求数据：
async def split_user_data(query, prompt: str, max_seq: int, only_for_table: bool = False) -> tuple:
    def init(n_splits):
        n_splits += 1
        user_data = {
            'technical_name': query.get('technical_name', '')[:100],
            'business_name': query.get('business_name', '')[:100],
            'desc': query.get('desc', '')[:200],
            'subject': query.get('subject', '')[:100],
            'database': query.get('database', '')[:100]
        }
        fields, field_ids, demo_data = [], [], []
        return n_splits, user_data, fields, field_ids, demo_data

    splits = []

    # 记录拼接prompt的长度
    n_prompt = len(prompt)

    # 所有字段信息
    all_fields = query.get('columns', [])
    gen_field_ids = query.get('gen_field_ids', [])
    all_field_ids = []
    field_map_dico, new_id = {}, 1

    field_dico = collections.OrderedDict()
    for field in all_fields:
        f_id = field.get('id', '')
        # 要生成描述的字段id
        if isinstance(gen_field_ids, list):
            if f_id in gen_field_ids:
                all_field_ids.append(str(new_id))
        # 字段名映射字典
        field_map_dico[str(new_id)] = f_id
        # 更新字段id
        field['id'] = str(new_id)
        field_dico[str(new_id)] = field

        new_id += 1

    # 需要生成信息的字段id列表
    if only_for_table or not isinstance(gen_field_ids, list):
        all_field_ids = []
    else:
        all_field_ids = all_field_ids if all_field_ids else list(field_dico.keys())

    # 一条示例数据
    all_demo_data = query.get('demo_data', {})

    # 切分成多条数据
    # prior for fields that need completion
    n_splits, user_data, fields, field_ids, demo_data = init(n_splits=-1)
    # 这里的f_id其实是映射new_id
    for new_id in all_field_ids:
        field = field_dico.get(new_id, {})
        if field:
            fields.append(field)
            field_ids.append(new_id)
            demo_data.append(all_demo_data.get(new_id, ''))
            n1, n2, n3, n4 = len(str(user_data)), len(str(fields)), len(str(field_ids)), len(str(demo_data))
            if n_prompt + n1 + n2 + n3 + n4 > max_seq:
                user_data['columns'] = fields
                user_data['demo_data'] = demo_data
                item = {
                    'user_data': f'{user_data}',
                    'field_ids': f'{field_ids}'
                }
                splits.append(item)
                n_splits, user_data, fields, field_ids, demo_data = init(n_splits=n_splits)

    # 所有应该生成的数据都已经处理完毕，如果没有清空，说明长度不大于4000，也就是可以再添加额外的数据
    if field_ids or not splits:
        for new_id, field in field_dico.items():
            if new_id not in field_ids:
                fields.append(field)
                demo_data.append(all_demo_data.get(new_id, ''))
                n1, n2, n3, n4 = len(str(user_data)), len(str(fields)), len(str(field_ids)), len(str(demo_data))
                if n_prompt + n1 + n2 + n3 + n4 > max_seq:
                    user_data['columns'] = fields
                    user_data['demo_data'] = demo_data
                    item = {
                        'user_data': f'{user_data}',
                        'field_ids': f'{field_ids}'
                    }
                    splits.append(item)
                    n_splits, user_data, fields, field_ids, demo_data = init(n_splits=n_splits)
                    break
    # 或者，所有字段都加上之后，还是不超过4000
    # 或者，如果splits为空：也就是没有字段信息，那么就添加表信息
    if field_ids or not splits:
        user_data['columns'] = fields
        user_data['demo_data'] = demo_data
        item = {
            'user_data': f'{user_data}',
            'field_ids': f'{field_ids}'
        }
        splits.append(item)

    return field_map_dico, all_field_ids, splits


async def table_completion_task(task_info, query, appid, af_auth, only_for_table=False):
    task_id = task_info.get('task_id', '')
    logger.info(f'正在执行补全任务： task_id = {task_id} ....')
    # 补全任务的参数
    params = af_params_connector()
    llm_input_len = params.llm_input_len
    llm_output_len = params.llm_out_len

    # prompt
    prompt_name = 'table_understand_only_for_table' if only_for_table else 'table_understand'
    prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=prompt_name)
    logger.info(f'prompt_id={prompt_id}, prompt={prompt}')
    if not prompt:
        logger.info('读取 AD prompt 错误！')
        post_kafka(task_info, task_id, error='读取 AD prompt 错误！')
        return False
    else:
        try:
            # 获取样例数据
            sample = await get_one_sample(query.technical_name, query.view_source_catalog_name, af_auth)
            logger.info(f'{task_id} 的样例数据：{sample}')
        except Exception as e:
            logger.info(f'{task_id} 获取样例数据失败：{e}')
        try:
            # 根据大模型上下文长度限制，切分成多次请求（上下文长度<10000，回复长度限制设为了4000，因此这里设置4000）
            m_field_map_dico, m_field_ids, m_inputs = \
                await split_user_data(query=query.dict(), prompt=prompt, max_seq=llm_input_len, only_for_table=only_for_table)

            # 单线程异步执行
            tasks = [llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=llm_output_len) for inputs in m_inputs]
            infos = await asyncio.gather(*tasks)
            # infos = []
            # for inputs in m_inputs:
            #     info = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=llm_output_len)
            #     logger.info(f'model res -- 1: {info}')
            #     infos.append(info)

            # 收集所有的生成结果，进行后处理
            completion_infos = []
            for info in infos:
                if str(info).startswith('报错'):
                    # 大模型报错
                    post_kafka(task_info, task_id, error=f'执行 AD LLM 补全报错！{info}')
                    return False
                try:
                    # 结果后处理
                    info = info.replace('```json', '').replace('```', '').strip().replace('\'', '"')
                    splits = info.split('{', 1)
                    info = '{' + splits[1] if len(splits) > 1 else info
                    logger.info(f'model res: {info}')
                    info = info.encode("utf-8").decode('utf-8')
                    logger.info(f'model res 转码: {info.encode("utf-8").decode()}')
                    if not isinstance(info, dict):
                        info = json.loads(info)
                except:
                    info = {'table': {}, 'columns': []}
                completion_infos.append(info)

            # 封装结果
            result = await completion(tb_id=query.id,
                                      gen_field_ids=m_field_ids,
                                      completion_info_list=completion_infos,
                                      field_map_dico=m_field_map_dico)
            # 存到redis
            task_info = save_redis(task_info,
                                   task_id=task_id,
                                   status=Task_Status.PROCESSED.value,
                                   reason=Task_Info.PROCESSED_INFO.value,
                                   result=result)

            # kafka发送消息
            post_kafka(task_info, task_id)
            return True
        except Exception as e:
            logger.info(f'补全任务报错：{e}')
            post_kafka(task_info, task_id, error=e)
            return False

async def table_completion_task_v2(task_info, query, user_id, af_auth, only_for_table=False):
    task_id = task_info.get('task_id', '')
    logger.info(f'正在执行补全任务： task_id = {task_id} ....')
    # 补全任务的参数
    params = af_params_connector()
    llm_input_len = params.llm_input_len
    llm_output_len = params.llm_out_len

    # prompt
    prompt_name = 'table_understand_only_for_table' if only_for_table else 'table_understand'
    # prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=
    if prompt_name == "table_understand_only_for_table":
        prompt = TABLE_UNDERSTAND_ONLY_FOR_TABLE_PROMPT
    else:
        prompt= TABLE_UNDERSTAND_PROMPT
    logger.info(f'prompt={prompt}')
    if not prompt:
        logger.info('读取 AD prompt 错误！')
        post_kafka(task_info, task_id, error='读取 AD prompt 错误！')
        return False
    else:
        try:
            # 获取样例数据
            sample = await get_one_sample(query.technical_name, query.view_source_catalog_name, af_auth)
            logger.info(f'{task_id} 的样例数据：{sample}')
        except Exception as e:
            logger.info(f'{task_id} 获取样例数据失败：{e}')
        try:
            # 根据大模型上下文长度限制，切分成多次请求（上下文长度<10000，回复长度限制设为了4000，因此这里设置4000）
            m_field_map_dico, m_field_ids, m_inputs = \
                await split_user_data(query=query.dict(), prompt=prompt, max_seq=llm_input_len, only_for_table=only_for_table)

            # 单线程异步执行
            tasks = [llm_func.exec_prompt_by_llm_dip(inputs=inputs, prompt=prompt, user_id=user_id, max_tokens=llm_output_len) for inputs in m_inputs]
            infos = await asyncio.gather(*tasks)
            # infos = []
            # for inputs in m_inputs:
            #     info = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=llm_output_len)
            #     logger.info(f'model res -- 1: {info}')
            #     infos.append(info)

            # 收集所有的生成结果，进行后处理
            completion_infos = []
            for info in infos:
                if str(info).startswith('报错'):
                    # 大模型报错
                    post_kafka(task_info, task_id, error=f'执行 AD LLM 补全报错！{info}')
                    return False
                try:
                    # 结果后处理
                    info = info.replace('```json', '').replace('```', '').strip().replace('\'', '"')
                    splits = info.split('{', 1)
                    info = '{' + splits[1] if len(splits) > 1 else info
                    logger.info(f'model res: {info}')
                    info = info.encode("utf-8").decode('utf-8')
                    logger.info(f'model res 转码: {info.encode("utf-8").decode()}')
                    if not isinstance(info, dict):
                        info = json.loads(info)
                except:
                    info = {'table': {}, 'columns': []}
                completion_infos.append(info)

            # 封装结果
            result = await completion(tb_id=query.id,
                                      gen_field_ids=m_field_ids,
                                      completion_info_list=completion_infos,
                                      field_map_dico=m_field_map_dico)
            # 存到redis
            task_info = save_redis(task_info,
                                   task_id=task_id,
                                   status=Task_Status.PROCESSED.value,
                                   reason=Task_Info.PROCESSED_INFO.value,
                                   result=result)

            # kafka发送消息
            post_kafka(task_info, task_id)
            return True
        except Exception as e:
            logger.info(f'补全任务报错：{e}')
            post_kafka(task_info, task_id, error=e)
            return False


async def tableCompletion(background_tasks, query, user_id, af_auth, only_for_table=False):
    logger.info('逻辑视图业务含义自动填充......')
    logger.info(f'INPUT: query={query}, user_id={user_id}')

    task_id = f'{uuid.uuid4()}'
    # 存到redis
    task_info = save_redis(task_info=None,
                           task_id=task_id,
                           status=Task_Status.INIT.value,
                           request_type=query.request_type,
                           reason=Task_Info.INIT_INFO.value,
                           result={},
                           time=datetime.datetime.now().strftime(dtime_format))

    # 后台运行补全任务
    background_tasks.add_task(table_completion_task_v2, task_info, query, user_id, af_auth, only_for_table)

    # 存到redis
    save_redis(task_info, task_id=task_id, status=Task_Status.PROCESSING.value, reason=Task_Info.PROCESSING_INFO.value)

    logger.info(f'OUTPUT_01: task_id={task_id} 补全任务')
    return {'task_id': task_id}


async def tableCompletion_by_task_id(task_id):
    logger.info('根据task_id获取视图结果......')
    logger.info(f'INPUT: task_id={task_id}')

    # 从redis读取数据
    res = redis_processor._hmget(hname=redis_hashtable_name, keys=[task_id])
    result = res.get(task_id, {})
    if not result:
        result = {
            'task_id': task_id,
            'status': Task_Status.FAIL.value,
            'request_type': None,
            'reason': Task_Info.FAIL_EX_INFO.value,
            'result': {}
        }
        logger.info(f'task_id={task_id} 补全任务 {Task_Status.FAIL} {Task_Info.FAIL_EX_INFO} ！！')

    logger.info(f'OUTPUT_03: result={result} 补全任务')
    return result


if __name__ == '__main__':
    import asyncio

    # data = {
    #     "query": {
    #         "id": "Table-ID-01",
    #         "technical_name": "T_ActiceCodeApplyImplement",
    #         "business_name": "",
    #         "desc": "",
    #         "database": "",
    #         "subject_id": "",
    #         "columns": [
    #             {"id": "Field-Id-01", "technical_name": "id", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-02", "technical_name": "activeCodeApplyId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-03", "technical_name": "modId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-04", "technical_name": "configDeviceId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-05", "technical_name": "sn", "business_name": "id", "data_type": "varchar", "comment": ""},
    #             {"id": "Field-Id-06", "technical_name": "rowId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-07", "technical_name": "registrationCodeId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-08", "technical_name": "equipmentCode", "business_name": "id", "data_type": "varchar", "comment": ""},
    #             {"id": "Field-Id-01", "technical_name": "id", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-02", "technical_name": "activeCodeApplyId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-03", "technical_name": "modId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-04", "technical_name": "configDeviceId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-05", "technical_name": "sn", "business_name": "id", "data_type": "varchar", "comment": ""},
    #             {"id": "Field-Id-06", "technical_name": "rowId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-07", "technical_name": "registrationCodeId", "business_name": "id", "data_type": "int", "comment": ""},
    #             {"id": "Field-Id-08", "technical_name": "equipmentCode", "business_name": "id", "data_type": "varchar", "comment": ""}
    #         ],
    #         "demo_data": {},
    #         "gen_field_ids": ["Field-Id-06", "Field-Id-07", "Field-Id-02"]
    #     },
    #     "appid": "NrjzS5Q0gNkQuZEzLFc"
    # }
    # prompt, prompt_id = asyncio.run(ad_service.from_anydata(appid='NrjzS5Q0gNkQuZEzLFc', name='table_understand'))
    # print(len(prompt))
    # field_ids, splits = asyncio.run(split_user_data(query=data['query'], prompt=prompt, max_seq=1900))
    # for _ in splits:
    #     for k, v in _.items():
    #         print(k, v)

    st = datetime.datetime.now().strftime(dtime_format)
    print(st)
    time.sleep(2)
    now = datetime.datetime.now()
    st = datetime.datetime.strptime(st, dtime_format)
    delta = (now-st).total_seconds()
    print(delta)
    if now.hour == 0 and now.minute == 0 and now.second == 0:
        print("当前时间是凌晨0点")
    else:
        print("当前时间不是凌晨0点")
