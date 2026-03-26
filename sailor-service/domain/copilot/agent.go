package copilot

import (
	"context"
	"encoding/json"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/adp_agent_factory"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"

	//"fmt"
	"github.com/samber/lo"
)

const (
	LISTSTATUS = 1
	ALLSTATUS  = 0
)

func (u *useCase) GetAFAgentList(ctx context.Context, req *AFAgentListReq) (*AFAgentListResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	adpReq := adp_agent_factory.AgentListReq{
		Name:                req.Name,
		Size:                req.Size,
		PaginationMarkerStr: req.PaginationMarkerStr,
	}

	agentList, err := u.qaRepo.GetAgentList(ctx)
	if err != nil {
		return nil, err
	}
	agentKeys := []string{}
	agentKey2AFAgent := map[string]string{}
	for _, item := range agentList {
		agentKeys = append(agentKeys, item.AdpAgentKey)
		agentKey2AFAgent[item.AdpAgentKey] = item.ID
	}
	if req.ListFlag == LISTSTATUS {
		adpReq.AgentKeys = agentKeys
		adpReq.Ids = []string{}
		adpReq.ExcludeAgentKeys = []string{}
		adpReq.BusinessDomainIds = []string{}

	}
	//if err := util.CopyUseJson(&adReq, req); err != nil {
	//	log.WithContext(ctx).Error(err.Error())
	//	return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	//}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adpReq)).A)

	//请求
	adpResp, err := u.adpAgentFactory.AgentList(ctx, adpReq)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp AFAgentListResp
	if err := util.CopyUseJson(&resp, &adpResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	var entityList []adp_agent_factory.AgentItem
	for i := range resp.Entries {

		val1, ok1 := agentKey2AFAgent[resp.Entries[i].Key]
		if ok1 {
			resp.Entries[i].AFAgentID = val1
			resp.Entries[i].ListStatus = "put-on"
			entityList = append(entityList, resp.Entries[i])

		} else {
			resp.Entries[i].ListStatus = "pull-off"
		}
	}

	//resp.Entries = entityList

	return &resp, nil
}

func (u *useCase) PutOnAFAgent(ctx context.Context, req *PutOnAFAgentReq) (*PutOnAFAgentResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	for _, item := range req.AgentList {
		_, err := u.qaRepo.InsertAgent(ctx, item.AgentKey)
		if err != nil {
			return nil, err
		}
	}

	resp := PutOnAFAgentResp{}
	resp.Res.Status = "success"

	return &resp, err
}

func (u *useCase) PullOffAgent(ctx context.Context, req *PullOffAFAgentReq) (*PullOffAFAgentResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	err = u.qaRepo.DeleteAgent(ctx, req.AfAgentId)

	if err != nil {
		return nil, err
	}

	resp := PullOffAFAgentResp{}
	resp.Res.Status = "success"

	return &resp, err
}
