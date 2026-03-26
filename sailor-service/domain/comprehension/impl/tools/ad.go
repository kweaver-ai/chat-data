package tools

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

const CommonGraphSQLKey = "nsql"

type AnyDataSearch struct {
	Client    knowledge_network.AD
	cfgHelper knowledge_build.Helper
}

func NewAnyDataSearch(c knowledge_network.AD, cfgHelper knowledge_build.Helper) AnyDataSearch {
	return AnyDataSearch{
		Client:    c,
		cfgHelper: cfgHelper,
	}
}

func (o AnyDataSearch) formatService(data comprehension.MiddleData, tags []string) (comprehension.MiddleData, error) {
	middleData := make(map[string]any)
	for _, tag := range tags {
		key, value, err := comprehension.GetMiddleDataValue[any](data, tag)
		if err != nil {
			return nil, err
		}
		middleData[key] = value
	}
	bytes, _ := json.Marshal(middleData)
	log.Info(string(bytes))
	return middleData, nil
}

func (o AnyDataSearch) formatGQL(data comprehension.MiddleData, graphQL string, tags []string) (comprehension.MiddleData, error) {
	if len(tags) <= 0 {
		reg, _ := regexp.Compile("\\${[\\w|\\.]+}")
		tags = reg.FindAllString(graphQL, -1)
	}

	d := make(map[string]any)
	for _, tag := range tags {
		key, value, err := comprehension.GetMiddleDataValue[any](data, tag)
		if err != nil {
			return d, err
		}
		key = fmt.Sprintf("${%s}", key)
		bytes, _ := json.Marshal(*value)
		graphQL = strings.Replace(graphQL, key, string(bytes), -1)
	}
	log.Info(graphQL)
	d[CommonGraphSQLKey] = graphQL
	return d, nil
}

func (o AnyDataSearch) formatResult(adSearchResult *knowledge_network.CustomSearchResp, p comprehension.Process) (comprehension.MiddleData, error) {
	middleData := make(map[string]any)
	if len(adSearchResult.Res) <= 0 {
		return middleData, fmt.Errorf("ad search no result")
	}
	format := p.Format
	key := p.FormatKey()

	nodes := make([]comprehension.MiddleData, 0)
	nodesMap := make(map[string]int)
	format = strings.Replace(format, "...", "", -1)
	for _, vertex := range adSearchResult.Res {
		for _, v := range vertex.VerticesParsedList {
			node := make(map[string]any)
			for _, p := range v.Properties[0].Props {
				if strings.Contains(format, p.Name) {
					node[p.Name] = p.Value
				}
			}
			bytes, _ := json.Marshal(node)
			key := string(md5.New().Sum(bytes))
			if _, ok := nodesMap[key]; !ok {
				nodesMap[key] = 1
				nodes = append(nodes, node)
			}
		}
	}
	if p.IsSlice() || len(nodes) > 1 {
		middleData[key] = nodes
	}
	if !p.IsSlice() && len(nodes) == 1 {
		middleData[key] = nodes[0]
	}
	log.Info("ad result:", zap.Any("entity", nodes))
	return middleData, nil
}

func (o AnyDataSearch) Search(ctx context.Context, t comprehension.Process, middleData comprehension.MiddleData) (comprehension.MiddleData, error) {
	searchConfig, err := util.Transfer[comprehension.AnydataConfig](t.Config)
	if err != nil {
		return nil, err
	}
	//邻居查询
	if searchConfig.ServiceID != "" {
		postBody, err := o.formatService(middleData, t.Inputs)
		if err != nil {
			return nil, err
		}
		results, err := o.Client.Services(ctx, searchConfig.ServiceID, postBody)
		if err != nil {
			return nil, err
		}
		return o.formatResult(results, t)
	}
	//查询语句模式
	postBody, err := o.formatGQL(middleData, searchConfig.SQL, t.Inputs)
	if err != nil {
		return nil, err
	}

	searchId, err := o.cfgHelper.GetGraphAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataComprehensionGraphAnalysisServiceConfigId)
	if err != nil {
		return nil, err
	}

	results, err := o.Client.Services(ctx, searchId, postBody)
	if err != nil {
		return nil, err
	}
	return o.formatResult(results, t)
}
