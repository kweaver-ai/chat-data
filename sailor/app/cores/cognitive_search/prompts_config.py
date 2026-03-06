# 图查询语句
#
# 图查询返回结构
resource_entity = {
    "id": "",
    "alias": "数据资源",
    "color": "rgba(89,163,255,1)",
    "class_name": "resource",
    "icon": "graph-layer",
    "default_property": {
        "name": "resourcename",
        "value": "",
        "alias": "数据资源名称"
    },
    "tags": [
        "resource"
    ],
    "properties": [
        {
            "tag": "resource",
            "props": [
                {
                    "name": "resourcename",
                    "value": " ",
                    "alias": "数据资源名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_name",
                    "value": "__NULL__",
                    "alias": "主题名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path_id",
                    "value": "__NULL__",
                    "alias": "部门层级路径id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "publish_status_category",
                    "value": "__NULL__",
                    "alias": "上线状态类别",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "publish_status",
                    "value": "__NULL__",
                    "alias": "发布状态",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "description",
                    "value": " ",
                    "alias": "数据资源描述",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_id",
                    "value": "__NULL__",
                    "alias": "部门ID",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "technical_name",
                    "value": " ",
                    "alias": "技术名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "owner_id",
                    "value": " ",
                    "alias": "数据owner_id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "owner_name",
                    "value": " ",
                    "alias": "数据owner",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_path_id",
                    "value": "__NULL__",
                    "alias": "主题层级路径id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "code",
                    "value": " ",
                    "alias": "数据资源编码code",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department",
                    "value": "__NULL__",
                    "alias": "部门",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "color",
                    "value": "rgba(89,163,255,1)",
                    "alias": "资产的颜色",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_id",
                    "value": "__NULL__",
                    "alias": "主题id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "online_status",
                    "value": "__NULL__",
                    "alias": "上线状态",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path",
                    "value": "__NULL__",
                    "alias": "部门层级路径",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "online_at",
                    "value": "__NULL__",
                    "alias": "上线时间",
                    "type": "null",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_path",
                    "value": "__NULL__",
                    "alias": "主题层级路径",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "resourceid",
                    "value": " ",
                    "alias": "数据资源ID",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "asset_type",
                    "value": " ",
                    "alias": "资产类型",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "published_at",
                    "value": " ",
                    "alias": "发布时间",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "info_system_uuid",
                    "value": "__NULL__",
                    "alias": "info_system_uuid",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "info_system_name",
                    "value": "__NULL__",
                    "alias": "信息系统名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                }
            ]
        }
    ],
    "score": 1.5,
    "key": []
}
# 图查询返回结构
catalog_entity = {
    "id": "fccb51e1d8ebffff27174a133e147ff0",
    "alias": "数据资源目录",
    "color": "rgba(89,163,255,1)",
    "class_name": "datacatalog",
    "icon": "graph-layer",
    "default_property": {
        "name": "datacatalogname",
        "value": "知识产权",
        "alias": "数据资源目录名称"
    },
    "tags": [
        "datacatalog"
    ],
    "properties": [
        {
            "tag": "datacatalog",
            "props": [
                {
                    "name": "info_system_name",
                    "value": "__NULL__",
                    "alias": "信息系统名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "online_time",
                    "value": "__NULL__",
                    "alias": "上线时间",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "datacatalogid",
                    "value": "__NULL__",
                    "alias": "数据资源目录ID",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "owner_id",
                    "value": "__NULL__",
                    "alias": "数据owner_id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "color",
                    "value": "rgba(89,163,255,1)",
                    "alias": "资产的颜色",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path_id",
                    "value": "__NULL__",
                    "alias": "部门层级路径id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "datacatalogname",
                    "value": "__NULL__",
                    "alias": "数据资源目录名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "publish_status",
                    "value": "__NULL__",
                    "alias": "发布状态",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "description_name",
                    "value": "__NULL__",
                    "alias": "数据资源目录描述",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "code",
                    "value": "__NULL__",
                    "alias": "数据资源目录编码code",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "update_cycle",
                    "value": "__NULL__",
                    "alias": "更新周期",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "asset_type",
                    "value": "__NULL__",
                    "alias": "资产类型",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "info_system_id",
                    "value": "__NULL__",
                    "alias": "信息系统id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "ves_catalog_name",
                    "value": "__NULL__",
                    "alias": "数据源在虚拟化引擎中的技术名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "online_status",
                    "value": "__NULL__",
                    "alias": "上线状态",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "data_owner",
                    "value": "__NULL__",
                    "alias": "数据owner",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department",
                    "value": "__NULL__",
                    "alias": "部门名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "datasource",
                    "value": "__NULL__",
                    "alias": "数据源",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "metadata_schema",
                    "value": "__NULL__",
                    "alias": "库名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "published_at",
                    "value": "__NULL__",
                    "alias": "发布时间",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_id",
                    "value": "__NULL__",
                    "alias": "部门ID",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path",
                    "value": "__NULL__",
                    "alias": "部门层级路径",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "data_kind",
                    "value": "__NULL__",
                    "alias": "基础信息分类",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "shared_type",
                    "value": "__NULL__",
                    "alias": "共享属性",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                }
            ]
        }
    ],
    "score": 2,
    "key": []
}
# 图查询返回结构
formview_entity = {
    "id": "59eff2e6ae5831420e4f10b783c50a6d",
    "alias": "逻辑视图",
    "color": "rgba(1,229,9,1)",
    "class_name": "form_view",
    "icon": "graph-form",
    "default_property": {
        "name": "business_name",
        "value": "水果质量记录表",
        "alias": "业务名称"
    },
    "tags": [
        "form_view"
    ],
    "properties": [
        {
            "tag": "form_view",
            "props": [
                {
                    "name": "business_name",
                    "value": "__NULL__",
                    "alias": "业务名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "technical_name",
                    "value": "__NULL__",
                    "alias": "技术名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "type",
                    "value": "__NULL__",
                    "alias": "逻辑视图来源",
                    "type": "int",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "datasource_id",
                    "value": "__NULL__",
                    "alias": "数据源id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "formview_code",
                    "value": "__NULL__",
                    "alias": "逻辑视图编码code",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path_id",
                    "value": "__NULL__",
                    "alias": "部门层级路径id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "owner_name",
                    "value": "__NULL__",
                    "alias": "数据owner",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_name",
                    "value": "__NULL__",
                    "alias": "主题名称",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "description",
                    "value": "__NULL__",
                    "alias": "逻辑视图描述",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department",
                    "value": "__NULL__",
                    "alias": "部门",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_path",
                    "value": "__NULL__",
                    "alias": "主题层级路径",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "formview_uuid",
                    "value": "__NULL__",
                    "alias": "逻辑视图id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_id",
                    "value": "__NULL__",
                    "alias": "部门id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "owner_id",
                    "value": "__NULL__",
                    "alias": "数据owner_id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "publish_at",
                    "value": "__NULL__",
                    "alias": "发布时间",
                    "type": "datetime",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_path_id",
                    "value": "__NULL__",
                    "alias": "主题层级路径id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "department_path",
                    "value": "__NULL__",
                    "alias": "部门层级路径",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                },
                {
                    "name": "subject_id",
                    "value": "__NULL__",
                    "alias": "主题域id",
                    "type": "string",
                    "disabled": False,
                    "checked": False
                }
            ]
        }
    ],
    "score": 2,
    "key": [

    ]
}
# 资源版,查中间实体点
resource_entity_search = " match (v:resource)  where  id(v) in {start_vids} and (v.resource.asset_type in {asset_type} or '{asset_type}'=='[-1]') " \
                         "and (v.resource.online_at >= {start_time} or {start_time}==0) " \
                         "and   (v.resource.online_at <=  {end_time} or  {end_time}==0) " \
                         "and     (v.resource.owner_id in {owner_id} or '{owner_id}'=='[-1]')  " \
                         "and   (v.resource.department_id in {department_id} or '{department_id}'=='[-1]') " \
                         "and   (v.resource.publish_status_category in {publish_status} or '{publish_status}'=='[-1]')  " \
                         "and   (v.resource.online_status in {online_status} or '{online_status}'=='[-1]')  " \
                         "and (v.resource.subject_id in {subject_id} or '{subject_id}'=='[-1]')  return v"
# 资源版,查临近的点
resource_graph_search = "go 0 to 2 steps from {start_vids} over *  where ($$.resource.asset_type in {asset_type} or '{asset_type}'=='[-1]')  and  ($$.resource.online_at >= {start_time} or {start_time}==0)  and ($$.resource.online_at <=  {end_time} or  {end_time}==0)   and   ($$.resource.owner_id in {owner_id} or '{owner_id}'=='[-1]')  and  ($$.resource.department_id in {department_id} or '{department_id}'=='[-1]') and  ($$.resource.publish_status_category in {publish_status} or '{publish_status}'=='[-1]')  and  ($$.resource.online_status in {online_status} or '{online_status}'=='[-1]')  and   ($$.resource.subject_id in {subject_id} or '{subject_id}'=='[-1]')   yield $$ as nodes,edge as relationships"
# 目录版,查中间实体点
catalog_entity_search = "match (v:datacatalog)   where  id(v) in {start_vids}  " \
                        "and   (v.datacatalog.asset_type in {asset_type} or '{asset_type}'=='[-1]') " \
                        "and   (v.datacatalog.update_cycle in {update_cycle}  or '{update_cycle}'=='[-1]' ) " \
                        "and   (v.datacatalog.shared_type in {shared_type}    or '{shared_type}'=='[-1]') " \
                        "and   (v.datacatalog.online_time >= {start_time} or {start_time}==0) " \
                        "and   (v.datacatalog.online_time <=  {end_time} or  {end_time}==0) " \
                        "and   (v.datacatalog.info_system_id in {info_system} or '{info_system}'=='[-1]') " \
                        "and   (v.datacatalog.department_id in {department_id} or '{department_id}'=='[-1]') " \
                        "and   (v.datacatalog.online_status in {online_status} or '{online_status}'=='[-1]')  " \
                        "and   (v.datacatalog.publish_status_category in {publish_status} or '{publish_status}'=='[-1]')  " \
                        "and   (any (n in {subject_id} where n in split(v.datacatalog.subject_id_list,',')) or '{subject_id}'=='[-1]')  " \
                        "and   (any (n in {cate_node_id} where n in split(v.datacatalog.customized_cate_node_id_list,',')) or '{cate_node_id}'=='[-1]')  " \
                        "and   (v.datacatalog.resource_type in {resource_type} or '{resource_type}'=='[-1]') return v "
# 目录版,查临近的点
catalog_graph_search = "go 0 to 2 steps from {start_vids} over   *  " \
                       " where   ($$.datacatalog.asset_type in {asset_type} or '{asset_type}'=='[-1]') " \
                       "and   ($$.datacatalog.update_cycle in {update_cycle}  or '{update_cycle}'=='[-1]' ) " \
                       "and   ($$.datacatalog.shared_type in {shared_type}    or '{shared_type}'=='[-1]') " \
                       "and   ($$.datacatalog.online_time >= {start_time} or {start_time}==0) " \
                       "and   ($$.datacatalog.online_time <=  {end_time} or  {end_time}==0)  " \
                       "and   ($$.datacatalog.department_id in {department_id} or '{department_id}'=='[-1]')  " \
                       "and   ($$.datacatalog.info_system_id in {info_system} or '{info_system}'=='[-1]') " \
                       "and   ($$.datacatalog.online_status in {online_status} or '{online_status}'=='[-1]')  " \
                       "and   ($$.datacatalog.publish_status_category in {publish_status} or '{publish_status}'=='[-1]') " \
                       "and   (any (n in {subject_id} where n in split($$.datacatalog.subject_id_list,',')) or '{subject_id}'=='[-1]') " \
                       "and   (any (n in {cate_node_id} where n in split($$.datacatalog.customized_cate_node_id_list,',')) or '{cate_node_id}'=='[-1]')  " \
                       "and   ($$.datacatalog.resource_type in {resource_type} or '{resource_type}'=='[-1]') yield $$ as nodes,edge as relationships"

# 目录版, 首页智能问数, 根据一个数据资源目录,查相关的图谱子图
nebula_get_connected_subgraph_catalog_match = "MATCH (v)-[e*1..3]->(n) WHERE id(n) == {datacatalog_graph_vid} RETURN v, e, n;"

#测试用
catalog_graph_search_old = "go 0 to 2 steps from {start_vids} over   *   " \
                           " where   (bit_and($$.datacatalog.data_kind, {data_kind}) > 0 or {data_kind}==0) " \
                           "and   ($$.datacatalog.asset_type in {asset_type} or '{asset_type}'=='[-1]') " \
                           "and   ($$.datacatalog.update_cycle in {update_cycle}  or '{update_cycle}'=='[-1]' ) " \
                           "and   ($$.datacatalog.shared_type in {shared_type}    or '{shared_type}'=='[-1]') " \
                           "and   ($$.datacatalog.published_at >= {start_time} or {start_time}==0) " \
                           "and   ($$.datacatalog.published_at <=  {end_time} or  {end_time}==0)  " \
                           "and   ($$.datacatalog.owner_id in {owner_id} or '{owner_id}'=='[-1]') " \
                           "and   ($$.datacatalog.department_id in {department_id} or '{department_id}'=='[-1]')  " \
                           "and   ($$.datacatalog.info_system_id in {info_system} or '{info_system}'=='[-1]') yield $$ as nodes,edge as relationships"
#测试用
abc = "go 0 to 2 steps from {start_vids} over   *   " \
      " where   ($$.datacatalog.asset_type in {asset_type} or '{asset_type}'=='[-1]') " \
      "and   ($$.datacatalog.update_cycle in {update_cycle}  or '{update_cycle}'=='[-1]' ) " \
      "and   ($$.datacatalog.shared_type in {shared_type}    or '{shared_type}'=='[-1]') " \
      "and   ($$.datacatalog.published_at >= {start_time} or {start_time}==0) " \
      "and   ($$.datacatalog.published_at <=  {end_time} or  {end_time}==0)  " \
      "and   ($$.datacatalog.department_id in {department_id} or '{department_id}'=='[-1]')  " \
      "and   ($$.datacatalog.info_system_id in {info_system} or '{info_system}'=='[-1]')  " \
      "and   ($$.datacatalog.online_status in {online_status} or '{online_status}'=='[-1]')  " \
      "and   ($$.datacatalog.publish_status in {publish_status_c} or '{publish_status_c}'=='[-1]')" \
      "and   (any (n in {subject_id} where n in split($$.datacatalog.subject_id_list,',')) or '{subject_id}'=='[-1]')  and   (any (n in {cate_node_id} where n in split($$.datacatalog.customized_cate_node_id_list,',')) or '{cate_node_id}'=='[-1]') and   ($$.datacatalog.resource_type in {resource_type} or '{resource_type}'=='[-1]') yield $$ as nodes,edge as relationships"
# 场景 分析
formview_entity_search = "match (v:{source_type})    " \
                         " where  id(v) in {start_vids} return v"
formview_graph_search = "go 0 to 2 steps from {start_vids} over   * yield $$ as nodes,edge as relationships"
# resource_graph_search = \'go 0 to 2 steps from {start_vids} over *  where ($$.resource.asset_type in {asset_type} or "{asset_type}"=="[-1]")  and ($$.resource.online_at >= {start_time} or {start_time}==0)  and   ($$.resource.online_at <=  {end_time} or  {end_time}==0)   and  ($$.resource.owner_id in {owner_id} or "{owner_id}"=="[-1]")  and   ($$.resource.department_id in {department_id} or "{department_id}"=="[-1]") and  ($$.resource.publish_status_category in {publish_status} or "{publish_status}"=="[-1]")  and  ($$.resource.online_status in {online_status} or "{online_status}"=="[-1]")  and  ($$.resource.subject_id in {subject_id} or "{subject_id}"=="[-1]")  yield $$ as nodes,edge as relationships'

# "and   (v.datacatalog.publish_status in {publish_status} or '{publish_status}'=='[-1]')  " \','
# "and   (v.datacatalog.online_status in {online_status} or '{online_status}'=='[-1]')  " \

# "and   ($$.datacatalog.publish_status in {publish_status} or '{publish_status}'=='[-1]')  " \
# "and   ($$.datacatalog.online_status in {online_status} or '{online_status}'=='[-1]')  "
