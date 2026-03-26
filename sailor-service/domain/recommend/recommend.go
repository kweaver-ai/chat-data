package recommend

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	ad_rec "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/ad_rec"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"go.uber.org/zap"
	"gorm.io/gorm"
)

type useCase struct {
	adProxy     knowledge_network.AD
	adCfgHelper knowledge_build.Helper
	data        *db.Data
}

func NewUseCase(adProxy knowledge_network.AD, cfgHelper knowledge_build.Helper, db *db.Data) UseCase {
	return &useCase{
		adProxy:     adProxy,
		adCfgHelper: cfgHelper,
		data:        db,
	}
}

func (u *useCase) getServiceId(ctx context.Context, cfgId string) (string, error) {
	srvCfgId, err := u.adCfgHelper.GetSearchEngineId(ctx, cfgId)
	if err != nil {
		return "", err
	}
	if len(srvCfgId) < 1 {
		return "", nil
	}
	return srvCfgId, nil
}

func (u *useCase) TableRecommendation(ctx context.Context, req *TableRecommendationReq) (*TableRecommendationResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.TableReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	//获取serviceId
	serviceId, err := u.getServiceId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.FormRecommendConfigId)
	if err != nil {
		return nil, err
	}
	//包装参数
	args := make(map[string]any)
	args["af_query"] = adReq

	//请求
	adResp, err := u.adProxy.SearchEngine(ctx, serviceId, &args)
	if err != nil {
		return nil, err
	}

	var dag client.RecommdedDAG
	if err = util.CopyUseJson(&dag, &adResp.Res.RecommdedDAG); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//处理返回值
	var resp TableRecommendationResp
	if err := util.CopyUseJson(&resp, &dag.Outputs.GraphRecommendAnswerList); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) FlowRecommendation(ctx context.Context, req *FlowRecommendationReq) (*FlowRecommendationResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.FlowReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//获取serviceId
	serviceId, err := u.getServiceId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.FlowRecommendConfigId)
	if err != nil {
		return nil, err
	}
	//包装参数
	args := make(map[string]any)
	args["af_query"] = adReq

	adResp, err := u.adProxy.SearchEngine(ctx, serviceId, &args)
	if err != nil {
		return nil, err
	}

	var dag client.RecommdedDAG
	if err = util.CopyUseJson(&dag, &adResp.Res.RecommdedDAG); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	var resp FlowRecommendationResp
	if err := util.CopyUseJson(&resp, &dag.Outputs.GraphRecommendAnswerList); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) FieldStandardRecommendation(ctx context.Context, req *FieldStandardRecommendationReq) (*FieldStandardRecommendationResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.FieldStandardizationReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)
	//获取serviceId
	serviceId, err := u.getServiceId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.FieldStandardRecommendConfigId)
	if err != nil {
		return nil, err
	}
	//包装参数
	args := make(map[string]any)
	args["query"] = adReq

	adResp, err := u.adProxy.SearchEngine(ctx, serviceId, &args)
	if err != nil {
		return nil, err
	}

	var dag client.RecommdedDAG
	if err = util.CopyUseJson(&dag, &adResp.Res.RecommendCodeDAG); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	var resp FieldStandardRecommendationResp
	if err := util.CopyUseJson(&resp, &dag.Outputs.GraphRecommendAnswerList); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//标准推荐的返回字段类型被改了，下面的逻辑转换下类型,
	for i := 0; i < len(resp.TableFields); i++ {
		for j := 0; j < len(resp.TableFields[i].RecStds); j++ {
			code, _ := strconv.ParseInt(fmt.Sprintf("%s", resp.TableFields[i].RecStds[j].StdCode), 10, 64)
			resp.TableFields[i].RecStds[j].StdCode = code
		}
	}
	return &resp, nil
}

func (u *useCase) CheckCode(ctx context.Context, req *CheckCodeReq) (*CheckCodeResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	adReq := make([]*ad_rec.CheckFieldsReq, 0, len(req.Data))
	if err := util.CopyUseJson(&adReq, req.Data); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//获取serviceId
	serviceId, err := u.getServiceId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.StandardCheckConfigId)
	if err != nil {
		return nil, err
	}
	//包装参数
	args := make(map[string]any)
	args["check_af_query"] = adReq

	adResp, err := u.adProxy.SearchEngine(ctx, serviceId, &args)
	if err != nil {
		return nil, err
	}

	var dag client.RecommdedDAG
	if err = util.CopyUseJson(&dag, &adResp.Res.RecommdedDAG); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	var resp CheckCodeResp
	if err = util.CopyUseJson(&resp.Data, dag.Outputs.GraphRecommendAnswerList); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	return &resp, nil
}

