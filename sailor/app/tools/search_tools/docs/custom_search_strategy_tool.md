# 用户自定义搜索策略工具
1. 文件名：app/tools/search_tools/custom_search_strategy_tool.py
2. 依赖的http函数全部都写在app/api/af_api.py中
3. 新的kubenetes service服务配置全部在config.py中添加获取

## 功能描述
强制性意图，可以根据用户的输入的问题，找出可能匹配的自定义搜索策略，然后将结果保存到缓存中，返回缓存的key，供下个工具使用
下个工具会根据缓存的key，获取缓存的数据，然后实现相应的功能


## 术语
解释下流程中用到的术语的定义，方便理解

### 规则库
术语库，规则库，每个规则库可以包含很多规则，可以通过规则库列表接口查询到

### 规则
规则库的下面key/value的value,其中value才是规则的具体内容


### 优先表缓存
内容：优先表ID，标记该资源类型时表的type=data_view, 还有规则库名称，规则的key和value，
key的格式："{tool_name}/rules/{rule_base_id}/{rule_id}"
缓存时间：24小时


### 优先表
如果用户的输入命中了某规则，该规则规定的表应该排在结果列表的第一位，不过该排序不用本工具实现，本工具只负责找到这个表的ID

### 数据源
各种各样的业务数据库，mysql, mariadb用户可能接入了很多的数据源

## 流程
1. 参数是用户输入的问题， 还有就是规则库的名称，可以不填，不填就设置默认的值"自定义规则库"
2. 根据规则库的名称，查询规则库的所有键值对，这些键值对就是规则。
3. 将所有的规则组成数组，结合用户输入，让大模型判断命中了哪个规则,、优先表所在的名称和所在的数据源的名称。
4. 如果没有命中规则，结束。如果命中了规则，根据规则和规则名称找到优先表缓存， 判断数据正确后返回优先表缓存key
5. 如果没有，调用下面的优先表缓存规则方法，详情参考下面的："优先表详情的缓存规则"


## 优先表缓存规则
提供查询优先表的功能

### 缓存策略
1. 如果缓存中没有，那么就调用下面的初始化策略，如果缓存有并且数据合法，那就返回该缓存的key

### 初始化策略
1. 参数是数据源名称和表的名称，数据源名称非必填
2. 根据数据源列表接口，遍历数据源结果，和传入数据源名称一样的就是命中的数据源
3. 根据视图列表接口，传入数据源ID和表的中文名称，查询到的第一个表为优先表
4. 将优先表的UUID拿出来，然后结合规则，组成优先表缓存保存到redis中去


## 依赖
下面的http方法写在app/api/af_api.py里面，如果有新的kubenetes service的配置，要写在config.py里面\

### 查缓存
参考app\tools\search_tools\datasource_filter_v2.py的202行


### 大模型
参考：app\tools\search_tools\data_view_explore_tool.py的394行


### 规则库列表
```
kubenetes service: mdl-data-model-svc:13020
GET https://10.4.134.26/api/mdl-data-model/v1/data-dicts?name_pattern
response: 
{
  "entries": [
    {
      "comment": "",
      "create_time": 1770011103899,
      "dimension": {
        "keys": [
          {
            "id": "item_key",
            "name": "key"
          }
        ],
        "values": [
          {
            "id": "item_value",
            "name": "value"
          }
        ]
      },
      "id": "d603jnuavnnd8il5gltg",
      "items": null,
      "name": "自定义搜索策略-主推表策略",
      "operations": [
        "authorize",
        "view_detail",
        "create",
        "import",
        "export",
        "modify",
        "delete"
      ],
      "tags": [],
      "type": "kv_dict",
      "unique_key": true,
      "update_time": 1770011717116
    }
  ],
  "total_count": 1
}
```


### 视图列表接口
```
kubenetes services: data-view:8123
GET https://10.4.134.26/api/data-view/v1/form-view?type=datasource&include_sub_department=true&keyword=table_name&datasource_id=bd26ec8b-545f-4c52-8ce9-8b6c21d667b6
response:
{
  "entries": [
    {
      "apply_num": 0,
      "audit_advice": "",
      "business_name": "城镇居民人均可支配收入表（2022年）",
      "catalog_provider": "",
      "created_at": 1769059241509,
      "created_by": "liberly",
      "data_catalog_id": "",
      "data_catalog_name": "",
      "data_origin_form_id": "",
      "database_name": "bigdata_open_analysis_dm",
      "datasource": "市大数据中心",
      "datasource_catalog_name": "maria_pgrrqehi",
      "datasource_id": "b067ad44-ac31-4338-96b9-47b820d64008",
      "datasource_type": "maria",
      "department": "统计局",
      "department_id": "cc6bf4f2-f787-11f0-84c6-aea245f5b9d4",
      "department_path": "市大数据中心/统计局",
      "edit_status": "latest",
      "excel_file_name": "",
      "explore_job_id": "604217341428899252",
      "explore_job_version": 1,
      "explored_classification": 0,
      "explored_data": 1,
      "explored_timestamp": 0,
      "field_count": 0,
      "has_dwh_data_auth_req_form": false,
      "id": "c445f4d5-71e5-4617-8ccc-79ecd34b8bed",
      "metadata_form_id": "",
      "online_status": "notline",
      "online_time": 0,
      "original_name": "stjj_czjmrjkzpsr2022n",
      "owners": [
        {
          "owner_id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
          "owner_name": "liberly"
        }
      ],
      "publish_at": 1769341043472,
      "scene_analysis_id": "",
      "source_sign": 0,
      "status": "new",
      "subject": "未分组",
      "subject_id": "80caec87-eba6-4f18-a967-44fb922ea344",
      "subject_path": "IDRM/未分组",
      "subject_path_id": "c76f6f81-5829-4663-8fb1-67e4d5608bbb/80caec87-eba6-4f18-a967-44fb922ea344",
      "technical_name": "stjj_czjmrjkzpsr2022n",
      "type": "datasource",
      "uniform_catalog_code": "SJKB20260122/001808",
      "updated_at": 1770109828821,
      "updated_by": "liberly",
      "view_source_catalog_name": "maria_pgrrqehi.bigdata_open_analysis_dm"
    }
  ],
  "explore_time": 1769671199824,
  "total_count": 1
}
```


### 查所有的数据源
```
kubenetes service: data-view:8123
GET https://10.4.134.26/api/data-view/v1/datasource?limit=1000&direction=desc&sort=updated_at&_t=1770100904507
response:
{
    "entries": [
        {
            "data_source_id": 604834939136908800,
            "id": "dda82373-5cd4-4343-aa45-f5b305ea84ac",
            "info_system_id": "",
            "name": "三定职责",
            "catalog_name": "maria_d5zivfhe",
            "type": "maria",
            "host": "",
            "port": 0,
            "username": "",
            "database_name": "biz_knowledge_network",
            "schema": "",
            "created_at": 1770039316961,
            "updated_at": 1770039316952,
            "status": 0
        }
    ]
}
```