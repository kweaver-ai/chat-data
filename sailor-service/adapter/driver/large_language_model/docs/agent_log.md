# 智能助手问答记录接口

## 场景&价值
1. 运营管理员根据使用智能问数、智能找数的使用情况分析统计智能体使用情况
2. 运营管理员分析智能助手的日志定期分析常见问题及业务使用情况等

## 鉴权
1. token权限即可


## 接口
1. GET接口，参数是query参数 
2. 层级结构参照SampleData接口


## 逻辑

### 入参
入参的参数名字，参考项目中的其他接口的参数
1. 分页查询，最大每页100条，默认10条
2. 根据时间范围、部门ID、用户ID、关键词模糊搜索筛选条件:
    a、时间范围（创建时间）分为开始时间、结束时间，非必填, 结束时间需要大于开始时间
    b、部门ID（问题创建者的部门ID），非必填，使用ISF部门ID，只能查询一个部门下所有用户的日志，暂时不管子部门
    c、用户ID（问题创建者ID），非必填，使用ISF用户ID，只能查询一个用户
    d、关键词糊搜索的内容为t_data_agent_conversation_message.f_content，非必填

#### 参数处理
1. 如果过滤参数有部门，那么先查询下部门下的用户ID，然后使用部门的下的ID和创建者匹配

### 返回
1. 列表接口显示字段分别为：创建时间、部门、用户、类型（问题、答案）、结果、过程
2. 数据库中没有部门，需要批量查询用户的创建部门后返回
3. 当f_role=assistant时，t_data_agent_conversation_message.f_content的结构如下，final_answer为结果，middle_answer是过程, 要挨个解析赋值
```
{
    "final_answer": {...},
    "middle_answer": {...}
}
```
4. 当f_role=user时，t_data_agent_conversation_message.f_content的结构如下，text为问题
```
{"text":"基于以上数据，计算机相关行业的占比分别是多少，请做图展示","temp_file":null}
```

### 数据表
接口的数据主要来自下面的两个表
#### 会话表
```
-- adp.t_data_agent_conversation definition   
CREATE TABLE `t_data_agent_conversation` (
  `f_id` varchar(40) NOT NULL COMMENT '会话 ID，会话唯一标识',
  `f_agent_app_key` varchar(40) NOT NULL COMMENT 'agent app key',
  `f_title` varchar(255) NOT NULL COMMENT '会话标题，默认使用首次用户提问消息的前20个字符，支持修改标题',
  `f_origin` varchar(40) NOT NULL DEFAULT 'web_chat' COMMENT '用于标记会话发起源：1. web_chat: 通过浏览器对话发起 2. api_call: api 调用发起（当前 API 暂不记录会话，只是预留未来扩展）',
  `f_message_index` int(11) NOT NULL DEFAULT 0 COMMENT '最新消息下标，会话消息下标从0开始，每产生一条新消息，下标 +1',
  `f_read_message_index` int(11) NOT NULL DEFAULT 0 COMMENT '最新已读消息下标，用于实现未读消息提醒功能，当前已读会话消息下标 < 最新会话消息下标时，表示有未读的消息',
  `f_ext` mediumtext NOT NULL COMMENT '预留扩展字段',
  `f_create_time` bigint(20) NOT NULL DEFAULT 0 COMMENT '创建时间',
  `f_update_time` bigint(20) NOT NULL DEFAULT 0 COMMENT '最后修改时间',
  `f_create_by` varchar(40) NOT NULL DEFAULT '' COMMENT '创建者',
  `f_update_by` varchar(40) NOT NULL DEFAULT '' COMMENT '最后修改者',
  `f_is_deleted` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否删除：0-否 1-是',
  PRIMARY KEY (`f_id`),
  KEY `idx_agent_app_key` (`f_agent_app_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='data agent 会话表';
```


#### 会话消息表
```
-- adp.t_data_agent_conversation_message definition

CREATE TABLE `t_data_agent_conversation_message` (
  `f_id` varchar(40) NOT NULL COMMENT '消息ID，消息唯一标识',
  `f_agent_app_key` varchar(40) NOT NULL COMMENT 'agent app key',
  `f_conversation_id` varchar(40) NOT NULL DEFAULT '' COMMENT '会话ID，会话唯一标识',
  `f_agent_id` varchar(40) NOT NULL COMMENT 'agent ID',
  `f_agent_version` varchar(32) NOT NULL COMMENT 'agent版本',
  `f_reply_id` varchar(40) NOT NULL DEFAULT '' COMMENT '回复消息ID，用于关联问答消息',
  `f_index` int(11) NOT NULL COMMENT '消息下标，用于标记消息在整个会话中的位置、顺序，比如基于Index正序在前端按照时间线展示对话消息',
  `f_role` varchar(255) NOT NULL COMMENT '产生消息的角色，支持一下角色：User: 用户；Assistant: 助手',
  `f_content` mediumtext NOT NULL COMMENT '消息内容，结构随角色类型变化。当角色为User时，用户输入包括文字和临时区文件（图片、文档、音视频）；当角色为Assistant时，包括最终返回结果和中间结果',
  `f_content_type` varchar(32) DEFAULT NULL COMMENT '内容类型',
  `f_status` varchar(32) DEFAULT NULL COMMENT '消息状态，随Role类型变化，Role为 User时：Received :  已接收(消息成功接收并持久化， 初始状态)Processed: 处理完成（成功触发后续的Agent Call）；Role为Assistant时：Processing： 生成中（消息正在生成中 ， 初始状态）Succeded： 生成成功（消息处理完成，返回成功）Failed： 生成失败（消息生成失败）Cancelled: 取消生成（用户、系统终止会话）',
  `f_ext` mediumtext NOT NULL COMMENT '预留扩展字段',
  `f_create_time` bigint(20) NOT NULL DEFAULT 0 COMMENT '创建时间',
  `f_update_time` bigint(20) NOT NULL DEFAULT 0 COMMENT '最后修改时间',
  `f_create_by` varchar(40) NOT NULL DEFAULT '' COMMENT '创建者',
  `f_update_by` varchar(40) NOT NULL DEFAULT '' COMMENT '最后修改者',
  `f_is_deleted` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否删除：0-否 1-是',
  PRIMARY KEY (`f_id`),
  KEY `idx_agent_app_key` (`f_agent_app_key`),
  KEY `idx_conversation_id` (`f_conversation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话消息表';
```


## 依赖

1. 查询部门下的用户接口
GoCommon/rest/user_management.DrivenUserMgnt.GetDepAllUsers

2. 批量查询户信息(含部门)接口
GoCommon/rest/user_management.DrivenUserMgnt.BatchGetUserInfoByID

