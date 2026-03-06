"""
@File: model_filter.py
@Date: 2025-01-09
@Author: Danny.gao
@Desc: 筛选任务，从搜索结果中筛选中真正相关的项
"""

import json
from typing import Any

from app.logs.logger import logger
from app.cores.recommend.common import ad_service, llm_func


class ModelFilter(object):
    def __init__(self):
        self.appid = ''

    def split_user_data(self, datas, prompt: str, max_seq: int):
        splits = []
        # 记录拼接prompt的长度
        n_prompt = len(prompt)
        split = []
        for data in datas:
            split.append(data)
            if n_prompt + len(str(split)) >= max_seq:
                splits.append(split)
                split = []
        return splits

    def rule_based(
            self
    ) -> list[tuple[Any, str | list[str], Any, str | list[str]]]:
        pass

    def ml_based(
            self
    ) -> list[tuple[Any, str | list[str], Any, str | list[str]]]:
        pass
    async def llm_based(
            self,
            datas: list[Any],
            appid: str,
            prompt_id: str,
            llm_max_output_len: int
    ) -> tuple[bool, Any]:
        # 提示词
        # prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=prompt_name)
        # logger.info(f'prompt_id={prompt_id}, prompt={prompt}')
        # if not prompt:
        #     logger.info('读取 AD prompt 错误！')
        #     return False, []
        all_results = []
        inputs = {
            'input_datas': json.dumps(datas, ensure_ascii=False)
        }
        results = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id,
                                                    max_tokens=llm_max_output_len)
        logger.info(f'大模型返回结果：{results}')
        return True, results

    async def run(
        self,
        input_datas: list[Any],
        search_results: list[dict],
        params: dict
        # prompt_name: str = None,    # 如果with_llm，那么prompt_name必须存在
    ):
        final_results, msg = [], ''
        # step1：解析数据
        search_results = [list(search.values()) for search in search_results]
        datas, search_datas = [], {}
        for inputs, search in zip(input_datas, search_results):
            new_search = []
            for item in search:
                info = {}
                # {"id": "id-09", "name": "建立时间", "description": "", "score": 0.90}
                if 'id' not in item:
                    continue
                id_ = item['id']
                score = item.get('_score', 0.0)
                if score > 0.0:
                    info['score'] = '{:.2f}'.format(score)

                source = item.get('_source', {})
                for k, v in source.items():
                    if 'id' in k and k != 'id':
                        continue
                    info[k] = v

                if info:
                    new_search.append(info)
                    search_datas[id_] = info
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
            item = {
                'user_data': f'{new_input}',
                'search_data': f'{new_search}'
            }
            datas.append(item)

        # step2：解析参数
        # with_rule = config.filter.rule.with_execute
        # with_ml = config.filter.rule.with_execute
        with_llm = params.get('filter', {}).get('llm', {}).get('with_execute', False)

        # step5大模型结果
        try:
            if with_llm:
                llm_results = {}
                prompt_name =  params.get('filter', {}).get('llm', {}).get('prompt_name', None)
                prompt_name = prompt_name if prompt_name else 'recommend_filter'
                prompt, prompt_id = await ad_service.from_anydata(appid=self.appid, name=prompt_name)
                llm_max_output_len = params.get('rec_llm_output_len', 8000)

                splits = self.split_user_data(datas=datas, prompt=prompt, max_seq=llm_max_output_len)
                for split in splits:
                    flag, llm_result = await self.llm_based(datas=split, appid=self.appid, prompt_id=prompt_id,
                                                             llm_max_output_len=llm_max_output_len)
                    if isinstance(llm_result, str):
                        llm_result = llm_result.strip('```').strip('json').strip()
                        llm_result = json.loads(llm_result)
                    if isinstance(llm_result, list) and len(llm_result) == len(split):
                        for res in llm_result:
                            # {
                            #     "id": "object-id-01",
                            #     "match_ids": ["id-02", "id-01"],
                            #     "reason": "1. 这两项的名称都是“姓名”，且描述相符或相近；同时，它们的匹配分数较高，表明它们与输入参数中的“姓名”有较高的相似度。\n 2. “名称”、“公司名”虽然与“姓名”在语义上相近，但“名称”可能指的是更广泛的概念，“公司名”特指公司的名称。由于指定了“人的姓氏和名字”，因此这些项未被推荐"
                            # },
                            if 'id' not in res:
                                continue
                            id_ = res['id']
                            new_list = []
                            match_ids = res.get('match_ids', [])
                            if match_ids:
                                for v_id in match_ids:
                                    if v_id in search_datas:
                                        new_list.append(search_datas[v_id])
                            new_item = {
                                'filter_reason': res.get('reason', ''),
                                'filter_data': new_list
                            }
                            llm_results[id_] = new_item
                    else:
                        logger.info(f'过滤模块：大模型没有返回有效、准确的列表信息:\n{llm_results}')
                for data in datas:
                    item = {
                        'user_data': f'{data.get("new_input", {})}',
                        'search_data': f'{data.get("new_search", {})}'
                    }
                    id_ = item.get('user_data', {}).get('id', '')
                    if not id_:
                        continue
                    res = llm_results.get(id_, [])
                    final_results.append(res)
        except Exception as e:
            logger.error(f'过滤模块：大模型执行错误:\n{e}')
            msg = f'\n过滤模块：大模型执行错误:\n{e}'
        if len(final_results) < len(datas):
            final_results = [{'filter_reason': '', 'filter_data': item} for item in search_results]
        logger.info(f'过滤结果：{final_results}')
        return msg, final_results


