package knowledge_network

import (
	"context"
	"fmt"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type GraphSchema struct {
	GraphStep    string       `json:"graph_step"`
	GraphProcess GraphProcess `json:"graph_process"`
}
type GraphProcess struct {
	Entity []*GraphKMEntity `json:"entity"`
	Edge   []*GraphKMEdge   `json:"edge"`
	Files  []*GraphKMFile   `json:"files"`
}

func (a *ad) UpdateSchema(ctx context.Context, knwId int, schema *GraphSchema) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/graph/%v`, knwId)

	if _, err = httpPostDo[commonSimpleResp](ctx, rawURL, schema, nil, a); err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}
