package knowledge_network

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

const (
	ServiceNotExistedMsg       = "service id does not exist"
	LexiconNotExistedErrorCode = "DeleteLexicon.LexiconIdNotExist"
	GraphNotExistsCode         = "GetGraphById.CheckByIdError"
	GraphNotExistedMsg         = "not exists"
	DataSourceNotExists        = "not exits"
	NetworkNotExistsMsg        = "not find the knowledge network"
)

type commonSimpleResp struct {
	Res string `json:"res"`
}

type commonResp[T any] struct {
	GraphID int `json:"graph_id,omitempty"`
	Res     T   `json:"res" json:"res"`
}

func (a *ad) DeleteKnowledgeNetwork(ctx context.Context, knwId int) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/open/knw/delete_knw`

	m := make(map[string]int)
	m["knw_id"] = knwId

	if _, err := httpPostDo[commonSimpleResp](ctx, rawURL, m, nil, a); err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) DeleteDataSource(ctx context.Context, ids []int) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/open/ds/delbydsids`

	m := make(map[string][]int)
	m["dsids"] = ids

	bs, _ := json.Marshal(m)

	if _, err := httpADDo[commonSimpleResp](ctx, http.MethodDelete, rawURL, string(bs), nil, true, a); err != nil {
		if errorcode.Contains(err, DataSourceNotExists) || errorcode.Contains(err, GraphNotExistedMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

type deleteKnowledgeGraphReq struct {
	GraphIds []int `json:"graphids"`
	KnwId    int   `json:"knw_id"`
}

func (a *ad) DeleteKnowledgeGraph(ctx context.Context, knwId int, graphIds []int) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/open/graph/delbyids`

	reqData := deleteKnowledgeGraphReq{
		GraphIds: graphIds,
		KnwId:    knwId,
	}

	if _, err := httpPostDo[commonSimpleResp](ctx, rawURL, reqData, nil, a); err != nil {
		if errorcode.Contains(err, GraphNotExistedMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) DeleteSynonymsLexicon(ctx context.Context, ids []int) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/open/lexicon/delete`

	m := make(map[string][]int)
	m["id_list"] = ids

	if _, err := httpPostDo[commonSimpleResp](ctx, rawURL, m, nil, a); err != nil {
		if errorcode.Contains(err, LexiconNotExistedErrorCode) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) simplePostReq(ctx context.Context, rawURL string) error {
	if _, err := httpPostDo[commonSimpleResp](ctx, rawURL, nil, nil, a); err != nil {
		if errorcode.Contains(err, ServiceNotExistedMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}

func (a *ad) GraphAnalysisCancelRelease(ctx context.Context, serviceId string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/cognitive-service/v1/open/services/%s/cancel-service`, serviceId)
	return a.simplePostReq(ctx, rawURL)
}

func (a *ad) DeleteGraphAnalysis(ctx context.Context, serviceId string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/cognitive-service/v1/open/services/%s/delete-service`, serviceId)
	return a.simplePostReq(ctx, rawURL)
}

func (a *ad) CognitionServiceCancelRelease(ctx context.Context, serviceId string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/cognition-search/v1/open/services/%s/cancel-service`, serviceId)
	return a.simplePostReq(ctx, rawURL)
}

func (a *ad) DeleteCognitionService(ctx context.Context, serviceId string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/cognition-search/v1/open/services/%s/delete-service`, serviceId)
	return a.simplePostReq(ctx, rawURL)
}
