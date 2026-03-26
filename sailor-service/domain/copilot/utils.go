package copilot

import (
	"context"
	"encoding/json"
	"strconv"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
)

type GenerateFakeSamplesReq struct {
	GenerateFakeSamplesReqBody `param_type:"body"`
}

type GenerateFakeSamplesReqBody struct {
	ViewId      string `json:"view_id" binding:"required"`
	SamplesSize int    `json:"samples_size" binding:"required,gt=0"`
	MaxRetry    int    `json:"max_retry"`
}
type SamplesItem struct {
	ColumnName  string      `json:"column_name"`
	ColumnValue interface{} `json:"column_value"`
}

type GenerateFakeSamplesResp struct {
	Res [][]*SamplesItem `json:"res"`
}

func (u *useCase) FormViewGenerateFakeSamples(ctx context.Context, req *GenerateFakeSamplesReq) (*GenerateFakeSamplesResp, error) {
	var err error
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()

	// 获取appid
	//appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}
	//包装参数
	args := make(map[string]any)
	//args["appid"] = appid
	userInfo := GetUserInfo(ctx)
	args["user_id"] = userInfo.ID
	args["view_id"] = req.ViewId
	args["samples_size"] = req.SamplesSize
	if req.MaxRetry == 0 {
		args["max_retry"] = 2
	} else {
		args["max_retry"] = req.MaxRetry
	}

	log.WithContext(ctx).Infof("\nreq vo:\n%s", lo.T2(json.Marshal(args)).A)

	//请求
	adResp, err := u.adProxy.SailorFormViewGenerateFakeSamples(ctx, args)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp GenerateFakeSamplesResp
	if err := util.CopyUseJson(&resp.Res, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

type GetKgConfigReq struct {
}

type GetKgConfigResp struct {
	CognitiveSearchDataCatalogGraphID  string `json:"cognitive_search_data_catalog_graph_id"`
	CognitiveSearchDataResourceGraphID string `json:"cognitive_search_data_resource_graph_id"`
	SmartRecommendationGraphID         string `json:"smart_recommendation_graph_id"`
	CognitiveSearchSynonymsID          string `json:"cognitive_search_synonyms_id"`
	CognitiveSearchStopWordsID         string `json:"cognitive_search_stopwords_id"`
	APPID                              string `json:"app_id"`
}

func (u *useCase) GetKgConfig(ctx context.Context, req *GetKgConfigReq) (*GetKgConfigResp, error) {
	var err error

	//处理返回值
	var resp GetKgConfigResp

	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	resp.APPID = appid

	cognitiveSearchDataResourceGraphID, err := u.adCfgHelper.GetGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId)
	if err != nil {
		return nil, err
	}

	resp.CognitiveSearchDataResourceGraphID = cognitiveSearchDataResourceGraphID

	CognitiveSearchDataCatalogGraphID, err := u.adCfgHelper.GetGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId)
	if err != nil {
		return nil, err
	}

	resp.CognitiveSearchDataCatalogGraphID = CognitiveSearchDataCatalogGraphID

	smartRecommendationGraphID, err := u.adCfgHelper.GetGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	if err != nil {
		return nil, err
	}

	resp.SmartRecommendationGraphID = smartRecommendationGraphID

	lexiconActrieId, err := u.getAdLexiconId(ctx, "cognitive_search_synonyms")
	if err != nil {
		return nil, err
	}

	resp.CognitiveSearchSynonymsID = lexiconActrieId

	stopwordsId, err := u.getAdLexiconId(ctx, "cognitive_search_stopwords")
	if err != nil {
		return nil, err
	}

	resp.CognitiveSearchStopWordsID = stopwordsId

	return &resp, nil
}

type RecommendOpenSearchReq struct {
}

type RecommendOpenSearchResp struct {
	Status string `json:"status"`
}

