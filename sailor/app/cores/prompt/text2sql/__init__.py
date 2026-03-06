# -*- coding: utf-8 -*-
GENERATE_SQL_CONCLUSION_TEMPLATE = """你是一位优秀的答案整理专家，你能根据表格，整理出问题的答案：
问题：
{{UserQuestion}}？
表格：
{{Table}}
回答需要满足以下要求：
1. 请仔细地一步步思考，用播报新闻的口吻回答。
2. 不要说废话，文字越少越好。
3. 最终的答案一定是以"因此"开始。
问题：
{{UserQuestion}}？
答案：
"""

GENERATE_SQL_TEMPLATE = '''你是一个顶尖数据库专家，非常精通SQL语言。以下是一个用户的问题，用户希望你回复一个SQL语句从而帮助他可以从数据库中查询出这个问题的答案：

{{query}}

这个数据库当中可以用于回答上述问题的数据库表及示例信息按照如下三重反引号（```）内格式给你作为参考：

```
$表名
CREATE TABLE 业务表ID
(
$字段名 $字段类型 comment $字段详细信息
...
)

示例:
{{
$字段名：$字段值
...
}}
------------------------------------
...
```

接下来，请仔细阅读及理解下述可能可以用于回答上述问题的数据库表及示例信息：

{{ddl_and_sample}}

严格按照以下格式用SQL语言回复用户问题以帮助用户查询对应的答案：
```sql
$SQL
```

====== 以下为对你提出的要求 ======
1. 只需要给出SQL，不需要说明你为什么这么做；
2. SQL语法一定要严格符合规范；
3. 当SQL中使用 GROUP BY 时，你的 SELECT 需要格外关注，不能导致SQL格式错误；
4. 样例中的 comment 是这个样例的码表值，不能出现在SQL中；
5. 当你在写 SQL中 时，需要假设 表（table） 或者 表的 字段名（column） 时， 你需要明确指出；
6. 当需要进行多表关联查询时，需要为每一张表 起一个形式为 "英文+数字" 的别名，例如： "T1", "IS1"；
7. 如果 SQL 中 出现 聚合或者运算结果，则需要使用中文 进行 重命名，并用双引号（""）括住；
8. 不使用 "DATE_SUB，DATE_ADD" 函数，因为用户的数据库不支持，所以你需要换一种方式去实现相同的功能。

====== 为你提供一些背景信息 ======
{{background}}


{{error_code}}


'''

# ====== 以下为对你提出的要求 ======
# 1. 只需要给出SQL，不需要说明你为什么这么做；
# 2. SQL语法一定要严格符合规范；
# 3. 当SQL中使用 GROUP BY 时，你的 SELECT 需要格外关注，不能导致SQL格式错误；
# 4. 样例中的 comment 是这个样例的码表值，不能出现在SQL中；
# 5. 当你在写 SQL中 时，需要假设 表（table） 或者 表的 字段名（column） 时， 你需要明确指出；
# 6. 当需要进行多表关联查询时，需要为每一张表 起一个形式为 "英文+数字" 的别名，例如： "T1", "IS1"；
# 7. 如果 SQL 中 出现 聚合或者运算结果，则需要使用中文 进行 重命名，并用双引号（""）括住；
# 8. 不使用 "DATE_SUB" 函数，但是你需要换一种方式去实现相同的功能。


PARTICIPLE_TEMPLATE = """你是一个文本分词大师，擅长对文本进行分词，并对分词结果按其在文本中的重要性进行排序。

===== 需要进行分词的文本 =====
{{text}}


===== 请注意： =====
1. 输出结果用列表表示，例如：
["chunk1", "chunk2", "chunk3", ...]
2. 越重要的词块越放在前面；
3. 输出结果返回列表即可；
"""

CREATE_SCHEMA_TEMPLATE = """CREATE TABLE {source}.{schema}.{title}
(
{middle}
);
"""

