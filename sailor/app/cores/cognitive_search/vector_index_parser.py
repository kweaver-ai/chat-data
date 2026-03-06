# -*- coding: utf-8 -*-
"""
向量索引字段解析工具
从实体类型配置数据中解析出启用了向量索引的字段
"""
from typing import Dict, List, Any, Optional, Tuple
from app.logs.logger import logger


def parse_vector_index_fields(entries_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    从实体类型配置数据中解析出启用了向量索引的字段
    
    Args:
        entries_data: 包含实体类型配置的字典，格式为：
            {
                'entries': [
                    {
                        'id': '实体类型名',
                        'data_properties': [
                            {
                                'name': '字段名',
                                'index_config': {
                                    'vector_config': {
                                        'enabled': True/False
                                    }
                                }
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
    
    Returns:
        Dict[str, List[str]]: 格式为 {实体类型名: [启用了向量索引的字段名称列表]}
        例如: {"datacatalog": ["datacatalogname", "description_name"], "form_view": ["description"]}
    
    Example:
        >>> data = {
        ...     'entries': [
        ...         {
        ...             'id': 'datacatalog',
        ...             'data_properties': [
        ...                 {
        ...                     'name': 'datacatalogname',
        ...                     'index_config': {
        ...                         'vector_config': {'enabled': True}
        ...                     }
        ...                 },
        ...                 {
        ...                     'name': 'description_name',
        ...                     'index_config': {
        ...                         'vector_config': {'enabled': True}
        ...                     }
        ...                 }
        ...             ]
        ...         }
        ...     ]
        ... }
        >>> result = parse_vector_index_fields(data)
        >>> print(result)
        {'datacatalog': ['datacatalogname', 'description_name']}
    """
    vector_index_filed: Dict[str, List[str]] = {}
    
    if not entries_data or 'entries' not in entries_data:
        logger.warning("entries_data 中没有找到 'entries' 字段")
        return vector_index_filed
    
    entries = entries_data.get('entries', [])
    if not isinstance(entries, list):
        logger.warning("entries 不是列表类型")
        return vector_index_filed
    
    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning(f"entry 不是字典类型: {entry}")
            continue
        
        entity_id = entry.get('id')
        if not entity_id:
            logger.warning(f"entry 中没有找到 'id' 字段: {entry}")
            continue
        
        data_properties = entry.get('data_properties', [])
        if not isinstance(data_properties, list):
            logger.warning(f"entry['data_properties'] 不是列表类型: {data_properties}")
            continue
        
        # 收集该实体类型中启用了向量索引的字段
        vector_fields = []
        for data_prop in data_properties:
            if not isinstance(data_prop, dict):
                continue
            
            field_name = data_prop.get('name')
            if not field_name:
                continue
            
            # 检查是否启用了向量索引
            index_config = data_prop.get('index_config', {})
            if not isinstance(index_config, dict):
                continue
            
            vector_config = index_config.get('vector_config', {})
            if not isinstance(vector_config, dict):
                continue
            
            # 检查 enabled 是否为 True
            if vector_config.get('enabled') is True:
                vector_fields.append(field_name)
                logger.debug(f"实体类型 '{entity_id}' 的字段 '{field_name}' 启用了向量索引")
        
        # 如果该实体类型有启用了向量索引的字段，则添加到结果中
        if vector_fields:
            vector_index_filed[entity_id] = vector_fields
            logger.info(f"实体类型 '{entity_id}' 的向量索引字段: {vector_fields}")
        else:
            logger.debug(f"实体类型 '{entity_id}' 没有启用了向量索引的字段")
    
    logger.info(f"解析结果 vector_index_filed = {vector_index_filed}")
    return vector_index_filed


def parse_vector_index_fields_from_entries_list(entries: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    从实体类型列表（entries）中解析出启用了向量索引的字段
    
    Args:
        entries: 实体类型配置列表
    
    Returns:
        Dict[str, List[str]]: 格式为 {实体类型名: [启用了向量索引的字段名称列表]}
    """
    return parse_vector_index_fields({'entries': entries})


def parse_entity_types(entries_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    从实体类型配置数据中解析出 entity_types 字典
    
    Args:
        entries_data: 包含实体类型配置的字典，格式为：
            {
                'entries': [
                    {
                        'id': '实体类型名',
                        'display_key': '显示键名',
                        ...
                    },
                    ...
                ]
            }
    
    Returns:
        Dict[str, Dict[str, str]]: 格式为 {实体类型名: {'default_tag': 'display_key'}}
        例如: {'datacatalog': {'default_tag': 'datacatalogname'}, 'form_view': {'default_tag': 'business_name'}}
    """
    entity_types: Dict[str, Dict[str, str]] = {}
    
    if not entries_data or 'entries' not in entries_data:
        logger.warning("entries_data 中没有找到 'entries' 字段")
        return entity_types
    
    entries = entries_data.get('entries', [])
    if not isinstance(entries, list):
        logger.warning("entries 不是列表类型")
        return entity_types
    
    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning(f"entry 不是字典类型: {entry}")
            continue
        
        entity_id = entry.get('id')
        if not entity_id:
            logger.warning(f"entry 中没有找到 'id' 字段: {entry}")
            continue
        
        display_key = entry.get('display_key')
        if display_key:
            entity_types[entity_id] = {'default_tag': display_key}
            logger.debug(f"实体类型 '{entity_id}' 的 default_tag: {display_key}")
        else:
            logger.warning(f"实体类型 '{entity_id}' 中没有找到 'display_key' 字段")
    
    logger.info(f"解析结果 entity_types = {entity_types}")
    return entity_types


def parse_data_params(entries_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从实体类型配置数据中解析出 data_params 字典
    
    Args:
        entries_data: 包含实体类型配置的字典
    
    Returns:
        Dict[str, Any]: 格式为 {
            'type2names': {},
            'indextag2tag': {实体id小写: 实体id原始形式}
        }
        例如: {
            'type2names': {},
            'indextag2tag': {'datacatalog': 'datacatalog', 'form_view': 'form_view'}
        }
    """
    data_params: Dict[str, Any] = {
        'type2names': {},
        'indextag2tag': {}
    }
    
    if not entries_data or 'entries' not in entries_data:
        logger.warning("entries_data 中没有找到 'entries' 字段")
        return data_params
    
    entries = entries_data.get('entries', [])
    if not isinstance(entries, list):
        logger.warning("entries 不是列表类型")
        return data_params
    
    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning(f"entry 不是字典类型: {entry}")
            continue
        
        entity_id = entry.get('id')
        if not entity_id:
            logger.warning(f"entry 中没有找到 'id' 字段: {entry}")
            continue
        
        # indextag2tag: key是id的小写形式，value是id的原始形式
        entity_id_lower = entity_id.lower()
        data_params['indextag2tag'][entity_id_lower] = entity_id
        logger.debug(f"indextag2tag: '{entity_id_lower}' -> '{entity_id}'")
    
    logger.info(f"解析结果 data_params = {data_params}")
    return data_params


def parse_all_entity_info(entries_data: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, str]], Dict[str, Any]]:
    """
    一次性解析所有实体信息，返回 vector_index_filed, entity_types, data_params
    
    Args:
        entries_data: 包含实体类型配置的字典
    
    Returns:
        Tuple[Dict[str, List[str]], Dict[str, Dict[str, str]], Dict[str, Any]]:
            (vector_index_filed, entity_types, data_params)
    """
    vector_index_filed = parse_vector_index_fields(entries_data)
    entity_types = parse_entity_types(entries_data)
    data_params = parse_data_params(entries_data)
    
    return vector_index_filed, entity_types, data_params


# 向后兼容的函数接口
def get_vector_index_fields(entries_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    向后兼容的函数接口，功能与 parse_vector_index_fields 相同
    """
    return parse_vector_index_fields(entries_data)


# 使用示例
if __name__ == '__main__':
    # 示例数据（基于用户提供的数据结构）
    # sample_data = {
    #     'entries': [
    #         {
    #             'id': 'datacatalog',
    #             'data_properties': [
    #                 {
    #                     'name': 'datacatalogname',
    #                     'index_config': {
    #                         'vector_config': {'enabled': True}
    #                     }
    #                 },
    #                 {
    #                     'name': 'description_name',
    #                     'index_config': {
    #                         'vector_config': {'enabled': True}
    #                     }
    #                 },
    #                 {
    #                     'name': 'code',
    #                     'index_config': {
    #                         'vector_config': {'enabled': False}
    #                     }
    #                 }
    #             ]
    #         },
    #         {
    #             'id': 'form_view',
    #             'data_properties': [
    #                 {
    #                     'name': 'description',
    #                     'index_config': {
    #                         'vector_config': {'enabled': True}
    #                     }
    #                 }
    #             ]
    #         }
    #     ]
    # }
    
    # 解析向量索引字段

    sample_data={'entries': [{'id': 'datacatalog', 'name': '数据资源目录', 'data_source': {'type': 'data_view', 'id': '2008850967890853889', 'name': '数据资源目录-实体类'}, 'data_properties': [{'name': 'asset_type', 'display_name': '资产类型', 'type': 'integer', 'comment': '资产类型', 'mapped_field': {'name': 'asset_type', 'type': 'integer', 'display_name': 'asset_type'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'code', 'display_name': '数据资源目录编码code', 'type': 'string', 'comment': '数据资源目录编码code', 'mapped_field': {'name': 'code', 'type': 'string', 'display_name': '目录编码'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'customized_cate_node_id_list', 'display_name': '自定义类目node_id列表', 'type': 'text', 'comment': '自定义类目node_id列表', 'mapped_field': {'name': 'customized_cate_node_id_list', 'type': 'text', 'display_name': 'customized_cate_node_id_list'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'customized_cate_nodes', 'display_name': '自定义类目nodes', 'type': 'text', 'comment': '自定义类目nodes', 'mapped_field': {'name': 'customized_cate_nodes', 'type': 'text', 'display_name': 'customized_cate_nodes'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'datacatalogid', 'display_name': '数据资源目录ID', 'type': 'integer', 'comment': '数据资源目录ID', 'mapped_field': {'name': 'datacatalogid', 'type': 'integer', 'display_name': '唯一id雪花算法'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'datacatalogname', 'display_name': '数据资源目录名称', 'type': 'string', 'comment': '数据资源目录名称', 'mapped_field': {'name': 'datacatalogname', 'type': 'string', 'display_name': '目录名称'}, 'index_config': {'keyword_config': {'enabled': True, 'ignore_above_len': 1024}, 'fulltext_config': {'enabled': True, 'analyzer': 'standard'}, 'vector_config': {'enabled': True, 'model_id': '2008102955676471296'}}, 'condition_operations': ['==', '!=', 'in', 'not_in', 'match', 'multi_match', 'knn']}, {'name': 'department', 'display_name': '部门名称', 'type': 'string', 'comment': '部门名称', 'mapped_field': {'name': 'department', 'type': 'string', 'display_name': '对象名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'department_id', 'display_name': '部门ID', 'type': 'string', 'comment': '部门ID', 'mapped_field': {'name': 'department_id', 'type': 'string', 'display_name': '所属部门ID'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'department_path', 'display_name': '部门层级路径', 'type': 'text', 'comment': '部门层级路径', 'mapped_field': {'name': 'department_path', 'type': 'text', 'display_name': '路径'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'department_path_id', 'display_name': '部门层级路径id', 'type': 'text', 'comment': '部门层级路径id', 'mapped_field': {'name': 'department_path_id', 'type': 'text', 'display_name': '路径ID'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'description_name', 'display_name': '数据资源目录描述', 'type': 'string', 'comment': '资源目录描述', 'mapped_field': {'name': 'description_name', 'type': 'string', 'display_name': '资源目录描述'}, 'index_config': {'keyword_config': {'enabled': True, 'ignore_above_len': 1024}, 'fulltext_config': {'enabled': True, 'analyzer': 'standard'}, 'vector_config': {'enabled': True, 'model_id': '2008102955676471296'}}, 'condition_operations': ['in', 'not_in', 'match', 'multi_match', 'knn', '==', '!=']}, {'name': 'info_system_id', 'display_name': '信息系统id', 'type': 'integer', 'comment': '信息系统雪花id', 'mapped_field': {'name': 'info_system_id', 'type': 'integer', 'display_name': '信息系统雪花id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'info_system_name', 'display_name': '信息系统名称', 'type': 'string', 'comment': '信息系统名称', 'mapped_field': {'name': 'info_system_name', 'type': 'string', 'display_name': '信息系统名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'online_status', 'display_name': '上线状态', 'type': 'string', 'comment': '接口状态 未上线 notline、已上线 online、已下线offline、上线审核中up-auditing、下线审核中down-auditing、上线审核未通过up-reject、下线审核未通过down-reject、已下线（上线审核中）offline-up-auditing、已下线（上线审核未通过）offline-up-reject', 'mapped_field': {'name': 'online_status', 'type': 'string', 'display_name': '接口状态未上线notline已上线online已下线offline上线审核中up-auditing下线审核中down-auditing上线审核未通过up-reject下线审核未通过down-reject已下线上线审核中offline-up-auditing已下线上线审核未通过offline-up-reject'}, 'condition_operations': ['in', 'not_in', '==', '!=']}, {'name': 'online_time', 'display_name': '上线时间', 'type': 'integer', 'comment': '上线时间', 'mapped_field': {'name': 'online_time', 'type': 'integer', 'display_name': 'online_time'}, 'condition_operations': ['in', 'not_in', '==', '!=']}, {'name': 'publish_status', 'display_name': '发布状态', 'type': 'string', 'comment': '发布状态 未发布unpublished 、发布审核中pub-auditing、已发布published、发布审核未通过pub-reject、变更审核中change-auditing、变更审核未通过change-reject', 'mapped_field': {'name': 'publish_status', 'type': 'string', 'display_name': '发布状态未发布unpublished发布审核中pub-auditing已发布published发布审核未通过pub-reject变更审核中change-auditing变更审核未通过change-reject'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'publish_status_category', 'display_name': '发布状态类别', 'type': 'string', 'comment': '发布状态类别', 'mapped_field': {'name': 'publish_status_category', 'type': 'string', 'display_name': 'publish_status_category'}, 'condition_operations': ['not_in', '==', '!=', 'in']}, {'name': 'published_at', 'display_name': '发布时间', 'type': 'decimal', 'comment': '发布时间', 'mapped_field': {'name': 'published_at', 'type': 'decimal', 'display_name': 'published_at'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'resource_id', 'display_name': '挂接的数据资源uuid', 'type': 'string', 'comment': '挂接的数据资源uuid', 'mapped_field': {'name': 'resource_id', 'type': 'string', 'display_name': '数据资源id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'resource_type', 'display_name': '挂接的数据资源类型1逻辑视图2接口', 'type': 'integer', 'comment': '数据资源类型 枚举值 1：逻辑视图 2：接口 3:文件资源', 'mapped_field': {'name': 'resource_type', 'type': 'integer', 'display_name': '数据资源类型枚举值1逻辑视图2接口3文件资源'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'shared_type', 'display_name': '共享属性', 'type': 'integer', 'comment': '共享属性 1 无条件共享 2 有条件共享 3 不予共享', 'mapped_field': {'name': 'shared_type', 'type': 'integer', 'display_name': '共享属性1无条件共享2有条件共享3不予共享'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'subject_id_list', 'display_name': '主题id列表', 'type': 'text', 'comment': '主题id列表', 'mapped_field': {'name': 'subject_id_list', 'type': 'text', 'display_name': 'subject_id_list'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'subject_nodes', 'display_name': '主题nodes', 'type': 'text', 'comment': '主题nodes', 'mapped_field': {'name': 'subject_nodes', 'type': 'text', 'display_name': 'subject_nodes'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'update_cycle', 'display_name': '更新周期', 'type': 'integer', 'comment': '更新频率 参考数据字典：GXZQ，1不定时 2实时 3每日 4每周 5每月 6每季度 7每半年 8每年 9其他', 'mapped_field': {'name': 'update_cycle', 'type': 'integer', 'display_name': '更新频率参考数据字典GXZQ1不定时2实时3每日4每周5每月6每季度7每半年8每年9其他'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'ves_catalog_name', 'display_name': '数据源在虚拟化引擎中的技术名称', 'type': 'string', 'comment': '数据源在虚拟化引擎中的技术名称', 'mapped_field': {'name': 'ves_catalog_name', 'type': 'string', 'display_name': '数据源catalog名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}], 'primary_keys': ['datacatalogid'], 'display_key': 'datacatalogname', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-datacatalog-d5f5gp26746ef0r11hj0', 'index_available': True, 'doc_count': 1, 'storage_size': 39661, 'update_time': 1767790700821}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767790663804, 'module_type': 'object_type'}, {'id': 'data_catalog_column', 'name': '信息项', 'data_source': {'type': 'data_view', 'id': '2008850967916019714', 'name': '信息项-实体类'}, 'data_properties': [{'name': 'business_name', 'display_name': '业务名称', 'type': 'string', 'comment': '业务名称', 'mapped_field': {'name': 'business_name', 'type': 'string', 'display_name': '业务名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'id', 'display_name': 'id', 'type': 'integer', 'comment': '唯一id，雪花算法', 'mapped_field': {'name': 'id', 'type': 'integer', 'display_name': '唯一id雪花算法'}, 'condition_operations': ['not_in', '==', '!=', 'in']}, {'name': 'technical_name', 'display_name': '技术名称', 'type': 'string', 'comment': '技术名称', 'mapped_field': {'name': 'technical_name', 'type': 'string', 'display_name': '技术名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}], 'primary_keys': ['id'], 'display_key': 'business_name', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-data_catalog_column-d5f5gp26746ef0r11hig', 'index_available': True, 'doc_count': 39, 'storage_size': 18521, 'update_time': 1767790696358}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767783074593, 'module_type': 'object_type'}, {'id': 'department', 'name': '部门', 'data_source': {'type': 'data_view', 'id': '2008850968218009601', 'name': '部门-实体类'}, 'data_properties': [{'name': 'departmentid', 'display_name': 'departmentid', 'type': 'string', 'comment': '对象ID', 'mapped_field': {'name': 'departmentid', 'type': 'string', 'display_name': '对象ID'}, 'condition_operations': ['in', 'not_in', '==', '!=']}, {'name': 'departmentname', 'display_name': '部门名称', 'type': 'string', 'comment': '部门名称', 'mapped_field': {'name': 'departmentname', 'type': 'string', 'display_name': '对象名称'}, 'condition_operations': ['not_in', '==', '!=', 'in']}], 'primary_keys': ['departmentid'], 'display_key': 'departmentname', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-department-d5f5gp26746ef0r11hmg', 'index_available': True, 'doc_count': 8, 'storage_size': 7885, 'update_time': 1767790699827}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767783031290, 'module_type': 'object_type'}, {'id': 'domain', 'name': '主题域分组', 'data_source': {'type': 'data_view', 'id': '2008850967815356418', 'name': '主题域分组-实体类'}, 'data_properties': [{'name': 'domainid', 'display_name': '主题域分组id', 'type': 'string', 'comment': '主题域分组id', 'mapped_field': {'name': 'domainid', 'type': 'string', 'display_name': '对象iduuid'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'domainname', 'display_name': '主题域分组名称', 'type': 'string', 'comment': '主题域分组名称', 'mapped_field': {'name': 'domainname', 'type': 'string', 'display_name': '名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'prefixname', 'display_name': 'prefixname', 'type': 'string', 'comment': 'prefixname', 'mapped_field': {'name': 'prefixname', 'type': 'string', 'display_name': 'prefixname'}, 'condition_operations': ['not_in', '==', '!=', 'in']}], 'primary_keys': ['domainid'], 'display_key': 'domainname', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-domain-d5f5gp26746ef0r11hng', 'index_available': True, 'doc_count': 1, 'storage_size': 5733, 'update_time': 1767790696218}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767783013825, 'module_type': 'object_type'}, {'id': 'form_view', 'name': '逻辑视图', 'data_source': {'type': 'data_view', 'id': '2008850967794384898', 'name': '逻辑视图-实体类'}, 'data_properties': [{'name': 'business_name', 'display_name': '业务名称', 'type': 'string', 'comment': '业务名称', 'mapped_field': {'name': 'business_name', 'type': 'string', 'display_name': 'business_name'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'datasource_id', 'display_name': '数据源id', 'type': 'string', 'comment': '数据源id', 'mapped_field': {'name': 'datasource_id', 'type': 'string', 'display_name': 'datasource_id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'department', 'display_name': '部门', 'type': 'string', 'comment': '部门', 'mapped_field': {'name': 'department', 'type': 'string', 'display_name': 'department'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'department_id', 'display_name': '部门id', 'type': 'string', 'comment': '部门id', 'mapped_field': {'name': 'department_id', 'type': 'string', 'display_name': 'department_id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'department_path', 'display_name': '部门层级路径', 'type': 'text', 'comment': '部门层级路径', 'mapped_field': {'name': 'department_path', 'type': 'text', 'display_name': 'department_path'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'department_path_id', 'display_name': '部门层级路径id', 'type': 'text', 'comment': '部门层级路径id', 'mapped_field': {'name': 'department_path_id', 'type': 'text', 'display_name': 'department_path_id'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'description', 'display_name': '逻辑视图描述', 'type': 'string', 'comment': '逻辑视图描述', 'mapped_field': {'name': 'description', 'type': 'string', 'display_name': 'description'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'formview_code', 'display_name': '逻辑视图编码code', 'type': 'string', 'comment': '逻辑视图编码code', 'mapped_field': {'name': 'formview_code', 'type': 'string', 'display_name': 'formview_code'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'formview_uuid', 'display_name': '逻辑视图id', 'type': 'string', 'comment': '逻辑视图id', 'mapped_field': {'name': 'formview_uuid', 'type': 'string', 'display_name': 'formview_uuid'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'owner_id', 'display_name': '数据owner_id', 'type': 'string', 'comment': '数据owner_id', 'mapped_field': {'name': 'owner_id', 'type': 'string', 'display_name': 'owner_id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'owner_name', 'display_name': '数据owner', 'type': 'string', 'comment': '数据owner', 'mapped_field': {'name': 'owner_name', 'type': 'string', 'display_name': 'owner_name'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'publish_at', 'display_name': '发布时间', 'type': 'datetime', 'comment': '发布时间', 'mapped_field': {'name': 'publish_at', 'type': 'datetime', 'display_name': '发布时间'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'subject_id', 'display_name': '主题域id', 'type': 'string', 'comment': '主题域id', 'mapped_field': {'name': 'subject_id', 'type': 'string', 'display_name': 'subject_id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'subject_name', 'display_name': '主题名称', 'type': 'string', 'comment': '主题名称', 'mapped_field': {'name': 'subject_name', 'type': 'string', 'display_name': '名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'subject_path', 'display_name': '主题层级路径', 'type': 'text', 'comment': '主题层级路径', 'mapped_field': {'name': 'subject_path', 'type': 'text', 'display_name': '路径'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'subject_path_id', 'display_name': '主题层级路径id', 'type': 'text', 'comment': '主题层级路径id', 'mapped_field': {'name': 'subject_path_id', 'type': 'text', 'display_name': '路径ID'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'technical_name', 'display_name': '技术名称', 'type': 'string', 'comment': '技术名称', 'mapped_field': {'name': 'technical_name', 'type': 'string', 'display_name': 'technical_name'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'type', 'display_name': '逻辑视图来源', 'type': 'integer', 'comment': '视图来源 1：元数据视图、2：自定义视图、3：逻辑实体视图', 'mapped_field': {'name': 'type', 'type': 'integer', 'display_name': '视图来源1元数据视图2自定义视图3逻辑实体视图'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}], 'primary_keys': ['formview_uuid'], 'display_key': 'business_name', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-form_view-d5f5gp26746ef0r11hlg', 'index_available': True, 'doc_count': 10, 'storage_size': 26100, 'update_time': 1767790699038}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782993521, 'module_type': 'object_type'}, {'id': 'form_view_field', 'name': '逻辑视图字段', 'data_source': {'type': 'data_view', 'id': '2008850967848910850', 'name': '逻辑视图字段-实体类'}, 'data_properties': [{'name': 'business_name', 'display_name': '字段业务名称', 'type': 'string', 'comment': '列业务名称', 'mapped_field': {'name': 'business_name', 'type': 'string', 'display_name': '列业务名称'}, 'condition_operations': ['in', 'not_in', '==', '!=']}, {'name': 'column_id', 'display_name': '字段ID', 'type': 'string', 'comment': '列uuid', 'mapped_field': {'name': 'column_id', 'type': 'string', 'display_name': '列uuid'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'data_type', 'display_name': '数据类型', 'type': 'string', 'comment': '数据类型', 'mapped_field': {'name': 'data_type', 'type': 'string', 'display_name': '数据类型'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'formview_uuid', 'display_name': '逻辑视图id', 'type': 'string', 'comment': '数据表视图uuid', 'mapped_field': {'name': 'formview_uuid', 'type': 'string', 'display_name': '数据表视图uuid'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'technical_name', 'display_name': '字段技术名称', 'type': 'string', 'comment': '列技术名称', 'mapped_field': {'name': 'technical_name', 'type': 'string', 'display_name': '列技术名称'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}], 'primary_keys': ['column_id'], 'display_key': 'business_name', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-form_view_field-d5f5gp26746ef0r11hm0', 'index_available': True, 'doc_count': 308, 'storage_size': 138987, 'update_time': 1767790695897}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782898117, 'module_type': 'object_type'}, {'id': 'info_system', 'name': '信息系统', 'data_source': {'type': 'data_view', 'id': '2008850967857299457', 'name': '信息系统-实体类'}, 'data_properties': [{'name': 'info_system_description', 'display_name': '信息系统描述', 'type': 'string', 'comment': '信息系统描述', 'mapped_field': {'name': 'info_system_description', 'type': 'string', 'display_name': '信息系统描述'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'info_system_uuid', 'display_name': '信息系统业务id', 'type': 'string', 'comment': '信息系统业务id', 'mapped_field': {'name': 'info_system_uuid', 'type': 'string', 'display_name': '信息系统业务id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'infosystemid', 'display_name': '信息系统雪花id', 'type': 'integer', 'comment': '信息系统雪花id', 'mapped_field': {'name': 'infosystemid', 'type': 'integer', 'display_name': '信息系统雪花id'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'infosystemname', 'display_name': '信息系统名称', 'type': 'string', 'comment': '信息系统名称', 'mapped_field': {'name': 'infosystemname', 'type': 'string', 'display_name': '信息系统名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}], 'primary_keys': ['info_system_uuid'], 'display_key': 'infosystemname', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-info_system-d5f5gp26746ef0r11hi0', 'index_available': True, 'doc_count': 0, 'storage_size': 208, 'update_time': 1767790697762}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782830180, 'module_type': 'object_type'}, {'id': 'response_field', 'name': '接口出参', 'data_source': {'type': 'data_view', 'id': '2008850968054431746', 'name': '接口出参-实体类'}, 'data_properties': [{'name': 'cn_name', 'display_name': '中文名称', 'type': 'string', 'comment': '中文名称', 'mapped_field': {'name': 'cn_name', 'type': 'string', 'display_name': '中文名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'en_name', 'display_name': '英文名称', 'type': 'string', 'comment': '英文名称', 'mapped_field': {'name': 'en_name', 'type': 'string', 'display_name': '英文名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'field_id', 'display_name': '主键', 'type': 'integer', 'comment': '主键', 'mapped_field': {'name': 'field_id', 'type': 'integer', 'display_name': '主键'}, 'condition_operations': ['in', 'not_in', '==', '!=']}], 'primary_keys': ['field_id'], 'display_key': 'cn_name', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-response_field-d5f5gp26746ef0r11hk0', 'index_available': True, 'doc_count': 0, 'storage_size': 208, 'update_time': 1767790697005}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782781304, 'module_type': 'object_type'}, {'id': 'service', 'name': '接口服务', 'data_source': {'type': 'data_view', 'id': '2008850967874076674', 'name': '接口服务-实体类'}, 'data_properties': [{'name': 'asset_type', 'display_name': 'asset_type', 'type': 'integer', 'comment': '', 'mapped_field': {'name': 'asset_type', 'type': 'integer', 'display_name': 'asset_type'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'code', 'display_name': 'code', 'type': 'string', 'comment': '接口编码', 'mapped_field': {'name': 'code', 'type': 'string', 'display_name': 'code'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'description', 'display_name': 'description', 'type': 'text', 'comment': '接口说明', 'mapped_field': {'name': 'description', 'type': 'text', 'display_name': 'description'}, 'condition_operations': ['match', 'multi_match']}, {'name': 'id', 'display_name': 'id', 'type': 'string', 'comment': '', 'mapped_field': {'name': 'id', 'type': 'string', 'display_name': 'id'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'name', 'display_name': '业务名称', 'type': 'string', 'comment': '业务名称', 'mapped_field': {'name': 'name', 'type': 'string', 'display_name': 'name'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'online_at', 'display_name': '上线时间', 'type': 'integer', 'comment': '上线时间', 'mapped_field': {'name': 'online_at', 'type': 'integer', 'display_name': 'online_at'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'online_status', 'display_name': '上线状态', 'type': 'string', 'comment': '接口状态 未上线 notline、已上线 online、已下线offline、上线审核中up-auditing、下线审核中down-auditing、上线审核未通过up-reject、下线审核未通过down-reject', 'mapped_field': {'name': 'online_status', 'type': 'string', 'display_name': '接口状态未上线notline已上线online已下线offline上线审核中up-auditing下线审核中down-auditing上线审核未通过up-reject下线审核未通过down-reject'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'publish_status', 'display_name': '发布状态', 'type': 'string', 'comment': '发布状态 未发布unpublished 、发布审核中pub-auditing、已发布published、发布审核未通过pub-reject、变更审核中change-auditing、变更审核未通过change-reject', 'mapped_field': {'name': 'publish_status', 'type': 'string', 'display_name': '发布状态未发布unpublished发布审核中pub-auditing已发布published发布审核未通过pub-reject变更审核中change-auditing变更审核未通过change-reject'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'publish_status_category', 'display_name': '发布状态归类', 'type': 'string', 'comment': '', 'mapped_field': {'name': 'publish_status_category', 'type': 'string', 'display_name': 'publish_status_category'}, 'condition_operations': ['!=', 'in', 'not_in', '==']}, {'name': 'published_at', 'display_name': '发布时间', 'type': 'integer', 'comment': '', 'mapped_field': {'name': 'published_at', 'type': 'integer', 'display_name': 'published_at'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'technical_name', 'display_name': '技术名称', 'type': 'string', 'comment': '', 'mapped_field': {'name': 'technical_name', 'type': 'string', 'display_name': 'technical_name'}, 'condition_operations': ['not_in', '==', '!=', 'in']}], 'primary_keys': ['id'], 'display_key': 'name', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-service-d5f5gp26746ef0r11hkg', 'index_available': True, 'doc_count': 0, 'storage_size': 208, 'update_time': 1767790698070}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782763451, 'module_type': 'object_type'}, {'id': 'subdomain', 'name': '主题域', 'data_source': {'type': 'data_view', 'id': '2008850967827939329', 'name': '主题域-实体类'}, 'data_properties': [{'name': 'prefixname', 'display_name': 'prefixname', 'type': 'string', 'comment': 'prefixname', 'mapped_field': {'name': 'prefixname', 'type': 'string', 'display_name': 'prefixname'}, 'condition_operations': ['in', 'not_in', '==', '!=']}, {'name': 'subdomainid', 'display_name': '主题域id', 'type': 'string', 'comment': '主题域id', 'mapped_field': {'name': 'subdomainid', 'type': 'string', 'display_name': '对象iduuid'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}, {'name': 'subdomainname', 'display_name': '主题域名称', 'type': 'string', 'comment': '主题域名称', 'mapped_field': {'name': 'subdomainname', 'type': 'string', 'display_name': '名称'}, 'condition_operations': ['==', '!=', 'in', 'not_in']}], 'primary_keys': ['subdomainid'], 'display_key': 'subdomainname', 'incremental_key': '', 'tags': [], 'comment': '', 'icon': 'icon-dip-suanziguanli', 'color': '#0e5fc5', 'detail': '', 'kn_id': 'cognitive_search_data_catalog', 'branch': 'main', 'status': {'incremental_key': '', 'incremental_value': '', 'index': 'dip-kn_ot_index-cognitive_search_data_catalog-main-subdomain-d5f5gp26746ef0r11hn0', 'index_available': True, 'doc_count': 1, 'storage_size': 5771, 'update_time': 1767790696095}, 'creator': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'create_time': 1767779029813, 'updater': {'id': 'cbf93ec4-ea19-11f0-9c74-c2868d7b6f84', 'type': 'user', 'name': 'liberly'}, 'update_time': 1767782743401, 'module_type': 'object_type'}], 'total_count': 12}
    # 解析向量索引字段
    vector_index_filed = parse_vector_index_fields(sample_data)
    print("vector_index_filed:")
    print(vector_index_filed)
    
    # 解析 entity_types
    entity_types = parse_entity_types(sample_data)
    print("\nentity_types:")
    print(entity_types)
    
    # 解析 data_params
    data_params = parse_data_params(sample_data)
    print("\ndata_params:")
    print(data_params)
    
    # 一次性解析所有信息
    print("\n一次性解析所有信息:")
    vec_fields, ent_types, data_pars = parse_all_entity_info(sample_data)
    print(f"vector_index_filed: {vec_fields}")
    print(f"entity_types: {ent_types}")
    print(f"data_params: {data_pars}")