func (u *useCase) InitRecommendOpenSearch(ctx context.Context, req *RecommendOpenSearchReq) (*RecommendOpenSearchResp, error) {
	entitySubjectModelList, err := u.dbRepo.GetEntitySubjectModelList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entitySubjectModelList {
		objBase := es_subject_model.BaseObj{
			ID:             item.Id,
			BusinessName:   item.BusinessName,
			TechnicalName:  item.TechnicalName,
			DataViewID:     item.DataViewId,
			DisplayFieldID: "",
		}
		subjectModel := es_subject_model.SubjectModelDoc{
			DocID:   item.Id,
			BaseObj: objBase,
		}

		err = u.esClient.Index(ctx, &subjectModel)
		if err != nil {
			log.Info("fail index subject model")
			break
		}
	}

	entitySubjectModelLabelList, err := u.dbRepo.GetEntitySubjectModelLabelList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entitySubjectModelLabelList {
		objBase := es_subject_model.SubjectModelLabelDoc{
			DocID:           item.Id,
			ID:              item.Id,
			Name:            item.Name,
			RelatedModelIds: strings.Split(item.RelatedModelIds, ","),
		}

		err = u.esClient.IndexLabel(ctx, &objBase)
		if err != nil {
			log.Info("fail index subject model label")
			break
		}
	}

	// form view
	entityEntityFormViewList, err := u.dbRepo.GetEntityFormViewList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entityEntityFormViewList {
		indexData := es_subject_model.EntityFormView{
			DocID:         item.Id,
			ID:            item.Id,
			TechnicalName: item.TechnicalName,
			Name:          item.Name,
			Type:          item.Type,
			DatasourceID:  item.DatasourceId,
			SubjectID:     item.SubjectId,
			Description:   item.Description,
		}

		err = u.esClient.IndexEntityFormView(ctx, &indexData)
		if err != nil {
			log.Info("fail index form view")
			break
		}
	}

	// business_form_standard
	entityEntityFormList, err := u.dbRepo.GetEntityFormList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entityEntityFormList {
		indexData := es_subject_model.EntityFormDoc{
			DocID:           item.Id,
			ID:              item.Id,
			Name:            item.Name,
			BusinessModelID: item.BusinessModelId,
			Description:     item.Description,
		}

		err = u.esClient.IndexEntityFormDoc(ctx, &indexData)
		if err != nil {
			log.Info("fail index business_form_standard")
			break
			//return nil, err
		}
	}

	// DataElement
	entityEntityDataElementList, err := u.dbRepo.GetEntityDataElementList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entityEntityDataElementList {
		itemId := strconv.FormatInt(item.Id, 10)
		indexData := es_subject_model.EntityDataElement{
			DocID:         itemId,
			ID:            itemId,
			DepartmentIds: item.DepartmentIds,
			Code:          item.Code,
			NameCn:        item.NameCn,
			NameEN:        item.NameEn,
			StdType:       item.StdType,
		}

		err = u.esClient.IndexEntityDataElement(ctx, &indexData)
		if err != nil {
			log.Info("fail index data element")
			break
		}
	}

	// rule
	entityEntityRuleList, err := u.dbRepo.GetEntityRuleList(ctx)

	if err != nil {
		return nil, err
	}

	for _, item := range entityEntityRuleList {
		itemId := strconv.FormatInt(item.Id, 10)
		indexData := es_subject_model.EntityRuleDoc{
			DocID:         itemId,
			ID:            itemId,
			Name:          item.Name,
			CatalogId:     item.CategoryId,
			OrgType:       item.OrgType,
			Description:   item.Description,
			RuleType:      item.RuleType,
			Expression:    item.Expression,
			DepartmentIds: item.DepartmentIds,
		}
		err = u.esClient.IndexEntityRule(ctx, &indexData)
		if err != nil {
			log.Info("fail index data element")
			break
		}
	}

	// subject property
	entityEntitySubjectPropertyList, err := u.dbRepo.GetEntitySubjectPropertyList(ctx)
	for _, item := range entityEntitySubjectPropertyList {

		indexData := es_subject_model.EntitySubjectProperty{
			DocID:       item.Id,
			ID:          item.Id,
			Name:        item.Name,
			Description: item.Description,
			PathID:      item.PathId,
			Path:        item.Path,
			StandardID:  item.StandardId,
		}

		err = u.esClient.IndexEntitySubjectProperty(ctx, &indexData)
		if err != nil {
			log.Info("fail index subject property")
			break
		}
	}

	var resp RecommendOpenSearchResp

	resp.Status = "success"
	return &resp, nil

}
