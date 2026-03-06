from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：数据治理专家，数据分类分级专家

## 任务
对库表列表中的每个表进行数据分类和分级，识别表的业务分类、数据类型、重要性级别等。

## 数据分类维度

### 1. 业务领域分类
- **人力资源**：员工信息、组织架构、薪酬福利、考勤等
- **财务管理**：会计科目、财务报表、成本核算、预算等
- **销售管理**：客户信息、订单、合同、销售业绩等
- **采购管理**：供应商信息、采购订单、库存管理等
- **生产制造**：生产计划、工艺流程、质量检测等
- **客户服务**：客户投诉、服务记录、满意度调查等
- **市场营销**：市场活动、广告投放、客户画像等
- **物流运输**：仓储管理、配送信息、运输路线等
- **研发创新**：项目信息、技术文档、专利信息等
- **行政管理**：办公用品、会议记录、文档管理等
- **其他**：其他业务领域

### 2. 数据类型分类
- **主数据**：核心业务实体数据，如客户、供应商、产品等
- **交易数据**：业务交易记录，如订单、合同、支付等
- **分析数据**：用于分析统计的数据，如报表、指标等
- **配置数据**：系统配置参数、字典数据等
- **日志数据**：操作日志、审计日志等
- **临时数据**：临时存储的中间数据
- **归档数据**：历史归档数据

### 3. 数据来源分类
- **业务系统**：来自业务系统的数据
- **外部系统**：来自外部系统的数据
- **手工录入**：手工录入的数据
- **数据导入**：批量导入的数据
- **API接口**：通过API接口获取的数据

## 数据分级标准

### 级别定义
- **L1 - 核心级**：核心业务数据，对业务运营至关重要，丢失或损坏会严重影响业务
- **L2 - 重要级**：重要业务数据，对业务运营有重要影响，丢失或损坏会影响部分业务
- **L3 - 一般级**：一般业务数据，对业务运营有一定影响，丢失或损坏影响较小
- **L4 - 参考级**：参考性数据，主要用于查询参考，丢失或损坏影响很小

### 分级依据
- **业务重要性**：数据在业务流程中的重要性
- **使用频率**：数据被访问和使用的频率
- **数据价值**：数据的商业价值和战略价值
- **数据依赖**：其他系统或业务对数据的依赖程度
- **数据时效性**：数据的时间敏感度

