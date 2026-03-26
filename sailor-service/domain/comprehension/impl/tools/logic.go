package tools

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/collection"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

type LogicHelper struct{}

func NewLogicHelper() LogicHelper {
	return LogicHelper{}
}

func (l LogicHelper) format(result any, p comprehension.Process) comprehension.MiddleData {
	if result == nil {
		return nil
	}
	key := p.FormatKey()
	rs := comprehension.NewMiddleData()
	if !p.IsSlice() {
		rs[key] = result
	} else {
		rs[key] = []any{result}
	}
	return rs
}

func (l LogicHelper) Search(ctx context.Context, p comprehension.Process, data comprehension.MiddleData) (comprehension.MiddleData, error) {
	logicHelperConfig, err := util.Transfer[comprehension.LogicHelperConfig](p.Config)
	if err != nil {
		return nil, err
	}
	_, d, err := comprehension.GetMiddleDataValue[any](data, p.Inputs[0])
	if err != nil {
		return nil, err
	}
	rs := collection.Handle(logicHelperConfig.FuncStr, d)
	log.WithContext(ctx).Info("logic helper:", zap.Any("result", rs))
	return l.format(rs, p), nil
}
