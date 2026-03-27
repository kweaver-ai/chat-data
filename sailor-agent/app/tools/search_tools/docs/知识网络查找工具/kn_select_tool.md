# 知识网络选择工具
根据用户的问题或者表，然后在知识网络列表中，找到合适的知识网络，以便后续的问数功能


## 匹配逻辑
1. 用户输入的参数，如果输入了表，那就优先表匹配，如果没有表就进行问题匹配，都没有则报参数错误
2. 若入参提供 **kn_ids**（知识网络ID数组）且非空：**不调用知识网络列表接口**，仅将这些 ID 作为候选，在其上继续做对象类型拉取与表/问题匹配；未提供或为空时仍拉取全量知识网络列表（含缓存）
3. 表匹配使用id和知识网络对象里面的data_source.id比较，相等则匹配上
4. 如果是表匹配，有50%以上的表匹配就算匹配上了，选择匹配最多的网络返回，只要一个即可
5. 问题匹配使用一个或多个知识网络的名称、tags、comment，对象类的匹配信息等和用户问题输入大模型，让大模型得出匹配的知识网络 
6. 返回关联的知识网络 **kn_id** 与 **kn_name**（名称以详情接口合并结果为准，问题匹配时优先采用服务端名称），最好是只返回一个。可以是多个但是必须是都相关，没结果，返回空ID字符串

### 统计与名称（知识网络信息接口）
对每个候选知识网络调用 **知识网络信息** 接口（`include_statistics=true`），合并 `name`、`tags`、`comment`、`statistics`。若 **`statistics.object_types_total` 为 0**，则**过滤掉**该网络（接口失败或未返回 `statistics` 时不据此过滤）。`kn_ids` 模式下依赖本步补全 **kn_name**。

### 对象类的匹配信息
使用'知识网络对象'接口查询，该接口的limit请传最大值1000，如果该接口的entries中没有module_type=object_type那就过滤掉该知识网络。
1. name
2. data_properties.display_name
3. data_properties.type

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
  ],
  "kn_ids": ["知识网络ID1", "知识网络ID2"]
}
```

- **kn_ids**（可选）：字符串数组。非空时不请求知识网络列表，只在这些 ID 上执行后续逻辑（对象类型接口、表匹配、问题匹配）。

## 输出参数
```
[{
  "kn_id": "知识网络ID",
  "kn_name": "知识网络名称"
}]
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


### 知识网络信息
```
kubenetes services: bkn-backend-svc:13014
header:  x-business-domain:bd_public
GET https://10.4.134.26/api/ontology-manager/v1/knowledge-networks/d70k1i5egmr904lu1lvg?include_detail=false&include_statistics=true
response:
{
    "id": "d70k1i5egmr904lu1lvg",
    "name": "动态计划协同V6",
    "tags": [],
    "comment": "供应链计划协同知识网络，实现从产品需求预测到生产工单的全链路跟踪",
    "icon": "icon-dip-graph",
    "color": "#0e5fc5",
    "detail": "",
    "branch": "main",
    "business_domain": "bd_public",
    "creator": {
        "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
        "type": "user",
        "name": "liberly"
    },
    "create_time": 1774272712147,
    "updater": {
        "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
        "type": "user",
        "name": "liberly"
    },
    "update_time": 1774272712147,
    "module_type": "knowledge_network",
    "statistics": {
        "concept_groups_total": 0,
        "object_types_total": 12,
        "relation_types_total": 13,
        "action_types_total": 0
    },
    "operations": [
        "export",
        "modify",
        "delete",
        "create",
        "data_query",
        "authorize",
        "task_manage",
        "view_detail",
        "import"
    ]
}
```

### 知识网络列表接口
```
kubenetes services: bkn-backend-svc:13014
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
kubenetes services: bkn-backend-svc:13014
GET https://10.4.134.26/api/ontology-manager/v1/knowledge-networks/{kn_id}/object-types?offset=0&limit=5
response:
{
    "entries": [
        {
            "id": "d6u0vj46vfkhfektv71g",
            "name": "物料",
            "data_source": {
                "type": "data_view",
                "id": "2014535573594247171",
                "name": "物料信息"
            },
            "data_properties": [
                {
                    "name": "materialCode",
                    "display_name": "物料编码",
                    "type": "string",
                    "comment": ""
                }
            ],
            "primary_keys": [
                "materialCode"
            ],
            "display_key": "materialCode",
            "incremental_key": "",
            "tags": [],
            "comment": "物料",
            "icon": "icon-dip-graph",
            "color": "#0e5fc5",
            "detail": "",
            "kn_id": "d6u0v246vfkhfektv6gg",
            "branch": "main",
            "status": {
                "incremental_key": "",
                "incremental_value": "",
                "index": "",
                "index_available": false,
                "doc_count": 0,
                "storage_size": 0,
                "update_time": 1773933147772
            },
            "creator": {
                "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
                "type": "user",
                "name": "liberly"
            },
            "create_time": 1773932492829,
            "updater": {
                "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
                "type": "user",
                "name": "liberly"
            },
            "update_time": 1773933147772,
            "module_type": "object_type"
        },
    ],
    "total_count": 14
}
```