func (u *useCase) AssetSearch(ctx context.Context, req *AssetSearchReq) (result *AssetSearchResp, err error) {
	reqData := client.AssetSearch(req.AssetSearchReqBody)
	reqData.Init()

	result = &AssetSearchResp{}

	cache := u.NewCacheLoader(&reqData)
	if cache.Has(ctx) {
		cacheData := &result.Data
		cacheData, err = cache.Load(ctx)
		if err != nil {
			log.Warnf("load query from cache error %v", err.Error())
		}
		result.Data = *cacheData
	}
	if result == nil || len(result.Data.QueryCuts) <= 0 {
		result, err = u.assetSearch(ctx, &reqData)
		if err != nil {
			return nil, err
		}
		//当有结果时才缓存
		if result != nil && len(result.Data.Entities) > 0 {
			if err := cache.Store(ctx, result.Data); err != nil {
				log.Warn("cache query error", zap.Error(err), zap.Any("query", *req), zap.Any("data", result.Data))
			}
		}
	}
	//过滤下
	filter(&reqData, result)
	return result, nil
}
func (u *useCase) assetSearch(ctx context.Context, req *client.AssetSearch) (*AssetSearchResp, error) {
	//获取serviceId
	serviceId, err := u.getServiceId(ctx, "CognitiveSearchConfigId")
	if err != nil {
		return nil, err
	}
	//包装参数
	req.MaxLimit = MaxLimit
	args := req.GenAssetSearchADRequest()

	adResp, err := u.adProxy.SearchEngine(ctx, serviceId, &args)
	if err != nil {
		return nil, err
	}

	var dag client.GraphSynSearchDAG
	if err = util.CopyUseJson(&dag, &adResp.Res.GraphSynSearchDAG); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	return readProperties(dag.Outputs), nil
}
func filter(reqData *client.AssetSearch, data *AssetSearchResp) {
	if data == nil || len(data.Data.Entities) <= 0 {
		return
	}
	entities := make([]client.AssetSearchAnswerEntity, 0, reqData.Limit)
	for _, entity := range data.Data.Entities {
		if entity.Score < reqData.LastScore || len(entities) >= reqData.Limit || entity.Entity.VID == reqData.LastId {
			continue
		}
		entities = append(entities, entity)
	}
	data.Data.Entities = entities
	return
}

func (u *useCase) getGraphId(ctx context.Context, cfgId string) (string, error) {
	srvCfgId, err := u.adCfgHelper.GetGraphId(ctx, cfgId)
	if err != nil {
		return "", err
	}
	if len(srvCfgId) < 1 {
		return "", nil
	}
	return srvCfgId, nil
}

func (u *useCase) MetaDataViewRecommendV2(ctx context.Context, req *MetaDataViewRecommendReq) (*MetaDataViewRecommendResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.LogicalViewGraphConfigId)
	if err != nil {
		return nil, err
	}
	entityId := req.LogicalEntityId
	kgId := graphId
	var resp MetaDataViewRecommendResp

	entityInfo, err := u.adProxy.EntitySearchByEngine(ctx, entityId, kgId)
	if len(entityInfo.Res.Nodes) == 0 {
		log.Info("logical entity id not exists")
		resp.Res = []MetaDataView{}
		return &resp, err
	}
	vid := entityInfo.Res.Nodes[0].Id

	//fmt.Println("metadata vid:", vid)

	metaViewInfo, err := u.adProxy.NeighborSearchByEngine(ctx, vid, 4, kgId)
	if err != nil {
		return nil, err
	}
	if len(metaViewInfo.Res.Nodes) == 0 {
		resp.Res = []MetaDataView{}
		return &resp, err
	}
	metaItem := metaViewInfo.Res.Nodes[0]

	//fmt.Println("metadata vid:", metaItem.Id)
	metadataId := ""
	technicalName := ""
	businessName := ""
	for _, it := range metaItem.Properties {
		//fmt.Println("it.Tag", it.Tag)
		if it.Tag == "data_source_view" {

			for _, itProp := range it.Props {
				if itProp.Name == "id" {
					metadataId = itProp.Value
				}
				if itProp.Name == "technical_name" {
					technicalName = itProp.Value
				}
				if itProp.Name == "business_name" {
					businessName = itProp.Value
				}
			}
		}

	}
	if metadataId == "" {
		log.Warn("查询出的三跳结果有问题")
		resp.Res = []MetaDataView{}
		return &resp, err
	}
	//var resp MetaDataViewRecommendResp
	item := MetaDataView{metadataId, technicalName, businessName}
	resp.Res = append(resp.Res, item)
	return &resp, err
}

