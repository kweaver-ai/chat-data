package alg_server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
	"go.uber.org/zap"
)

type useCase struct {
	adProxy             knowledge_network.AD
	adCfgHelper         knowledge_build.Helper
	configurationCenter configuration_center.DrivenConfigurationCenter
}

func NewUseCase(adProxy knowledge_network.AD, cfgHelper knowledge_build.Helper, configurationCenter configuration_center.DrivenConfigurationCenter) UseCase {
	return &useCase{adProxy: adProxy, adCfgHelper: cfgHelper, configurationCenter: configurationCenter}
}

func (u *useCase) FullText(ctx context.Context, req *FullTextReq) (*FullTextResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := knowledge_build.GetGraphId(ctx, req.KgType, u.adCfgHelper)
	if err != nil {
		return nil, err
	}
	req.KgId = graphId

	return u.fullText(ctx, req)
}

func (u *useCase) fullText(ctx context.Context, req *FullTextReq) (*FullTextResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	searchCfg := make([]*knowledge_network.SearchConfig, 0)
	if err := util.CopyUseJson(&searchCfg, req.SearchConfig); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	adResp, err := u.adProxy.FulltextSearch(ctx, req.KgId, req.Query, searchCfg)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataAuthError) {
			return nil, err
		}
		if errorcode.IsSameErrorCode(err, errorcode.PublicServiceInternalError) {
			return nil, errorcode.Desc(errorcode.AnyDataServiceError)
		}
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataConnectionError) {
			return nil, errorcode.Desc(errorcode.AnyDataConnectionError)
		}
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	var resp FullTextResp
	if err := util.CopyUseJson(&resp, adResp); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) Neighbors(ctx context.Context, req *NeighborsReq) (*NeighborsResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := knowledge_build.GetGraphId(ctx, req.KgType, u.adCfgHelper)
	if err != nil {
		return nil, err
	}
	req.Id = graphId

	adResp, err := u.adProxy.NeighborSearch(ctx, req.Vid, req.Steps, req.Id)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	var resp NeighborsResp
	if err = util.CopyUseJson(&resp, adResp); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	// 特殊处理，ad变更的响应参数的形式，导致上层不兼容，这里改回来
	// 之前: t_lineage_edge_table:"d06bd642141b9715c7ba23409fa60737"->"349f5850cca21eeecf12f118f7aa8475"
	// 现在: t_lineage_edge_table:738f0f22c0548f9f4e2b505ee4f1c295-4ea708fb9d826a77cdba9b132f3e7b3f
	for i, res := range resp.Res.VResult {
		for j, vertex := range res.Vertexes {
			for k, edge := range vertex.InEdges {
				idx := strings.IndexByte(edge, ':')
				if idx < 0 {
					continue
				}

				val := edge[idx+1:]
				if strings.Contains(val, `"->"`) {
					continue
				}

				val = `"` + val[:32] + `"->"` + val[33:] + `"`
				resp.Res.VResult[i].Vertexes[j].InEdges[k] = edge[:idx+1] + val
			}
		}
	}

	log.WithContext(ctx).Infof("neighbors resp: %s", lo.T2(json.Marshal(resp)).A)
	return &resp, nil
}

func (u *useCase) Iframe(ctx context.Context, req *IframeReq) (rurl string, err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	defer func() {
		if e := recover(); e != nil {
			log.WithContext(ctx).Error("iframe panic", zap.Any("panic", e))
			rurl = ""
			err = fmt.Errorf("iframe panic %v", req.ID)
			return
		}
	}()
	//调用全文搜索接口，返回vid
	serviceId, graphId, err := GetServiceConfigIDByName(ctx, req.ServiceName, u.adCfgHelper, "")
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get analysis service id by name, err: %v", err)
		return "", err
	}

	fullTextQuery := &FullTextReq{
		FullTextReqBody{
			Query: "",
			KgId:  graphId,
			SearchConfig: []client.SearchConfigItem{
				{
					Tag: req.Entity,
					Properties: []*client.SearchProp{
						{
							Name:      req.PropName,
							Operation: "eq",
							OpValue:   req.ID,
						},
					},
				},
			},
		},
	}
	fullTextQueryResult, err := u.fullText(ctx, fullTextQuery)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return "", err
	}
	if len(fullTextQueryResult.Res.Result) == 0 || len(fullTextQueryResult.Res.Result[0].Vertexs) == 0 {
		log.WithContext(ctx).Errorf("fulltext search result not found, data-catalog id: %s", req.ID)
		return "", errorcode.Desc(errorcode.FullTextSearchEmptyError)
	}
	vid := fullTextQueryResult.Res.Result[0].Vertexs[0].Id
	//获取APPID
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return "", errorcode.Detail(errorcode.AnyDataAuthError, err.Error())
	}
	//拼接重定向的URL地址
	cfg := settings.GetConfig().AnyDataConf
	direction := cfg.URL + "/iframe/graph"
	query, _ := url.Parse(direction)
	values := query.Query()
	values.Set("appid", appid)
	values.Set("operation_type", "neighbors")
	values.Set("service_id", serviceId)
	values.Set("steps", "4")
	values.Set("iframeFrom", "af-template-asset")
	values.Set("vids", vid)
	return fmt.Sprintf("%s?%s", query.String(), values.Encode()), nil
}

func (u *useCase) GraphAnalysis(ctx context.Context, req *GraphAnalysisReq) (resp *GraphAnalysisResp, err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	dataVersion := ""
	afVersion, err := u.configurationCenter.DataUseType(ctx)
	if err == nil {
		if afVersion.Using == 1 {
			dataVersion = "data-catalog"
		} else if afVersion.Using == 2 {
			dataVersion = "data-resource"
		}
	}

	//如果是单个实体
	if req.GraphAnalysisReqBody.ServiceName == AssetSubgraphService && req.GraphAnalysisReqBody.IsSingle() {
		return u.entityGraphAnalysis(ctx, req, dataVersion)
	}
	return u.subGraphAnalysis(ctx, req, dataVersion)
}

func (u *useCase) entityGraphAnalysis(ctx context.Context, req *GraphAnalysisReq, dataVersion string) (resp *GraphAnalysisResp, err error) {
	serviceId, _, err := GetServiceConfigIDByName(ctx, AssetSubgraphEntityService, u.adCfgHelper, dataVersion)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get analysis service id by name, err: %v", err)
		return nil, err
	}
	args := make(map[string]any)
	args["vid"] = req.End
	data, err := u.adProxy.GraphAnalysis(ctx, serviceId, args)
	if err != nil {
		return nil, err
	}
	respData := GraphAnalysisResp(*data)
	return &respData, err
}
func (u *useCase) subGraphAnalysis(ctx context.Context, req *GraphAnalysisReq, dataVersion string) (resp *GraphAnalysisResp, err error) {
	serviceId, _, err := GetServiceConfigIDByName(ctx, req.ServiceName, u.adCfgHelper, dataVersion)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get analysis service id by name, err: %v", err)
		return nil, err
	}
	args := make(map[string]any)
	args["end_vid"] = req.End
	args["start_vids"] = string(lo.T2(json.Marshal(req.Starts)).A)
	data, err := u.adProxy.GraphAnalysis(ctx, serviceId, args)
	if err != nil {
		return nil, err
	}
	respData := GraphAnalysisResp(*data)
	return &respData, err
}
