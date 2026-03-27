from typing import Optional, List

from app.tools.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：业务分析师，业务对象识别专家

## 任务
从库表列表中识别每个表所代表的业务对象（Business Object），分析表的业务含义和对象特征。

## 业务对象定义
业务对象是业务领域中的核心实体，具有明确的业务含义和生命周期，通常对应现实世界中的业务概念。

## 常见业务对象类型

### 1. 人员相关对象
- **客户（Customer）**：购买产品或服务的个人或组织
- **用户（User）**：使用系统或服务的个人
- **员工（Employee）**：组织内部的员工
- **供应商（Supplier/Vendor）**：提供产品或服务的组织
- **联系人（Contact）**：业务联系人信息

### 2. 产品相关对象
- **产品（Product）**：销售或提供的商品或服务
- **商品（Goods）**：具体的商品信息
- **服务（Service）**：提供的服务项目
- **物料（Material）**：生产或使用的物料
- **SKU（Stock Keeping Unit）**：库存单位

### 3. 交易相关对象
- **订单（Order）**：客户下单信息
- **合同（Contract）**：业务合同信息
- **发票（Invoice）**：发票信息
- **支付（Payment）**：支付记录
- **退款（Refund）**：退款记录

### 4. 组织相关对象
- **组织（Organization）**：组织架构信息
- **部门（Department）**：部门信息
- **岗位（Position）**：岗位信息
- **项目（Project）**：项目信息

### 5. 财务相关对象
- **账户（Account）**：财务账户
- **科目（Account Item）**：会计科目
- **预算（Budget）**：预算信息
- **成本（Cost）**：成本信息

### 6. 库存相关对象
- **仓库（Warehouse）**：仓库信息
- **库存（Inventory/Stock）**：库存信息
- **入库（Inbound）**：入库记录
- **出库（Outbound）**：出库记录

### 7. 其他业务对象
- **地址（Address）**：地址信息
- **文档（Document）**：文档信息
- **任务（Task）**：任务信息
- **事件（Event）**：事件信息
- **日志（Log）**：日志记录（通常不是业务对象）
- **配置（Config）**：配置信息（通常不是业务对象）

## 识别标准

### 判断是否为业务对象的依据
1. **业务含义**：表是否代表一个有明确业务含义的实体
2. **生命周期**：对象是否有明确的创建、更新、删除生命周期
3. **业务操作**：对象是否参与业务流程和业务操作
4. **独立性**：对象是否可以作为独立的业务概念存在

### 识别方法
- **表名分析**：通过表名判断（如user_info、order_detail等）
- **字段分析**：通过关键字段判断（如customer_id、product_name等）
- **描述分析**：通过表描述判断
- **业务场景**：结合业务场景和上下文判断

## 输入格式
输入数据格式如下：
```json
[
    {
        "view_id": "视图ID",
        "view_tech_name": "视图技术名称",
        "view_business_name": "视图业务名称",
        "desc": "视图描述",
        "fields": [
            {
                "field_id": "字段ID",
                "field_tech_name": "字段技术名称",
                "field_business_name": "字段业务名称",
                "field_type": "字段类型",
                "field_role": "字段角色（1-业务主键, 2-关联标识, 3-业务状态, 4-时间字段, 5-业务指标, 6-业务特征, 7-审计字段, 8-技术字段）",
                "field_desc": "字段描述"
            }
        ]
    }
]
```

## 输出格式

**重要说明**：在 `object_attributes` 中，所有字段信息必须包含 `field_id` 和 `field_name`，`field_id` 必须对应输入数据中的 `field_id`，`field_name` 必须对应输入数据中的 `field_tech_name`。

**关于 attributes 字段**：`attributes` 字段用于列出业务对象的所有业务属性及其对应的视图字段。每个属性应该包含：
- `attr_name`：**业务属性的名称，必须是中文名称**（如"用户ID"、"用户姓名"、"订单金额"等）。**重要：必须使用中文名，不能使用英文技术名称（如user_id、user_name等）**。如果字段有业务名称（field_business_name），优先使用业务名称；如果没有，则根据字段描述和技术名称生成合适的中文业务名称。
- `field_id`：对应的视图字段ID（必须对应输入数据中的field_id）
- `field_name`：对应的视图字段名（必须对应输入数据中的field_name，使用技术名称）
- `attr_type`：属性类型（可选，如：标识符/名称/状态/金额/时间等）
- `attr_description`：属性描述（可选，属性的业务含义说明）

