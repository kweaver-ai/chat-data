"""
Intent Router Tool

需求：
- 可配置多意图列表（意图名称、keywords、examples）
- 输出意图候选与最终意图（含置信度、slots）
- 意图模糊时返回澄清反问问题
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Type
import numpy as np
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import SystemMessage

from app.tools.base import (
    LLMTool,
    construct_final_answer,
    async_construct_final_answer,
)
from app.utils.llm import CustomChatOpenAI
from config import get_settings
from app.logs.logger import logger
from app.tools.base import api_tool_decorator
from app.tools.basic_tools.prompts.intent_router_prompt import IntentRouterPrompt
from app.service.adp_service import ADPService


DEFAULT_INTENTS: Dict[str, Dict[str, Any]] = {
    "找数/问数_找表": {
        "description": "定位满足查询需求的数据表/字段/部门信息，不直接返回最终数据结果。",
        "keywords": ["找表", "数据表", "表名", "数据表格", "字段", "部门"],
        "examples": ["帮我找2025年销售数据表", "用户留存率的表叫什么", "包含姓名字段的表有几张", "根据相关职责查询部门", "主责部门查询",
                     "应该由什么部门负责财务"],
        "route": ["找表"],
        "notes": "找表不需要条件澄清"
    },
    "找数/问数_数据查询": {
        "description": "用户目标是直接获取数据结果，通常会提出“查什么数据、在什么条件下查、时间范围/维度/过滤口径”等查询诉求。该意图关注的是返回具体数值、明细或统计结果，而不是仅定位库表。",
        "keywords": ["查询", "查一下", "是多少", "数据值", "筛选", "过滤", "排除", "大于","小于","等于", "请问"],
        "examples": ["查询2025年Q1销售额", "筛选出客单价大于1000的订单", "查找包含企业注册资本金信息的数据表，并查询注册资本金数值排名前10%的企业名称",
                     "找表，再查表", "基于某个库表，获取信息"],
        "route": ["先找表，然后数据查询", "基于某个表，进行提问"],
        "notes": "数据查询的流程中包含了找表，如果问句中包含了找表，但是最后还是查表，那么意图就是查表。"
    },
    "数据分析_趋势": {
        "description": "分析指标随时间变化的趋势、走势和变化规律。",
        "keywords": ["趋势", "变化", "走势", "月度变化"],
        "examples": ["分析近6个月的用户增长趋势", "销售额的月度变化趋势是什么"],
        "route": ["先找表，然后进行数据查询，最后进行趋势分析"],
        "notes": ""
    },
    "数据分析_对比": {
        "description": "比较不同对象在同一指标上的差异（如地区、时间、渠道）。",
        "keywords": ["对比", "比较", "和...比", "差异"],
        "examples": ["对比北京和上海的转化率", "2024和2025年的复购率对比"],
        "route": ["先找表，然后进行数据查询，最后进行对比分析"],
        "notes": ""
    },
    "数据分析_归因": {
        "description": "解释结果变化原因，识别关键驱动因素或异常来源。",
        "keywords": ["原因", "归因", "为什么", "分析...原因"],
        "examples": ["分析销售额下降的原因", "为什么Q2的用户留存率降"],
        "route": ["先找表，然后进行数据查询，最后进行归因分析"],
        "notes": ""
    },
    "数据分析_预测": {
        "description": "基于历史数据对未来趋势或结果进行预测与预估。",
        "keywords": ["预测", "预估", "预计", "推算"],
        "examples": ["筛选出客单价大于1000的订单", "排除2024年的数据"],
        "route": ["先找表，然后进行数据查询，最后进行预测分析"],
        "notes": ""
    },
    "数据解读_核心结论": {
        "description": "对数据结果进行解读，提炼核心结论、亮点与业务洞察。",
        "keywords": ["解读", "结论", "总结", "亮点"],
        "examples": ["解读一下这份用户行为数据的核心结论", "总结下Q2的运营数据亮点"],
        "route": ["先找表，然后进行数据查询，最后进行总结、解读"],
        "notes": ""
    },
    "报告编写": {
        "description": "生成结构化报告内容（如分析报告初稿、周报、专题报告）。",
        "keywords": ["报告", "初稿", "生成报告"],
        "examples": ["生成分析报告初稿", "写一份用户增长数据的周报"],
        "route": ["先找表，然后进行数据查询，最后进行报告编写"],
        "notes": "除非问题中非常明确要写报告，不然不要选择报告编写"
    }
}


def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)


class IntentRouterArgs(BaseModel):
    """意图路由工具入参"""

    query: str = Field(..., description="用户输入的原始问题/需求")

    background: str = Field(
        default="",
        description="用于大模型意图识别的背景信息/参考上下文（可选）。当需要调用大模型澄清或做最终判别时会传入提示词。",
    )

    intents: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: DEFAULT_INTENTS,
        description=(
            "意图配置，形如：{intent_name: {description: '...', keywords: [...], examples: [...], notes: ...}}。"
            "keywords/examples 为字符串列表，notes 支持字符串或字符串列表。"
        ),
    )

    top_k: int = Field(default=3, ge=1, le=10, description="返回候选意图数量")

    min_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="低于该置信度判定为模糊，需要澄清",
    )

    min_margin: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Top1-Top2 置信度差值低于该阈值判定为模糊，需要澄清",
    )

    report_intents: bool = Field(
        default=True,
        description="是否在日志中输出意图配置报告（意图名称/关键词/示例/注意事项）",
    )

    enable_field_clarify: bool = Field(
        default=False,
        description="是否启用字段消歧（识别 query 中可能歧义的名词并返回候选含义）。",
    )


_SETTINGS = get_settings()
SQL_RISK_KEYWORDS = ("delete", "update", "insert", "alter", "drop")


class IntentRouterTool(LLMTool):
    """
    意图路由工具（规则打分版）

    输出结构示例（与需求保持一致，**不返回 module_result**，仅日志记录）：
    {
      "intent": "...",
      "confidence": 0.98,
      "slots": {...},
      "is_unknown": false,
      "need_clarify": false,
      "clarify_questions": []
    }
    """

    name: str = "intent_router"
    token: str = ""
    description: str = (
        "意图路由工具：根据可配置的多意图列表（名称/关键词/示例）对用户输入进行意图识别。"
        "当意图模糊时输出澄清反问问题。"
    )
    background: str = ""
    kn_id: str = ""
    adp_service: Any = None
    args_schema: Type[BaseModel] = IntentRouterArgs

    @classmethod
    def _contains_sql_risk_tokens(cls, query: str) -> bool:
        """轻量规则：识别用户问题中是否出现 SQL 高危操作关键词。"""
        q = (query or "").strip().lower()
        if not q:
            return False
        has_sql_ctx = any(token in q for token in ("sql", "数据库", "表", "语句"))
        has_risk_kw = any(re.search(rf"\b{re.escape(kw)}\b", q) for kw in SQL_RISK_KEYWORDS)
        # 既兼容明确 SQL 场景，也兼容直接输入 SQL 语句（例如 "delete from ..."）
        return bool(has_risk_kw and (has_sql_ctx or re.search(r"\b(from|table|where|set|into)\b", q)))

    async def _llm_sql_risk_review(self, query: str) -> Dict[str, Any]:
        """
        使用大模型对疑似 SQL 高危请求做二次判定，避免误伤。
        返回: {"blocked": bool, "reason": str}
        """
        if not getattr(self, "llm", None):
            return {"blocked": True, "reason": "命中 SQL 高危操作关键词，且未配置 LLM，按安全策略拦截。"}

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "你是 SQL 安全审查助手。"
                        "请判断用户输入是否在请求执行或生成具有数据破坏风险的 SQL 操作。"
                        "高危操作包括：DELETE、UPDATE、INSERT、ALTER、DROP。"
                        "仅输出 JSON：{\"blocked\": true/false, \"reason\": \"...\"}。不要输出其他文本。"
                    )
                ),
                HumanMessagePromptTemplate.from_template("用户输入：{query}"),
            ]
        )
        messages = prompt.format_messages(query=(query or "").strip())
        resp = await self.llm.ainvoke(messages)
        content = getattr(resp, "content", "") or ""
        text = content.strip()
        if not text.startswith("{"):
            l = text.find("{")
            r = text.rfind("}")
            if l != -1 and r != -1 and r > l:
                text = text[l : r + 1]
        try:
            parsed = json.loads(text)
            blocked = bool(parsed.get("blocked", False))
            reason = str(parsed.get("reason", "") or "").strip() or "SQL 风险审查结果"
            return {"blocked": blocked, "reason": reason}
        except Exception:
            # 解析失败时采取保守策略
            return {"blocked": True, "reason": "SQL 风险审查解析失败，按安全策略拦截。"}

    def _build_sql_risk_block_result(self, query: str, reason: str) -> Dict[str, Any]:
        safe_question = "请改为只读查询需求（例如 SELECT），并明确查询目标与过滤条件。"
        summary_text = (
            f"用户问题：{(query or '').strip()}\n"
            "安全审查：检测到疑似 SQL 高危操作请求，已拦截处理。\n"
            f"原因：{reason}"
        )
        return {
            "intent": "",
            "confidence": 1.0,
            "slots": self._extract_slots(query),
            "is_unknown": False,
            "need_clarify": True,
            "intent_need_clarify": True,
            "condition_need_clarify": False,
            "clarify_conditions": [],
            "clarify_questions": [safe_question],
            "refer_clarify": [],
            "field_clarify": [],
            "noun_phrases": [],
            "summary_text": summary_text,
            "security_review": {
                "blocked": True,
                "review_type": "sql_risk",
                "reason": reason,
                "risk_keywords": list(SQL_RISK_KEYWORDS),
            },
        }

    @staticmethod
    def _build_summary_text(
        query: str,
        intent: str,
        confidence: float,
        slots: Dict[str, str],
        is_unknown: bool,
        need_clarify: bool,
        clarify_questions: List[str],
        intent_need_clarify: bool = False,
        condition_need_clarify: bool = False,
    ) -> str:
        """构造面向用户/调用方的中文总结文本。"""
        q = (query or "").strip()
        parts: List[str] = []

        if q:
            parts.append(f"用户问题：{q}")

        if need_clarify:
            if intent_need_clarify and condition_need_clarify:
                parts.append("意图识别：意图与关键条件均需进一步澄清。")
            elif intent_need_clarify:
                if is_unknown:
                    parts.append("意图识别：暂无法确定（未知/不匹配），需要进一步澄清。")
                else:
                    parts.append("意图识别：存在歧义，需要进一步澄清。")
            elif condition_need_clarify:
                parts.append("意图识别：意图已明确，但关键条件缺失，需要补充条件。")
            else:
                parts.append("意图识别：需要进一步澄清。")
        else:
            parts.append(f"意图识别：{intent or '—'}（置信度 {confidence:.4f}）。")

        # 槽位摘要
        if isinstance(slots, dict):
            slot_pairs = []
            for k in ["数据对象", "时间范围", "维度", "操作条件"]:
                v = (slots.get(k) or "").strip()
                if v:
                    slot_pairs.append(f"{k}={v}")
            if slot_pairs:
                parts.append("关键信息：" + "；".join(slot_pairs) + "。")

        if need_clarify and clarify_questions:
            # 仅取前2条，避免过长
            qs = [str(x).strip() for x in clarify_questions if str(x).strip()]
            if qs:
                parts.append("澄清问题：" + " / ".join(qs[:2]))

        return "\n".join(parts).strip()

    @staticmethod
    def _normalize_refer_clarify(raw: Any) -> List[Dict[str, Any]]:
        """规范化 refer_clarify 输出结构。"""
        if not raw:
            return []
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "") or "").strip()
            refer = str(item.get("refer", "") or "").strip()
            chose_type = str(item.get("chose_type", "") or "").strip()
            options = item.get("options", [])
            if not isinstance(options, list):
                options = [options] if options else []
            options = [str(o).strip() for o in options if str(o).strip()]

            if not (question or refer or options):
                continue
            normalized.append(
                {
                    "question": question,
                    "refer": refer,
                    "options": options,
                    "chose_type": chose_type or "单选",
                }
            )
        return normalized

    @staticmethod
    def _normalize_field_clarify(raw: Any) -> List[Dict[str, Any]]:
        """规范化 field_clarify 输出结构。"""
        if not raw:
            return []
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field", "") or "").strip()
            question = str(item.get("question", "") or "").strip()
            chose_type = str(item.get("chose_type", "") or "").strip() or "单选"
            options = item.get("options", [])
            if not isinstance(options, list):
                options = [options] if options else []
            options = [str(o).strip() for o in options if str(o).strip()]
            if len(options) < 2:
                continue
            if not field:
                field = "待确认字段"
            if not question:
                question = f"你提到的“{field}”是指哪一个？"
            normalized.append(
                {
                    "field": field,
                    "question": question,
                    "options": options,
                    "chose_type": chose_type,
                }
            )
        return normalized

    @staticmethod
    def _normalize_nouns(raw: Any) -> List[str]:
        """规范化 LLM 名词抽取输出。"""
        if not raw:
            return []
        if isinstance(raw, dict):
            raw = raw.get("nouns", [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []

        out: List[str] = []
        seen = set()
        for item in raw:
            noun = str(item or "").strip()
            if not noun or noun in seen:
                continue
            seen.add(noun)
            out.append(noun)
        return out[:20]

    async def _llm_extract_nouns(self, query: str) -> List[str]:
        """
        使用 LLM 抽取用户问题中的名词（仅名词，不做解释）。
        返回去重后的名词列表。
        """
        if not getattr(self, "llm", None):
            return []
        q = (query or "").strip()
        if not q:
            return []

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "你是中文语义分析助手。"
                        "请从用户问题中抽取所有名词/名词短语（如实体、指标、对象、时间表达、地区等），"
                        "仅输出 JSON，格式为：{\"nouns\": [\"...\", \"...\"]}。"
                        "不要输出其他文本。"
                    )
                ),
                HumanMessagePromptTemplate.from_template("用户问题：{query}"),
            ]
        )
        messages = prompt.format_messages(query=q)
        resp = await self.llm.ainvoke(messages)
        content = getattr(resp, "content", "") or ""
        text = content.strip()
        if not text.startswith("{"):
            l = text.find("{")
            r = text.rfind("}")
            if l != -1 and r != -1 and r > l:
                text = text[l : r + 1]
        try:
            parsed = json.loads(text)
            return self._normalize_nouns(parsed)
        except Exception:
            # LLM 返回非 JSON 时，做最小兜底：按顿号/逗号分割
            rough = re.split(r"[，,、；;\n\t ]+", text)
            return self._normalize_nouns(rough)

    @staticmethod
    def _build_field_clarify(query: str) -> List[Dict[str, Any]]:
        """
        规则版字段消歧：识别 query 中可能存在歧义的名词，并给出候选含义。
        """
        q = (query or "").strip()
        if not q:
            return []

        # 可按业务逐步扩展词典
        ambiguity_map: Dict[str, List[str]] = {
            "用户数": ["注册用户数", "活跃用户数", "付费用户数", "下单用户数"],
            "用户": ["注册用户", "活跃用户", "新用户", "存量用户"],
            "销售额": ["含税销售额", "不含税销售额", "支付销售额", "下单销售额"],
            "收入": ["营业收入", "确认收入", "回款收入"],
            "订单": ["下单订单", "支付订单", "完成订单", "有效订单"],
            "订单量": ["下单订单量", "支付订单量", "完成订单量"],
            "转化率": ["访问-下单转化率", "下单-支付转化率", "注册转化率"],
            "留存率": ["次日留存率", "7日留存率", "30日留存率"],
            "去年": ["按自然年去年", "按滚动12个月去年同期", "按财年去年"],
            "本月": ["自然月（1号至今）", "近30天", "财务月"],
        }

        out: List[Dict[str, Any]] = []
        for noun, options in ambiguity_map.items():
            if noun not in q:
                continue
            out.append(
                {
                    "field": noun,
                    "question": f"你提到的“{noun}”具体指哪一个口径？",
                    "options": options,
                    "chose_type": "单选",
                }
            )
        return out[:3]

    @staticmethod
    def _build_intent_clarify(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构造意图多选澄清信息。"""
        options: List[str] = []
        for c in candidates or []:
            if not isinstance(c, dict):
                continue
            name = str(c.get("intent", "") or "").strip()
            if not name:
                continue
            # 候选意图只返回意图名称（不带示例/解释）
            options.append(name)
        # 去重保序
        seen = set()
        options = [x for x in options if not (x in seen or seen.add(x))]

        return {
            "question": "你的需求更接近哪些意图？（可多选）",
            "options": options,
            "chose_type": "多选",
        }

    @staticmethod
    def _normalize_llm_clarify_questions(raw: Any) -> List[str]:
        """仅保留大模型返回的澄清问题：去空、去重、保序。"""
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            raw = [raw]
        out: List[str] = []
        seen = set()
        for item in raw:
            q = str(item or "").strip()
            if not q or q in seen:
                continue
            seen.add(q)
            out.append(q)
        return out[:10]

    @staticmethod
    def _normalize_clarify_conditions(raw: Any) -> List[str]:
        """规范化缺失条件列表。"""
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            raw = [raw]
        out: List[str] = []
        seen = set()
        for item in raw:
            cond = str(item or "").strip()
            if not cond or cond in seen:
                continue
            seen.add(cond)
            out.append(cond)
        return out[:10]

    @staticmethod
    def _infer_missing_conditions_from_slots(slots: Dict[str, Any]) -> List[str]:
        """当 condition_need_clarify=true 但缺失条件为空时，基于槽位做最小兜底。"""
        if not isinstance(slots, dict):
            return []
        missing: List[str] = []
        if not str(slots.get("数据对象", "") or "").strip():
            missing.append("数据对象")
        if not str(slots.get("时间范围", "") or "").strip():
            missing.append("时间范围")
        if not str(slots.get("维度", "") or "").strip():
            missing.append("统计维度")
        return missing

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(cls, params: dict):
        """
        参考 semantic_complete_tool: 提供 HTTP/API 方式调用入口

        约定入参：
        {
          "query": "...",
          "background": "...",         # 可选
          "intents": {...},           # 可选
          "top_k": 3,                 # 可选
          "min_confidence": 0.6,      # 可选
          "min_margin": 0.15,         # 可选
          "report_intents": false,     # 可选
          "enable_field_clarify": false, # 可选
          "kn_id": "idrm_metadata_knowledge_network_lbb",                 # 可选，知识网络ID，默认 duty
          "llm": {},
          "auth": {
            "token": "Bearer xxx",      // 推荐，
            "user_id": "123456"         // 可选
          },
        }
        """
        # LLM 配置（参考 semantic_complete_tool）
        llm_dict = {
            "model_name": getattr(_SETTINGS, "TOOL_LLM_MODEL_NAME", ""),
            "openai_api_key": getattr(_SETTINGS, "TOOL_LLM_OPENAI_API_KEY", ""),
            "openai_api_base": getattr(_SETTINGS, "TOOL_LLM_OPENAI_API_BASE", ""),
            "max_tokens": 6000,
            "temperature": 0.1,
        }
        llm_out_dict = params.get("llm", {}) or {}
        # 兼容：llm.name / llm.model_name
        if llm_out_dict.get("name"):
            llm_dict["model_name"] = llm_out_dict.get("name")
        llm = CustomChatOpenAI(**llm_dict)

        kn_id = params.get("kn_id", "idrm_metadata_knowledge_network_lbb")
        token = params.get("auth", {}).get("token", "")

        tool = cls(llm=llm, background=params.get("background", ""), kn_id=kn_id, token=token)
        tool_params = {
            "query": params.get("query", ""),
            "intents": params.get("intents", DEFAULT_INTENTS),
            "top_k": params.get("top_k", 3),
            "min_confidence": params.get("min_confidence", 0.6),
            "min_margin": params.get("min_margin", 0.15),
            "report_intents": params.get("report_intents", False),
            "enable_field_clarify": params.get("enable_field_clarify", False),
        }
        res = await tool.ainvoke(input=tool_params)
        return res

    @staticmethod
    async def get_api_schema():
        """参考 semantic_complete_tool: 提供 OpenAPI schema（供工具路由与文档生成）"""
        return {
            "post": {
                "summary": "intent_router",
                "description": "意图路由工具：根据可配置的多意图列表（名称/关键词/示例）对用户输入进行意图识别；模糊时返回澄清反问。",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "用户输入的原始问题/需求"},
                                    "background": {
                                        "type": "string",
                                        "description": "用于大模型意图识别的背景信息/参考上下文（可选）。当需要调用大模型澄清或做最终判别时会传入提示词。",
                                    },
                                    "intents": {
                                        "type": "object",
                                        "description": "意图配置：{intent_name: {description: '...', keywords: [...], examples: [...], notes: ...}}，notes 支持字符串或字符串数组。",
                                    },
                                    "top_k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
                                    "min_confidence": {"type": "number", "default": 0.6, "minimum": 0, "maximum": 1},
                                    "min_margin": {"type": "number", "default": 0.15, "minimum": 0, "maximum": 1},
                                    "report_intents": {"type": "boolean", "default": False},
                                    "enable_field_clarify": {
                                        "type": "boolean",
                                        "default": True,
                                        "description": "是否启用字段消歧（识别 query 中可能歧义的名词并返回候选含义）",
                                    },
                                    "kn_id": {
                                        "type": "string",
                                        "default": "idrm_metadata_knowledge_network_lbb",
                                        "description": "可选，知识网络ID",
                                    },
                                    "auth": {
                                        "type": "object",
                                        "description": "可选，鉴权信息。",
                                        "properties": {
                                            "token": {"type": "string", "description": "认证令牌，支持 Bearer token"},
                                            "user_id": {"type": "string", "description": "可选，用户ID"},
                                        },
                                    },
                                    "llm": {
                                        "type": "object",
                                        "description": "LLM 配置参数"
                                    }
                                },
                                "required": ["query"],
                            },
                            "examples": {
                                "default": {
                                    "summary": "意图路由示例",
                                    "value": {
                                        "query": "帮我找2025年销售数据表",
                                        "intents": DEFAULT_INTENTS,
                                        "top_k": 3,
                                        "min_confidence": 0.6,
                                        "min_margin": 0.15,
                                        "report_intents": False,
                                        "enable_field_clarify": False,
                                        "kn_id": "idrm_metadata_knowledge_network_lbb",
                                        "auth": {"token": "Bearer xxx"},
                                        "llm": {"name": "Tome-pro"},
                                    },
                                }
                            },
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "intent": {"type": "string", "description": "最终意图（需澄清时为空）"},
                                        "confidence": {"type": "number", "description": "意图置信度"},
                                        "slots": {"type": "object", "description": "抽取槽位"},
                                        "is_unknown": {"type": "boolean", "description": "是否未知意图"},
                                        "need_clarify": {"type": "boolean", "description": "是否需要澄清"},
                                        "intent_need_clarify": {"type": "boolean", "description": "是否需要意图澄清（意图模糊/不在候选中）"},
                                        "condition_need_clarify": {"type": "boolean", "description": "是否需要条件澄清（意图明确但关键条件缺失）"},
                                        "clarify_conditions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "缺失的关键条件列表，例如时间范围、维度、口径等",
                                        },
                                        "clarify_questions": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "澄清问题建议",
                                        },
                                        "intent_clarify": {
                                            "type": "object",
                                            "description": "意图澄清选项（多选）",
                                        },
                                        "refer_clarify": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                            "description": "指代澄清信息",
                                        },
                                        "field_clarify": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                            "description": "字段消歧信息",
                                        },
                                        "noun_phrases": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "模糊意图时由LLM抽取的名词/名词短语",
                                        }
                                        ,
                                        "summary_text": {"type": "string", "description": "中文摘要文本"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }

    async def _llm_choose(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        slots_hint: Dict[str, str],
        background: str = "",
    ) -> Dict[str, Any]:
        """
        使用大模型在候选意图中做最终判别，并产出标准输出结构（含 need_clarify/反问/slots）。
        失败时抛异常，由上层 fallback。
        """
        if not getattr(self, "llm", None):
            raise ValueError("llm is not configured")

        system_prompt = IntentRouterPrompt(language="cn", background=self.background or "")
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt.render()),
                HumanMessagePromptTemplate.from_template(
                    "用户query：{query}\n\n"
                    "背景知识（可为空）：\n{background}\n\n"
                    "候选意图列表（按相关性排序）：\n{candidates_json}\n\n"
                    "槽位提示（可参考，可覆盖）：\n{slots_hint_json}\n"
                ),
            ]
        )

        messages = prompt.format_messages(
            query=query,
            background=(background or "").strip(),
            candidates_json=json.dumps(candidates, ensure_ascii=False, indent=2),
            slots_hint_json=json.dumps(slots_hint, ensure_ascii=False, indent=2),
        )

        resp = await self.llm.ainvoke(messages)
        content = getattr(resp, "content", "") or ""

        # 尝试解析 JSON（容错：截取首尾大括号）
        text = content.strip()
        if not text.startswith("{"):
            l = text.find("{")
            r = text.rfind("}")
            if l != -1 and r != -1 and r > l:
                text = text[l : r + 1]

        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("llm output is not a dict")
        return parsed

    @staticmethod
    def _normalize_text(text: str) -> str:
        return (text or "").strip().lower()

    @classmethod
    def _merge_ranked_by_final_intent(
        cls,
        ranked: List[Tuple[str, float, Dict[str, Any], float]],
    ) -> List[Tuple[str, float, Dict[str, Any], float]]:
        """
        将候选按最终意图归并，避免中间流程意图（如“找表”）覆盖最终意图（如“问数”）。
        归并策略：同一最终意图取置信度更高者；若置信度相同取规则分更高者。
        """
        merged: Dict[str, Tuple[str, float, Dict[str, Any], float]] = {}
        for name, conf, meta, score in ranked:

            prev = merged.get(name)
            candidate = (name, conf, meta, score)
            if prev is None or (conf, score) > (prev[1], prev[3]):
                merged[name] = candidate
        return sorted(merged.values(), key=lambda x: (x[1], x[3]), reverse=True)

    @staticmethod
    def _score_intent(query: str, keywords: List[str], examples: List[str], notes: List[str]) -> float:
        """
        规则打分：
        - keyword 命中（包含）加分
        - keyword 完整词边界命中加额外分（英文/数字边界有限）
        - examples 作为弱特征：与 query 的字面重叠（仅做轻量加分）
        """
        q = IntentRouterTool._normalize_text(query)
        if not q:
            return 0.0

        score = 0.0

        for kw in keywords or []:
            k = IntentRouterTool._normalize_text(kw)
            if not k:
                continue
            if k in q:
                score += 1.0
                # 英文/数字关键词用边界再加一点（中文不适用但无害）
                try:
                    if re.search(rf"\b{re.escape(k)}\b", q):
                        score += 0.25
                except re.error:
                    pass

        # examples 轻量加分：共享的连续字符片段
        for ex in examples or []:
            e = IntentRouterTool._normalize_text(ex)
            if not e:
                continue
            # 取长度>=2 的公共子串数量作为粗略重叠
            common = 0
            for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}", e):
                if token and token in q:
                    common += 1
            score += min(common * 0.15, 0.45)

        # notes 弱特征加分（低于 examples 权重）
        for note in notes or []:
            n = IntentRouterTool._normalize_text(note)
            if not n:
                continue
            common = 0
            for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}", n):
                if token and token in q:
                    common += 1
            score += min(common * 0.08, 0.24)

        return score

    @staticmethod
    def _normalize_notes(notes: Any) -> List[str]:
        """兼容 notes 为 str/list 的场景。"""
        if notes is None:
            return []
        if isinstance(notes, str):
            v = notes.strip()
            return [v] if v else []
        if isinstance(notes, list):
            out: List[str] = []
            for item in notes:
                s = str(item or "").strip()
                if s:
                    out.append(s)
            return out
        return []

    @staticmethod
    def _softmax_confidences(scores: List[float]) -> List[float]:
        # 简单稳定 softmax
        if not scores:
            return []
        m = max(scores)
        exps = [pow(2.718281828, s - m) for s in scores]
        denom = sum(exps) or 1.0
        return [v / denom for v in exps]

    @staticmethod
    def _extract_slots(query: str) -> Dict[str, str]:
        """
        轻量槽位抽取（可按业务继续增强）：
        - 时间范围：2025年/2025年Q1/2025Q1/2025-01 等
        - 维度：北京/上海/地区/省/市（简单命中）
        - 数据对象：尽量从“销售额/用户数/留存率/订单量”等常见指标词抓取
        """
        q = (query or "").strip()

        time_patterns = [
            r"20\d{2}年Q[1-4]",
            r"20\d{2}Q[1-4]",
            r"20\d{2}年",
            r"20\d{2}[-/\.](0?[1-9]|1[0-2])",
            r"(0?[1-9]|1[0-2])月",
        ]
        time_range = ""
        for p in time_patterns:
            m = re.search(p, q, flags=re.IGNORECASE)
            if m:
                time_range = m.group(0)
                break

        # 简单地域维度
        dims = []
        for city in ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆"]:
            if city in q:
                dims.append(city)
        dimension = "、".join(dims)

        # 常见指标/对象词
        metric_candidates = [
            "销售额",
            "销售量",
            "用户数",
            "留存率",
            "转化率",
            "订单量",
            "GMV",
            "收入",
            "成本",
            "利润",
        ]
        data_object = ""
        for m in metric_candidates:
            if m in q:
                data_object = m
                break

        return {
            "数据对象": data_object,
            "时间范围": time_range,
            "维度": dimension,
            "操作条件": "",
        }

    @construct_final_answer
    def _run(
        self,
        query: str,
        intents: Dict[str, Dict[str, Any]] = None,
        top_k: int = 3,
        min_confidence: float = 0.6,
        min_margin: float = 0.15,
        report_intents: bool = True,
        enable_field_clarify: bool = False,
        title: str = "",
        background: str = "",
        **_: Any,
    ) -> Dict[str, Any]:
        if background:
            self.background = str(background)
        # 同步版本：只走规则兜底（避免 sync 中 await LLM）
        return self._route_rules(
            query=query,
            intents=intents or DEFAULT_INTENTS,
            top_k=top_k,
            min_confidence=min_confidence,
            min_margin=min_margin,
            report_intents=report_intents,
            enable_field_clarify=enable_field_clarify,
        )

    @async_construct_final_answer
    async def _arun(
        self,
        query: str,
        intents: Dict[str, Dict[str, Any]] = None,
        top_k: int = 3,
        min_confidence: float = 0.6,
        min_margin: float = 0.15,
        report_intents: bool = True,
        enable_field_clarify: bool = False,
        title: str = "",
        background: str = "",
        **_: Any,
    ) -> Dict[str, Any]:
        if background:
            self.background = str(background)
        return await self._route_async(
            query=query,
            intents=intents or DEFAULT_INTENTS,
            top_k=top_k,
            min_confidence=min_confidence,
            min_margin=min_margin,
            report_intents=report_intents,
            enable_field_clarify=enable_field_clarify,
        )

    def _route_rules(
        self,
        query: str,
        intents: Dict[str, Dict[str, Any]],
        top_k: int,
        min_confidence: float,
        min_margin: float,
        report_intents: bool,
        enable_field_clarify: bool = False,
    ) -> Dict[str, Any]:
        if self._contains_sql_risk_tokens(query):
            return self._build_sql_risk_block_result(
                query=query,
                reason="命中 SQL 高危操作关键词（规则审查）。",
            )

        # 1) 打分
        intent_names = list(intents.keys())
        scores: List[float] = []
        metas: List[Dict[str, Any]] = []
        for name in intent_names:
            meta = intents.get(name) or {}
            keywords = meta.get("keywords") or []
            examples = meta.get("examples") or []
            notes = self._normalize_notes(meta.get("notes"))
            s = self._score_intent(query, keywords, examples, notes)
            scores.append(s)
            metas.append({
                "description": str(meta.get("description", "") or ""),
                "keywords": keywords,
                "examples": examples,
                "notes": notes,
                "route": meta.get("route", [])
            })

        # 2) 置信度
        confidences = self._softmax_confidences(scores) if scores else []

        # 3) 候选排序
        ranked_raw = sorted(
            [
                (intent_names[i], confidences[i] if i < len(confidences) else 0.0, metas[i], scores[i])
                for i in range(len(intent_names))
            ],
            key=lambda x: (x[1], x[3]),
            reverse=True,
        )
        ranked = self._merge_ranked_by_final_intent(ranked_raw)

        candidates = [
            {
                "intent": name,
                "confidence": round(conf, 4),
                "score": round(score, 4),
                "description": meta.get("description", ""),
                "keywords": meta.get("keywords", []),
                "examples": meta.get("examples", []),
                "notes": meta.get("notes", []),
            }
            for (name, conf, meta, score) in ranked[: max(1, top_k)]
        ]

        slots = self._extract_slots(query)

        best_intent, best_conf, best_meta, best_score = ranked[0] if ranked else ("", 0.0, {}, 0.0)
        second_conf = ranked[1][1] if len(ranked) > 1 else 0.0

        # 规则兜底：判断未知/模糊
        is_unknown = best_score <= 0.0
        need_clarify = False
        clarify_questions: List[str] = []

        if is_unknown:
            need_clarify = True
            # 澄清问题仅由大模型产出；规则路径不生成模板澄清句
            clarify_questions = []
        else:
            if best_conf < min_confidence or (best_conf - second_conf) < min_margin:
                need_clarify = True
                clarify_questions = []

        # 5) module_result：仅用于日志，不返回给调用方
        module_result: Dict[str, Any] = {
            "candidates": candidates,
        }
        if report_intents:
            module_result["intents_report"] = intents

        try:
            logger.info(
                "intent_router module_result (rules): %s",
                json.dumps(module_result, ensure_ascii=False),
            )
        except Exception:
            logger.info("intent_router module_result (rules): %s", module_result)

        return {
            "intent": "" if need_clarify else best_intent,
            "confidence": round(float(best_conf), 4),
            "slots": slots,
            "is_unknown": bool(is_unknown),
            "need_clarify": bool(need_clarify),
            "intent_need_clarify": bool(need_clarify),
            "condition_need_clarify": False,
            "clarify_conditions": [],
            "clarify_questions": clarify_questions,
            # "intent_clarify": self._build_intent_clarify(candidates) if need_clarify else {},
            "refer_clarify": [],
            "field_clarify": self._build_field_clarify(query) if enable_field_clarify else [],
            "noun_phrases": [],
            "summary_text": self._build_summary_text(
                query=query,
                intent=("" if need_clarify else best_intent),
                confidence=float(best_conf),
                slots=slots,
                is_unknown=bool(is_unknown),
                need_clarify=bool(need_clarify),
                clarify_questions=clarify_questions,
                intent_need_clarify=bool(need_clarify),
                condition_need_clarify=False,
            ),
        }

    def _route_embedding(
        self,
            query: str,
            intents: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        向量匹配路由：如果匹配度非常高（>0.99），返回匹配结果
        
        Returns:
            如果找到高匹配度意图，返回包含 intent 和 score 的字典；否则返回 None
        """
        try:
            adp = ADPService()

            query_embedding = adp.get_adp_embedding([query])
            query_embedding = query_embedding["data"][0]["embedding"]

            best_match = None
            best_score = 0.0

            for intent_name, intent_meta in intents.items():
                example_embedding = adp.get_adp_embedding(intent_meta["examples"])
                embedding_data_list = [embedding["embedding"] for embedding in example_embedding["data"]]

                score = [cosine_similarity(q_embedding, query_embedding) for q_embedding in embedding_data_list]

                highest_score = np.max(score) if score else 0.0
                if highest_score > best_score:
                    best_score = highest_score
                    best_match = {
                        "intent": intent_name,
                        "score": highest_score,
                        "description": str(intent_meta.get("description", "") or ""),
                        "keywords": intent_meta.get("keywords", []),
                        "examples": intent_meta.get("examples", []),
                        "notes": self._normalize_notes(intent_meta.get("notes")),
                        "route": intent_meta.get("route", []),
                    }

            # 如果向量匹配度非常高（>0.99），返回匹配结果
            if best_match and best_score > 0.99:
                return best_match
            
            return None
        except Exception as e:
            logger.warning(f"intent_router embedding failed: {e}")
            return None

    async def _route_async(
        self,
        query: str,
        intents: Dict[str, Dict[str, Any]],
        top_k: int,
        min_confidence: float,
        min_margin: float,
        report_intents: bool,
        enable_field_clarify: bool = False,
    ) -> Dict[str, Any]:
        """
        异步路由流程：
        1. 如果向量匹配度非常高（>0.99），直接返回向量匹配结果，不使用LLM
        2. 如果规则匹配非常明确（置信度高且不需要澄清），直接返回规则结果，不使用LLM
        3. 如果出现模糊意图（need_clarify=True）且配置了LLM，自动使用LLM生成反问信息
        """
        if self._contains_sql_risk_tokens(query):
            review = await self._llm_sql_risk_review(query)
            if bool(review.get("blocked", False)):
                return self._build_sql_risk_block_result(
                    query=query,
                    reason=str(review.get("reason", "") or "命中 SQL 高危操作，已拦截。"),
                )

        # 1. 先尝试向量匹配
        embedding_res = self._route_embedding(
            query=query,
            intents=intents,
        )
        
        # 如果向量匹配度非常高，直接返回结果
        if embedding_res and embedding_res.get("score", 0.0) > 0.99:
            slots = self._extract_slots(query)
            module_result: Dict[str, Any] = {
                "candidates": [{
                    "intent": embedding_res["intent"],
                    "confidence": round(embedding_res["score"], 4),
                    "score": round(embedding_res["score"], 4),
                    "description": embedding_res.get("description", ""),
                    "keywords": embedding_res.get("keywords", []),
                    "examples": embedding_res.get("examples", []),
                    "notes": embedding_res.get("notes", []),
                }],
                "embedding_match": True,
            }
            if report_intents:
                module_result["intents_report"] = intents

            try:
                logger.info(
                    "intent_router module_result (embedding): %s",
                    json.dumps(module_result, ensure_ascii=False),
                )
            except Exception:
                logger.info("intent_router module_result (embedding): %s", module_result)
            
            return {
                "intent": embedding_res["intent"],
                "confidence": round(embedding_res["score"], 4),
                "slots": slots,
                "is_unknown": False,
                "need_clarify": False,
                "intent_need_clarify": False,
                "condition_need_clarify": False,
                "clarify_conditions": [],
                "clarify_questions": [],
                "intent_clarify": {},
                "refer_clarify": [],
                "field_clarify": [],
                "noun_phrases": [],
                "summary_text": self._build_summary_text(
                    query=query,
                    intent=embedding_res["intent"],
                    confidence=float(embedding_res["score"]),
                    slots=slots,
                    is_unknown=False,
                    need_clarify=False,
                    clarify_questions=[],
                    intent_need_clarify=False,
                    condition_need_clarify=False,
                ),
            }

        # 2. 使用规则召回候选（以及规则 slots hint）
        rule_res = self._route_rules(
            query=query,
            intents=intents,
            top_k=top_k,
            min_confidence=min_confidence,
            min_margin=min_margin,
            report_intents=report_intents,
            enable_field_clarify=enable_field_clarify,
        )

        # _route_rules 不返回 module_result；这里单独生成 candidates 供 LLM 使用（仅日志，不返回）
        intent_names = list(intents.keys())
        scores: List[float] = []
        metas: List[Dict[str, Any]] = []
        for name in intent_names:
            meta = intents.get(name) or {}
            keywords = meta.get("keywords") or []
            examples = meta.get("examples") or []
            notes = self._normalize_notes(meta.get("notes"))
            s = self._score_intent(query, keywords, examples, notes)
            scores.append(s)
            metas.append({
                "description": str(meta.get("description", "") or ""),
                "keywords": keywords,
                "examples": examples,
                "notes": notes,
                "route": meta.get("route", [])
            })

        confidences = self._softmax_confidences(scores) if scores else []
        ranked_raw = sorted(
            [
                (intent_names[i], confidences[i] if i < len(confidences) else 0.0, metas[i], scores[i])
                for i in range(len(intent_names))
            ],
            key=lambda x: (x[1], x[3]),
            reverse=True,
        )
        ranked = self._merge_ranked_by_final_intent(ranked_raw)
        candidates = [
            {
                "intent": name,
                "confidence": round(conf, 4),
                "score": round(score, 4),
                "description": meta.get("description", ""),
                "keywords": meta.get("keywords", []),
                "examples": meta.get("examples", []),
                "notes": meta.get("notes", []),
            }
            for (name, conf, meta, score) in ranked[: max(1, top_k)]
        ]
        slots_hint = rule_res.get("slots", {}) or self._extract_slots(query)
        
        # 3. 判断规则匹配是否非常明确（置信度高且不需要澄清）
        rule_confidence = rule_res.get("confidence", 0.0)
        rule_need_clarify = rule_res.get("need_clarify", False)
        rule_is_unknown = rule_res.get("is_unknown", False)
        
        # 如果规则匹配非常明确（置信度高且不需要澄清），直接返回规则结果
        if not rule_need_clarify and not rule_is_unknown and rule_confidence >= min_confidence:
            # 检查与第二名的差距是否足够大
            if len(candidates) >= 2:
                first_conf = candidates[0].get("confidence", 0.0)
                second_conf = candidates[1].get("confidence", 0.0)
                if (first_conf - second_conf) >= min_margin:
                    # 规则匹配非常明确：记录候选日志，直接返回
                    try:
                        logger.info(
                            "intent_router module_result (rules_clear): %s",
                            json.dumps({"candidates": candidates, "rule_match": True}, ensure_ascii=False),
                        )
                    except Exception:
                        logger.info("intent_router module_result (rules_clear): %s", {"candidates": candidates, "rule_match": True})
                    return rule_res
            elif len(candidates) == 1:
                # 只有一个候选，且置信度高：记录候选日志，直接返回
                try:
                    logger.info(
                        "intent_router module_result (rules_clear): %s",
                        json.dumps({"candidates": candidates, "rule_match": True}, ensure_ascii=False),
                    )
                except Exception:
                    logger.info("intent_router module_result (rules_clear): %s", {"candidates": candidates, "rule_match": True})
                return rule_res

        # 4. 如果出现模糊意图（need_clarify=True），必须使用LLM生成反问信息
        if rule_need_clarify and getattr(self, "llm", None) and candidates:
            try:
                llm_out = await self._llm_choose(
                    query=query,
                    candidates=candidates,
                    slots_hint=slots_hint,
                    background=self.background or "",
                )

                module_result: Dict[str, Any] = {
                    "candidates": candidates,
                    "llm_decision": llm_out,
                    "embedding_match": False,
                    "rule_match": True,
                }
                if report_intents:
                    module_result["intents_report"] = intents

                try:
                    logger.info(
                        "intent_router module_result (llm): %s",
                        json.dumps(module_result, ensure_ascii=False),
                    )
                except Exception:
                    logger.info("intent_router module_result (llm): %s", module_result)

                intent = llm_out.get("intent", "") or ""
                confidence = float(llm_out.get("confidence", 0.0) or 0.0)
                out_slots = llm_out.get("slots") if isinstance(llm_out.get("slots"), dict) else slots_hint
                is_unknown = bool(llm_out.get("is_unknown", False))
                need_clarify = bool(llm_out.get("need_clarify", False))
                intent_need_clarify = bool(llm_out.get("intent_need_clarify", False))
                condition_need_clarify = bool(llm_out.get("condition_need_clarify", False))
                clarify_conditions = self._normalize_clarify_conditions(llm_out.get("clarify_conditions", []))
                clarify_questions = llm_out.get("clarify_questions", []) or []
                refer_clarify = self._normalize_refer_clarify(llm_out.get("refer_clarify"))
                field_clarify = self._normalize_field_clarify(llm_out.get("field_clarify"))
                if not isinstance(clarify_questions, list):
                    clarify_questions = [str(clarify_questions)]
                clarify_questions = self._normalize_llm_clarify_questions(clarify_questions)

                # 约束：intent 必须来自候选意图
                candidate_intents = {str(c.get("intent", "")).strip() for c in candidates if isinstance(c, dict)}
                if intent and intent not in candidate_intents:
                    intent = ""
                    need_clarify = True
                    intent_need_clarify = True
                    condition_need_clarify = False

                # 若显式声明某类澄清，则 need_clarify 必须为 true
                if intent_need_clarify or condition_need_clarify:
                    need_clarify = True

                # need_clarify 为 true 但分类未给出时，按语义补齐分类
                if need_clarify and not intent_need_clarify and not condition_need_clarify:
                    if not intent or is_unknown:
                        intent_need_clarify = True
                    elif clarify_conditions:
                        condition_need_clarify = True
                    else:
                        intent_need_clarify = True

                # 条件澄清应带缺失条件列表；若未给出，按 slots 兜底推断
                if condition_need_clarify and not clarify_conditions:
                    clarify_conditions = self._infer_missing_conditions_from_slots(out_slots if isinstance(out_slots, dict) else slots_hint)

                noun_phrases: List[str] = []
                if need_clarify:
                    field_clarify = []
                    if enable_field_clarify:
                        noun_phrases = await self._llm_extract_nouns(query)
                        adp_service = ADPService()
                        for noun_phrase in noun_phrases:
                            query_params = {
                                "condition": {
                                    "operation": "or",
                                    "sub_conditions": [
                                        {
                                            "field": "fields",
                                            "operation": "match",
                                            "value": noun_phrase
                                        }
                                    ]
                                },
                                "need_total": True,
                                "limit": 5
                            }
                            try:

                                search_results = await adp_service.dip_ontology_query_by_object_types_external(
                                    self.token,
                                    kn_id=self.kn_id or "duty",
                                    class_id="metadata",
                                    body=query_params
                                )

                                logger.info(
                                    f"[IntentRouterTool] search success, total_count={search_results.get('total_count', 0)}")
                                mat_fields_list = set()
                                for data in search_results.get("datas", []):
                                    if data.get("fields", ""):
                                        m_fields = data.get("fields", "")

                                        for m in m_fields.split(","):
                                            if m.strip():
                                                result = re.findall(r'\((.*?)\)', m.strip())
                                                for m_res in result:
                                                    if noun_phrase in m_res:
                                                        mat_fields_list.add(m_res)
                                if len(mat_fields_list):
                                    score_fields_list = []
                                    for m_field in mat_fields_list:
                                        score = levenshtein_similarity(m_field, noun_phrase)
                                        score_fields_list.append((m_field, score))
                                    score_fields_list.sort(key=lambda x: x[1], reverse=True)
                                    score_fields_list = score_fields_list[:3]
                                    logger.info("{} score_fields_list {}".format(noun_phrase, score_fields_list))
                                    field_clarify.append({
                                        "可能歧义字段": noun_phrase,
                                        "可选项": [sfm[0] for sfm in score_fields_list] + ["其他"]
                                    })
                            except Exception as query_error:
                                logger.warning(
                                    f"[IntentRouterTool] failed: {query_error}, but continue")

                if not enable_field_clarify:
                    field_clarify = []

                return {
                    "intent": "" if intent_need_clarify else intent,
                    "confidence": round(max(0.0, min(1.0, confidence)), 4),
                    "slots": {
                        "数据对象": str(out_slots.get("数据对象", "")) if isinstance(out_slots, dict) else "",
                        "时间范围": str(out_slots.get("时间范围", "")) if isinstance(out_slots, dict) else "",
                        "维度": str(out_slots.get("维度", "")) if isinstance(out_slots, dict) else "",
                        "操作条件": str(out_slots.get("操作条件", "")) if isinstance(out_slots, dict) else "",
                    },
                    "is_unknown": is_unknown,
                    "need_clarify": need_clarify,
                    "intent_need_clarify": bool(intent_need_clarify),
                    "condition_need_clarify": bool(condition_need_clarify),
                    "clarify_conditions": clarify_conditions,
                    "clarify_questions": clarify_questions,
                    # "intent_clarify": self._build_intent_clarify(candidates) if need_clarify else {},
                    "refer_clarify": refer_clarify,
                    "field_clarify": field_clarify,
                    "noun_phrases": noun_phrases,
                    "summary_text": self._build_summary_text(
                        query=query,
                        intent=("" if intent_need_clarify else intent),
                        confidence=float(max(0.0, min(1.0, confidence))),
                        slots={
                            "数据对象": str(out_slots.get("数据对象", "")) if isinstance(out_slots, dict) else "",
                            "时间范围": str(out_slots.get("时间范围", "")) if isinstance(out_slots, dict) else "",
                            "维度": str(out_slots.get("维度", "")) if isinstance(out_slots, dict) else "",
                            "操作条件": str(out_slots.get("操作条件", "")) if isinstance(out_slots, dict) else "",
                        },
                        is_unknown=bool(is_unknown),
                        need_clarify=bool(need_clarify),
                        clarify_questions=clarify_questions,
                        intent_need_clarify=bool(intent_need_clarify),
                        condition_need_clarify=bool(condition_need_clarify),
                    ),
                }
            except Exception as e:
                logger.warning(f"intent_router llm choose failed, fallback to rules: {e}")
                # LLM失败时，返回规则结果（包含规则生成的澄清问题）

        # 5. 其他情况：记录候选日志，返回规则结果
        try:
            logger.info(
                "intent_router module_result (final_rules): %s",
                json.dumps({"candidates": candidates, "rule_match": True}, ensure_ascii=False),
            )
        except Exception:
            logger.info("intent_router module_result (final_rules): %s", {"candidates": candidates, "rule_match": True})
        # 为规则返回补充 summary_text
        if "summary_text" not in rule_res:
            rule_res["summary_text"] = self._build_summary_text(
                query=query,
                intent=str(rule_res.get("intent", "") or ""),
                confidence=float(rule_res.get("confidence", 0.0) or 0.0),
                slots=rule_res.get("slots", {}) if isinstance(rule_res.get("slots"), dict) else {},
                is_unknown=bool(rule_res.get("is_unknown", False)),
                need_clarify=bool(rule_res.get("need_clarify", False)),
                clarify_questions=rule_res.get("clarify_questions", []) or [],
                intent_need_clarify=bool(rule_res.get("intent_need_clarify", False)),
                condition_need_clarify=bool(rule_res.get("condition_need_clarify", False)),
            )
        if "refer_clarify" not in rule_res:
            rule_res["refer_clarify"] = []
        if "field_clarify" not in rule_res:
            rule_res["field_clarify"] = self._build_field_clarify(query) if enable_field_clarify else []
        if "intent_need_clarify" not in rule_res:
            rule_res["intent_need_clarify"] = bool(rule_res.get("need_clarify", False))
        if "condition_need_clarify" not in rule_res:
            rule_res["condition_need_clarify"] = False
        if "clarify_conditions" not in rule_res:
            rule_res["clarify_conditions"] = []
        # if "intent_clarify" not in rule_res:
            # rule_res["intent_clarify"] = self._build_intent_clarify(candidates) if bool(rule_res.get("need_clarify", False)) else {}
        if "noun_phrases" not in rule_res:
            rule_res["noun_phrases"] = []
        return rule_res


def levenshtein_similarity(s1: str, s2: str) -> float:
    """
    计算字符串相似度 0~1，越大越相似
    """
    # 初始化矩阵
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # 动态规划计算编辑距离
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1,  # 删除
                           dp[i][j - 1] + 1,  # 插入
                           dp[i - 1][j - 1] + cost)  # 替换

    max_len = max(m, n)
    if max_len == 0:
        return 1.0
    # 转成 0~1 相似度
    return 1.0 - (dp[m][n] / max_len)