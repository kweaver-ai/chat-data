# """
# @File: get_ad_builder.py
# @Date:2024-03-12
# @Author : Danny.gao
# @Desc:
# """
#
# import json
# # from anydata import Builder
# # from anydata.base import ConnectionData
# # from anydata.services.engine import CogEngine
# # from anydata.sdk_error import SDKError, BuilderError, CogEngineError
#
# from config import settings
# from app.logs.logger import logger
# from app.utils.exception import SDKRequestException
#
# ad_version = settings.AD_VERSION
#
# async def ad_builder_connector(appid, graph_id):
#     try:
#         builder_engine = Builder.from_conn_data(
#             addr=settings.AD_GATEWAY_URL,
#             acc_key=appid
#         )
#         builder_engine.version = ad_version
#         builder_engine._gen_api_url()
#         space_name = await builder_engine.get_kg_dbname_by_id(str(graph_id))
#         return str(space_name)
#     except (SDKError, BuilderError) as e:
#         logger.info(f'AF-AD-SDK 错误: {e.url} {e.reason}')
#         # return SDKRequestException(status=e.status, reason=f'{e.url} {e.reason}')
#     except:
#         logger.info(f'AF-AD-SDK 错误: Internal Server Error')
#
#     return False
#
#
# async def ad_opensearch_connector(appid, params):
#     try:
#         connData = ConnectionData(
#             addr=settings.AD_GATEWAY_URL,
#             access_key=appid
#         )
#         engine = CogEngine(conn=connData)
#         res = engine.opensearch_custom_search(
#             params=params
#         )
#
#         return res
#     except (SDKError, BuilderError, CogEngineError) as e:
#         logger.info(f'AF-AD-SDK 错误: {e.url} {e.reason}')
#     except:
#         logger.info(f'AF-AD-SDK 错误: Internal Server Error')
#
# if __name__ == '__main__':
#     pass
