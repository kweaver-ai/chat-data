package alg_server

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
)

// GetServiceConfigIDByName 根据服务名称查询服务ID
func GetServiceConfigIDByName(ctx context.Context, name string, adCfgHelper knowledge_build.Helper, dataVersion string) (srvId string, graphId string, err error) {
	cfgIdMap := settings.GetConfig().KnowledgeNetworkResourceMap
	srvCfgId := ""
	if dataVersion == "data-catalog" {
		srvCfgId = lo.Switch[string, string](name).
			Case(AssetSubgraphService, cfgIdMap.CognitiveSearchDataCatalogSubgraphSearchConfigId).
			Case(AssetSubgraphEntityService, cfgIdMap.CognitiveSearchDataCatalogSubgraphEntitySearchConfigId).
			Default("")
	} else if dataVersion == "data-resource" {
		srvCfgId = lo.Switch[string, string](name).
			Case(AssetSubgraphService, cfgIdMap.CognitiveSearchDataResourceSubgraphSearchConfigId).
			Case(AssetSubgraphEntityService, cfgIdMap.CognitiveSearchDataResourceSubgraphEntitySearchConfigId).
			Default("")
	} else {
		srvCfgId = lo.Switch[string, string](name).
			Case(AssetService, cfgIdMap.AssetGraphAnalysisServiceConfigId).
			Case(AssetSubgraphService, cfgIdMap.AssetSubgraphSearchConfigId).
			Case(AssetSubgraphEntityService, cfgIdMap.AssetSubgraphEntitySearchConfigId).
			Default("")
	}
	if len(srvCfgId) < 1 {
		return "", "", nil
	}

	srvId, err = adCfgHelper.GetGraphAnalysisId(ctx, srvCfgId)
	if err != nil {
		return "", "", err
	}

	var gCfgId string
	for _, analysis := range settings.GetConfig().KnowledgeNetworkBuild.GraphAnalysis {
		if analysis.ID == srvCfgId {
			gCfgId = analysis.GraphID
			break
		}
	}

	if len(gCfgId) < 1 {
		log.WithContext(ctx).Warnf("name: %s, analysis service cfg id: %s, graph cfg id: %v", name, srvCfgId, gCfgId)
		return srvId, "", nil
	}

	graphId, err = adCfgHelper.GetGraphId(ctx, gCfgId)
	if err != nil {
		return "", "", err
	}

	return srvId, graphId, nil
}
