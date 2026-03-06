"""
@File: model_check.py
@Date: 2024-12-20
@Author: Danny.gao
@Desc: 基于大模型生成任务
"""

import json
from typing import Any, List, Dict

from app.logs.logger import logger
from app.cores.recommend.common import ad_service, llm_func


class ModelGenerate(object):
    def __init__(self):
        self.appid = ''

    def rule_based(self):
        pass

    def ml_based(self):
        pass

    async def llm_based(
        self,
        datas: list[Any],
        appid: str,
        prompt_name: str,
        args: dict,
    ):
        # TODO：添加样例数据、

        # 提示词
        prompt, prompt_id = await ad_service.from_anydata(appid=appid, name=prompt_name)
        # logger.info(f'prompt_id={prompt_id}, prompt={prompt}')

        if not prompt:
            logger.info('读取 AD prompt 错误！')
            return [], ''
        generates = {}
        inputs = {
            'input_datas': json.dumps(datas, ensure_ascii=False)
        }
        inputs.update(args)
        results = await llm_func.exec_prompt_by_llm(inputs=inputs, appid=appid, prompt_id=prompt_id, max_tokens=4000)
        logger.info(f'大模型返回结果：{results}')
        if isinstance(results, str):
            results = results.strip('```').strip('json').strip()
            results = eval(results)
        if isinstance(results, list):
            # [
            #     {
            #         "id": "object-id-01"
            #         "generate": "^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
            #         "distinct": "true"
            #         "reason": "身份证是每个公民唯一、不变的身份代码，符合18位编码规则。"
            #     }
            # ]
            for res in results:
                logger.info(f'res={res}')
                if 'id' not in res or 'generate' not in res:
                    continue
                if 'distinct' not in res:
                    res['distinct'] = 'false'
                id_ = res['id']
                generates[id_] = res
        # logger.info(f'generates={generates}')
        return generates

    async def run(
        self,
        params: dict,
        input_datas,
        api_flag: str = None
    ):
        generate_res, msg = {}, ''

        """ 解析数据 """
        with_rule = params.get('generate', {}).get('rule', {}).get('with_execute', False)
        with_ml = params.get('generate', {}).get('ml', {}).get('with_execute', False)
        with_llm = params.get('generate', {}).get('llm', {}).get('with_execute', False)
        if not with_llm and not with_ml and not with_rule:
            with_rule = True

        """ 大模型 """
        if with_llm:
            # 大模型参数
            if api_flag == 'explore_rule':
                from app.cores.recommend.prompts.generate_field_subject import role_skills, role_tasks, examples
                llm_args = {
                    'role_skills': role_skills,
                    'role_tasks': role_tasks,
                    'examples': examples
                }
            else:
                llm_args = {}

            try:
                prompt_name = params.get('check', {}).get('llm', {}).get('prompt_name', None)
                prompt_name = prompt_name if prompt_name else 'recommend_generate'

                generate_res = await self.llm_based(datas=input_datas, appid=self.appid, prompt_name=prompt_name, args=llm_args)

            except Exception as e:
                msg = f'\n生成模块：大模型执行错误, \n{e}'
                logger.error(msg)

        """ TODO: 规则 """
        

        """ TODO: 机器学习 """
        
        
        logger.info(f'生成模块输出: generate_res={generate_res}')
        return msg, generate_res


