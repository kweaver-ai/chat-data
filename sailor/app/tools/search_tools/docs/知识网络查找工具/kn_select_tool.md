# 知识网络选择工具
根据用户的问题或者表，然后在知识网络列表中，找到合适的知识网络，以便后续的问数功能


## 匹配逻辑
1. 用户输入的参数，如果输入了表，那就优先表匹配，如果没有表就进行问题匹配，都没有则报参数错误
2. 过滤掉对象类数量为0的网络
3. 表匹配使用id和知识网络对象里面的data_source.id比较，相等则匹配上
4. 如果是表匹配，有50%以上的表匹配就算匹配上了，选择匹配最多的网络返回，只要一个即可
5. 问题匹配使用一个或多个知识网络的名称、tags、comment等和用户问题输入大模型，让大模型得出匹配的知识网络 
6. 有结果返回知识网络ID和名称，没结果，返回空ID字符串

## 输入参数
```
{
  "query": "用户输入问题",
  "tables": [
    {
      "id": "视图的id",
      "uuid": "视图的uuid",
      "business_name": "视图的业务名称",
      "technical_name": "视图的技术名称"
    }
  ]
}
```

## 输出参数
```
{
  "kn_id": "知识网络ID",
  "kn_name": "知识网络名称"
}
```


## 缓存策略
将知识网络的信息缓存起来，加速下次访问，所关注的核心逻辑有：
1. 使用哈希结构保存知识网络信息业务对象信息，每个知识网络使用id作为key，value是网络的json对象
2. 整个哈希对象的过期时间是12小时，同时支持接口传参数，主动过期整个hash缓存
3. 当知识网络更新的时候，删除当前hash里面的知识网络对象信息，转而重新查询该知识网络对象信息
4. 支持批量查询，缓存没有查询到的再调用接口，同时缓存到哈希里


## 依赖
下面的http方法写在app/api/adp_api.py里面，如果有新的kubenetes service的配置，要写在config.py里面
1. adp_api.py文件的内容参考同级的af_api.py
2. 新的kubenetes service服务配置全部在config.py中添加获取


### 大模型
参考：app\tools\search_tools\data_view_explore_tool.py的394行

### 知识网络列表接口
```
kubenetes services: ontology-manager-svc:13014
header:  x-business-domain:bd_public
GET https://10.4.134.26/api/ontology-manager/v1/knowledge-networks?offset=0&limit=50&direction=desc&sort=update_time&name_pattern=kn_name
response:
{
    "entries": [
        {
            "id": "d5efgga6746ef0r11g1g",
            "name": "上市公司营收知识网络",
            "tags": [],
            "comment": "",
            "icon": "icon-dip-suanziguanli",
            "color": "#0e5fc5",
            "detail": "{\"network_info\":{\"action_types_count\":0,\"concept_groups_count\":0,\"id\":\"d5efgga6746ef0r11g1g\",\"name\":\"上市公司营收知识网络\",\"tags\":[],\"comment\":\"\",\"object_types_count\":10,\"relation_types_count\":12},\"object_types\":[{\"id\":\"used_name\",\"name\":\"A股上市公司股票曾用名表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"balance\",\"name\":\"负债表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"listedco_freport\",\"name\":\"财务指标表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"top_ten_float_shareholders_info\",\"name\":\"A股上市公司十大流通股东信息表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"top_ten_shareholders_info\",\"name\":\"A股上市公司十大股东信息表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"listed_company_baseinfo\",\"name\":\"A股上市公司基本信息\",\"tags\":[],\"comment\":\"\"},{\"id\":\"income\",\"name\":\"A股上市公司利润表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"fund_holding_info\",\"name\":\"A股上市公司基金持股信息表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"cash_flow\",\"name\":\"A股上市公司现金流量表\",\"tags\":[],\"comment\":\"\"},{\"id\":\"equity_structure_info\",\"name\":\"A股上市公司股本结构信息表\",\"tags\":[],\"comment\":\"\"}],\"relation_types\":[{\"id\":\"baseinfo2top_ten_float_shareholders_info\",\"name\":\"基本信息关联十大流通股东信息\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司十大流通股东信息表\"},{\"id\":\"baseinfo2top_ten_shareholders_info\",\"name\":\"基本信息关联十大股东信息表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司十大股东信息表\"},{\"id\":\"baseinfo2usedname\",\"name\":\"基本信息关联曾用名\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司股票曾用名表\"},{\"id\":\"basic2cash_flow\",\"name\":\"上市公司基本信息关联现金流量表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司现金流量表\"},{\"id\":\"income2balance\",\"name\":\"利润表关联负债表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司利润表\",\"target_object_type_name\":\"负债表\"},{\"id\":\"balance2listedco_freport\",\"name\":\"负债表关联财务指标表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"负债表\",\"target_object_type_name\":\"财务指标表\"},{\"id\":\"baseinfo2fund_holding_info\",\"name\":\"基本信息关联基金持股信息表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司基金持股信息表\"},{\"id\":\"baseinfo2listedco_freport\",\"name\":\"基本信息关联财务指标表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"财务指标表\"},{\"id\":\"income2listedco_freport\",\"name\":\"利润表关联财务指标表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司利润表\",\"target_object_type_name\":\"财务指标表\"},{\"id\":\"baseinfo2balance\",\"name\":\"基本信息关联负债表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"负债表\"},{\"id\":\"baseinfo2equity_structure_info\",\"name\":\"基本信息关联股本结构信息表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司股本结构信息表\"},{\"id\":\"baseinfo2income\",\"name\":\"基本信息关联利润表\",\"tags\":[],\"comment\":\"\",\"source_object_type_name\":\"A股上市公司基本信息\",\"target_object_type_name\":\"A股上市公司利润表\"}],\"action_types\":[],\"concept_groups\":[]}",
            "branch": "main",
            "business_domain": "bd_public",
            "module_type": "knowledge_network"
        }
    ],
    "total_count": 1
}
```

## 知识网络对象
```
kubenetes services: ontology-manager-svc:13014
GET https://10.4.134.26/api/ontology-manager/v1/knowledge-networks/{kn_id}/object-types?offset=0&limit=5
response:
{
    "total_count": 10,
    "entries": [
      {
            "id": "cash_flow",
            "name": "A股上市公司现金流量表",
            "data_source": {
                "type": "data_view",
                "id": "2008493788360966146",
                "name": "A股上市公司现金流量表"
            },
            "data_properties": [
                {
                    "name": "beginning_cash_equivalents",
                    "display_name": "加期初现金及现金等价物余额",
                    "type": "float",
                    "comment": "加：期初现金及现金等价物余额",
                    "mapped_field": {
                        "name": "beginning_cash_equivalents",
                        "type": "float",
                        "display_name": "加期初现金及现金等价物余额"
                    }
                }
            ],
            "primary_keys": [
                "id"
            ],
            "display_key": "security_code",
            "incremental_key": "",
            "tags": [],
            "detail": "",
            "kn_id": "d5efgga6746ef0r11g1g",
            "branch": "main",
            "module_type": "object_type"
        }
    ]
}
```








