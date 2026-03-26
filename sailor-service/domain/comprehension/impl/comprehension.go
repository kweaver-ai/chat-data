package impl

import (
	"context"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/concepts"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"go.uber.org/zap"
)

type ComprehensionDomainImpl struct {
	Brain *Brain
	data  *db.Data
}

func NewComprehensionDomain(brain *Brain, data *db.Data) comprehension.Domain {
	return &ComprehensionDomainImpl{
		data:  data,
		Brain: brain,
	}
}

func (c ComprehensionDomainImpl) Test(ctx context.Context, q string) (answer any, err error) {
	bigBrain := c.Brain.Clone()
	return bigBrain.OpenAPI.SearchQ(ctx, q)
}

func (c ComprehensionDomainImpl) AIComprehension(ctx context.Context, catalogId string, dimension string) (answer any, err error) {
	defer func() {
		if e := recover(); e != nil {
			log.WithContext(ctx).Error("AIComprehension panic", zap.Any("panic", e))
			answer = []string{}
			err = nil
			return
		}
	}()

	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	ts := ThinkingMap[dimension]
	data := comprehension.MiddleData(make(map[string]any))
	data["catalog_id"] = catalogId
	data["service_domain"] = ServiceDomain
	bigBrain := c.Brain.Clone()

	//提前执行大模型的概念
	dimensionConcepts := concepts.Support(dimension)
	if dimensionConcepts != nil {
		onePromote := strings.Join(dimensionConcepts, "。")
		if err := bigBrain.OpenAPI.Concepts(ctx, onePromote); err != nil {
			return []string{}, nil
		}
	}
	if err := bigBrain.Flows(ctx, ts.Thinking, data); err != nil {
		log.WithContext(ctx).Info("process error", zap.Error(err))
	}
	answer = bigBrain.Result(ts.ResultKey)
	if answer == nil {
		return []string{}, nil
	}
	return answer, nil
}

func (c ComprehensionDomainImpl) AIComprehensionConfig() any {
	return Configs()
}

func (c ComprehensionDomainImpl) SetAIComprehensionConfig(id string) string {
	if id != "" {
		SetGlobalADGraphSQLSearchID(id)
		return "ok"
	}
	return "no changes"
}
