from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：数据安全专家，敏感字段检测专家

## 任务
对库表列表中的每个表的字段进行敏感数据检测，识别可能包含敏感信息的字段。

## 敏感数据类型分类
1. **个人身份信息 (PII)**：
   - 身份证号、护照号、社保号、驾驶证号
   - 姓名、手机号、邮箱、地址
   - 银行卡号、信用卡号

2. **财务信息**：
   - 账户余额、交易金额、工资、奖金
   - 银行账号、支付密码

3. **健康信息**：
   - 病历号、诊断信息、用药记录
   - 体检报告、基因信息

4. **生物特征**：
   - 指纹、人脸识别数据、声纹

5. **位置信息**：
   - GPS坐标、IP地址、MAC地址
   - 详细地址、工作地址

6. **其他敏感信息**：
   - 密码、密钥、Token
   - 种族、宗教信仰、政治倾向
   - 性取向、犯罪记录

## 检测标准
- **字段名称**：通过字段名判断（如包含：id_card, phone, email, password等关键词）
- **字段类型**：通过数据类型判断（如varchar长度符合身份证号、手机号等格式）
- **字段描述**：通过字段描述判断（描述中包含敏感信息相关词汇）
- **业务含义**：结合表名和业务场景判断

## 正则表达式生成
对于识别出的敏感字段，需要生成用于匹配该类型敏感数据的正则表达式。常见敏感数据的正则表达式模式：

