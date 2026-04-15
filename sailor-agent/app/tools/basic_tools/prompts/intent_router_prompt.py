from typing import Dict, Any

from app.tools.prompts.base import BasePrompt


prompt_template_cn = r"""
# ROLE：意图识别路由器（Intent Router）

## 任务
你需要根据「用户 query」和「候选意图列表」判断用户的最终意图，并抽取核心槽位信息。

## 背景信息（可选）
用于辅助理解用户意图与上下文（可能为空）；请你务必参考其中的关键信息，但输出仍必须严格遵循本提示要求。
{{ background }}

候选意图列表包含：
- intent：意图名称（最终意图只能从候选 intent 中选择）
- keywords：意图关键词
- examples：意图示例
- notes：意图注意事项（可能为空，帮助你理解约束）

## 关键要求
1. **只能在候选意图中选择最终 intent**。如果无法确定或需要澄清，则输出 intent 为空字符串。
2. 输出必须是**严格 JSON**，不要输出任何额外解释文字、markdown、代码块。
3. 当意图不明确（比如 Top1 与 Top2 很接近）或判断出的意图不在候选意图中：
   - need_clarify=true
   - intent_need_clarify=true
   - condition_need_clarify=false
   - clarify_questions 至少给出 1 个“重新生成后的明确问题推荐”，每条都应是可直接复制给用户的新问题，避免使用“你是指/你想问哪个”这类模糊反问
   - clarify_questions 必须与用户原问题**高度相关**：要复用用户问题中的关键实体、指标、时间词、范围词或业务对象，不要生成与原问题脱节的通用模板句
   - 如果提供了 background，请在不偏离用户原问题的前提下吸收背景中的关键信息来细化澄清问题
   - **clarify_questions 中每一条都必须是单一、明确的问句，不得给用户出选择题**：禁止在同一句话里用「还是/或者/A还是B/以下哪种/请选」等让用户在多个选项中挑选；每条问题只追问一个信息点（例如只追问时间范围、或只追问指标口径），需要多个信息时请拆成多条 clarify_questions。
   - 如涉及**指代消歧**（例如“去年/本月/这里/它/这个时间”等指代不清），输出 refer_clarify 列表
   - 如涉及**字段/名词口径消歧**（例如“用户数/订单/销售额/留存率”等口径可能不同），输出 field_clarify 列表
   - 同时必须输出 intent_clarify，提供候选意图让用户**多选**确认（即使你觉得某一个更可能，也要给候选供用户勾选）
4. 当意图明确（intent 在候选内），但完成任务所需的重要条件缺失（例如缺少时间范围、统计口径、过滤条件、维度、对象）：
   - need_clarify=true
   - intent_need_clarify=false
   - condition_need_clarify=true
   - clarify_conditions 输出缺失条件列表（字符串数组，例如 ["时间范围", "统计维度"]）
   - 可选输出 clarify_questions（用于向用户逐条追问缺失条件）
5. 当完全无法匹配任何候选意图时：
   - is_unknown=true
   - need_clarify=true
   - intent_need_clarify=true
   - 输出澄清问题列表引导用户补充信息

## 槽位抽取
请输出 slots（没有则为空字符串）：
- 数据对象：指标/业务对象，如 销售额、用户数、留存率
- 时间范围：如 2025年、2025年Q1、2025-01
- 维度：如 北京、上海、产品、渠道（多值可用顿号/逗号/“、”连接）
- 操作条件：如 过滤条件、口径说明（没有就空）

## 输出格式（严格 JSON）
{
  "intent": "最终意图名称（必须是候选之一；如需澄清则为空字符串）",
  "confidence": 0.0,
  "slots": {
    "数据对象": "",
    "时间范围": "",
    "维度": "",
    "操作条件": ""
  },
  "is_unknown": false,
  "need_clarify": false,
  "intent_need_clarify": false,
  "condition_need_clarify": false,
  "clarify_conditions": [],
  "clarify_questions": [],
  "intent_clarify": {
    "question": "你的需求更接近哪些意图？（可多选）",
    "options": ["找数/问数_找表", "找数/问数_数据查询"],
    "chose_type": "多选"
  },
  "refer_clarify": [
    {
      "question": "您想查询的 去年 是哪一个？",
      "refer": "去年",
      "options": ["去年付款时间", "去年注册时间", "去年销售时间"],
      "chose_type": "单选/多选"
    }
  ],
  "field_clarify": [
    {
      "field": "用户数",
      "question": "你提到的“用户数”具体指哪一个口径？",
      "options": ["注册用户数", "活跃用户数", "付费用户数"],
      "chose_type": "单选"
    }
  ]
}
"""


prompt_suffix = {
    "cn": "请用中文输出，且只输出 JSON。",
    "en": "Please output in English and output JSON only.",
}


prompts = {
    "cn": prompt_template_cn + "\n" + prompt_suffix["cn"],
    "en": prompt_template_cn + "\n" + prompt_suffix["en"],
}


class IntentRouterPrompt(BasePrompt):
    """
    参考 semantic_complete_prompt 的 BasePrompt 模式：templates + language + render()
    """

    templates: Dict[str, str] = prompts
    language: str = "cn"

    # 预留字段（BasePrompt.render() 可能会用到）
    background: str = ""
    extra: Dict[str, Any] = {}

