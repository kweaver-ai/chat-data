package copilot

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

func (u *useCase) LogicalViewDataCategorize(ctx context.Context, req *LogicalViewDatacategorizeReq) (*LogicalViewDataCategorizeResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//var adReq ad_rec.CPRecommendCheckCodeReq
	//if err := util.CopyUseJson(&adReq, req); err != nil {
	//	log.WithContext(ctx).Error(err.Error())
	//	return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	//}
	//log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	//// 获取graphId
	//graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	//if err != nil {
	//	return nil, err
	//}
	//// 获取appid
	//appid, err := u.adProxy.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}
	//包装参数
	args := make(map[string]any)
	args["query"] = req
	args["graph_id"] = ""
	args["appid"] = "" // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.SailorLogicalViewDataCategorizeEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp LogicalViewDataCategorizeResp
	if err := util.CopyUseJson(&resp, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}