func (u *useCase) do(ctx context.Context) *gorm.DB {
	return u.data.DB.WithContext(ctx)
}

type MetaDataViewModel struct {
	ID            string `json:"id"`
	TechnicalName string `json:"technical_name"`
	BusinessName  string `json:"business_name"`
}

// 根据业务表关联元数据视图

func (u *useCase) GetMetaDataView(ctx context.Context, logicalId string) (*MetaDataViewModel, error) {
	var ms []MetaDataViewModel
	if err := u.do(ctx).Raw(
		"SELECT e.id, e.technical_name, e.business_name FROM af_main.subject_domain a JOIN af_main.form_business_object_relation b ON a.id = b.logical_entity_id JOIN af_business.business_form_standard c ON b.form_id = c.business_form_id JOIN af_business.dw_form d ON c.from_table_id = d.id JOIN af_main.form_view e ON d.`name`= CONVERT (e.technical_name USING utf8) COLLATE utf8_unicode_ci WHERE a.deleted_at=0 and c.deleted_at=0 and  d.deleted_at=0 and e.deleted_at = 0 AND  e.type=1 and e.publish_at is not null and a.id= ? ORDER BY e.created_at desc", logicalId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return &ms[0], nil
	}
	return nil, nil
}

type MetaDataViewModelV1 struct {
	PathId string `json:"path_id"`
}

