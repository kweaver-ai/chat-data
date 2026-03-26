package copilot

import (
	"context"
	"encoding/json"
	"strconv"

	"github.com/google/uuid"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
)

func (u *useCase) CognitiveResourceAnalysisSearch(ctx context.Context, req *CognitiveResourceAnalysisSearchReq) (*CognitiveResourceAnalysisSearchResp, error) {
	// 获取图谱id
	kgConfigId := settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	graphId, err := u.getGraphId(ctx, kgConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	args := make(map[string]any)

	args["query"] = req.Query
	args["limit"] = req.Size

	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}
	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	//myFilter["data_kind"] = "0"
	//myFilter["update_cycle"] = "[-1]"
	//myFilter["shared_type"] = "[-1]"
	//myFilter["department_id"] = "[-1]"
	//myFilter["info_system_id"] = "[-1]"
	//myFilter["owner_id"] = "[-1]"
	//myFilter["subject_id"] = "[-1]"
	//myFilter["start_time"] = "1600122122"
	//myFilter["end_time"] = "1800122122"
	//myFilter["asset_type"] = "[3]"
	args["filter"] = myFilter

	args["ad_appid"] = appid
	args["kg_id"] = graphId

	//entity2service, err := u.GetCognitiveSearchConfig(ctx, constant.DataResourceVersion)
	//if err != nil {
	//	return nil, err
	//}

	args["roles"] = []string{}
	args["entity2service"] = map[string]string{}
	args["required_resource"] = map[string]lexiconInfo{}

	uInfo := GetUserInfo(ctx)
	args["subject_id"] = uInfo.ID
	args["available_option"] = req.AvailableOption
	args["subject_type"] = "user"

	resp, err := u.adProxy.SailorCognitiveResourceAnalysisSearchEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	searchRest := CognitiveResourceAnalysisSearchResp{}
	i := 1
	for _, entity := range resp.Res.Entities {

		eId := ""
		eType := "data_view"
		eTitle := ""
		eTechnicalName := ""
		eCode := ""

		ePermission := entity.IsPermissions
		for _, prop := range entity.Entity.Properties[0].Props {
			if prop.Name == "resourceid" {
				eId = prop.Value
			}
			if prop.Name == "resourcename" {
				eTitle = prop.Value
			}
			if prop.Name == "technical_name" && prop.Value != "__NULL__" {
				eTechnicalName = prop.Value
			}
			if prop.Name == "code" && prop.Value != "__NULL__" {
				eCode = prop.Value
			}

		}
		eSerialNumber := i
		searchRest.Res.Entities = append(searchRest.Res.Entities, AnalysisEntity{eId, eType, eTitle, eSerialNumber, ePermission, eTechnicalName, eCode})
		i++
	}

	qAId, _ := uuid.NewRandom()

	searchRest.Res.Count = resp.Res.Count
	searchRest.Res.QaId = qAId.String()
	searchRest.Res.ExplanationFormView = resp.Res.ExplanationFormView
	searchRest.ResStatus = resp.ResStatus
	searchRest.ExplanationStatus = resp.ExplanationStatus

	return &searchRest, nil

}

func (u *useCase) CognitiveAnalysisSearchAnswerLike(ctx context.Context, qaId string, req *CognitiveAnalysisSearchAnswerLikeReq) (*CognitiveAnalysisSearchAnswerLikeResp, error) {
	var err error
	userid := ctx.Value(constant.UserId)
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	// 记录用户对答案是否喜欢
	log.WithContext(ctx).Infof("analysis search qa user_id:%s qa_id:%s like_status:%s", userid, qaId, req.Action)
	var resp CognitiveAnalysisSearchAnswerLikeResp

	resp.Res.Status = "success"

	return &resp, nil
}

