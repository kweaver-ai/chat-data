package knowledge_build

import (
	"context"
	"fmt"

	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"

	repo "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
)

type Helper interface {
	GetGraphId(ctx context.Context, cfgId string) (string, error)
	GetGraphAnalysisId(ctx context.Context, cfgId string) (string, error)
	GetSearchEngineId(ctx context.Context, cfgId string) (string, error)
	GetLexiconId(ctx context.Context, cfgId string) (string, error)
	GetLexiconIds(ctx context.Context, cfgId string) ([]string, error)
	GetGraphAnalysisInfo(ctx context.Context) (map[string]string, error)
	GetNetworkId(ctx context.Context, cfgId string) (string, error)
	//GetSearchEngineId(ctx context.Context, cfgId string) (string, error)
	//GetAnalysisGraphInfo(ctx context.Context, cfgId string) (string, error)
}

func GetGraphId(ctx context.Context, kgType string, helper Helper) (string, error) {
	resMapCfg := settings.GetConfig().KnowledgeNetworkResourceMap
	cfgId := lo.Switch[string, string](kgType).
		Case(client.GraphTypeBusinessRelations, resMapCfg.AFBusinessRelationsGraphConfigId).
		Case(client.GraphTypeConsanguinity, resMapCfg.LineageGraphConfigId).
		Case(client.GraphTypeDataAssets, resMapCfg.DataAssetsGraphConfigId).
		Default(resMapCfg.LineageGraphConfigId) // 默认血缘图谱id，兼容之前的逻辑

	if len(cfgId) < 1 {
		log.WithContext(ctx).Errorf("unknown graph type: %v", kgType)
		return "", fmt.Errorf("unknown graph type: %v", kgType)
	}

	return helper.GetGraphId(ctx, cfgId)
}

func GetGraphAnalysisServiceId(ctx context.Context, kgAnalysisType string, helper Helper) (string, error) {
	//resMapCfg := settings.GetConfig().KnowledgeNetworkResourceMap
	cfgId := lo.Switch[string, string](kgAnalysisType).
		Default("")

	if len(cfgId) < 1 {
		log.WithContext(ctx).Errorf("unknown graph analysis service type: %v", kgAnalysisType)
		return "", fmt.Errorf("unknown graph analysis service type: %v", kgAnalysisType)
	}

	return helper.GetGraphAnalysisId(ctx, cfgId)
}

type helper struct {
	repo repo.Repo
}

func NewHelper(repo repo.Repo) Helper {
	return &helper{repo: repo}
}

func (h *helper) getIdByTypeAndCfgId(ctx context.Context, tpe KNResourceType, cfgId string) (string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	m, err := h.repo.GetInfoByTypeAndConfigId(ctx, tpe.ToInt32(), cfgId)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get knowledge network resource id, tpe: %v, cfg id: %v, err: %+v", tpe, cfgId, err)
		return "", errorcode.Detail(errorcode.PublicInternalError, errors.Cause(err))
	}
	if m == nil {
		return "", errorcode.Desc(errorcode.AnyDataConfigError)
	}
	return m.RealID, nil
}

func (h *helper) getIdsByTypeAndCfgId(ctx context.Context, tpe KNResourceType, cfgId string) ([]string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	m, err := h.repo.GetInfosByTypeAndConfigId(ctx, tpe.ToInt32(), cfgId)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get knowledge network resource id, tpe: %v, cfg id: %v, err: %+v", tpe, cfgId, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, errors.Cause(err))
	}
	if m == nil {
		return nil, errorcode.Desc(errorcode.AnyDataConfigError)
	}
	//var mi = len(m)
	var mm = []string{}
	for _, elem := range m {
		mm = append(mm, elem.RealID)
	}
	return mm, nil
}

// 获取图分析服务配置
func (h *helper) GetGraphAnalysisInfo(ctx context.Context) (map[string]string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	m, err := h.repo.ListInfoByType(ctx, KNResourceTypeDomainAnalysis.ToInt32())
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get knowledge network anslysis: %v, err: %+v", KNResourceTypeDomainAnalysis, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, errors.Cause(err))
	}
	if m == nil {
		return nil, errorcode.Desc(errorcode.AnyDataConfigError)
	}

	var mm = map[string]string{}
	for _, elem := range m {
		mm[elem.ConfigID] = elem.RealID
	}
	return mm, nil

}

func (h *helper) GetGraphId(ctx context.Context, cfgId string) (string, error) {
	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeKnowledgeGraph, cfgId)
}

func (h *helper) GetNetworkId(ctx context.Context, cfgId string) (string, error) {
	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeKnowledgeNetwork, cfgId)
}

func (h *helper) GetGraphAnalysisId(ctx context.Context, cfgId string) (string, error) {
	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeDomainAnalysis, cfgId)
}

func (h *helper) GetSearchEngineId(ctx context.Context, cfgId string) (string, error) {
	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeSearchEngine, cfgId)
}

func (h *helper) GetLexiconId(ctx context.Context, cfgId string) (string, error) {
	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeLexiconService, cfgId)
}

func (h *helper) GetLexiconIds(ctx context.Context, cfgId string) ([]string, error) {
	return h.getIdsByTypeAndCfgId(ctx, KNResourceTypeLexiconService, cfgId)
}

//func (h *helper) GetSearchEngineId(ctx context.Context, cfgId string) (string, error) {
//	return h.getIdByTypeAndCfgId(ctx, KNResourceTypeSearchEngine, cfgId)
//}

func (h *helper) GetSearchConfigByIds(ctx context.Context, cfgIds ...string) ([]*model.KnowledgeNetworkInfo, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	m, err := h.repo.ListInfoByConfigIds(ctx, cfgIds...)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get knowledge network resource id, tpcfgIdse: %v, err: %+v", cfgIds, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, errors.Cause(err))
	}
	if m == nil {
		return nil, errorcode.Desc(errorcode.AnyDataConfigError)
	}
	return m, nil
}
