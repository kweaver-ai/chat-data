# # -*- coding: utf-8 -*-
# # @Time : 2023/12/20 16:40
# # @Author : Jack.li
# # @Email : jack.li@xxx.cn
# # @File : agent.py.py
# # @Project : copilot
#
# from anydata import OpenSearch
# from app.logs.logger import logger
# from config import settings
#
# logger.info('AD Opensearch 对象初始化开始......')
# opensearch_engine = OpenSearch(
#     ips=[settings.AF_OPENSEARCH_HOST],
#     ports=[int(settings.AF_OPENSEARCH_PORT)],
#     user=settings.AF_OPENSEARCH_USER,
#     password=settings.AF_OPENSEARCH_PASS
# )
# logger.info('AD Opensearch 对象初始化完成功！！！')