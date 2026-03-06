"""
@File: redis_processor.py
@Date:2024-08-06
@Author : Danny.gao
@Desc:
"""

import json
import redis
from redis.sentinel import Sentinel

from config import settings
from app.logs.logger import logger
from app.cores.understand.commons.task_params import EnumEncoder


class Redis_Processor(object):
    def __init__(self):
        # Redis连接信息
        self.redis_cluster_mode = settings.REDIS_CONNECT_TYPE
        self.db = settings.REDIS_DB

        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.password = settings.REDIS_PASSWORD

        self.sentinel_host = settings.REDIS_SENTINEL_HOST
        self.sentinel_port = settings.REDIS_SENTINEL_PORT
        self.sentinel_user_name = settings.REDIS_SENTINEL_USER_NAME
        self.sentinel_password = settings.REDIS_SENTINEL_PASSWORD
        self.master_name = settings.REDIS_MASTER_NAME

        # # Redis连接信息
        # self.redis_cluster_mode = 'master-slave'
        # # self.redis_cluster_mode = 'sentinel'
        # self.db = '4'
        #
        # self.host = '10.4.110.50'
        # self.port = '6379'
        # self.password = ''
        #
        # self.sentinel_host = 'proton-redis-proton-redis-sentinel.resource'
        # self.sentinel_port = '26379'
        # self.sentinel_user_name = 'root'
        # self.sentinel_password = ''
        # self.master_name = 'mymaster'

        # # 数据元补全的hashtable名称
        # self.table_completion_hashtable = settings.TABLE_COMPLETION_REDIS_HASHTABLE_NAME

        # 启动时，尝试连接redis
        try:
            self.r = self.connect()
            logger.info('Redis连接成功！！')
        except Exception as e:
            self.r = None
            logger.info(f'Redis连接失败！！{e}')

    def connect(self):
        if self.redis_cluster_mode == 'master-slave':
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
            )
            client = redis.StrictRedis(connection_pool=pool)
            return client
        if self.redis_cluster_mode == 'sentinel':
            sentinel = Sentinel(
                [(self.sentinel_host, self.sentinel_port)],
                password=self.sentinel_password,
                sentinel_kwargs={
                    'password': self.sentinel_password,
                    'username': self.sentinel_user_name
                }
            )

            client = sentinel.master_for(
                self.master_name,
                password=self.sentinel_password,
                username=self.sentinel_user_name,
                db=self.db
            )
            return client

    def check_and_try_reconnect(self):
        if self.r:
            return True
        logger.info(f'Redis连接失败！！重新连接中......')
        idx = 1
        while idx < 3:
            try:
                self.r = self.connect()
                return True
            except Exception as e:
                logger.info(f'第{idx-1}次重试Redis连接失败！！{e}')
            idx += 1
        return False

    def _hmset(self, hname: str, datas: dict[str, dict]) -> bool:
        if self.check_and_try_reconnect():
            try:
                all_data = {k: json.dumps(v, cls=EnumEncoder, ensure_ascii=False) for k, v in datas.items()}
                self.r.hmset(name=hname, mapping=all_data)
                return True
            except Exception as e:
                logger.info(f'Redis hmset error: {e}')
        logger.info('Redis连接失败！！')
        return False

    def _hmget(self, hname: str, keys: list[str]) -> dict[str, dict]:
        final_res = {}
        if self.check_and_try_reconnect():
            results = self.r.hmget(name=hname, keys=keys)
            try:
                for res in results:
                    res = res.decode('utf-8')
                    res = json.loads(res)
                    task_id = res.get('task_id', '')
                    if task_id:
                        final_res[task_id] = res
            except Exception as e:
                logger.info(f'Redis hmget error: {e}')
                pass
        else:
            logger.info('Redis连接失败！！')
        return final_res

    def _hgetall(self, hname: str) -> dict[str, dict]:
        final_res = {}
        if self.check_and_try_reconnect():
            results = self.r.hgetall(name=hname)
            try:
                for k, v in results.items():
                    final_res[k.decode()] = json.loads(v)
            except Exception as e:
                logger.info(f'Redis hgetall error: {e}')
        else:
            logger.info('Redis连接失败！！')
        return final_res

    def _hdel(self, hname: str, key: str) -> bool:
        if self.check_and_try_reconnect():
            try:
                self.r.hdel(hname, key)
                return True
            except Exception as e:
                logger.info(f'Redis hdel error: {e}')
        logger.info('Redis连接失败！！')
        return False


if __name__ == '__main__':
    redis_processer = Redis_Processor()

    # res = redis_processer._hmget(hname='af_sailor_table_completion', keys=['21bb297a-e582-4205-af5a-1d1294f3a271'])
    # print('res: ', res)

    # res = redis_processer._hgetall(hname='af_sailor_table_completion')
    # for k, v in res.items():
    #     redis_processer._hdel(hname='af_sailor_table_completion', key=k)

    redis_processer.r.hdel('af_sailor_table_completion', '8e352797-d59a-4f')