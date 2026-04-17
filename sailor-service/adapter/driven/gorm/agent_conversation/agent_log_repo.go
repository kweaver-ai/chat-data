package agent_conversation

import (
	"context"
	"fmt"
	"strings"

	llmDriver "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type repo struct {
	data *db.Data
}

// NewAgentConversationLogRepo gorm 查询实现：返回 domain 侧需要的接口类型
func NewAgentConversationLogRepo(data *db.Data) llmDriver.AgentConversationLogRepo {
	return &repo{data: data}
}

func (r *repo) do(ctx context.Context) *gorm.DB {
	return r.data.DB.WithContext(ctx)
}

func (r *repo) ListAgentConversationLogList(ctx context.Context, filter llmDriver.AgentConversationLogFilter) (items []llmDriver.AgentConversationLogMessage, total int64, err error) {
	conditions := make([]string, 0, 6)
	args := make([]any, 0, 10)

	conditions = append(conditions, "m.f_is_deleted=0")
	conditions = append(conditions, "c.f_is_deleted=0")

	if filter.StartTime != nil {
		conditions = append(conditions, "m.f_create_time >= ?")
		args = append(args, *filter.StartTime)
	}
	if filter.EndTime != nil {
		conditions = append(conditions, "m.f_create_time <= ?")
		args = append(args, *filter.EndTime)
	}
	if len(filter.UserIDs) > 0 {
		conditions = append(conditions, "c.f_create_by in ?")
		args = append(args, filter.UserIDs)
	}
	if strings.TrimSpace(filter.Keyword) != "" {
		kw := "%" + strings.TrimSpace(filter.Keyword) + "%"
		// 文档要求：keyword 模糊搜索内容为 t_data_agent_conversation_message.f_content
		conditions = append(conditions, "m.f_content like ?")
		args = append(args, kw)
	}

	whereSQL := strings.Join(conditions, " AND ")
	countSQL := fmt.Sprintf(
		"select count(1) from adp.t_data_agent_conversation_message m "+
			"join adp.t_data_agent_conversation c on c.f_id = m.f_conversation_id "+
			"where %s",
		whereSQL,
	)

	if err = r.do(ctx).Raw(countSQL, args...).Scan(&total).Error; err != nil {
		return nil, 0, errors.Wrap(err, "list agent conversation log count failed")
	}

	if filter.Limit <= 0 {
		return nil, total, nil
	}
	if filter.Offset < 0 {
		filter.Offset = 0
	}
	orderDirection := "desc"
	if strings.EqualFold(strings.TrimSpace(filter.Direction), "asc") {
		orderDirection = "asc"
	}
	orderField := "m.f_create_time"
	if strings.EqualFold(strings.TrimSpace(filter.Sort), "update_time") {
		orderField = "m.f_update_time"
	}

	dataSQL := fmt.Sprintf(
		"select "+
			"	m.f_create_time as create_time, "+
			"	c.f_create_by as creator_user_id, "+
			"	m.f_role as role, "+
			"	m.f_content as content, "+
			"	m.f_ext as ext "+
			"from adp.t_data_agent_conversation_message m "+
			"join adp.t_data_agent_conversation c on c.f_id = m.f_conversation_id "+
			"where %s "+
			"order by %s %s, m.f_index %s "+
			"limit ? offset ?",
		whereSQL, orderField, orderDirection, orderDirection,
	)

	argsWithPage := append(args, filter.Limit, filter.Offset)
	if err = r.do(ctx).Raw(dataSQL, argsWithPage...).Scan(&items).Error; err != nil {
		return nil, 0, errors.Wrap(err, "list agent conversation log list failed")
	}

	return items, total, nil
}
