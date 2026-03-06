"""
@File: on_clock_task.py
@Date:2024-08-08
@Author : Danny.gao
@Desc:
"""

import os
import time
import datetime
from config import settings

from app.cores.understand.commons import redis_processor, kafka_producer
from app.cores.understand.commons.task_params import Task_Info, Task_Status
from app.logs.logger import logger
from app.cores.understand.commons.get_params import af_params_connector


redis_hashtable_name = settings.TABLE_COMPLETION_REDIS_HASHTABLE_NAME
dtime_format = '%Y-%m-%d %H:%M:%S'


st_time = datetime.datetime.now()
last_clean_num = 1


def on_clock_task():
    # 获取参数
    params = af_params_connector()
    ex_time = params.task_ex_time

    # 凌晨进行清理操作
    now = datetime.datetime.now()
    # 和pod重启时间间隔
    delta_time = (now-st_time).total_seconds()

    if now.hour == 0 and now.minute < 60:
        logger.info('凌晨：')
        clean(now, ex_time)
        return True

    global last_clean_num
    devider = delta_time // ex_time
    if devider > last_clean_num + 1:
        logger.info(f'第 {last_clean_num} 次检查超时任务：')
        clean(now, ex_time)
        last_clean_num = devider


def clean(now, ex_time):
    logger.info(f'time={now}，清除补全任务启动、进行中......')

    # redis 的所有补全结果
    all_res = redis_processor._hgetall(hname=redis_hashtable_name)
    # 遍历
    for task_id, task_info in all_res.items():
        if isinstance(task_info, dict):
            if 'time' not in task_info:
                # 清除该任务，默认该任务出错
                redis_processor._hdel(hname=redis_hashtable_name, key=task_id)
                logger.info(f'清除补全任务：task_id={task_id}，没有time')
            else:
                try:
                    task_status = task_info.get('status', '')
                    task_reason = task_info.get('reason', '')
                    # kafka发送未成功或没有发送
                    if task_status == Task_Status.SUCCESS.value or task_status == Task_Status.PROCESSED.value:
                        task_info['status'] = Task_Status.SUCCESS.value
                        task_info['reason'] = Task_Info.FAIL_SEND_INFO.value
                        kafka_status = post_and_clean(task_info, task_id)
                        logger.info(f'清除补全任务：task_id={task_id}，task_reason={task_reason}, task_status={task_status}, kafka_status={kafka_status}')
                        continue
                    # 失败
                    if task_status == Task_Status.FAIL.value:
                        kafka_status = post_and_clean(task_info, task_id)
                        logger.info(f'清除补全任务：task_id={task_id}，task_reason={task_reason}, task_status={task_status}, kafka_status={kafka_status}')
                        continue
                    # 超时
                    st = datetime.datetime.strptime(task_info['time'], dtime_format)
                    delta = (now - st).total_seconds()
                    if delta > ex_time:
                        task_info['status'] = Task_Status.FAIL.value
                        task_info['reason'] = Task_Info.FAIL_EX_INFO.value
                        kafka_status = post_and_clean(task_info, task_id)
                        logger.info(
                            f'清除补全任务：task_id={task_id}，task_reason=超时, task_status={task_status}, kafka_status={kafka_status}')
                        continue
                except Exception as e:
                    task_info['status'] = Task_Status.FAIL.value
                    task_info['reason'] = Task_Info.FAIL_ERROR_INFO.value.format(e=f'{e}')
                    kafka_status = post_and_clean(task_info, task_id)
                    logger.info(f'清除补全任务：task_id={task_id}，task_reason=解析出错, kafka_status={kafka_status}')


def post_and_clean(task_info, task_id):
    if 'time' in task_info:
        task_info.pop('time')
    kafka_info = {'res': task_info}
    logger.info(f'kafka发送的消息：{kafka_info}')
    kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
    # 每隔10s重试
    for idx in range(5):
        if kafka_status:
            break
        time.sleep(10)
        kafka_status = kafka_producer.post(topic=settings.KAFKA_TOPIC, key=task_id, value=kafka_info)
    redis_processor._hdel(hname=redis_hashtable_name, key=task_id)
    return kafka_status


# 锁文件：用于补全任务的定时任务
LOCK_FILE = 'app/cores/understand/clock.lock'


def already_running():
    """
    检查锁文件，判断应用是否已在运行
    :return:
    """
    return os.path.isfile(LOCK_FILE) and os.getpid() != int(open(LOCK_FILE).read())


def create_lock():
    """
    创建锁文件
    :return:
    """
    with open(LOCK_FILE, 'w') as lock:
        lock.write(str(os.getpid()))


def delete_lock():
    """
    删除锁文件
    :return:
    """
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass

