package es

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/opensearch"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/olivere/elastic/v7"
)

const (
	indicesAlreadyExistsErrType = "resource_already_exists_exception"
)

func InitIndices(ctx context.Context, indicesAlias, indicesName, mapping string, searchCli *opensearch.SearchClient) error {
	// 检测alias是否存在
	notFound := false
	result, err := searchCli.WriteClient.Aliases().Alias(indicesAlias).Do(ctx)
	if err != nil {
		if esErr, ok := err.(*elastic.Error); ok && esErr.Status == http.StatusNotFound {
			notFound = true
		} else {
			return err
		}
	}

	if notFound {
		return createIndicesIfNotExists(ctx, indicesAlias, indicesName, mapping, searchCli)
	}

	idxs := result.IndicesByAlias(indicesAlias)
	if len(idxs) > 1 {
		err := fmt.Errorf("internal error, es idx alias exists multi idx, alias: %v, idxs: %v", indicesAlias, idxs)
		log.WithContext(ctx).Error(err.Error())
		return err
	}
	sourceIdx := idxs[0]
	if sourceIdx == indicesName {
		return nil
	}
	if err = compareIdxVersion(sourceIdx, indicesName); err != nil {
		return err
	}

	// create new idx
	createIdxResp, err := searchCli.WriteClient.CreateIndex(indicesName).BodyString(mapping).Do(ctx)
	if err != nil {
		if esErr, ok := err.(*elastic.Error); ok && esErr.Details.Type == indicesAlreadyExistsErrType {
			// indices已经存在，返回错误，重新走流程
			err = fmt.Errorf("index already exists, index: %v", indicesName)
			return err
		}
	}
	log.WithContext(ctx).Infof("create indices from es, ack: %v, shards_ack: %v, index: %v", createIdxResp.Acknowledged, createIdxResp.ShardsAcknowledged, createIdxResp.Index)

	// reindex
	_, err = searchCli.WriteClient.Reindex().SourceIndex(sourceIdx).DestinationIndex(indicesName).Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to reindex in es, err: %v", err)
		return err
	}

	// alias转移
	_, err = searchCli.WriteClient.Alias().
		Action(
			elastic.NewAliasRemoveAction(indicesAlias).Index(sourceIdx),
			elastic.NewAliasAddAction(indicesAlias).Index(indicesName),
		).Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to alias action batch opera, err: %v", err)
		return err
	}

	// 删除老idx
	//if _, err = searchCli.WriteClient.DeleteIndex(sourceIdx).Do(ctx); err != nil {
	//	log.Errorf("failed to delete old indices, old indices: %v", sourceIdx)
	//	return err
	//}

	return nil
}

func createIndicesIfNotExists(ctx context.Context, indicesAlias, indicesName, mapping string, searchCli *opensearch.SearchClient) error {
	// 查看索引是否存在
	exist, err := searchCli.WriteClient.
		IndexExists(indicesName).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to access es, err: %v", err)
		return err
	}

	// 存在，直接返回
	if exist {
		return nil
	}

	// 不存在，去创建
	curMapping, err := addAlias(mapping, indicesAlias)
	if err != nil {
		return err
	}
	result, err := searchCli.WriteClient.
		CreateIndex(indicesName).
		BodyJson(curMapping).
		Do(ctx)
	if err == nil {
		log.WithContext(ctx).Infof("create indices from es, ack: %v, shards_ack: %v, index: %v", result.Acknowledged, result.ShardsAcknowledged, result.Index)
		return nil
	}

	if esErr, ok := err.(*elastic.Error); ok && esErr.Details.Type == indicesAlreadyExistsErrType {
		// indices已经存在
		log.WithContext(ctx).Infof("index already exists, index: %v", indicesName)
		return nil
	}

	log.WithContext(ctx).Errorf("failed to create indices, err: %v", err)
	return err
}

func addAlias(mapping, alias string) (map[string]any, error) {
	m := make(map[string]any)
	if err := json.Unmarshal([]byte(mapping), &m); err != nil {
		return nil, fmt.Errorf("invalid es mapping format, err: %w", err)
	}

	m["aliases"] = map[string]any{
		alias: map[string]any{},
	}

	return m, nil
}

func compareIdxVersion(srcV, destV string) error {
	sourceVNum, err := getIdxVersionNum(srcV)
	if err != nil {
		return err
	}

	destVNum, err := getIdxVersionNum(destV)
	if err != nil {
		return err
	}

	if sourceVNum > destVNum {
		err = fmt.Errorf("es idx mapping unsupported downgrade, cur version: %v, dest version: %v", srcV, destV)
		log.Error(err.Error())
		return err
	}

	return nil
}

func getIdxVersionNum(idxName string) (int, error) {
	idx := strings.LastIndex(idxName, "_")
	if idx < 0 || idx > len(idxName)-3 {
		return 0, fmt.Errorf("invalid es index name: %v", idxName)
	}

	vNum, err := strconv.ParseInt(idxName[idx+2:], 10, 0)
	if err != nil {
		return 0, fmt.Errorf("invalid es index name, err: %w: %v", idxName, err)
	}

	return int(vNum), nil
}
