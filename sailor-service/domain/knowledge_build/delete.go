package knowledge_build

import (
	"context"
	"strconv"

	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/pkg/errors"
	"go.uber.org/zap"
)

func (s *Server) delete(ctx context.Context) (err error) {
	if err = s.canDelete(ctx); err != nil {
		log.Errorf("fail to load network configuration data , err: %v", err)
		return err
	}
	//删除图分析服务
	if err = s.deleteGraphAnalysis(ctx); err != nil {
		log.Errorf("failed to delete graph analysis in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	//删除词库
	if err = s.deleteSynonymsLexicon(ctx); err != nil {
		log.Errorf("failed to delete synonyms lexicon in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	//删除自定义认知服务
	if err = s.deleteCognitiveService(ctx); err != nil {
		log.Errorf("failed to delete cognitive service in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	//删除知识图谱
	if err = s.deleteKnowledgeGraph(ctx); err != nil {
		log.Errorf("failed to delete graph in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	//删除数据源
	if err = s.deleteDataSource(ctx); err != nil {
		log.Errorf("failed to delete datasource in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	//删除知识网络
	if err = s.deleteKnowledgeNetwork(ctx); err != nil {
		log.Errorf("failed to delete knowledge network in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}
	return nil
}

func (s *Server) needDelete(t KNResourceType) bool {
	ids := s.deleteCache.Get(t)
	return len(ids) > 0
}

func (s *Server) deleteKnowledgeNetwork(ctx context.Context) (err error) {
	resourceType := KNResourceTypeKnowledgeNetwork
	if !s.needDelete(resourceType) {
		log.Info("no knowledge network delete")
		return nil
	}
	log.Info("start delete knowledge network ")
	ids := util.SliceStr2Int(s.deleteCache.Get(resourceType))
	if len(ids) <= 0 {
		log.Info("empty knowledge network delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	if err = s.adProxy.DeleteKnowledgeNetwork(ctx, ids[0]); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return err
}
func (s *Server) deleteDataSource(ctx context.Context) (err error) {
	resourceType := KNResourceTypeDataSource
	if !s.needDelete(resourceType) {
		log.Info("no data source delete")
		return nil
	}
	log.Info("start delete data source ")
	dsList := util.SliceStr2Int(s.deleteCache.Get(resourceType))
	if len(dsList) <= 0 {
		log.Info("empty data source delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	if err = s.adProxy.DeleteDataSource(ctx, dsList); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return err
}
func (s *Server) deleteKnowledgeGraph(ctx context.Context) (err error) {
	resourceType := KNResourceTypeKnowledgeGraph
	if !s.needDelete(resourceType) {
		log.Info("no graph delete")
		return nil
	}
	log.Info("start delete graph ")
	ids := util.SliceStr2Int(s.deleteCache.Get(resourceType))
	if len(ids) <= 0 {
		log.Info("empty graph delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	//挨个删除，一次性删除，有可能因为个别图谱不存在而删除失败
	for _, id := range ids {
		if err = s.adProxy.DeleteKnowledgeGraph(ctx, s.deleteCache.NetworkID, []int{id}); err != nil {
			log.Errorf(err.Error())
			return err
		}
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return err
}
func (s *Server) deleteSynonymsLexicon(ctx context.Context) (err error) {
	resourceType := KNResourceTypeLexiconService
	if !s.needDelete(resourceType) {
		log.Info("no lexicon delete")
		return nil
	}
	log.Info("start delete lexicon ")
	ids := util.SliceStr2Int(s.deleteCache.Get(resourceType))
	if len(ids) <= 0 {
		log.Info("empty lexicon delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	if err = s.adProxy.DeleteSynonymsLexicon(ctx, ids); err != nil {
		log.Errorf(err.Error())
		return err
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return nil
}
func (s *Server) deleteGraphAnalysis(ctx context.Context) (err error) {
	resourceType := KNResourceTypeDomainAnalysis
	if !s.needDelete(resourceType) {
		log.Info("no graph analysis delete")
		return nil
	}
	log.Info("start delete graph analysis")
	ids := s.deleteCache.Get(resourceType)
	if len(ids) <= 0 {
		log.Info("empty graph analysis delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	uniqueDict := make(map[string]int)
	for _, id := range ids {
		uniqueDict[id] = 1
	}
	for id, _ := range uniqueDict {
		if err = s.adProxy.GraphAnalysisCancelRelease(ctx, id); err != nil {
			log.Errorf(err.Error())
			return err
		}
		if err = s.adProxy.DeleteGraphAnalysis(ctx, id); err != nil {
			log.Errorf(err.Error())
			return err
		}
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return err
}
func (s *Server) deleteCognitiveService(ctx context.Context) (err error) {
	resourceType := KNResourceTypeSearchEngine
	if !s.needDelete(resourceType) {
		log.Info("no cognitive service delete")
		return nil
	}
	log.Info("start delete cognitive service")
	ids := s.deleteCache.Get(resourceType)
	if len(ids) <= 0 {
		log.Info("empty cognitive service delete", zap.Any("ids", s.deleteCache.Get(resourceType)))
		return nil
	}
	for _, id := range ids {
		if err = s.adProxy.CognitionServiceCancelRelease(ctx, id); err != nil {
			log.Errorf(err.Error())
			return err
		}
		if err = s.adProxy.DeleteCognitionService(ctx, id); err != nil {
			log.Errorf(err.Error())
			return err
		}
	}
	if err == nil {
		s.refreshDeleteCacheData(ctx, resourceType)
	}
	return err
}

func (s *Server) deleteOldGraph(ctx context.Context, mInfo *model.KnowledgeNetworkInfo) (err error) {
	// 版本需要更新，先删除存在的资源
	if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
		return err
	}
	// 直接删除图谱,删除失败不报错，返回即可
	knwId := s.getKnowledgeNetworkIdFromResCache(mInfo.ConfigID)
	graphId, _ := strconv.Atoi(mInfo.RealID)
	if knwId <= 0 || graphId <= 0 {
		log.Warnf("invalid knwId %v and graphId %v", knwId, graphId)
		return nil
	}
	if err := s.adProxy.DeleteKnowledgeGraph(ctx, knwId, []int{graphId}); err != nil {
		log.Warnf("delete graph failed: %v", err)
	}
	return nil
}

func (s *Server) deleteFailedGraph(ctx context.Context, knwId int, graphIds ...int) {
	if err := s.adProxy.DeleteKnowledgeGraph(ctx, knwId, graphIds); err != nil {
		log.Warnf("delete failed graph error: %v", err)
	}
	return
}
