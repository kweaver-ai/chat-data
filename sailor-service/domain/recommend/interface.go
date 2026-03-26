package recommend

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/client"
	//"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
)

type UseCase interface {
	TableRecommendation(ctx context.Context, req *TableRecommendationReq) (*TableRecommendationResp, error)
	FlowRecommendation(ctx context.Context, req *FlowRecommendationReq) (*FlowRecommendationResp, error)
	FieldStandardRecommendation(ctx context.Context, req *FieldStandardRecommendationReq) (*FieldStandardRecommendationResp, error)
	CheckCode(ctx context.Context, req *CheckCodeReq) (*CheckCodeResp, error)
	AssetSearch(ctx context.Context, req *AssetSearchReq) (*AssetSearchResp, error)
	MetaDataViewRecommend(ctx context.Context, req *MetaDataViewRecommendReq) (*MetaDataViewRecommendResp, error)
	ListKnowledgeNetwork(ctx context.Context, req *ListKnowledgeNetworkReq) (*ListKnowledgeNetworkResp, error)
	ListKnowledgeGraph(ctx context.Context, req *ListKnowledgeGraphReq) (*ListKnowledgeGraphResp, error)
	ListKnowledgeLexicon(ctx context.Context, req *ListKnowledgeLexiconReq) (*ListKnowledgeLexiconResp, error)
}

const (
	MaxLimit = 100
)

////////////////////////// TableRecommendation //////////////////////////

type TableRecommendationReq struct {
	TableRecommendationReqBody `param_type:"body"`
}

type TableRecommendationReqBody client.RecTableReq

type TableRecommendationResp client.RecTableResp

////////////////////////// FlowRecommendation //////////////////////////

type FlowRecommendationReq struct {
	FlowRecommendationReqBody `param_type:"body"`
}

type FlowRecommendationReqBody client.RecFlowReq

type FlowRecommendationResp client.RecFlowResp

////////////////////////// FieldStandardRecommendation //////////////////////////

type FieldStandardRecommendationReq struct {
	FieldStandardRecommendationReqBody `param_type:"body"`
}

type FieldStandardRecommendationReqBody client.RecCodeReq

type FieldStandardRecommendationResp client.RecCodeResp

////////////////////////// CheckCode //////////////////////////

type CheckCodeReq struct {
	CheckCodeReqBody `param_type:"body"`
}

type CheckCodeReqBody client.CheckCodeReq

type CheckCodeResp client.CheckCodeResp

type AssetSearchReq struct {
	AssetSearchReqBody `param_type:"body"`
}

type AssetSearchReqBody client.AssetSearch

type AssetSearchResp client.AssetSearchResp

//var configServices = []string{
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-datacatalog",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-businessobject",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-catalogtag",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-info_system",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-department",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-department",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-department",
//	settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId + "-department",
//}

type MetaDataViewRecommendReq struct {
	MetaDataViewRecommendReqBody `param_type:"body"`
}

type MetaDataViewRecommendReqBody struct {
	LogicalEntityId string `json:"logical_entity_id"`
}

type MetaDataViewRecommendResp struct {
	Res []MetaDataView `json:"res"`
}

type MetaDataView struct {
	Id            string `json:"id"`
	TechnicalName string `json:"technical_name"`
	BusinessName  string `json:"business_name"`
}

type ListKnowledgeNetworkReq struct {
	ListKnowledgeNetworkReqBody `param_type:"query"`
}

type ListKnowledgeNetworkReqBody struct {
	//Type  string `json:"type" form:"type" binding:"required,oneof=default all"`
}

type ListKnowledgeNetworkResp struct {
	Entries []KnowledgeNetworkItem `json:"entries"` //AD 的iframe的地址
}

type KnowledgeNetworkItem struct {
	Id      int    `json:"id"`
	KnwName string `json:"knw_name"`
	Type    string `json:"type"`
}

type ListKnowledgeGraphReq struct {
	ListKnowledgeGraphReqBody `param_type:"query"`
}

type ListKnowledgeGraphReqBody struct {
	KnwID int    `json:"knw_id" form:"knw_id"`
	Type  string `json:"type" form:"type" binding:"required,oneof=default specify"`
}

type ListKnowledgeGraphResp struct {
	Entries []KnowledgeGraphItem `json:"entries"` //AD 的iframe的地址
}

type KnowledgeGraphItem struct {
	Id        int    `json:"id"`
	GraphName string `json:"graph_name_name"`
}

type ListKnowledgeLexiconReq struct {
	ListKnowledgeLexiconReqBody `param_type:"query"`
}

type ListKnowledgeLexiconReqBody struct {
	KnwID int    `json:"knw_id" form:"knw_id"`
	Type  string `json:"type" form:"type" binding:"required,oneof=default specify"`
}

type ListKnowledgeLexiconResp struct {
	Entries []KnowledgeLexiconItem `json:"entries"` //AD 的iframe的地址
}

type KnowledgeLexiconItem struct {
	Id          int    `json:"id"`
	LexiconName string `json:"lexicon_name"`
}