func (u *useCase) GetMetaDataViewV1(ctx context.Context, logicalId string) (*MetaDataViewModelV1, error) {
	var ms []MetaDataViewModelV1
	if err := u.do(ctx).Raw(
		"SELECT path_id from af_main.subject_domain where deleted_at=0 and id  = ? limit 1", logicalId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	//fmt.Println(ms, "++++++++++++", len(ms))
	if len(ms) > 0 {
		return &ms[0], nil
	}
	return nil, nil
}

func (u *useCase) GetMetaDataViewV2(ctx context.Context, logicalId string) (*MetaDataViewModel, error) {
	var ms []MetaDataViewModel
	if err := u.do(ctx).Raw(
		"select b.id as id, b.technical_name as technical_name,b.business_name as business_name from af_main.subject_domain a join af_main.form_view b on CONVERT (a.id USING utf8) COLLATE utf8_unicode_ci = b.subject_id where  b.deleted_at=0  and b.type=1 and b.publish_at is not null and a.id = ? ORDER BY b.created_at desc", logicalId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return &ms[0], nil
	}
	return nil, nil
}

func (u *useCase) MetaDataViewRecommendV3(ctx context.Context, req *MetaDataViewRecommendReq) (*MetaDataViewRecommendResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp MetaDataViewRecommendResp
	meta, err := u.GetMetaDataView(ctx, req.LogicalEntityId)
	if err != nil || meta == nil {
		resp.Res = []MetaDataView{}
		return &resp, err
	}

	item := MetaDataView{meta.ID, meta.TechnicalName, meta.BusinessName}
	resp.Res = append(resp.Res, item)
	return &resp, err
}

func (u *useCase) MetaDataViewRecommend(ctx context.Context, req *MetaDataViewRecommendReq) (*MetaDataViewRecommendResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp MetaDataViewRecommendResp
	metaValue, err := u.GetMetaDataView(ctx, req.LogicalEntityId)

	if err != nil {
		resp.Res = []MetaDataView{}
		return &resp, err
	}

	if metaValue == nil {
		log.Info("search meta data view by business table fail")
		respS, err := u.MetaDataViewRecommendBySubDomain(ctx, req.LogicalEntityId)
		if err != nil {
			resp.Res = []MetaDataView{}
			return &resp, err
		}
		return respS, nil
	}

	item := MetaDataView{metaValue.ID, metaValue.TechnicalName, metaValue.BusinessName}
	resp.Res = append(resp.Res, item)
	return &resp, err
}

// 基于主题域推荐
func (u *useCase) MetaDataViewRecommendBySubDomain(ctx context.Context, logicalId string) (*MetaDataViewRecommendResp, error) {
	var resp MetaDataViewRecommendResp
	meta, err := u.GetMetaDataViewV1(ctx, logicalId)

	if err != nil || meta == nil {
		resp.Res = []MetaDataView{}
		return &resp, err
	}
	pathId := meta.PathId
	log.Infof("path id %s", pathId)
	subjectId := strings.Split(pathId, "/")
	if len(subjectId) < 2 {
		resp.Res = []MetaDataView{}
		return &resp, err
	}

	if len(subjectId) >= 3 {
		metaValueSub, err := u.GetMetaDataViewV2(ctx, subjectId[2])
		if err != nil || metaValueSub == nil {
			log.Info("search subject domain level 3 fail")
		} else {
			item := MetaDataView{metaValueSub.ID, metaValueSub.TechnicalName, metaValueSub.BusinessName}
			resp.Res = append(resp.Res, item)
			return &resp, err
		}

	}

	metaValue, err := u.GetMetaDataViewV2(ctx, subjectId[1])
	if err != nil || metaValue == nil {
		resp.Res = []MetaDataView{}
		return &resp, err
	}
	item := MetaDataView{metaValue.ID, metaValue.TechnicalName, metaValue.BusinessName}
	resp.Res = append(resp.Res, item)
	return &resp, err
}

// 基于获取知识网络
func (u *useCase) ListKnowledgeNetwork(ctx context.Context, req *ListKnowledgeNetworkReq) (*ListKnowledgeNetworkResp, error) {
	var resp ListKnowledgeNetworkResp
	nReq := knowledge_network.ListKnowledgeNetworkReq{
		Order: "desc",
		Page:  1,
		Size:  10000,
		Rule:  "update",
	}
	kwnList, err := u.adProxy.ListKnowledgeNetwork(ctx, &nReq)

	if err != nil {
		return nil, err
	}

	selfNetworkID, err := u.adCfgHelper.GetNetworkId(ctx, "knowledge-network-business-relation")
	if err != nil {
		return nil, err
	}
	selfNetworkIDInt, _ := strconv.Atoi(selfNetworkID)

	resp.Entries = []KnowledgeNetworkItem{}

	for _, item := range kwnList.Res.Df {
		nItem := KnowledgeNetworkItem{
			Id:      item.Id,
			KnwName: item.KnwName,
		}

		if item.Id == selfNetworkIDInt {
			nItem.Type = "default"
		} else {
			nItem.Type = "other"
		}
		resp.Entries = append(resp.Entries, nItem)
	}

	return &resp, err
}

// 获取知识图谱
func (u *useCase) ListKnowledgeGraph(ctx context.Context, req *ListKnowledgeGraphReq) (*ListKnowledgeGraphResp, error) {

	var resp ListKnowledgeGraphResp

	nReq := knowledge_network.ListKnowledgeGraphReq{
		Filter: "all",
		KnwId:  req.KnwID,
		Order:  "desc",
		Page:   1,
		Size:   10000,
		Rule:   "update",
	}
	if req.Type == "default" {
		selfNetworkID, err := u.adCfgHelper.GetNetworkId(ctx, "knowledge-network-business-relation")
		if err != nil {
			return nil, err
		}
		selfNetworkIDInt, _ := strconv.Atoi(selfNetworkID)
		nReq.KnwId = selfNetworkIDInt
	}
	kGraphList, err := u.adProxy.ListKnowledgeGraph(ctx, &nReq)

	if err != nil {
		return nil, err
	}

	for _, item := range kGraphList.Res.Df {
		resp.Entries = append(resp.Entries, KnowledgeGraphItem{
			Id:        item.Id,
			GraphName: item.Name,
		})
	}

	return &resp, err
}

// 获取词库
func (u *useCase) ListKnowledgeLexicon(ctx context.Context, req *ListKnowledgeLexiconReq) (*ListKnowledgeLexiconResp, error) {
	var resp ListKnowledgeLexiconResp
	resp.Entries = []KnowledgeLexiconItem{}
	nReq := knowledge_network.ListKnowledgeLexiconReq{
		KnowledgeId: req.KnwID,
		Order:       "desc",
		Page:        1,
		Size:        10000,
		Rule:        "update_time",
		Word:        "",
	}
	if req.Type == "default" {
		selfNetworkID, err := u.adCfgHelper.GetNetworkId(ctx, "knowledge-network-business-relation")
		if err != nil {
			return nil, err
		}
		selfNetworkIDInt, _ := strconv.Atoi(selfNetworkID)
		nReq.KnowledgeId = selfNetworkIDInt
	}
	kLexiconList, err := u.adProxy.ListKnowledgeLexicon(ctx, &nReq)

	if err != nil {
		return nil, err
	}

	for _, item := range kLexiconList.Res.Df {
		resp.Entries = append(resp.Entries, KnowledgeLexiconItem{
			Id:          item.Id,
			LexiconName: item.Name,
		})
	}

	return &resp, err
}
