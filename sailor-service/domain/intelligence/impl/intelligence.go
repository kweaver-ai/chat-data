package impl

import (
	"context"
	"fmt"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/intelligence"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type useCase struct {
	llm large_language_model.OpenAI
}

func NewUseCase(llm large_language_model.OpenAI) intelligence.UseCase {
	return &useCase{llm: llm}
}

func (u useCase) TableSampleData(ctx context.Context, req *intelligence.SampleDataReq) (*intelligence.SampleDataResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	prompt := fmt.Sprintf(intelligence.SampleDataPromptNoExample, intelligence.Example1,
		intelligence.Example2, req.Titles, req.Differs)
	if len(req.Example) > 0 {
		prompt = fmt.Sprintf(intelligence.SampleDataPromptWithExample, intelligence.Example1,
			intelligence.Example2, req.Titles, req.Example, req.Differs)
	}
	result, err := u.llm.ChatGPT35(ctx, prompt)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, err
	}
	samples, err := util.GetJsonInAnswer[intelligence.SampleDataResp](result)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, err
	}
	return samples, nil
}
