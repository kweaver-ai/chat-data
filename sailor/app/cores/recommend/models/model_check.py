"""
@File: model_check.py
@Date: 2024-12-20
@Author: Danny.gao
@Desc: 基于规则、大模型进行一致性校验
"""

from typing import Any
import json

from app.cores.recommend.utils import build_similarity_matrix,\
    aggregate_docs, calculate_consistency_rate
from app.logs.logger import logger
from app.cores.recommend.common import ad_service, llm_func


class ModelCheck(object):
    def __init__(self, params: dict = None):
        self.appid = ''

    def parser_inputs(self, input_datas, search_results):
        ids = []
        new_search_datas = []
        datas = []
        search_results = [list(search.values()) for search in search_results]
        for inputs, search in zip(input_datas, search_results):
            # 输入数据
            if not isinstance(inputs, dict):
                try:
                    inputs = inputs.dict()
                    new_input = {}
                    for k, v in inputs.items():
                        if 'id' in k and k != 'id':
                            continue
                        new_input[k] = v
                except:
                    new_input = inputs
            else:
                new_input = inputs
            ids.append(new_input.get('id', ''))
            # 搜索结果
            new_search = []
            for item in search:
                info = {}
                score = item.get('_score', 0.0)
                if score > 0.0:
                    info['score'] = score

                source = item.get('_source', {})
                for k, v in source.items():
                    if 'id' in k and k != 'id':
                        continue
                    info[k] = v
                if info:
                    new_search.append(info)

            new_search_datas.append(new_search)
            datas.append(new_input)
        # 映射
        info_map = {idx: data for idx, data in zip(ids, datas)}
        return ids, new_search_datas, datas, info_map

    def split_user_data(self, rule_groups, datas, prompt: str, max_seq: int):
        splits = []
        # 数据
        dico = {data['id']: data for data in datas if 'id' in data}
        groups = []
        for group_ in rule_groups:
            group = []
            for item in group_:
                for _ in item.get('group', []):
                    if 'id' in _:
                        id_ = _['id']
                        group.append(id_)
            groups.append(group)
        # 记录拼接prompt的长度
        n_prompt = len(prompt)
        # 根据相似度分组的结果
        g_1 = []
        for group in groups:
            n = len(group)
            if n < 0:
                continue
            if n == 1:
                id_ = group[0]
                if id_ in dico:
                    g_1.append(dico[id_])
                continue
            split = []
            for id_ in group:
                if id_ in dico:
                    data = dico[id_]
                    split.append(data)
            splits.append(split)
        return splits

    def rule_based(self, ids, search_datas):
        # 相似性矩阵：行归一化、对角线得分设置为0.01
        similarity_matrix = build_similarity_matrix(ids_x=ids, ids_y=ids,
                                                    search_datas=search_datas, diagonal=True, normalize=True)
        # 分组，同时按照一定的规则聚合、切割
        clusters = aggregate_docs(ids=ids, similarity_matrix=similarity_matrix, threshold=1.0 / similarity_matrix.shape[-1])
        
        return clusters

    def ml_based(self):
        pass

    async def llm_based(
        self,
        rule_groups,
        info_map,
        datas: list[Any],
        appid: str,
        prompt_name: str,
        llm_max_output_len: int
    ):
        # 提示词
        prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=prompt_name)
        # logger.info(f'prompt_id={prompt_id}, prompt={prompt}')
        if not prompt:
            logger.info('读取 AD prompt 错误！')
            return [], 0.0
        splits = self.split_user_data(rule_groups=rule_groups, datas=datas, prompt=prompt, max_seq=llm_max_output_len)
        llm_results = []
        for split in splits:
            inputs = {
                'input_datas': json.dumps(split, ensure_ascii=False)
            }
            results = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=llm_max_output_len)
            logger.info(f'大模型返回结果：{results}')
            if isinstance(results, str):
                results = results.strip('```').strip('json').strip()
                results = json.loads(results)
                if isinstance(results, list):
                    llm_results.extend(results)
        visited_ids, clusters, reasons = [], [], ''
        for res in llm_results:
            # {
            #     "group_ids": [
            #         "ab3887d6-43fa-4b69-81f7-c991a23f816b",
            #         "3652ab5d-ea3d-43c3-9380-b16b678b14b2"
            #     ],
            #     "reason": "这两项的名称都是“身份证”，都泛指公民的身份证明，因此具有相同的业务含义。"
            # }
            group_ids = res.get('group_ids', [])
            visited_ids.extend(group_ids)
            clusters.append([id_ for id_ in group_ids if id_ in info_map])
            reason = res.get('reason', '')
            reasons += f'\n{reason}'
        for id_ in info_map:
            if id_ not in visited_ids:
                clusters.append([id_])
        
        return clusters

    async def run(
        self,
        params: dict,
        input_datas: list,
        search_results: list[dict],
        group_names: list[str] = None,
        distinct: bool = False,
        i_type: str = "check_code"
    ):
        groups, rate, msg, reason, t_count, in_count = [], 0.0, '', '', 0, 0

        """ 解析数据 """
        ids, new_search_datas, new_datas, info_map = self.parser_inputs(input_datas=input_datas, search_results=search_results)
        # with_rule = params.get('filter', {}).get('rule', {}).get('with_execute', False)
        # with_ml = params.get('filter', {}).get('ml', {}).get('with_execute', False)
        with_llm = params.get('filter', {}).get('llm', {}).get('with_execute', False)

        clusters = []
        """ 规则 """
        try:
            clusters = self.rule_based(ids=ids, search_datas=new_search_datas)
        except Exception as e:
            logger.error(f'一致性校验模块：规则执行错误:\n{e}')
            msg = f'\n一致性校验模块：规则执行错误:\n{e}'
        """ 大模型 """
        if with_llm:
            try:
                prompt_name = params.get('check', {}).get('llm', {}).get('prompt_name', None)
                prompt_name = prompt_name if prompt_name else 'recommend_check'
                llm_max_output_len = params.get('rec_llm_output_len', 8000)
                clusters_ = await self.llm_based(rule_groups=groups,
                                                            info_map=info_map, datas=new_datas, appid=self.appid,
                                                            prompt_name=prompt_name,
                                                            llm_max_output_len=llm_max_output_len)
                clusters = clusters_
            except Exception as e:
                e = '请检查大模型名称、提示词名称是否配置正确。'
                msg = f'\n一致性校验模块：大模型执行错误，\n{e}'
                logger.error(msg)

        """ TODO：机器学习 """
        # if len(final_results) < len(datas):
        #     final_results = [{'check_reason': '', 'check_data': item} for item in search_results]

        """ 分组统计 """
        # 同一组cluster内的字段按照相同标准standard_id/standard_domain_id分成子组，然后选择子组元素最多的当作正确的标准id，其他子组的所有元素都是不一致的数据，然后计算不一致率
        groups, rate, t_count, in_count = calculate_consistency_rate(clusters=clusters, 
                                                                     basic_info_dict=info_map, 
                                                                     group_names=group_names,
                                                                     distinct=distinct,
                                                                     i_type=i_type)


        logger.info(f'一致性校验模块：rate={rate}, \ngroups={groups}, \nreason={reason}')
        return msg, groups, rate, reason, t_count, in_count

