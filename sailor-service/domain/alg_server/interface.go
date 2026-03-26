package alg_server

import (
	"context"

	adProxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
)

type UseCase interface {
	FullText(ctx context.Context, req *FullTextReq) (*FullTextResp, error)
	Neighbors(ctx context.Context, req *NeighborsReq) (*NeighborsResp, error)
	Iframe(ctx context.Context, req *IframeReq) (string, error)
	GraphAnalysis(ctx context.Context, req *GraphAnalysisReq) (resp *GraphAnalysisResp, err error)
}

////////////////////////// FullText //////////////////////////

type FullTextReq struct {
	FullTextReqBody `param_type:"body"`
}

type FullTextReqBody client.GraphFullTextReq

type FullTextResp client.GraphFullTextResp

////////////////////////// Neighbors //////////////////////////

type NeighborsReq struct {
	NeighborsReqBody `param_type:"body"`
}

type NeighborsReqBody client.GraphNeighborsReq

type NeighborsResp client.GraphNeighborsResp

type IframeReq struct {
	IframeReqBody `param_type:"query"`
}

type IframeReqBody struct {
	ID          string `json:"id" form:"id" binding:"required"`                      //属性id
	PropName    string `json:"prop_name" form:"prop_name"  binding:"required"`       //属性名称
	Entity      string `json:"entity" form:"entity"  binding:"required"`             //实体类的名称
	ServiceName string `json:"service_name"  form:"service_name" binding:"required"` //服务的名称
}

type IframeResp struct {
	URL       string `json:"url"`        //AD 的iframe的地址
	IDs       string `json:"ids"`        //属性id数组
	AppID     string `json:"app_id"`     //实体类的名称
	ServiceID string `json:"service_id"` //服务的名称
}

// AssetService 资产服务
const AssetService = "asset-service"
const AssetSubgraphService = "asset-subgraph-service"
const AssetSubgraphEntityService = "asset-subgraph-entity-service"

type GraphAnalysisReq struct {
	GraphAnalysisReqBody `param_type:"body"`
}

type GraphAnalysisResp adProxy.GraphAnalysisResp

type GraphAnalysisReqBody struct {
	ServiceName string   `json:"service_name"  form:"service_name" binding:"required"` //服务的名称
	End         string   `json:"end" form:"end" binding:"required"`                    //终点的vid列表
	Starts      []string `json:"starts" form:"starts"  binding:"required"`             //起点的vid列表
	DataVersion string   `json:"data_version" form:"data_version"`
}

func (g GraphAnalysisReqBody) IsSingle() bool {
	return len(g.Starts) == 1 && g.Starts[0] == g.End
}
