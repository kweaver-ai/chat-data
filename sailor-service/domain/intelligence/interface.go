package intelligence

import "context"

type UseCase interface {
	TableSampleData(ctx context.Context, req *SampleDataReq) (*SampleDataResp, error)
	// AgentConversationLogList 查询智能助手问答会话日志列表
	AgentConversationLogList(ctx context.Context, req *AgentConversationLogListReq) (*AgentConversationLogListResp, error)
}

type SampleItem map[string]any

type SampleDataReq struct {
	SampleDataReqBody `param_type:"body"`
}

type SampleDataReqBody struct {
	Titles  []string     `json:"titles" form:"titles" binding:"required"`
	Example []SampleItem `json:"example" form:"example"`
	Differs []string     `json:"differs" form:"differs"`
}

type SampleDataResp struct {
	Count      int          `json:"count"`
	SampleData []SampleItem `json:"sample_data"`
}

// AgentConversationLogListReq 智能助手问答记录列表入参
type AgentConversationLogListReq struct {
	AgentConversationLogListReqBody `param_type:"query"`
}

// AgentConversationLogListReqBody  智能助手问答记录列表入参
type AgentConversationLogListReqBody struct {
	Offset    int    `json:"offset" form:"offset,default=1" binding:"omitempty,min=1" default:"1"`                                         // 页码，默认1
	Limit     int    `json:"limit" form:"limit,default=10" binding:"omitempty,min=1,max=100" default:"10"`                                 // 每页大小，默认10
	Direction string `json:"direction" form:"direction,default=desc" binding:"omitempty,oneof=asc desc" default:"desc"`                    // 排序方向，枚举：asc：正序；desc：倒序。默认倒序
	Sort      string `json:"sort" form:"sort,default=create_time" binding:"omitempty,oneof=create_time update_time" default:"create_time"` // 排序类型，枚举：create_time：按创建时间排序；update_time：按更新时间排序；默认按创建时间排序

	// 时间范围（创建时间，毫秒时间戳）
	StartTime *int64 `json:"start_time" form:"start_time" binding:"omitempty,gte=0"`
	EndTime   *int64 `json:"end_time" form:"end_time" binding:"omitempty,gte=0"`

	// 部门ID（问题创建者的部门ID）
	DepartmentID string `json:"department_id" form:"department_id,uuid" binding:"omitempty"`

	// 用户ID（问题创建者ID）
	UserID string `json:"user_id" form:"user_id" binding:"omitempty,uuid"`

	// 关键词模糊搜索内容为问题或答案（非必填）
	Keyword string `json:"keyword" form:"keyword" binding:"omitempty,TrimSpace,min=1"`
}

// AgentConversationLogListResp 智能助手问答记录列表出参
type AgentConversationLogListResp struct {
	Entries    []AgentConversationLogItem `json:"entries"`
	TotalCount int64                      `json:"total_count"`
}

type AgentConversationLogItem struct {
	CreatedAt  int64  `json:"created_at"` // 创建时间
	Department string `json:"department"`
	User       string `json:"user_name"`
	UserID     string `json:"user_id"`
	Type       string `json:"type"` // 问题/答案

	// Result 结果（问题：原始内容；答案：final_answer）
	Result any `json:"result"`
	// ProcessJson 过程json（答案：middle_answer）
	ProcessJson any `json:"process_json"`
}
