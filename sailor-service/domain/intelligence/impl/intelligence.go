package impl

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/user_management"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/intelligence"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
)

type useCase struct {
	llm          large_language_model.OpenAI
	agentLogRepo large_language_model.AgentConversationLogRepo
	userMgnt     user_management.DrivenUserMgnt
	cc           configuration_center.DrivenConfigurationCenter
}

func NewUseCase(
	llm large_language_model.OpenAI,
	agentLogRepo large_language_model.AgentConversationLogRepo,
	userMgnt user_management.DrivenUserMgnt,
	cc configuration_center.DrivenConfigurationCenter,
) intelligence.UseCase {
	return &useCase{
		llm:          llm,
		agentLogRepo: agentLogRepo,
		userMgnt:     userMgnt,
		cc:           cc,
	}
}

func (u useCase) TableSampleData(ctx context.Context, req *intelligence.SampleDataReq) (*intelligence.SampleDataResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	prompt := fmt.Sprintf(intelligence.SampleDataPromptNoExample, intelligence.Example1,
		intelligence.Example2, req.Titles, req.Differs)
	if len(req.Example) > 0 {
		prompt = fmt.Sprintf(intelligence.SampleDataPromptWithExample, intelligence.Example1,
			intelligence.Example2, req.Titles, req.Example, req.Differs)
	}
	result, err := u.llm.ChatGPT35(ctx, prompt)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, err
	}
	samples, err := util.GetJsonInAnswer[intelligence.SampleDataResp](result)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, err
	}
	return samples, nil
}

func (u useCase) AgentConversationLogList(ctx context.Context, req *intelligence.AgentConversationLogListReq) (*intelligence.AgentConversationLogListResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if req.Offset <= 0 {
		req.Offset = 1
	}
	if req.Limit <= 0 {
		req.Limit = 10
	}

	filter := large_language_model.AgentConversationLogFilter{
		StartTime: req.StartTime,
		EndTime:   req.EndTime,
		Keyword:   req.Keyword,
		Limit:     req.Limit,
		Offset:    (req.Offset - 1) * req.Limit,
		Direction: req.Direction,
		Sort:      req.Sort,
	}

	// 文档要求：结束时间需要大于开始时间
	if req.StartTime != nil && req.EndTime != nil && *req.EndTime <= *req.StartTime {
		return nil, errorcode.Detail(errorcode.PublicInvalidParameter, "end_time must be greater than start_time")
	}

	// 部门过滤：先拿到部门下所有用户ID
	if strings.TrimSpace(req.UserID) != "" {
		userInfo, err := u.userMgnt.GetUserInfoByID(ctx, req.UserID)
		if err != nil {
			return nil, errorcode.Detail(errorcode.GetUserInfoFailed, err.Error())
		}
		if userInfo.Account == "" {
			return nil, errorcode.Detail(errorcode.PublicInvalidParameter, "用户不存在")
		}
		filter.UserIDs = []string{strings.TrimSpace(req.UserID)}
	} else if strings.TrimSpace(req.DepartmentID) != "" {
		filter.UserIDs, err = u.userMgnt.GetDepAllUsers(ctx, strings.TrimSpace(req.DepartmentID))
		if err != nil {
			log.WithContext(ctx).Error(err.Error())
			return nil, errorcode.Detail(errorcode.GetDepartmentPrecision, err.Error())
		}
	}

	messages, total, err := u.agentLogRepo.ListAgentConversationLogList(ctx, filter)
	if err != nil {
		return nil, errorcode.Detail(errorcode.PublicDatabaseError, err.Error())
	}

	resp := &intelligence.AgentConversationLogListResp{
		Entries:    make([]intelligence.AgentConversationLogItem, 0, len(messages)),
		TotalCount: total,
	}
	if len(messages) == 0 {
		return resp, nil
	}

	// 补齐用户/部门字段
	userIDs := make([]string, 0, len(messages))
	seen := make(map[string]struct{}, len(messages))
	for _, msg := range messages {
		if msg.CreatorUserID == "" {
			continue
		}
		if _, ok := seen[msg.CreatorUserID]; ok {
			continue
		}
		seen[msg.CreatorUserID] = struct{}{}
		userIDs = append(userIDs, msg.CreatorUserID)
	}

	userInfoMap, err := u.userMgnt.BatchGetUserInfoByID(ctx, userIDs)
	if err != nil {
		// 查询日志不依赖用户信息：兜底返回
		log.WithContext(ctx).Error(err.Error())
		userInfoMap = make(map[string]configuration_center.UserInfo)
	}

	deptNameMap := make(map[string]string, len(userIDs))
	for _, uid := range userIDs {
		// 优先使用批量接口结果（文档要求含部门/Groups）
		userInfo, ok := userInfoMap[uid]
		if !ok {
			continue
		}
		if len(userInfo.ParentDeps) > 0 {
			deptNameMap[userInfo.ID] = strings.Join(lo.Times(len(userInfo.ParentDeps[0]), func(index int) string {
				return userInfo.ParentDeps[0][index].Name
			}), "/")
		}
	}

	for _, msg := range messages {
		itemType := "other"
		switch strings.ToLower(strings.TrimSpace(msg.Role)) {
		case "user":
			itemType = "问题"
		case "assistant":
			itemType = "答案"
		default:
			itemType = msg.Role
		}

		uName := msg.CreatorUserID
		if info, ok := userInfoMap[msg.CreatorUserID]; ok {
			if strings.TrimSpace(info.VisionName) != "" {
				uName = info.VisionName
			} else if strings.TrimSpace(info.Account) != "" {
				uName = info.Account
			}
		}

		var result any = msg.Content
		var processJson any = nil
		// 文档要求：f_content 结构是 { final_answer: {...}, middle_answer: {...} }
		// 且 final_answer -> 结果，middle_answer -> 过程json
		if itemType == "答案" {
			type assistantContent struct {
				FinalAnswer  any `json:"final_answer"`
				MiddleAnswer any `json:"middle_answer"`
			}
			var ac assistantContent
			if errTmp := json.Unmarshal([]byte(msg.Content), &ac); errTmp == nil {
				result = ac.FinalAnswer
				processJson = ac.MiddleAnswer
			} else {
				// 非 JSON 则兜底：把原 content 作为结果
				result = msg.Content
				processJson = nil
			}
		} else if itemType == "问题" {
			// 文档要求：f_role=user 时，f_content 结构如下，result 取 text
			type userContent struct {
				Text string `json:"text"`
			}
			var uc userContent
			if errTmp := json.Unmarshal([]byte(msg.Content), &uc); errTmp == nil {
				result = uc.Text
				processJson = nil
			} else {
				// 非 JSON 则兜底：把原 content 作为结果
				result = msg.Content
				processJson = nil
			}
		}

		resp.Entries = append(resp.Entries, intelligence.AgentConversationLogItem{
			CreatedAt:   msg.CreateTime,
			Department:  deptNameMap[msg.CreatorUserID],
			User:        uName,
			UserID:      msg.CreatorUserID,
			Type:        itemType,
			Result:      result,
			ProcessJson: processJson,
		})
	}

	return resp, nil
}