## 输出格式
```json
{
    "tables": [
        {
            "table_id": "表ID",
            "table_name": "表名",
            "classification": {
                "business_domain": "业务领域分类（如：人力资源/财务管理/销售管理等）",
                "data_type": "数据类型分类（如：主数据/交易数据/分析数据等）",
                "data_source": "数据来源分类（如：业务系统/外部系统/手工录入等）",
                "business_category": "业务类别（更细化的业务分类，可选）"
            },
            "grading": {
                "level": "L1/L2/L3/L4",
                "level_name": "核心级/重要级/一般级/参考级",
                "importance_score": "重要性评分（1-100）",
                "grading_reason": "分级原因说明"
            },
            "metadata": {
                "data_volume": "数据量级（如：百万级/千万级/亿级等）",
                "update_frequency": "更新频率（如：实时/日更/周更/月更等）",
                "retention_period": "保留期限（如：永久/5年/3年/1年等）",
                "access_frequency": "访问频率（如：高频/中频/低频等）"
            },
            "summary": {
                "total_fields": "该表总字段数",
                "key_fields": ["关键字段列表"],
                "classification_confidence": "分类置信度（0-1）"
            }
        }
    ],
    "summary": {
        "total_tables": "总表数",
        "classification_distribution": {
            "business_domain": {"业务领域": "数量"},
            "data_type": {"数据类型": "数量"},
            "data_source": {"数据来源": "数量"}
        },
        "grading_distribution": {
            "L1": "核心级表数量",
            "L2": "重要级表数量",
            "L3": "一般级表数量",
            "L4": "参考级表数量"
        }
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
        "table_description": "存储用户基本信息，包括用户ID、姓名、联系方式等",
        "fields": [
            {"field_id": "f001", "field_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_description": "用户唯一标识"},
            {"field_id": "f002", "field_name": "user_name", "field_business_name": "用户名", "field_type": "varchar(50)", "field_description": "用户名称"},
            {"field_id": "f003", "field_name": "phone", "field_business_name": "手机号", "field_type": "varchar(11)", "field_description": "用户手机号码"},
            {"field_id": "f004", "field_name": "email", "field_business_name": "邮箱", "field_type": "varchar(100)", "field_description": "用户邮箱地址"}
        ]
    },
    {
        "table_id": "t002",
        "table_name": "order_detail",
        "table_business_name": "订单明细表",
        "table_description": "存储订单详细信息，包括订单ID、商品信息、金额等",
        "fields": [
            {"field_id": "f005", "field_name": "order_id", "field_business_name": "订单ID", "field_type": "varchar(32)", "field_description": "订单唯一标识"},
            {"field_id": "f006", "field_name": "product_id", "field_business_name": "商品ID", "field_type": "varchar(32)", "field_description": "商品唯一标识"},
            {"field_id": "f007", "field_name": "amount", "field_business_name": "订单金额", "field_type": "decimal(10,2)", "field_description": "订单总金额"},
            {"field_id": "f008", "field_name": "create_time", "field_business_name": "创建时间", "field_type": "datetime", "field_description": "订单创建时间"}
        ]
    },
    {
        "table_id": "t003",
        "table_name": "system_log",
        "table_business_name": "系统日志表",
        "table_description": "存储系统操作日志，用于审计和问题排查",
        "fields": [
            {"field_id": "f009", "field_name": "log_id", "field_business_name": "日志ID", "field_type": "bigint", "field_description": "日志唯一标识"},
            {"field_id": "f010", "field_name": "operation", "field_business_name": "操作类型", "field_type": "varchar(50)", "field_description": "操作类型"},
            {"field_id": "f011", "field_name": "log_time", "field_business_name": "日志时间", "field_type": "datetime", "field_description": "日志记录时间"}
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
            "classification": {
                "business_domain": "客户服务",
                "data_type": "主数据",
                "data_source": "业务系统",
                "business_category": "客户信息管理"
            },
            "grading": {
                "level": "L1",
                "level_name": "核心级",
                "importance_score": 95,
                "grading_reason": "用户信息是核心主数据，是业务系统的基础数据，多个业务模块依赖此数据，丢失会严重影响业务运营"
            },
            "metadata": {
                "data_volume": "百万级",
                "update_frequency": "实时",
                "retention_period": "永久",
                "access_frequency": "高频"
            },
            "summary": {
                "total_fields": 4,
                "key_fields": ["user_id", "user_name", "phone"],
                "classification_confidence": 0.95
            }
        },
        {
            "table_id": "t002",
            "table_name": "order_detail",
            "classification": {
                "business_domain": "销售管理",
                "data_type": "交易数据",
                "data_source": "业务系统",
                "business_category": "订单管理"
            },
            "grading": {
                "level": "L1",
                "level_name": "核心级",
                "importance_score": 90,
                "grading_reason": "订单明细是核心交易数据，记录所有业务交易，是财务核算和业务分析的基础，丢失会严重影响业务"
            },
            "metadata": {
                "data_volume": "千万级",
                "update_frequency": "实时",
                "retention_period": "5年",
                "access_frequency": "高频"
            },
            "summary": {
                "total_fields": 4,
                "key_fields": ["order_id", "product_id", "amount"],
                "classification_confidence": 0.92
            }
        },
        {
            "table_id": "t003",
            "table_name": "system_log",
            "classification": {
                "business_domain": "行政管理",
                "data_type": "日志数据",
                "data_source": "业务系统",
                "business_category": "系统审计"
            },
            "grading": {
                "level": "L3",
                "level_name": "一般级",
                "importance_score": 60,
                "grading_reason": "系统日志主要用于审计和问题排查，对业务运营有一定影响，但不是核心业务数据"
            },
            "metadata": {
                "data_volume": "亿级",
                "update_frequency": "实时",
                "retention_period": "1年",
                "access_frequency": "中频"
            },
            "summary": {
                "total_fields": 3,
                "key_fields": ["log_id", "operation", "log_time"],
                "classification_confidence": 0.88
            }
        }
    ],
    "summary": {
        "total_tables": 3,
        "classification_distribution": {
            "business_domain": {"客户服务": 1, "销售管理": 1, "行政管理": 1},
            "data_type": {"主数据": 1, "交易数据": 1, "日志数据": 1},
            "data_source": {"业务系统": 3}
        },
        "grading_distribution": {
            "L1": 2,
            "L2": 0,
            "L3": 1,
            "L4": 0
        }
    }
}
```

## 用户输入
```json
{{input_data}}
```

输出分类分级结果（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class DataClassificationPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