# 总的视图字段详细信息模板，以此为开始，将多个字段信息缀到其后
VIEW_COLUMN_DETAIL_INFO_TEMPLATE = '''本数据表名称为：{view_name_cn}，关于本数据表的详细说明如下:\n{view_description}\n本数据表字段详细信息罗列如下:\n{columns_detail_info}'''
# 字段信息基础模板，如果字段有其他信息，缀到本模板后，本详细信息模板缀到每个字段信息COMMENT已有信息之后作为补充
COLUMN_DETAIL_START_INFO_TEMPLATE = '''"{column_en}"字段的详细信息是：\n字段中文名为'{column_cn}'；'''
MAIN_KEY = '''此字段为主键，需满足唯一性，且可用于通过其他表的同名或类似字段关联。'''
# 以下为关联了数据标准后可获取的字段定义详细信息，根据有无以及字段类型判断，取值填充后缀到上面的字段信息基础模板后
DATA_STANDARD_INFO_TEMPLATE = '''该字段遵循名为'{standard_name}'的{standard_type}，关于该标准的简要说明为：{standard_description}；'''  # 如果字段定义关联了一个数据标准，缀上去standard_name->标准的数据元名称，standard_type->标准的类型，standard_description->标准的说明
COLUMN_LENGTH_INFO_TEMPLATE = '''字段最长长度为{data_length}；'''  # 只有字段类型为字符型时使用
NUMBER_OF_DECIMAL_PLACES_INFO_TEMPLATE = '''该字段总共有{place}位;'''  # 只有字段类型为数字型时使用
DECIMAL_NUMBER_INFO_TEMPLATE = '''小数点后精确到{decimal_precision}位;'''  # 只有字段类型为数字型且精度大于0时缀上在数字位后使用
# 以下为字段关联的数据标准额外还关联了码表信息，或者该字段直接使用了某个码表定义后从码表定义处取得的信息的拼接模板，如果有相关信息，填充后缀到字段信息后，注意，码表和编码规则互斥
ENUM_SET_INFO_TEMPLATE = '''该字段为枚举类型，其内容均为从名为 {enum_set_name} 的码表内取的值，针对当前字段，请随机从下面的码值选取一条作为样例:{enum_value_set}'''  # 如果字段或者字段的数据标准关联了一个码表，缀上去
# ENUM_VALUE_TEMPLATE = '''"{enum_value_name}":{enum_value}'''  # 码表里每一个码值的信息的模板，多个这样模板填充后的码值信息遵循组织成一定的形式码值信息集合，填入上方enum_value_set里。enum_value_name -> 码值描述，enum_value -> 码值
ENUM_VALUE_TEMPLATE = '''"{enum_value}":{enum_value_name}；'''  # 码表里每一个码值的信息的模板，多个这样模板填充后的码值信息遵循组织成一定的形式码值信息集合，填入上方enum_value_set里。enum_value_name -> 码值描述，enum_value -> 码值
ENUM_VALUE_DESCRIPTION_TEMPLATE = ''' // 说明：{enum_value_description}\n'''  # 如果有码值说明，缀到上方码值后
# 以下为字段关联的数据标准额外还关联了编码规则信息后从编码规则取得的信息的拼接模板，如果有相关信息，填充后缀到字段信息后，注意，码表和编码规则互斥
CODE_RULE_INFO_TEMPLATE = '''该字段严格遵循名为{code_rule_name}的{code_rule_standard_type}类型的编码规则；'''
# 如果是正则表达式编码规则，缀到上面编码规则信息后，与自定义编码规则互斥
RE_INFO_TEMPLATE = '''该编码规则下，字段内容需满足三重反引号(```)内的正则表达式：```{re}```。'''
# 如果是自定义编码规则，缀到上面编码规则信息后，与自定义编码规则互斥
SELFDEFINE_CODE_RULE_INFO_TEMPLATE = '''该编码规则下，字段内容需满足三重反引号(```)内的多条规则：```{rules}```。'''
# 下面是对每个编码分段规则的描述模板，按需直接缀在一起后形成多条规则的集合填入上方规则集合内
ONE_CODE_RULE_PLACE_EQUALS_ONE_INFO_TEMPLATE = '''第{present_place_number}位'''  # 当编码分段数量为1时的对编码位置的描述模板，present_place_number = SUM(之前所有分段位数) + 1
ONE_CODE_RULE_PLACE_GREATER_THAN_ONE_INFO_TEMPLATE = '''第{present_place_start_number}位至第{present_place_end_number}位'''  # 当编码分段数量为大于1时的对编码位置的描述模板，present_place_start_number = SUM(之前所有分段位数) + 1，present_place_end_number = SUM(之前所有分段位数) + 本分段编码位数
ONE_CODE_RULE_DESCRIPTION_TEMPLATE = '''是{code_rule_name}，其类型为{code_rule_type}。'''  # 缀到SELFDEFINE_CODE_RULE_INFO_TEMPLATE拼接了位数后，具体描述这个编码分段的定义
# 下面是各种编码分段类型
# 分段编码类型为码表
# 引用自码表内容，如果该段编码是码表，把这个缀到上方
# 分段类型为数字，英文字符，任意字符，汉字时无需额外信息增补
# 分段类型为日期时
ONE_CODE_RULE_DATA_TIME_TYPE_INFO_TEMPLATE = '''格式遵循{data_time_format}形式;\n'''
# 分段类型为分割字符串时，实际上等价于固定字符串
ONE_CODE_RULE_STRING_TYPE_INFO_TEMPLATE = '''该段填入后方三重反引号(```)内的固定字符串即可，```{string}```;\n'''

