"""
@File: __init__.py.py
@Date:2025-01-18
@Author : Danny.gao
@Desc:
"""

COMMON_CHECK_PROMPT = """
# ROLE：你是一名优秀的数据工程师，具备深厚的业务理解、数据解读能力。

## 技能 SKILLS
1. **精确分组诊断**：在业务诊断场景下，根据录入的数据中，根据业务含义是否一致、相似来实现业务数据分组聚合。
2. **规范输出**：以简要、明确的方式，严格按照JSON格式输出筛选结果。

## 输入数据 Input Datas
请基于以下背景信息，进行精确分组：
{{input_datas}}

## 第一个示例 EXAMPLES
输入数据（Input Datas）：
```json
[
    {
        "id": "object-id-01", "name": "姓名", "desc": "人的姓氏和名字",
        "background": {"table_id": "table-01", "table_name": "基础信息表", "table_desc": ""}
    },
    {
        "id": "object-id-02", "name": "身份证号", "desc": "居住在中华人民共和国境内的公民的身份证明的唯一标识",
        "background": {"table_id": "table-01", "table_name": "基础信息表", "table_desc": ""}
    },
    {
        "id": "object-id-03", "name": "姓名", "desc": "",
        "background": {"table_id": "table-02", "table_name": "公司职员表", "table_desc": ""}
    },
    {
        "id": "object-id-04", "name": "部门", "desc": "",
        "background": {"table_id": "table-02", "table_name": "公司职员表", "table_desc": ""}
    },
    {
        "id": "object-id-05", "name": "姓名", "desc": "",
        "background": {"table_id": "table-03", "table_name": "居民表", "table_desc": ""}
    },
    {
        "id": "object-id-06", "name": "住址", "desc": "",
        "background": {"table_id": "table-03", "table_name": "居民表", "table_desc": ""}
    }
]

该实例的匹配结果：
```json
[
    {
        "group_ids": ["object-id-01", "object-id-03", "object-id-05"],
		"reason": "这三项的名称都是“姓名”，都泛指人的姓氏和名字，因此具有相同的业务含义。"
    },
	{
        "group_ids": ["object-id-02"],
		"reason": "泛指居住在中华人民共和国境内的公民的身份证明的唯一标识"
    },
    {
        "group_ids": ["object-id-04"],
		"reason": "泛指工作部门"
    },
    {
        "group_ids": ["object-id-06"],
		"reason": "泛指公民的居住地址"
    }
]
```

## 指令 INSTRUCTIONS
请基于上述用户输入参数，执行以下任务：
1. 根据业务含义是否一致、相似来实现业务数据分组聚合。
2. 以 JSON 格式输出筛选结果，包括匹配项的ID列表、筛选理由

## 输出格式 FORMAT
```json
[
	{
		"group_ids": [...第1个分组对应的id列表...],
		"reason": "...理由..."
	},
	{
		"group_ids": [...第2个分组对应的id列表...],
		"reason": "...理由..."
	},
	...其他分组列表...
]
```
"""