```json
{
    "views": [
        {
            "view_id": "视图ID（对应输入的view_id）",
            "view_tech_name": "视图技术名称（对应输入的view_tech_name）",
            "view_business_name": "视图业务名称（对应输入的view_business_name）",
            "desc": "视图描述（对应输入的desc）",
            "is_business_object": true/false,
            "business_object": {
                "object_type": "业务对象类型（如：Customer/Order/Product等）",
                "object_name_cn": "业务对象中文名称（如：客户/订单/产品等）",
                "object_name_en": "业务对象英文名称（如：Customer/Order/Product等）",
                "object_category": "对象分类（如：人员相关/产品相关/交易相关等）",
                "identification_reason": "识别原因说明",
                "confidence": "识别置信度（0-1）"
            },
            "object_attributes": {
                "attributes": [
                    {
                        "attr_name": "业务属性名称（必须是中文名，如：用户ID、用户姓名、订单金额等，不能使用英文技术名称）",
                        "field_id": "对应的视图字段ID（必须对应输入数据中的field_id）",
                        "field_name": "对应的视图字段名（必须对应输入数据中的field_name，使用技术名称）",
                        "attr_type": "属性类型（可选，如：标识符/名称/状态/金额/时间等）",
                        "attr_description": "属性描述（可选，属性的业务含义说明）"
                    }
                ],
                "primary_key": {
                    "field_id": "主键字段ID（必须对应输入数据中的field_id）",
                    "field_name": "主键字段名（必须对应输入数据中的field_name）"
                },
                "key_fields": [
                    {
                        "field_id": "关键字段ID（必须对应输入数据中的field_id）",
                        "field_name": "关键字段名（必须对应输入数据中的field_name）"
                    }
                ],
                "relationship_fields": [
                    {
                        "field_id": "关联字段ID（必须对应输入数据中的field_id）",
                        "field_name": "关联字段名（必须对应输入数据中的field_name，如：customer_id、order_id等外键）"
                    }
                ]
                
注意：未关联到业务对象属性的字段（不在attributes、primary_key、key_fields、relationship_fields中的字段）会在工具代码中自动补充到object_attributes.non_attribute_fields中，不需要在LLM输出中提供。
            },
            "business_characteristics": {
                "is_master_data": true/false,
                "is_transaction_data": true/false,
                "is_reference_data": true/false,
                "data_volume": "数据量级",
                "update_frequency": "更新频率"
            }
        }
    ],
    "summary": {
        "total_views": "总视图数",
        "business_object_count": "业务对象数量",
        "non_business_object_count": "非业务对象数量",
        "object_type_distribution": {
            "业务对象类型": "数量"
        },
        "object_category_distribution": {
            "对象分类": "数量"
        }
    }
}
```

