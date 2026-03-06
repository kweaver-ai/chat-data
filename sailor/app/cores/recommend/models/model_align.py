"""
@File: model_align.py
@Date: 2024-12-20
@Author: Danny.gao
@Desc: 对齐任务，即两个集合的 n:n 匹配
"""

import numpy as np
from typing import Any, List, Dict
import json

from app.cores.recommend.utils import build_similarity_matrix, hungarian_match
from app.logs.logger import logger
from app.cores.recommend.common import ad_service, llm_func


class ModelAlign(object):
    def __init__(self):
        self.appid = ''

    def parser_inputs(self, input_datas, align_datas, search_results):
        ids_x, ids_y = [], []
        new_search_datas = []
        datas = []
        info_map, intersect_ids_map = {}, {}
        # 匹配的两个集合中id列表
        search_results = [list(search.values()) for search in search_results]
        indx = -1
        for inputs, aligns in zip(input_datas, align_datas):
            # 匹配的数据
            ids_y_ = {_['id']: _ for _ in aligns if 'id' in _}
            info_map.update(ids_y_)
            ids_y.extend(list(ids_y_.keys()))
            # 输入数据、搜索结果数据
            for data in inputs:
                indx += 1
                # 输入数据
                if not isinstance(data, dict):
                    try:
                        data = data.dict()
                    except:
                        continue
                else:
                    pass
                new_input = {}
                for k, v in data.items():
                    if 'id' in k and k != 'id':
                        continue
                    new_input[k] = v
                if 'id' not in new_input:
                    continue
                id_ = new_input['id']
                ids_x.append(id_)
                info_map[id_] = new_input
                intersect_ids_map[id_] = list(ids_y_.keys())
                
                # 搜索结果
                search = search_results[indx] if len(search_results) > indx else []
                new_search = []
                for item in search:
                    info = {}
                    score = item.get('_score', 0.0)
                    if score > 0.0:
                        info['score'] = score

                    source = item.get('_source', {})
                    id_ = source.get('id', '')
                    if id_ not in ids_y_:
                        continue
                    for k, v in source.items():
                        if 'id' in k and k != 'id':
                            continue
                        info[k] = v
                    if info:
                        new_search.append(info)

                new_search_datas.append(new_search)
            datas.append(
                {
                    'datas': inputs,
                    'align_datas': aligns
                }
            )
        # ids_x：不能做set，因为其顺序需要和搜索结果保持一致
        ids_y = list(set(ids_y))
        # 矩阵x的id列表、矩阵y的id列表，搜索结果、输入给大模型的数据、id与基本信息的映射、ids_x关联的ids_y的id列表（用来验证，对齐的id一定要有一致性）
        return ids_x, ids_y, new_search_datas, datas, info_map, intersect_ids_map
    
    def rule_based(
            self
    ) -> list[tuple[Any, str | list[str], Any, str | list[str]]]:
        pass

    def ml_based(
            self,
            algo: str = 'hungarian',
            ids_x: list[str] = None, ids_y: list[str] = None,
            search_datas: list = None,
            intersect_ids_map: dict = None
    ) -> list[Any] | list[dict[str, str | list[str]]]:
        # 参数校验
        if not ids_x or not ids_y or not search_datas:
            return []

        # step1: 相似性矩阵：行归一化、对角线得分设置为0.01
        similarity_matrix = build_similarity_matrix(ids_x=ids_x, ids_y=ids_y,
                                                    search_datas=search_datas, diagonal=True, normalize=True,
                                                    intersect_ids_map=intersect_ids_map)

        # step2：默认匈牙利算法找到最大权重路径
        # TODO: 添加其他对齐算法
        if not algo or algo == 'hungarian':
            matches = hungarian_match(similarity_matrix=similarity_matrix)
        else:
            matches = []

        # 构建映射列表
        mappings = [{'source': ids_x[index_x], 'target': ids_y[index_y]} for index_x, index_y in matches]

        return mappings

    async def llm_based(
        self,
        datas: list[Any],
        appid: str,
        prompt_name: str
    ):
        # 提示词
        prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=prompt_name)
        # logger.info(f'prompt_id={prompt_id}, prompt={prompt}')
        if not prompt:
            logger.info('读取 AD prompt 错误！')
            return [], ''
        mappings, reasons = [], ''
        for data in datas:
            inputs = {
                'input_datas': json.dumps([data], ensure_ascii=False)
            }
            results = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=4000)
            # logger.info(f'大模型返回结果：{results}')
            if isinstance(results, str):
                results = results.strip('```').strip('json').strip()
                results = json.loads(results)
            # logger.info(f'llm_res1={results}')
            if isinstance(results, list):
                for res in results:
                    # logger.info(f'llm_res2: {res}')
                    # {
                    #     "mappings": [
                    #         {"source": "object-id-01", "target": "align-id-02"},
                    #         {"source": "object-id-02", "target": "align-id-01"}
                    #     ],
                    #     "reason": "身份证具有相同的含义，都表示个体身份唯一标识；根据上下文背景信息，姓名也都是个体称呼，因此进行匹配。"
                    # }
                    mappings.extend(res.get('mappings', []))
                    reason = res.get('reason', '')
                    reasons += f'\n{reason}'
            # logger.info(f'llm_res3={mappings}')
            reasons += '\n\n'
        reasons = reasons.strip()
        return mappings, reasons

    def double_check(self, mappings, info_map, intersect_ids_map):
        # logger.info(f'mappings3: {mappings}')
        # logger.info(f'info_map = {info_map}')
        align_res = {}
        vistied = []
        for item in mappings:
            # logger.info(item)
            # {"source": "object-id-01", "target": "align-id-02"}
            idx = item['source']
            idy = item['target']
            if idx not in info_map or idy not in info_map or idx not in intersect_ids_map:
                continue
            # 校验：idx、idy是否匹配
            ids_y = intersect_ids_map[idx]
            if idy not in ids_y:
                continue
            # 校验：一致性，不同的ids_x没有匹配到重复的ids_y
            if idy in vistied:
                continue
            # 封装
            # logger.info(f'{idx}, {idy}')
            infox = info_map[idx]
            infoy = info_map[idy]
            if not infox or not infoy:
                continue
            align_res[idx] = {'source': infox, 'target': infoy}
            # logger.info('*'*100)
            # logger.info(infox)
            # logger.info(infoy)
            vistied.append(idy)
        return align_res

    async def run(
        self,
        params: dict,
        input_datas: list,
        align_datas: list,
        search_results: list[dict]
    ):
        mappings, msg, reasons = [], '', ''

        """ 解析数据 """
        ids_x, ids_y, new_search_datas, new_datas, info_map, intersect_ids_map = self.parser_inputs(input_datas=input_datas, align_datas=align_datas,
                                                                                                    search_results=search_results)
        with_rule = params.get('align', {}).get('rule', {}).get('with_execute', False)
        with_ml = params.get('align', {}).get('ml', {}).get('with_execute', False)
        with_llm = params.get('align', {}).get('llm', {}).get('with_execute', False)
        if not with_llm and not with_ml and not with_rule:
            with_rule = True

        """ 大模型 """
        if with_llm:
            try:
                prompt_name = params.get('check', {}).get('llm', {}).get('prompt_name', None)
                prompt_name = prompt_name if prompt_name else 'recommend_align'

                mappings, reasons = await self.llm_based(datas=new_datas, appid=self.appid, prompt_name=prompt_name)

            except Exception as e:
                msg = f'\n对齐（匹配）模块：大模型执行错误, \n{e}'
                logger.error(msg)

        """ TODO：规则 """
        

        """ 机器学习 """
        # logger.info(f'mappings1: {mappings}')
        if with_ml or not mappings:
            try:
                mappings = self.ml_based(ids_x=ids_x, ids_y=ids_y, search_datas=new_search_datas, intersect_ids_map=intersect_ids_map)
            except Exception as e:
                msg = f'\n对齐（匹配）模块：机器学习方法执行错误, \n{e}'
                logger.error(msg)

        """ 封装结果: 包括校验 """
        # logger.info(f'mappings2: {mappings}')
        align_res = self.double_check(mappings, info_map, intersect_ids_map)
        
        logger.info(f'对齐（匹配）模块输出: align_res={align_res}, \nreason={reasons}')
        return msg, align_res, reasons

