"""
@File: post_kafka.py
@Date:2024-08-06
@Author : Danny.gao
@Desc:
"""

import json
from kafka import KafkaProducer
from kafka.errors import kafka_errors

from config import settings
from app.logs.logger import logger


class Kafka_Producer(object):
    def __init__(self):
        # kafka连接信息
        self.host = settings.KAFKA_HOST
        self.port = settings.KAFKA_PORT
        self.sasl_mechanism = settings.KAFKA_MECHANISM
        self.security_protocol = settings.KAFKA_SECURITY_PROTOCOL
        self.sasl_plain_username = settings.KAFKA_USERNAME
        self.sasl_plain_password = settings.KAFKA_PASSWORD
        self.partition = settings.KAFKA_PARTITION
        self.ex_time = settings.KAFKA_EX_TIME

        # self.host = '10.4.109.234'
        # self.port = '31000'
        # self.sasl_mechanism = 'PLAIN'
        # self.security_protocol = 'SASL_PLAINTEXT'
        # self.sasl_plain_username = 'kafka-exporter'
        # self.sasl_plain_password = ''
        # self.partition = settings.KAFKA_PARTITION
        # self.ex_time = settings.KAFKA_EX_TIME

        # 启动时，尝试连接kafka
        try:
            self.producer = self.connect()
            logger.info('Kafka连接成功！！')
        except Exception as e:
            self.producer = None
            logger.info(f'Kafka连接失败！！{e}')

    def connect(self):
        producer = KafkaProducer(
            sasl_mechanism=self.sasl_mechanism,
            security_protocol=self.security_protocol,
            sasl_plain_username=self.sasl_plain_username,
            sasl_plain_password=self.sasl_plain_password,
            bootstrap_servers=[f'{self.host}:{self.port}'],
            key_serializer=lambda k: json.dumps(k, ensure_ascii=False).encode(),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode())
        return producer

    def check_and_try_reconnect(self):
        if self.producer:
            return True
        logger.info(f'Kafka连接失败！！重新连接中......')
        idx = 1
        while idx < 3:
            try:
                self.producer = self.connect()
                return True
            except Exception as e:
                logger.info(f'第{idx-1}次重试Kafka连接失败！！{e}')
            idx += 1
        return False

    def post(self, topic: str, key: str, value: dict) -> bool:
        if self.check_and_try_reconnect():
            try:
                future = self.producer.send(
                    topic=topic,
                    key=key,
                    value=value,
                    partition=self.partition)
                future.get(timeout=self.ex_time)
                return True
            except kafka_errors:
                logger.info(f'Kafka发送消息失败！！{kafka_errors}')
                return False
        logger.info('Kafka连接失败！！')
        return False