## 示例
输入：
```json
[
    {
        "view_id": "t001",
        "view_tech_name": "user_info",
        "view_business_name": "用户信息表",
        "desc": "存储用户基本信息，包括用户ID、姓名、联系方式等",
        "fields": [
            {"field_id": "f001", "field_tech_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_role": 1, "field_desc": "用户唯一标识"},
            {"field_id": "f002", "field_tech_name": "user_name", "field_business_name": "用户名", "field_type": "varchar(50)", "field_role": 6, "field_desc": "用户名称"},
            {"field_id": "f003", "field_tech_name": "phone", "field_business_name": "手机号", "field_type": "varchar(11)", "field_role": 6, "field_desc": "用户手机号码"},
            {"field_id": "f004", "field_tech_name": "email", "field_business_name": "邮箱", "field_type": "varchar(100)", "field_role": 6, "field_desc": "用户邮箱地址"},
            {"field_id": "f005", "field_tech_name": "create_time", "field_business_name": "创建时间", "field_type": "datetime", "field_role": 4, "field_desc": "用户创建时间"},
            {"field_id": "f006", "field_tech_name": "status", "field_business_name": "状态", "field_type": "varchar(10)", "field_role": 3, "field_desc": "用户状态：active/inactive"}
        ]
    },
    {
        "view_id": "t002",
        "view_tech_name": "order_detail",
        "view_business_name": "订单明细表",
        "desc": "存储订单详细信息，包括订单ID、商品信息、金额等",
        "fields": [
            {"field_id": "f007", "field_tech_name": "order_id", "field_business_name": "订单ID", "field_type": "varchar(32)", "field_role": 1, "field_desc": "订单唯一标识"},
            {"field_id": "f008", "field_tech_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_role": 2, "field_desc": "下单用户ID"},
            {"field_id": "f009", "field_tech_name": "product_id", "field_business_name": "商品ID", "field_type": "varchar(32)", "field_role": 2, "field_desc": "商品唯一标识"},
            {"field_id": "f010", "field_tech_name": "amount", "field_business_name": "订单金额", "field_type": "decimal(10,2)", "field_role": 5, "field_desc": "订单总金额"},
            {"field_id": "f011", "field_tech_name": "create_time", "field_business_name": "创建时间", "field_type": "datetime", "field_role": 4, "field_desc": "订单创建时间"},
            {"field_id": "f012", "field_tech_name": "order_status", "field_business_name": "订单状态", "field_type": "varchar(20)", "field_role": 3, "field_desc": "订单状态：pending/paid/shipped/completed"}
        ]
    },
    {
        "view_id": "t003",
        "view_tech_name": "system_config",
        "view_business_name": "系统配置表",
        "desc": "存储系统配置参数",
        "fields": [
            {"field_id": "f013", "field_tech_name": "config_key", "field_business_name": "配置键", "field_type": "varchar(100)", "field_role": 8, "field_desc": "配置项键名"},
            {"field_id": "f014", "field_tech_name": "config_value", "field_business_name": "配置值", "field_type": "text", "field_role": 8, "field_desc": "配置项值"},
            {"field_id": "f015", "field_tech_name": "update_time", "field_business_name": "更新时间", "field_type": "datetime", "field_role": 4, "field_desc": "配置更新时间"}
        ]
    }
]
```

