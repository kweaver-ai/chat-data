# -*- coding: utf-8 -*-
# @Time : 2023/12/19 14:22
# @Author : Jack.li
# @Email : jack.li@aishu.cn
# @File : logger.py
# @Project : copilot
import logging

# 1、创建一个logger
logger = logging.getLogger('logs/sailor-agent')
logger.setLevel(logging.DEBUG)

# 2、创建一个handler，用于写入日志文件
fh = logging.FileHandler('logs/sailor-agent.log')
fh.setLevel(logging.DEBUG)

# 再创建一个handler，用于输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 3、定义handler的输出格式（formatter）
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 4、给handler添加formatter
fh.setFormatter(formatter)
ch.setFormatter(formatter)


# 5、给logger添加handler
logger.addHandler(fh)
logger.addHandler(ch)
