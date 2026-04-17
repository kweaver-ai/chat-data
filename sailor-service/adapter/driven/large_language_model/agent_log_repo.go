
package large_language_model

import (
	"context"
)

// AgentConversationLogRepo 智能助手问答会话日志查询仓库
type AgentConversationLogRepo interface {
	// ListAgentConversationLogList 返回分页后的会话消息列表及总数
	ListAgentConversationLogList(ctx context.Context, filter AgentConversationLogFilter) (items []AgentConversationLogMessage, total int64, err error)
}

// AgentConversationLogFilter 查询条件
type AgentConversationLogFilter struct {
	StartTime *int64
	EndTime   *int64
	UserIDs   []string
	Keyword   string

	Offset    int
	Limit     int
	Direction string
	Sort      string
}

// AgentConversationLogMessage 会话消息（原始字段）
type AgentConversationLogMessage struct {
	CreateTime    int64  `gorm:"column:create_time"`
	CreatorUserID string `gorm:"column:creator_user_id"`
	Role          string `gorm:"column:role"`
	Content       string `gorm:"column:content"`
	Ext           string `gorm:"column:ext"`
}

// 注意：具体 gorm 实现放在 `adapter/driven/gorm/agent_conversation` 包内，
// 避免该包与 gorm 实现形成 import cycle。

