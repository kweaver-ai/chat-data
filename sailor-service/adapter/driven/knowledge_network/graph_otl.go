package knowledge_network

import (
	"context"
	"fmt"
	"net/url"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type GraphNeedRemoveData struct {
	Entity []*GraphEntity `json:"entity"`
	Edge   []*GraphEdge   `json:"edge"`
}

type CreateGraphReq struct {
	GraphStep    string `json:"graph_step"`
	Updateoradd  string `json:"updateoradd,omitempty"`
	GraphProcess any    `json:"graph_process"`
	KnwId        int    `json:"knw_id,omitempty"`
}

type CreateGraphProcess struct {
	GraphName    *string `json:"graph_Name,omitempty"`
	GraphDes     *string `json:"graph_des,omitempty"`
	OntologyName *string `json:"ontology_name,omitempty"`
	OntologyDes  *string `json:"ontology_des,omitempty"`
}

type DeleteGraphReq struct {
	Graphids []int `json:"graphids"`
	KnwId    int   `json:"knw_id"`
}

type DeleteGraphResp struct {
	GraphId []int  `json:"graph_id"`
	State   string `json:"state"`
}

type QueryGraphByNameResp struct {
	Count int                      `json:"count"`
	Df    []QueryGraphByNameRespDF `json:"df"`
}
type QueryGraphByNameRespDF struct {
	GraphDbName   string `json:"graph_db_name"`
	Id            int    `json:"id"`
	KnowledgeType string `json:"knowledge_type"`
	KnwId         int    `json:"knw_id"`
	Name          string `json:"name"`
	OtlId         string `json:"otl_id"`
}

func (a *ad) CreateGraphOtl(ctx context.Context, req *CreateGraphReq) (graphID int, err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/graph`)

	res, err := httpPostDo[commonResp[string]](ctx, rawURL, req, nil, a)
	if err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return 0, err
		}
		log.Error(err.Error())
		return 0, err
	}
	return res.GraphID, nil
}

func (a *ad) UpdateGraphOtl(ctx context.Context, graphID int, req *CreateGraphReq) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/graph/%v`, graphID)

	if _, err = httpPostDo[any](ctx, rawURL, req, nil, a); err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) DeleteGraphOtl(ctx context.Context, knwID int, graphID int) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/graph/delbyids`)

	req := DeleteGraphReq{
		KnwId:    knwID,
		Graphids: []int{graphID},
	}
	_, err = httpPostDo[DeleteGraphResp](ctx, rawURL, req, nil, a)
	if err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) || errorcode.Contains(err, GraphNotExistedMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) QueryGraphByName(ctx context.Context, knwID int, graphName string) (graphID int, err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/knw/get_graph_by_knw?filter=all&knw_id=%v&page=1&size=1000&order=desc&name=%v&rule=create`, knwID, url.QueryEscape(graphName))
	realURL, _ := url.Parse(rawURL)

	res, err := httpGetDoV2[commonResp[QueryGraphByNameResp]](ctx, realURL, a)
	if err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return 0, err
		}
		log.Error(err.Error())
		return 0, err
	}
	if res.Res.Count <= 0 {
		return 0, nil
	}
	for i := range res.Res.Df {
		if res.Res.Df[i].Name == graphName {
			return res.Res.Df[i].Id, nil
		}
	}
	return 0, nil
}
