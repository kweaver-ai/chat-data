# 知识网络选择工具

## 功能描述

知识网络选择工具用于根据用户的问题或表信息，在知识网络列表中找到最匹配的知识网络，以便后续的问数功能使用。

**文件位置**：`app/tools/search_tools/kn_select_tool.py`

## 核心功能

1. **表匹配模式**：根据提供的表ID列表，匹配包含这些表的知识网络
2. **问题匹配模式**：使用大模型分析用户问题，匹配最相关的知识网络
3. **智能缓存**：使用Redis缓存知识网络信息，提升查询性能
4. **自动过滤**：自动过滤掉对象类数量为0的知识网络

## 匹配逻辑

### 优先级规则

1. **参数验证**：如果 `query` 和 `tables` 都为空，返回错误
2. **匹配优先级**：
   - 如果提供了 `tables`，优先使用表匹配模式
   - 如果没有表或表匹配失败，使用问题匹配模式
3. **过滤规则**：自动过滤掉 `object_types_count` 为 0 的知识网络

### 表匹配逻辑

1. 使用表ID和知识网络对象类型中的 `data_source.id` 进行比较
2. 计算匹配率：`匹配的表数量 / 输入的表数量`
3. 匹配阈值：匹配率 >= 50% 视为匹配成功
4. 选择策略：选择匹配表数量最多的知识网络（只返回一个）

### 问题匹配逻辑

1. 提取知识网络的名称、标签（tags）、描述（comment）等信息
2. 使用大模型分析用户问题与知识网络的关联度
3. 返回最匹配的知识网络ID和名称

## 输入参数

### 请求参数

```json
{
  "query": "用户输入问题（可选，如果提供了tables则优先使用表匹配）",
  "tables": [
    {
      "id": "视图的id（必填）",
      "uuid": "视图的uuid（必填）",
      "business_name": "视图的业务名称（必填）",
      "technical_name": "视图的技术名称（必填）"
    }
  ],
  "force_refresh_cache": false
}
```

### 参数说明

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| query | string | 否 | "" | 用户输入的问题，用于问题匹配模式 |
| tables | array | 否 | [] | 表信息列表，用于表匹配模式 |
| force_refresh_cache | boolean | 否 | false | 是否强制刷新缓存 |

### TableInfo 对象结构

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | string | 是 | 视图的ID，用于匹配知识网络对象类型中的 data_source.id |
| uuid | string | 是 | 视图的UUID |
| business_name | string | 是 | 视图的业务名称 |
| technical_name | string | 是 | 视图的技术名称 |

## 输出参数

### 成功响应

```json
{
  "kn_id": "知识网络ID",
  "kn_name": "知识网络名称"
}
```

### 未匹配响应