# 上面多条字段详细信息拼接后加入此处，形成完整的字段详细信息；
COLUMN_DETAIL_INFO_TEMPLATE = '''----------"{column_en}"字段的详细信息START----------\n{column_detail_info}\n----------"{column_en}"字段的详细信息END----------\n'''

SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME = "sample_generate"
SAMPLE_GENERATE_PROMPT_TEMPLATE = '''
你是一个顶尖数据库专家并且精通SQL数据库语言。下方是一个数据库表：

{{schema}}

以及该表内字段的详细信息：

{{column_detail_info}}

请仔细分析上述数据库表的信息后使用JSON格式创造{{sample_size}}条示例数据给我。特别注意给字符类型数据加上""。并且记住，如果数据库表信息里有示例，你创造的新的示例绝对不要包含数据库表信息的示例。
请严格遵循下方格式回答我:

SAMPLES_START
[
    {
        column_name1:value1,
        column_name2:value2,
    }
]
SAMPLES_END

你必须遵守以下几个原则：
1、回复的示例数据前加上 SAMPLES_START:
2、回复的示例数据后加上 SAMPLES_END:
3、确保回复的示例数据符合JSON格式；
4、对于如地址，人名以及任何其他实体信息以及说明类信息字段，如在对应的字段详细信内没有额外的说明，默认请使用中文；
5、如果字段关联了码表，请均匀获取对应码表中的值。
6、字段值也就是value值，不要太长超过20个字符
'''

SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME = "sample_generate_with_samples"
SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE = '''
你是一个顶尖数据库专家并且精通SQL数据库语言。下方是一个数据库表：

{{schema}}

以及该表内字段的详细信息：

{{column_detail_info}}

并且有一些已经存在的数据样例如下：

{{samples}}

请仔细分析上述数据库表的信息后使用JSON格式创造{{sample_size}}条示例数据给我。特别注意给字符类型数据加上""。并且记住，如果数据库表信息里有示例，你创造的新的示例绝对不要包含数据库表信息的示例。
请严格遵循下方格式回答我:

SAMPLES_START
[
    {
        column_name1:value1,
        column_name2:value2,
    }
]
SAMPLES_END

你必须遵守以下几个原则：
1、回复的示例数据前加上 SAMPLES_START:
2、回复的示例数据后加上 SAMPLES_END:
3、确保回复的示例数据符合JSON格式；
4、绝对不要和已经存在的数据样例重复；
5、对于如地址，人名以及任何其他实体信息以及说明类信息字段，如在对应的字段详细信内没有额外的说明，默认请使用中文；
6、如果字段关联了码表，请均匀获取对应码表中的值。
'''

RESP_TEMPLATE = """根据<strong>"{table}"</strong><i slice_idx=0>{index}</i>，检索到如下数据："""

CONSISTENCY_CHECK_TEMPLATE_FIRST = """我将为你提供三个参数，请根据参数按照注意事项回答问题：
=== question：用户的自然语言问题 ===
{{question}}

=== sql：ai 基于 question 生成的sql ===
{{sql}}

=== result：json 形式的数据 ===
{{result}}

================== 注意事项 ================== 
请严格按照如下伪代码逻辑返回结果：
    if question 和 sql 相对应:
        return {"res": "yes"}
    elif result 可以回答 question 全部问题:
        return {"res": "all"}
    elif result 可以回答 question 部分问题:
        return {"res": "part"}
    else:
        return {"res": "no", "reason": "${reason}"}
"""

CONSISTENCY_CHECK_TEMPLATE_SECOND = """我将为你提供三个参数，请根据参数按照注意事项回答问题：
====== question：用户的自然语言问题 ======
{{question}}

====== result：markdown 形式的数据 ======
{{result}}

================== 注意事项 ================== 
1 如果根据 result 能够回答 question 中的全部内容，请回复：{"res": "all"}；
2 如果根据 result 能够回答 question 中的部分内容，请回复：{"res": "part"}
3 如果根据 result 不能回答 question 中的任何内容，请回复：{"res": "no", "reason": ""}
"""