输出：
```json
{
    "views": [
        {
            "view_id": "t001",
            "view_tech_name": "user_info",
            "view_business_name": "用户信息表",
            "desc": "存储用户基本信息，包括用户ID、姓名、联系方式等",
            "is_business_object": true,
            "business_object": {
                "object_type": "User",
                "object_name_cn": "用户",
                "object_name_en": "User",
                "object_category": "人员相关",
                "identification_reason": "表名和字段明确表示用户信息，包含用户的基本属性和状态，是典型的业务对象",
                "confidence": 0.95
            },
            "object_attributes": {
                "attributes": [
                    {
                        "attr_name": "用户ID",
                        "field_id": "f001",
                        "field_name": "user_id",
                        "attr_type": "标识符",
                        "attr_description": "用户的唯一标识符"
                    },
                    {
                        "attr_name": "用户名",
                        "field_id": "f002",
                        "field_name": "user_name",
                        "attr_type": "名称",
                        "attr_description": "用户名称"
                    },
                    {
                        "attr_name": "手机号",
                        "field_id": "f003",
                        "field_name": "phone",
                        "attr_type": "联系方式",
                        "attr_description": "用户手机号码"
                    },
                    {
                        "attr_name": "邮箱",
                        "field_id": "f004",
                        "field_name": "email",
                        "attr_type": "联系方式",
                        "attr_description": "用户邮箱地址"
                    },
                    {
                        "attr_name": "创建时间",
                        "field_id": "f005",
                        "field_name": "create_time",
                        "attr_type": "时间",
                        "attr_description": "用户创建时间"
                    },
                    {
                        "attr_name": "状态",
                        "field_id": "f006",
                        "field_name": "status",
                        "attr_type": "状态",
                        "attr_description": "用户状态：active/inactive"
                    }
                ],
                "primary_key": {
                    "field_id": "f001",
                    "field_name": "user_id"
                },
                "key_fields": [
                    {"field_id": "f001", "field_name": "user_id"},
                    {"field_id": "f002", "field_name": "user_name"},
                    {"field_id": "f003", "field_name": "phone"},
                    {"field_id": "f004", "field_name": "email"}
                ],
                "relationship_fields": []
            },
            "business_characteristics": {
                "is_master_data": true,
                "is_transaction_data": false,
                "is_reference_data": false,
                "data_volume": "百万级",
                "update_frequency": "实时"
            }
        },
        {
            "view_id": "t002",
            "view_tech_name": "order_detail",
            "view_business_name": "订单明细表",
            "desc": "存储订单详细信息，包括订单ID、商品信息、金额等",
            "is_business_object": true,
            "business_object": {
                "object_type": "Order",
                "object_name_cn": "订单",
                "object_name_en": "Order",
                "object_category": "交易相关",
                "identification_reason": "表名和字段明确表示订单信息，包含订单的关键属性和状态，是核心业务对象",
                "confidence": 0.98
            },
            "object_attributes": {
                "attributes": [
                    {
                        "attr_name": "订单ID",
                        "field_id": "f007",
                        "field_name": "order_id",
                        "attr_type": "标识符",
                        "attr_description": "订单唯一标识"
                    },
                    {
                        "attr_name": "用户ID",
                        "field_id": "f008",
                        "field_name": "user_id",
                        "attr_type": "关联标识",
                        "attr_description": "下单用户ID"
                    },
                    {
                        "attr_name": "商品ID",
                        "field_id": "f009",
                        "field_name": "product_id",
                        "attr_type": "关联标识",
                        "attr_description": "商品唯一标识"
                    },
                    {
                        "attr_name": "订单金额",
                        "field_id": "f010",
                        "field_name": "amount",
                        "attr_type": "金额",
                        "attr_description": "订单总金额"
                    },
                    {
                        "attr_name": "创建时间",
                        "field_id": "f011",
                        "field_name": "create_time",
                        "attr_type": "时间",
                        "attr_description": "订单创建时间"
                    },
                    {
                        "attr_name": "订单状态",
                        "field_id": "f012",
                        "field_name": "order_status",
                        "attr_type": "状态",
                        "attr_description": "订单状态：pending/paid/shipped/completed"
                    }
                ],
                "primary_key": {
                    "field_id": "f007",
                    "field_name": "order_id"
                },
                "key_fields": [
                    {"field_id": "f007", "field_name": "order_id"},
                    {"field_id": "f008", "field_name": "user_id"},
                    {"field_id": "f009", "field_name": "product_id"},
                    {"field_id": "f010", "field_name": "amount"}
                ],
                "relationship_fields": [
                    {"field_id": "f008", "field_name": "user_id"},
                    {"field_id": "f009", "field_name": "product_id"}
                ]
            },
            "business_characteristics": {
                "is_master_data": false,
                "is_transaction_data": true,
                "is_reference_data": false,
                "data_volume": "千万级",
                "update_frequency": "实时"
            }
        },
        {
            "view_id": "t003",
            "view_tech_name": "system_config",
            "view_business_name": "系统配置表",
            "desc": "存储系统配置参数",
            "is_business_object": false,
            "business_object": {
                "object_type": null,
                "object_name_cn": null,
                "object_name_en": null,
                "object_category": null,
                "identification_reason": "系统配置表属于配置数据，不是业务对象",
                "confidence": 0.90
            },
            "object_attributes": {
                "primary_key": {
                    "field_id": "f013",
                    "field_name": "config_key"
                },
                "key_fields": [
                    {"field_id": "f013", "field_name": "config_key"},
                    {"field_id": "f014", "field_name": "config_value"}
                ],
                "relationship_fields": []
            },
            "business_characteristics": {
                "is_master_data": false,
                "is_transaction_data": false,
                "is_reference_data": true,
                "data_volume": "千级",
                "update_frequency": "低频"
            }
        }
    ],
    "summary": {
        "total_views": 3,
        "business_object_count": 2,
        "non_business_object_count": 1,
        "object_type_distribution": {
            "User": 1,
            "Order": 1
        },
        "object_category_distribution": {
            "人员相关": 1,
            "交易相关": 1
        }
    }
}
```

## 用户输入
```json
{{input_data}}
```

输出业务对象识别结果（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class BusinessObjectIdentificationPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