func (u *useCase) CognitiveDataCatalogAnalysisSearch(ctx context.Context, req *CognitiveDataCatalogAnalysisSearchReq) (*CognitiveDataCatalogAnalysisSearchResp, error) {
	// 获取图谱id
	kgConfigId := settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	graphId, err := u.getGraphId(ctx, kgConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	args := make(map[string]any)

	args["query"] = req.Query
	args["limit"] = req.Size

	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}
	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	//myFilter["data_kind"] = "0"
	//myFilter["update_cycle"] = "[-1]"
	//myFilter["shared_type"] = "[-1]"
	//myFilter["department_id"] = "[-1]"
	//myFilter["info_system_id"] = "[-1]"
	//myFilter["owner_id"] = "[-1]"
	//myFilter["subject_id"] = "[-1]"
	//myFilter["start_time"] = "1600122122"
	//myFilter["end_time"] = "1800122122"
	//myFilter["asset_type"] = "[-1]"
	args["filter"] = myFilter

	args["ad_appid"] = appid
	args["kg_id"] = graphId

	//entity2service, err := u.GetCognitiveSearchConfig(ctx, constant.DataCatalogVersion)
	//if err != nil {
	//	return nil, err
	//}

	args["entity2service"] = map[string]Entity2Service{}

	args["roles"] = []string{}
	args["required_resource"] = map[string]lexiconInfo{}

	uInfo := GetUserInfo(ctx)
	args["subject_id"] = uInfo.ID
	args["available_option"] = req.AvailableOption
	args["subject_type"] = "user"

	resp, err := u.adProxy.SailorCognitiveDataCatalogAnalysisSearchEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	log.WithContext(ctx).Infof("\ncognitive analysis search req vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(args)).A, lo.T2(json.Marshal(resp)).A)

	searchRest := CognitiveDataCatalogAnalysisSearchResp{}
	i := 1
	for _, entity := range resp.Res.Entities {

		eId := ""
		eType := "data_view"
		eTitle := ""
		eTechnicalName := "data_view"
		eCode := ""
		ePermission := entity.IsPermissions
		for _, prop := range entity.Entity.Properties[0].Props {
			if prop.Name == "formview_uuid" {
				eId = prop.Value
			}
			if prop.Name == "business_name" {
				eTitle = prop.Value
			}
			if prop.Name == "technical_name" && prop.Value != "__NULL__" {
				eTechnicalName = prop.Value
			}
			if prop.Name == "code" && prop.Value != "__NULL__" {
				eCode = prop.Value
			}

		}
		eSerialNumber := i
		searchRest.Res.Entities = append(searchRest.Res.Entities, AnalysisEntity{eId, eType, eTitle, eSerialNumber, ePermission, eTechnicalName, eCode})
		i++
	}

	qAId, _ := uuid.NewRandom()

	searchRest.Res.Count = resp.Res.Count
	searchRest.Res.QaId = qAId.String()
	searchRest.Res.ExplanationFormView = resp.Res.ExplanationFormView
	searchRest.ResStatus = resp.ResStatus
	searchRest.ExplanationStatus = resp.ExplanationStatus

	return &searchRest, nil

}

type CognitiveDataCatalogFormViewSearchReq struct {
	CognitiveDataCatalogFormViewSearchReqBody `param_type:"body"`
}

type CognitiveDataCatalogFormViewSearchReqBody struct {
	Size int `json:"size,omitempty" binding:"omitempty,gt=0" default:"20" example:"20"` // 要获取到的记录条数

	NextFlag []string `json:"next_flag"` // 分页参数，从该参数后面开始获取数据

	Keyword   string   `json:"keyword" binding:"TrimSpace,min=1"`    // 关键字查询，字符无限制
	Stopwords []string `json:"stopwords" binding:"omitempty,unique"` // 智能搜索对象，停用词

	AvailableOption int    `json:"available_option" binding:"omitempty,gte=0,lte=2"`
	SearchType      string `json:"search_type" binding:"omitempty"`
}

type CognitiveDataCatalogDataViewSearchResp client.AssetSearchResp

func (u *useCase) CognitiveDataCatalogFormViewSearch(ctx context.Context, req *CognitiveDataCatalogFormViewSearchReq) (*CogSearchResp, error) {
	kgConfigId := settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	graphId, err := u.getGraphId(ctx, kgConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)
	args["query"] = req.Keyword
	args["limit"] = req.Size
	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}
	//args["stop_entity_infos"] = req.StopEntityInfos

	myFilter := make(map[string]any)
	myFilter["data_kind"] = []int{-1}
	myFilter["shared_type"] = []int{-1}
	myFilter["department_id"] = []int{-1}
	myFilter["subject_id"] = []int{-1}
	myFilter["owner_id"] = []int{-1}
	myFilter["info_system_id"] = []int{-1}
	myFilter["start_time"] = "0"
	myFilter["end_time"] = "0"
	myFilter["asset_type"] = []int{-1}

	myFilter["stop_entity_infos"] = []string{}

	args["filter"] = myFilter

	args["ad_appid"] = appid
	uInfo := GetUserInfo(ctx)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"
	args["available_option"] = req.AvailableOption
	if err != nil {
		return nil, err
	}
	args["kg_id"] = graphId
	args["entity2service"] = map[string]Entity2Service{}
	args["roles"] = []string{}

	required_resource := make(map[string]any)
	lexicon_actrieId, err := u.getAdLexiconId(ctx, "cognitive_search_synonyms")
	if err != nil {
		return nil, err
	}
	required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

	// 这里暂时写死
	stopwordsId, err := u.getAdLexiconId(ctx, "cognitive_search_stopwords")
	if err != nil {
		return nil, err
	}
	required_resource["stopwords"] = lexiconInfo{stopwordsId}

	args["required_resource"] = required_resource

	result := &CopilotAssetSearchResp{}

	if result == nil || len(result.Data.QueryCuts) <= 0 {

		//请求
		adResp, err := u.adProxy.CpRecommendAssetSearchEngineV3(ctx, &args)
		if err != nil {
			return nil, err
		}

		log.WithContext(ctx).Infof("\nassert search req vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(args)).A, lo.T2(json.Marshal(adResp)).A)

		var dag client.GraphSynSearchDAG
		if err = util.CopyUseJson(&dag.Outputs, &adResp.Res); err != nil {
			log.Error(err.Error())
			return nil, errorcode.Detail(errorcode.PublicInternalError, err)
		}

		//处理返回值
		result = readPropertiesFormView(dag.Outputs)

	}

	filterV2(req, result)

	resp := u.NewCogSearchResp(ctx, result, constant.DataResourceVersion)
	return resp, nil

}

func filterV2(reqData *CognitiveDataCatalogFormViewSearchReq, data *CopilotAssetSearchResp) {
	if data == nil || len(data.Data.Entities) <= 0 {
		return
	}
	var lastScore float64
	var lastID string
	if len(reqData.NextFlag) == 2 {
		lastScore = float64(lo.T2(strconv.Atoi(reqData.NextFlag[0])).A)
		lastID = reqData.NextFlag[1]
	}

	entities := make([]client.AssetSearchAnswerEntity, 0, reqData.Size)
	for _, entity := range data.Data.Entities {
		if entity.Score < lastScore || len(entities) >= reqData.Size || entity.Entity.VID == lastID {
			continue
		}

		entities = append(entities, entity)
	}
	data.Data.Entities = entities
	return
}
