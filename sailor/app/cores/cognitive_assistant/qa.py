import json
import traceback

from fastapi import Request

from app.cores.cognitive_assistant.qa_base import QABase
from app.cores.cognitive_assistant.qa_func import qa_data_reorganize_to_json
from app.cores.cognitive_assistant.qa_model import CognitiveSearchResponseModel, QAParamsModelDIP
from app.cores.prompt.qa import NO_SOURCE, TIMEOUT_ERROR, NO_AUTH_WITH_RESOURCES
from app.cores.cognitive_search.search_config.get_params import SearchConfigs
from app.logs.logger import logger
from config import settings


class QA(QABase):

    def __init__(self):
        super(QA, self).__init__()

    async def forward(self, request, params: QAParamsModelDIP, search_configs: SearchConfigs , text=""):
        headers = {"Authorization": request.headers.get('Authorization')}
        assets: CognitiveSearchResponseModel
        try:
            assets, self.time_search = await self.cognitive_search(
                request=request,
                headers=headers,
                params=params,
                search_configs=search_configs
            )
            # assets.cites 就是 CognitiveSearch 实例的 self.save_cites，是以特殊的格式保持所有数据资源目录和接口服务，返回给前端
            self.save_cites = assets.cites
            # props是AF数据资产, props_cn是AF数据资产的中文名称
            # 如果认知搜索没有匹配到任何资源
            if all(not value for value in assets.props.values()):
                if params.resources:
                    data_map = {
                        "1": "data_catalog",
                        "2": "api",
                        "3": "data_view",
                        "4": "indicator",
                    }
                    logger.info(f"params.resources = {params.resources}")
                    tag = ""
                    cites = []
                    for i, msg in enumerate(params.resources):
                        tag += f"<i slice_idx=0>{i + 1}</i>"
                        cites.append(
                            {
                                "id": msg["id"],
                                "type": data_map[msg["type"]]
                            }
                        )
                    res = NO_AUTH_WITH_RESOURCES
                    res = res.replace("{resources}", tag)
                    return qa_data_reorganize_to_json(status="answer", cites=cites, detail=res).lstrip("data: ")
                else:
                    return qa_data_reorganize_to_json(status="answer", cites=[], detail=NO_SOURCE).lstrip("data: ")
            # 如果认知搜索匹配到资源
            else:
                # params.resources是指定资源问答中的指定资源
                logger.info(f'params.resources = {params.resources}')
                logger.info(f'search_configs.direct_qa = {search_configs.direct_qa}')
                # 指定资源问答
                if params.resources or search_configs.direct_qa == "true":
                    if assets.props.get("指标分析"):
                        logger.info("执行指标分析")
                        chunks = self.yield_search_response(params, assets)
                        async for chunk in chunks:
                            return json.loads(chunk[5:].strip())

                    # chunk = ""  # 为了保证每一次的回答都会有上一次的结果
                    # if assets.props.get("数据目录") or assets.props.get("逻辑视图"):
                    #     try:
                    #         chunks = self.yield_text2sql_response(headers, params, assets, af_editions, self.search_configs_dict)
                    #         async for chunk in chunks:
                    #             return chunk[5:].strip()
                    #     except Exception as e:
                    #         print("#" * 100 + "\n", e)
                    #         pass
                    # if assets.props.get("接口服务"):
                    #     try:
                    #         chunks = self.yield_service_response(headers, params, assets)
                    #         async for chunk in chunks:
                    #             continue
                    #         if self.timeout_flag:
                    #             return {"result": {"status": "answer",
                    #                                "res": {"cites": self.save_cites, "text": TIMEOUT_ERROR}}}
                    #         if self.yield_service:
                    #             return chunk[5:].strip()
                    #     except Exception as e:
                    #         print("#" * 100, e)
                    #         pass

                    chunks = self.yield_search_response(params, assets)
                    async for chunk in chunks:
                        return json.loads(chunk[5:].strip())
                else:
                    # 没有指定资源的找数问答
                    chunks = self.yield_search_response(params, assets)
                    # chunks 只有一个chunk，chunk 形如 f'data: {json.dumps(text, ensure_ascii=False)}\n'
                    # i=1
                    async for chunk in chunks:
                        # logger.info(f'chunk({i})...')
                        logger.info(f'chunk = \n{chunk}')
                        # i+=1
                        return json.loads(chunk[5:].strip())

            await self.logger_time()
        except Exception as e:
            logger.error(f'{"#" * 100}, {e}')

    async def stream(self, request: Request, params: QAParamsModelDIP,search_configs: SearchConfigs ):
        """流式返回"""
        headers = {"Authorization": request.headers.get('Authorization')}

        try:
            yield qa_data_reorganize_to_json("search")
            assets, self.time_search = await self.cognitive_search(
                request=request,
                headers=headers,
                params=params,
                search_configs=search_configs
            )

            self.save_cites = assets.cites
            if all(not value for value in assets.props.values()):
                if params.resources:
                    data_map = {
                        "1": "data_catalog",
                        "2": "api",
                        "3": "data_view",
                        "4": "indicator",
                    }
                    logger.info(f"params.resources = {params.resources}")
                    tag = ""
                    cites = []
                    for i, msg in enumerate(params.resources):
                        tag += f"<i slice_idx=0>{i + 1}</i>"
                        cites.append(
                            {
                                "id": msg["id"],
                                "type": data_map[msg["type"]]
                            }
                        )
                    res = NO_AUTH_WITH_RESOURCES
                    res = res.replace("{resources}", tag)
                    yield qa_data_reorganize_to_json(status="answer", cites=cites, detail=res)
                else:
                    yield qa_data_reorganize_to_json(status="answer", cites=[], detail=NO_SOURCE)
            else:
                yield qa_data_reorganize_to_json(status="answer", cites=assets.cites)

                if params.resources or search_configs.direct_qa == "true":
                    chunk = ""  # 为了保证每一次的回答都会有上一次的结果
                    strategy_tag = [1, 1, 1]
                    if assets.props.get("指标分析"):
                        logger.info("执行指标分析")
                        strategy_tag = [0, 1, 0]

                    # if assets.props.get("数据目录") or assets.props.get("逻辑视图"):
                    #     if strategy_tag[0]:
                    #         logger.info("执行text2sql")
                    #         try:
                    #             chunks = self.yield_text2sql_response(
                    #                 headers,
                    #                 params,
                    #                 assets,
                    #                 af_editions,
                    #                 config
                    #             )
                    #             async for chunk in chunks:
                    #                 yield chunk
                    #             strategy_tag = [0, 0, 0]
                    #         except Exception as e:
                    #             tb_str = traceback.format_exc()
                    #             print('==============================', tb_str)
                    #             strategy_tag = [1, 1, 1]
                    #             print("#" * 100, e)
                    #
                    # if assets.props.get("接口服务") and strategy_tag[2]:
                    #     try:
                    #         chunks = self.yield_service_response(headers, params, assets)
                    #         async for chunk in chunks:
                    #             yield chunk
                    #         if self.yield_service:
                    #             strategy_tag[1] = 0
                    #     except Exception as e:
                    #         tb_str = traceback.format_exc()
                    #         print('==============================', tb_str)
                    #         strategy_tag[1] = 1
                    #         print("#" * 100, e)
                    #
                    # if self.plus_flag:
                    #     chunks = self.yield_big_response(assets, chunk)
                    #     async for chunk in chunks:
                    #         yield chunk

                    if strategy_tag[1]:
                        chunks = self.yield_search_response(params, assets)
                        async for chunk in chunks:
                            yield chunk

                    chunks = self.get_timeout_res(chunk)  # 在最后一个阶段把调用超市的语言返回
                    async for chunk in chunks:
                        yield chunk
                else:
                    # 没有指定资源的找数问答
                    chunks = self.yield_search_response(params, assets)
                    async for chunk in chunks:
                        yield chunk

            await self.logger_time()
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.info(f'==============================, {tb_str}')
            logger.info(f'{"#" * 100}, {e}')
            yield qa_data_reorganize_to_json(status="answer", cites=[], detail=NO_SOURCE)
        finally:
            yield qa_data_reorganize_to_json(status="ending")
