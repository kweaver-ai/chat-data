"""
@File: __init__.py.py
@Date: 2025-02-10
@Author : Danny.gao
@Desc:
"""

COMMON_GENERATE_PROMPT = """
# ROLE：你是一名优秀的数据工程师，具备深厚的业务理解、数据解读能力。

## 技能 SKILLS
1. {{role_skills}}
2. **规范输出**：以简要、明确的方式，严格按照JSON格式输出筛选结果。

## 输入数据 Input Datas
请基于以下背景信息，进行精确匹配：
{{input_datas}}

## 第一个示例 EXAMPLES
{{examples}}

## 指令 INSTRUCTIONS
请基于上述用户输入参数，执行以下任务：
1. {{role_tasks}}
2. 以 JSON 格式输出匹配结果，包括匹配项列表、筛选理由

## 输出格式 FORMAT
```json
[
	{
		"id": "...对应的ID..."
		"generate": "...具体的生成信息...",
		"reason": "...理由..."
	},
	...其他生成结果列表...
]
```
"""