```json
{
  "kn_id": "",
  "kn_name": ""
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| kn_id | string | 匹配到的知识网络ID，如果未匹配则为空字符串 |
| kn_name | string | 匹配到的知识网络名称，如果未匹配则为空字符串 |

## 缓存策略

### 缓存结构

1. **知识网络列表缓存**
   - 缓存类型：Redis Hash
   - 缓存Key：`kn_select_tool/knowledge_networks`
   - 存储方式：每个知识网络以 `id` 作为 field，`value` 为完整的知识网络 JSON 对象
   - 过期时间：12小时

2. **知识网络对象类型缓存**
   - 缓存类型：Redis String
   - 缓存Key：`kn_select_tool/object_types/{kn_id}`
   - 存储内容：知识网络的对象类型列表（包含 entries 和 total_count）
   - 过期时间：12小时

### 缓存操作

1. **读取策略**：
   - 优先从缓存读取
   - 缓存未命中时调用接口获取
   - 获取后自动写入缓存

2. **更新策略**：
   - 支持通过 `force_refresh_cache` 参数强制刷新缓存
   - 可以清空整个知识网络列表缓存
   - 可以删除单个知识网络的对象类型缓存
   

3. **容错处理**：
   - 缓存操作失败不影响主流程
   - 支持 Redis 和 InMemory 两种 session 类型
   - 非 Redis session 时自动跳过缓存操作

## 依赖接口

### 1. 知识网络列表接口

**服务**：`ontology-manager-svc:13014`

**接口**：`GET /api/ontology-manager/v1/knowledge-networks`

**请求参数**：
- `offset`: 偏移量（默认：0）
- `limit`: 返回数量限制（默认：50）
- `direction`: 排序方向，asc 或 desc（默认：desc）
- `sort`: 排序字段（默认：update_time）
- `name_pattern`: 名称模式（可选）

**响应示例**：
```json
{
  "entries": [
    {
            "id": "d5dp89i6746ef0r11g00",
            "name": "零售业问数知识网络",
            "tags": [],
            "comment": "",
            "icon": "icon-dip-suanziguanli",
            "color": "#0e5fc5",
            "detail": "{\"network_info\":{\"tags\":[],\"comment\":\"\",\"object_types_count\":1,\"relation_types_count\":0,\"action_types_count\":0,\"concept_groups_count\":0,\"id\":\"d5dp89i6746ef0r11g00\",\"name\":\"零售业问数知识网络\"},\"object_types\":[{\"id\":\"t_sales\",\"name\":\"t_sales\",\"tags\":[],\"comment\":\"\"}],\"relation_types\":[],\"action_types\":[],\"concept_groups\":[]}",
            "branch": "main",
            "business_domain": "bd_public",
            "creator": {
                "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
                "type": "user",
                "name": "liberly"
            },
            "create_time": 1767609382351,
            "updater": {
                "id": "cbf93ec4-ea19-11f0-9c74-c2868d7b6f84",
                "type": "user",
                "name": "liberly"
            },
            "update_time": 1772179018035,
            "module_type": "knowledge_network",
            "operations": [
                "view_detail",
                "modify",
                "delete",
                "task_manage",
                "import",
                "create",
                "data_query",
                "authorize",
                "export"
            ]
        }
  ],
  "total_count": 1
}
```

### 2. 知识网络对象类型接口

**服务**：`ontology-manager-svc:13014`

**接口**：`GET /api/ontology-manager/v1/knowledge-networks/{kn_id}/object-types`

**请求参数**：
- `kn_id`: 知识网络ID（路径参数）
- `offset`: 偏移量（默认：0）
- `limit`: 返回数量限制（默认：1000）

**响应示例**：
```json
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
      "data_properties": [...],
      "primary_keys": ["id"],
      "display_key": "security_code",
      "kn_id": "d5efgga6746ef0r11g1g",
      "branch": "main",
      "module_type": "object_type"
    }
  ]
}
```

## 使用示例

### 示例1：表匹配模式

**请求**：
```json
{
  "tables": [
    {
      "id": "2008493788360966146",
      "uuid": "c445f4d5-71e5-4617-8ccc-79ecd34b8bed",
      "business_name": "A股上市公司现金流量表",
      "technical_name": "cash_flow_table"
    }
  ]
}
```

**响应**：
```json
{
  "kn_id": "d5efgga6746ef0r11g1g",
  "kn_name": "上市公司营收知识网络"
}
```

### 示例2：问题匹配模式

**请求**：
```json
{
  "query": "查询上市公司财务数据"
}
```

**响应**：
```json
{
  "kn_id": "d5efgga6746ef0r11g1g",
  "kn_name": "上市公司营收知识网络"
}
```

### 示例3：强制刷新缓存

**请求**：
```json
{
  "query": "查询上市公司财务数据",
  "force_refresh_cache": true
}
```

## 错误处理

### 参数错误

如果 `query` 和 `tables` 都为空：
```json
{
  "kn_id": "",
  "kn_name": ""
}
```

### 接口错误

如果知识网络列表接口调用失败，会抛出 `ToolFatalError` 异常。

### 缓存错误

缓存操作失败不会影响主流程，会记录警告日志并继续执行。

## 技术实现

### 依赖文件

1. **API 封装**：`app/api/adp_api.py`
   - `ADPServices.get_knowledge_networks()`: 获取知识网络列表
   - `ADPServices.get_knowledge_network_object_types()`: 获取知识网络对象类型

2. **配置**：`config.py`
   - `ADP_ONTOLOGY_MANAGER_HOST`: 知识网络管理服务地址

3. **大模型**：参考 `app/tools/search_tools/data_view_explore_tool.py` 的实现

### 代码结构

- **工具类**：`KnSelectTool`
- **参数模型**：`KnSelectArgs`, `TableInfo`
- **缓存方法**：`_get_knowledge_networks_from_cache()`, `_save_knowledge_networks_to_cache()` 等
- **匹配方法**：`_match_by_tables()`, `_match_by_query()`

## 注意事项

1. **缓存兼容性**：工具支持 Redis 和 InMemory 两种 session 类型，非 Redis session 时自动跳过缓存
2. **匹配精度**：表匹配需要至少 50% 的表匹配才能成功
3. **性能优化**：使用缓存可以显著提升重复查询的性能
4. **数据一致性**：建议在知识网络更新后使用 `force_refresh_cache` 刷新缓存
