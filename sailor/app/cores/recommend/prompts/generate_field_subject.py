role_skills = """**数据质量校验规则**：根据字段名称、描述等信息，生成能够对字段内容进行数据质量校验的规则，譬如唯一性约束、编码规则、逻辑表达式等"""

role_tasks = """根据字段名称、描述等信息，生成能够对字段内容进行数据质量校验的规则，譬如唯一性约束、编码规则、逻辑表达式等"""

examples = """
输入数据（Input Datas）：
```json
[
	{
		"id": "object-id-01", "standard_id": "1", "name": "身份证", "desc": "",
		"background": {"table_id": "table-01", "table_name": "test1", "table_desc": ""}
	},
	{
		"id": "object-id-02", "standard_id": "2", "name": "姓名", "desc": "",
		"background": {"table_id": "table-01", "table_name": "test1", "table_desc": ""}
	}
]
```

该实例的匹配结果：
```json
[
    {
		"id": "object-id-01"
        "generate": "^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
        "distinct": "true",
		"reason": "身份证是每个公民唯一、不变的身份代码，符合18位编码规则，并且具有唯一性。"
    }
]
```
"""

output_format = """
```json
[
	{
		"id": "...对应的ID..."
		"generate": "...具体的生成信息...",
        "distinct": "...唯一性约束: 是否..."
		"reason": "...理由..."
	},
	...其他生成结果列表...
]
```
"""