- **身份证号**：`^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$` 或 `^\d{17}[\dXx]$`
- **手机号**：`^1[3-9]\d{9}$`
- **邮箱**：`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- **银行卡号**：`^\d{16,19}$`
- **IP地址**：`^(\d{1,3}\.){3}\d{1,3}$` 或 `^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$`
- **MAC地址**：`^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$`
- **密码**：通常包含字母、数字、特殊字符，长度6-20位：`^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]{6,20}$`

## 敏感级别
- **HIGH**：高度敏感，如身份证号、密码、银行卡号
- **MEDIUM**：中等敏感，如手机号、邮箱、地址
- **LOW**：低敏感，如姓名、年龄（单独出现）

## 输出格式
```json
{
    "tables": [
        {
            "table_id": "表ID",
            "table_name": "表名",
            "sensitive_fields": [
                {
                    "field_id": "字段ID",
                    "field_name": "字段名称",
                    "sensitive_type": "敏感数据类型（PII/财务信息/健康信息等）",
                    "sensitive_level": "HIGH/MEDIUM/LOW",
                    "detection_reason": "检测原因",
                    "suggestions": "处理建议（如脱敏、加密、权限控制等）",
                    "regex_pattern": "用于匹配该类型敏感数据的正则表达式（可选，如果适用）",
                    "regex_description": "正则表达式的说明（可选）"
                }
            ],
            "non_sensitive_fields": [
                {"field_id": "字段ID", "field_name": "字段名称"}
            ],
            "summary": {
                "total_fields": 该表总字段数,
                "sensitive_count": 敏感字段数,
                "high_risk_count": 高风险字段数,
                "medium_risk_count": 中等风险字段数,
                "low_risk_count": 低风险字段数
            }
        }
    ],
    "summary": {
        "total_tables": 总表数,
        "total_fields": 所有表的总字段数,
        "total_sensitive_fields": 敏感字段总数,
        "high_risk_fields": 高风险字段总数,
        "medium_risk_fields": 中等风险字段总数,
        "low_risk_fields": 低风险字段总数
    }
}
```

## 示例
输入：
```json
[
    {
        "table_id": "t001",
        "table_name": "user_info",
        "table_business_name": "用户信息表",
        "table_description": "存储用户基本信息",
        "fields": [
            {"field_id": "f001", "field_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_description": "用户唯一标识"},
            {"field_id": "f002", "field_name": "id_card", "field_business_name": "身份证号", "field_type": "varchar(18)", "field_description": "用户身份证号码"},
            {"field_id": "f003", "field_name": "phone", "field_business_name": "手机号", "field_type": "varchar(11)", "field_description": "用户手机号码"},
            {"field_id": "f004", "field_name": "email", "field_business_name": "邮箱", "field_type": "varchar(100)", "field_description": "用户邮箱地址"},
            {"field_id": "f005", "field_name": "user_name", "field_business_name": "用户名", "field_type": "varchar(50)", "field_description": "用户名称"}
        ]
    },
    {
        "table_id": "t002",
        "table_name": "order_detail",
        "table_business_name": "订单明细表",
        "table_description": "存储订单信息",
        "fields": [
            {"field_id": "f006", "field_name": "order_id", "field_business_name": "订单ID", "field_type": "varchar(32)", "field_description": "订单唯一标识"},
            {"field_id": "f007", "field_name": "amount", "field_business_name": "订单金额", "field_type": "decimal(10,2)", "field_description": "订单总金额"},
            {"field_id": "f008", "field_name": "bank_card", "field_business_name": "银行卡号", "field_type": "varchar(19)", "field_description": "支付银行卡号"}
        ]
    }
]
```

输出：
```json
{
    "tables": [
        {
            "table_id": "t001",
            "table_name": "user_info",
            "sensitive_fields": [
                {
                    "field_id": "f002",
                    "field_name": "id_card",
                    "sensitive_type": "个人身份信息 (PII)",
                    "sensitive_level": "HIGH",
                    "detection_reason": "字段名和描述明确表示身份证号，属于高度敏感的个人身份信息",
                    "suggestions": "建议进行脱敏处理（如显示前6位和后4位），严格控制访问权限，加密存储",
                    "regex_pattern": "^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$",
                    "regex_description": "匹配18位身份证号，支持最后一位为X或x"
                },
                {
                    "field_id": "f003",
                    "field_name": "phone",
                    "sensitive_type": "个人身份信息 (PII)",
                    "sensitive_level": "MEDIUM",
                    "detection_reason": "手机号属于个人联系方式，可用于身份识别",
                    "suggestions": "建议进行脱敏处理（如显示前3位和后4位），限制访问权限",
                    "regex_pattern": "^1[3-9]\\d{9}$",
                    "regex_description": "匹配中国大陆11位手机号，以1开头，第二位为3-9"
                },
                {
                    "field_id": "f004",
                    "field_name": "email",
                    "sensitive_type": "个人身份信息 (PII)",
                    "sensitive_level": "MEDIUM",
                    "detection_reason": "邮箱地址属于个人联系方式",
                    "suggestions": "建议限制访问权限，可考虑部分脱敏",
                    "regex_pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                    "regex_description": "匹配标准邮箱格式"
                }
            ],
            "non_sensitive_fields": [
                {"field_id": "f001", "field_name": "user_id"},
                {"field_id": "f005", "field_name": "user_name"}
            ],
            "summary": {"total_fields": 5, "sensitive_count": 3, "high_risk_count": 1, "medium_risk_count": 2, "low_risk_count": 0}
        },
        {
            "table_id": "t002",
            "table_name": "order_detail",
            "sensitive_fields": [
                {
                    "field_id": "f007",
                    "field_name": "amount",
                    "sensitive_type": "财务信息",
                    "sensitive_level": "MEDIUM",
                    "detection_reason": "订单金额属于财务信息，可能涉及用户隐私",
                    "suggestions": "建议限制访问权限，仅授权人员可查看"
                },
                {
                    "field_id": "f008",
                    "field_name": "bank_card",
                    "sensitive_type": "财务信息",
                    "sensitive_level": "HIGH",
                    "detection_reason": "银行卡号属于高度敏感的财务信息",
                    "suggestions": "建议进行脱敏处理（如显示后4位），加密存储，严格控制访问权限",
                    "regex_pattern": "^\\d{16,19}$",
                    "regex_description": "匹配16-19位银行卡号"
                }
            ],
            "non_sensitive_fields": [
                {"field_id": "f006", "field_name": "order_id"}
            ],
            "summary": {"total_fields": 3, "sensitive_count": 2, "high_risk_count": 1, "medium_risk_count": 1, "low_risk_count": 0}
        }
    ],
    "summary": {"total_tables": 2, "total_fields": 8, "total_sensitive_fields": 5, "high_risk_fields": 2, "medium_risk_fields": 3, "low_risk_fields": 0}
}
```

## 用户输入
```json
{{input_data}}
```

输出检测结果（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class SensitiveDataDetectPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
