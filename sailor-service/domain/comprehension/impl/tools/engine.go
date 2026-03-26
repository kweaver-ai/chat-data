package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	engine "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/virtualization_engine"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
	"go.uber.org/zap"
)

type EngineSource struct {
	Client engine.VirtualizationEngine
}

func NewEngineSource(engine engine.VirtualizationEngine) EngineSource {
	return EngineSource{
		Client: engine,
	}
}

func (e EngineSource) sql(sql string, data comprehension.MiddleData, tags []string) (string, error) {
	if len(tags) <= 0 {
		reg, _ := regexp.Compile("\\${[\\w|\\.]+}")
		tags = reg.FindAllString(sql, -1)
	}

	for _, tag := range tags {
		key, value, err := comprehension.GetMiddleDataValue[string](data, tag)
		if err != nil {
			return "", err
		}
		keyString := fmt.Sprintf("${%v}", key)
		keyValue := fmt.Sprintf("%v", *value)
		if keyString == "" || keyValue == "" {
			return "", fmt.Errorf("empty engine parameter, SQL: %s", sql)
		}
		sql = strings.ReplaceAll(sql, keyString, keyValue)
	}
	log.Info(sql)
	return sql, nil
}

func (e EngineSource) format(response *engine.RawResult, format string, inData comprehension.MiddleData) (comprehension.MiddleData, error) {
	format = strings.ReplaceAll(format, "...", "")
	data := make([]map[string]any, 0, len(response.Data))
	for _, datum := range response.Data {
		m := make(map[string]any)
		for i, column := range response.Columns {
			if datum[i] != nil {
				m[column.Name] = datum[i]
			}
		}
		data = append(data, m)
	}

	cMap := make(map[string]string)
	for _, column := range response.Columns {
		cMap[fmt.Sprintf("%s", column.Name)] = column.Name
	}

	sampleData := make(map[string][]map[string]string)
	if err := json.Unmarshal([]byte(format), &sampleData); err != nil {
		log.Info(err.Error())
		return nil, err
	}

	var retKey string
	var retFormat map[string]string
	for k, v := range sampleData {
		for _, m := range v {
			retFormat = m
			break
		}

		retKey = k
		break
	}
	if retFormat == nil {
		return nil, nil
	}

	retArr := make([]map[string]any, 0)
	for _, datum := range data {
		retM := make(map[string]any)
		for k, v := range retFormat {
			for key, value := range cMap {
				if strings.Contains(v, key) {
					dv, ok := datum[value]
					if ok {
						retM[k] = dv
						break
					}
				}
			}
		}
		if len(retM) > 0 {
			retArr = append(retArr, retM)
		}
	}

	arr, ok := inData[retKey]
	if ok {
		tmpArr := make([]map[string]any, 0)
		_ = json.Unmarshal(lo.T2(json.Marshal(arr)).A, &tmpArr)
		retArr = append(retArr, tmpArr...)
	}
	log.Info("virtual engine result:", zap.Any("ret:", retArr))
	if len(retArr) <= 0 {
		return map[string]any{retKey: retArr}, fmt.Errorf("empty virtual engine result %v", retArr)
	}
	return map[string]any{retKey: retArr}, nil
}

func (e EngineSource) Search(ctx context.Context, p comprehension.Process, middleData comprehension.MiddleData) (comprehension.MiddleData, error) {
	engineConfig, err := util.Transfer[comprehension.VirtualEngineConfig](p.Config)
	if err != nil {
		return nil, err
	}

	sql, err := e.sql(engineConfig.SQL, middleData, p.Inputs)
	if err != nil {
		return nil, err
	}

	result, err := e.Client.Raw(ctx, sql)
	if err != nil {
		return nil, err
	}

	return e.format(result, p.Format, middleData)
}
