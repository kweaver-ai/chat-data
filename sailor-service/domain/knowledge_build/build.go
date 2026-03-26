package knowledge_build

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	adProxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"go.uber.org/zap"
	"golang.org/x/sync/errgroup"
)

func (s *Server) build(ctx context.Context) (err error) {
	//删除老的配置
	if err = s.delete(ctx); err != nil {
		log.WithContext(ctx).Errorf("fail to delete old network configuration, err: %v", err)
	}

	if err = s.knowledgeNetworkHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle knowledge network in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	if err = s.dataSourceHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle datasource in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	if err = s.knowledgeGraphHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle graph in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	//新建词库，词库将来可能被概念词库代替
	if err = s.synonymsLexiconHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle synonyms lexicon in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	//构建指定的图分析服务
	if err = s.graphAnalysisHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle graph analysis in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	if err = s.cognitiveServiceHandle(ctx); err != nil {
		log.WithContext(ctx).Errorf("failed to handle cognitive service in init, err: %+v\nsrc err: %v", err, errors.Cause(err))
		return errors.Cause(err)
	}

	return nil
}

type knowledgeNetworkInfo struct {
	ID    string
	Name  string
	Desc  string
	Color string
}

func (s *Server) knowledgeNetworkHandle(ctx context.Context) error {
	log.WithContext(ctx).Info("start handle knowledge network...")
	filterKg := ""
	afVersion, err := s.configCenter.DataUseType(ctx)
	if err == nil {
		if afVersion.Using == 1 {
			filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
		} else if afVersion.Using == 2 {
			filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
		}
		//fmt.Println("afVersion", afVersion)
	}
	log.WithContext(ctx).Infof("filter knowledge network, id: %s", filterKg)

	for _, kn := range settings.GetConfig().KnowledgeNetworkBuild.KnowledgeNetwork {
		log.WithContext(ctx).Infof("handle knowledge network, id: %s, name: %s", kn.ID, kn.Name)
		if len(kn.ID) < 1 {
			log.WithContext(ctx).Warn("invalid knowledge network cfg id")
			continue
		}
		// 筛选掉不需要的图谱
		if kn.ID == filterKg {
			log.WithContext(ctx).Infof("filter knowledge network, id: %s", kn.ID)
			continue
		}
		if _, ok := s.resCache[kn.ID]; ok {
			panic(fmt.Sprintf("knowledge network config id conflict, id: %s", kn.ID))
		}

		mInfo, err := s.repo.GetInfoByConfigId(ctx, kn.ID)
		if err != nil {
			return err
		}
		if mInfo != nil {
			log.WithContext(ctx).Infof("knowledge network already exist, id: %s, name: %s, exist name: %s, version: %d, need version: %d", kn.ID, kn.Name, mInfo.Name, mInfo.Version, kn.Version)
			// 知识网络已存在
			if mInfo.Version >= kn.Version {
				// 已存在版本高于要设置的版本，不处理
				s.resCache[kn.ID] = &knowledgeNetworkInfo{
					ID:   mInfo.RealID,
					Name: mInfo.Name,
				}
				continue
			}

			// 版本需要更新，先删除存在的资源
			if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
				return err
			}
		}

		// 创建知识网络
		req := &adProxy.CreateKnowledgeNetworkReq{
			KnwName:  genResName(kn.Name),
			KnwDes:   "",
			KnwColor: "#126EE3",
		}
		log.WithContext(ctx).Infof("start create knowledge network in ad, id: %s, name: %s", kn.ID, req.KnwName)
		resp, err := s.adProxy.CreateKnowledgeNetwork(ctx, req)
		if err != nil {
			return errors.WithStack(err)
		}

		knInfo := &knowledgeNetworkInfo{
			ID:    strconv.Itoa(resp.Data),
			Name:  req.KnwName,
			Desc:  req.KnwDes,
			Color: req.KnwColor,
		}

		// 保存知识网络信息
		now := time.Now()
		id := uuid.NewString()
		if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
			ID:        id,
			Name:      knInfo.Name,
			Version:   kn.Version,
			Type:      KNResourceTypeKnowledgeNetwork.ToInt32(),
			ConfigID:  kn.ID,
			RealID:    knInfo.ID,
			CreatedAt: &now,
			UpdatedAt: &now,
		}, &model.KnowledgeNetworkInfoDetail{
			ID:     id,
			Detail: lo.ToPtr(string(lo.T2(json.Marshal(knInfo)).A)),
		}); err != nil {
			return errors.WithMessage(err, "failed to save kn info")
		}

		s.resCache[kn.ID] = knInfo
		s.createdRes[kn.ID] = struct{}{}
	}

	return nil
}

type dataSourceInfo struct {
	ID                 string
	Name               string
	Source             string
	DataType           string
	Address            string
	Port               int
	User               string
	Password           string
	Path               string
	ExtractType        string
	ConnectType        string
	KnowledgeNetworkID string
}

func (s *Server) dataSourceHandle(ctx context.Context) error {
	for _, ds := range settings.GetConfig().KnowledgeNetworkBuild.Datasource {
		if len(ds.ID) < 1 {
			log.WithContext(ctx).Warn("invalid datasource cfg id")
			continue
		}

		if _, ok := s.resCache[ds.ID]; ok {
			panic(fmt.Sprintf("datasource config id conflict, id: %s", ds.ID))
		}

		if len(ds.OldID) > 0 {
			// 老数据源，不需要做处理
			s.resCache[ds.ID] = &dataSourceInfo{
				ID: ds.OldID,
			}
			continue
		}

		// 新数据源，需要创建和保存信息
		mInfo, err := s.repo.GetInfoByConfigId(ctx, ds.ID)
		if err != nil {
			return err
		}
		if mInfo != nil {
			// 数据源已存在
			if _, ok := s.createdRes[ds.KnowledgeNetworkID]; !ok && mInfo.Version >= ds.Version {
				// 已存在版本高于要设置的版本，不处理
				s.resCache[ds.ID] = &dataSourceInfo{
					ID:                 mInfo.RealID,
					Name:               mInfo.Name,
					KnowledgeNetworkID: strconv.Itoa(s.getKnowledgeNetworkIdFromResCache(ds.KnowledgeNetworkID)),
				}
				continue
			}

			// 版本需要更新，先删除存在的资源
			if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
				return err
			}
		}

		knId := s.getKnowledgeNetworkIdFromResCache(ds.KnowledgeNetworkID)

		// 创建数据源
		req := &adProxy.CreateDatasourceReq{
			DSName:      genResName(ds.Name),
			DataSource:  ds.Source,
			DataType:    ds.DataType,
			DSAddress:   ds.Address,
			DSPort:      ds.Port,
			DSUser:      ds.User,
			DSPassword:  base64.StdEncoding.EncodeToString([]byte(ds.Password)),
			DSPath:      ds.Path,
			ExtractType: ds.ExtractType,
			KnwId:       knId,
			ConnectType: ds.ConnectType,
		}
		resp, err := s.adProxy.CreateDataSource(ctx, req)
		if err != nil {
			return errors.WithStack(err)
		}

		dsInfo := &dataSourceInfo{
			ID:                 strconv.Itoa(resp.DSId),
			Name:               req.DSName,
			Source:             req.DataSource,
			DataType:           req.DataType,
			Address:            req.DSAddress,
			Port:               req.DSPort,
			User:               req.DSUser,
			Password:           req.DSPassword,
			Path:               req.DSPath,
			ExtractType:        req.ExtractType,
			ConnectType:        req.ConnectType,
			KnowledgeNetworkID: strconv.Itoa(req.KnwId),
		}

		// 保存数据源信息
		id := uuid.NewString()
		now := time.Now()
		if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
			ID:        id,
			Name:      dsInfo.Name,
			Version:   ds.Version,
			Type:      KNResourceTypeDataSource.ToInt32(),
			ConfigID:  ds.ID,
			RealID:    dsInfo.ID,
			CreatedAt: &now,
			UpdatedAt: &now,
		}, &model.KnowledgeNetworkInfoDetail{
			ID:     id,
			Detail: lo.ToPtr(string(lo.T2(json.Marshal(dsInfo)).A)),
		}); err != nil {
			return err
		}

		s.resCache[ds.ID] = dsInfo
		s.createdRes[ds.ID] = struct{}{}
	}

	return nil
}

func (s *Server) getKnowledgeNetworkIdFromResCache(cfgId string) int {
	knInfoAny, ok := s.resCache[cfgId]
	if !ok {
		panic(fmt.Sprintf("knowledge network id is invalid, cfg id: %s", cfgId))
	}

	idStr := knInfoAny.(*knowledgeNetworkInfo).ID
	knId, err := strconv.Atoi(idStr)
	if err != nil {
		panic(fmt.Sprintf("knowledge network id not is integer, val: %s", idStr))
	}

	return knId
}

func (s *Server) getDataSourceIdFromResCache(cfgId string) int {
	dsInfoAny, ok := s.resCache[cfgId]
	if !ok {
		panic(fmt.Sprintf("datasource id is invalid, cfg id: %s", cfgId))
	}

	idStr := dsInfoAny.(*dataSourceInfo).ID
	knId, err := strconv.Atoi(idStr)
	if err != nil {
		panic(fmt.Sprintf("datasource id not is integer, val: %s", idStr))
	}

	return knId
}

type knowledgeGraphInfo struct {
	ID      string
	Name    string
	KnwId   string
	DSIdMap string
}

func (s *Server) buildKnowledgeGraph(ctx context.Context, mtx *sync.Mutex, i int, g settings.GraphBuildInfo) error {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, nil) }()

	if len(g.ID) < 1 {
		log.WithContext(ctx).Warn("invalid knowledge graph cfg id")
		return nil
	}

	mtx.Lock()
	_, ok := s.resCache[g.ID]
	mtx.Unlock()
	if ok {
		panic(fmt.Sprintf("knowledge graph config id conflict, id: %s", g.ID))
	}

	mInfo, err := s.repo.GetInfoByConfigId(ctx, g.ID)
	if err != nil {
		return err
	}
	if mInfo != nil {
		// 图谱已经存在
		if _, ok := s.createdRes[g.NewDatasourceID]; !ok && mInfo.Version >= g.Version {
			// 已存在版本高于要设置的版本，不处理
			mtx.Lock()
			s.resCache[g.ID] = &knowledgeGraphInfo{
				ID:    mInfo.RealID,
				Name:  mInfo.Name,
				KnwId: strconv.Itoa(s.getKnowledgeNetworkIdFromResCache(g.KnowledgeNetworkID)),
			}
			mtx.Unlock()
			return nil
		}

		// 版本需要更新，先删除存在的资源
		if err = s.deleteOldGraph(ctx, mInfo); err != nil {
			return err
		}
	}

	if i > 0 {
		// ad的接口不能并发调用，所以这里sleep一下
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Duration(i*5) * time.Second):
		}
	}

	knId, oldDSId, newDSId := func() (int, int, int) {
		mtx.Lock()
		defer mtx.Unlock()
		return s.getKnowledgeNetworkIdFromResCache(g.KnowledgeNetworkID),
			s.getDataSourceIdFromResCache(g.OldDatasourceID),
			s.getDataSourceIdFromResCache(g.NewDatasourceID)
	}()
	dsIdMap := string(lo.T2(json.Marshal(map[int]int{oldDSId: newDSId})).A)

	filePath := settings.GetConfig().KnowledgeNetworkBuild.FilePath(g.FilePath)
	file, err := util.FileContentBuffer(filePath)
	if err != nil {
		return errors.Wrapf(err, "failed to open file: %v", filePath)
	}

	randName := genResName(g.Name)
	resp, err := s.adProxy.ImportKnowledgeGraph(ctx, &adProxy.ImportKnowledgeGraphReq{
		KnwId:   knId,
		Rename:  randName,
		File:    file,
		DSIdMap: dsIdMap,
	})
	if err != nil {
		return errors.Wrap(err, "failed to import knowledge graph")
	}

	// 发起图谱构建任务
	if _, err = s.adProxy.StartGraphBuildTask(ctx, strconv.Itoa(resp.GraphId[0]), &adProxy.ExecGraphBuildTaskReq{TaskType: "full"}); err != nil {
		s.deleteFailedGraph(ctx, knId, resp.GraphId...)
		return errors.Wrap(err, "failed to start graph build task")
	}

	// 等待图谱构建任务完成
	if err = s.checkGraphBuildNormal(ctx, resp.GraphId[0]); err != nil {
		s.deleteFailedGraph(ctx, knId, resp.GraphId...)
		return err
	}

	graphInfo := &knowledgeGraphInfo{
		ID:      strconv.Itoa(resp.GraphId[0]),
		Name:    randName,
		KnwId:   strconv.Itoa(knId),
		DSIdMap: dsIdMap,
	}

	id := uuid.NewString()
	now := time.Now()
	if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
		ID:        id,
		Name:      randName,
		Version:   g.Version,
		Type:      KNResourceTypeKnowledgeGraph.ToInt32(),
		ConfigID:  g.ID,
		RealID:    graphInfo.ID,
		CreatedAt: &now,
		UpdatedAt: &now,
	}, &model.KnowledgeNetworkInfoDetail{
		ID:     id,
		Detail: lo.ToPtr(string(lo.T2(json.Marshal(graphInfo)).A)),
	}); err != nil {
		s.deleteFailedGraph(ctx, knId, resp.GraphId...)
		return err
	}

	mtx.Lock()
	s.resCache[g.ID] = graphInfo
	s.createdRes[g.ID] = struct{}{}
	mtx.Unlock()
	return nil
}

func (s *Server) knowledgeGraphHandle(ctx context.Context) error {
	mtx := &sync.Mutex{}
	eg := &errgroup.Group{}
	//filterKg := ""
	//afVersion, err := s.configCenter.DataUseType(ctx)
	//if err == nil {
	//	if afVersion.Using == 1 {
	//		filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	//	} else if afVersion.Using == 2 {
	//		filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	//	}
	//	//fmt.Println("afVersion", afVersion)
	//}
	//log.WithContext(ctx).Infof("filter knowledge network, id: %s", filterKg)
	for i, g := range settings.GetConfig().KnowledgeNetworkBuild.Graph {

		fmt.Println("builder graph ", g.Name)
		//if g.ID == filterKg {
		//	log.WithContext(ctx).Infof("filter knowledge network, id: %s", g.ID)
		//	continue
		//}
		i := i
		g := g

		eg.Go(func() error {
			ctx := context.WithValue(ctx, "graph_index", i)
			return s.buildKnowledgeGraph(ctx, mtx, i, g)
		})
	}
	if err := eg.Wait(); err != nil {
		return err
	}
	return nil
}

func (s *Server) getGraphIdAndKNIdFromRecCache(graphCfgId string) (graphId, knId int) {
	gInfoAny, ok := s.resCache[graphCfgId]
	if !ok {
		panic(fmt.Sprintf("knowledge graph id is invalid, cfg id: %s", graphCfgId))
	}

	graphInfo := gInfoAny.(*knowledgeGraphInfo)
	graphId, err := strconv.Atoi(graphInfo.ID)
	if err != nil {
		panic(fmt.Sprintf("knowledge graph id not is integer, val: %s", graphInfo.ID))
	}

	knId, err = strconv.Atoi(graphInfo.KnwId)
	if err != nil {
		panic(fmt.Sprintf("knowledge network id not is integer, val: %s, knwId: %s, err: %v", graphInfo.ID, graphInfo.KnwId, err))
	}

	return graphId, knId
}

type graphAnalysisInfo struct {
	ID      string
	Name    string
	KnId    string
	GraphId string
}

func (s *Server) graphAnalysisHandle(ctx context.Context) error {
	graphAnalysisInfos := make([]settings.GraphAnalysis, 0)
	for _, a := range settings.GetConfig().KnowledgeNetworkBuild.GraphAnalysis {
		//log.Info("")
		//fmt.Println(a.FilePath)
		filePath := settings.GetConfig().KnowledgeNetworkBuild.FilePath(a.FilePath)
		isDir, err := util.IsDir(filePath)
		if err != nil {
			log.WithContext(ctx).Error("judge graph analysis is file or path error", zap.Error(err))
			return err
		}
		if !isDir {
			a.FilePath = filePath
			a.FileBaseName = util.FileBase(filePath)
			graphAnalysisInfos = append(graphAnalysisInfos, a)
			continue
		}
		if isDir {
			files, err := util.ReadDirFiles(filePath)
			if err != nil {
				log.WithContext(ctx).Error("read graph analysis path file error ", zap.Error(err))
				return err
			}
			for _, f := range files {
				baseName := util.FileBase(f)
				entityNames := strings.Split(a.EntityMap[baseName], ";")
				for _, entityName := range entityNames {
					graphAnalysisInfos = append(graphAnalysisInfos, settings.GraphAnalysis{
						ID:           a.ID + "-" + entityName,
						Name:         baseName + "_" + entityName,
						FileBaseName: baseName,
						GraphID:      a.GraphID,
						FilePath:     f,
						Version:      a.Version,
					})
				}
			}
		}
	}

	graphAnalysisCreateRecord := make(map[string]graphAnalysisInfo)
	for _, a := range graphAnalysisInfos {
		if len(a.ID) < 1 {
			log.WithContext(ctx).Warn("invalid graph analysis cfg id")
			continue
		}

		if _, ok := s.resCache[a.ID]; ok {
			panic(fmt.Sprintf("graph analysis config id conflict, id: %s", a.ID))
		}

		mInfo, err := s.repo.GetInfoByConfigId(ctx, a.ID)
		if err != nil {
			return err
		}
		if mInfo != nil {
			// 图分析服务已经存在
			if _, ok := s.createdRes[a.GraphID]; !ok && mInfo.Version >= a.Version {
				// 已存在版本高于要设置的版本，不处理
				graphId, knId := s.getGraphIdAndKNIdFromRecCache(a.GraphID)
				s.resCache[a.ID] = &graphAnalysisInfo{
					ID:      mInfo.RealID,
					Name:    mInfo.Name,
					KnId:    strconv.Itoa(knId),
					GraphId: strconv.Itoa(graphId),
				}
				continue
			}

			// 版本需要更新，先删除存在的资源
			if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
				return err
			}
		}

		graphId, knId := s.getGraphIdAndKNIdFromRecCache(a.GraphID)

		file, err := util.FileContentBuffer(a.FilePath)
		if err != nil {
			return errors.Wrapf(err, "failed to open graph analysis file: %s", a.FilePath)
		}

		randName := genResName(a.Name)
		recordInfo, ok := graphAnalysisCreateRecord[a.FileBaseName]
		gAnalysisInfo := &graphAnalysisInfo{
			ID:      recordInfo.ID,
			Name:    randName,
			KnId:    strconv.Itoa(knId),
			GraphId: strconv.Itoa(graphId),
		}
		//创建图分析服务
		if !ok {
			importResp, err := s.adProxy.ImportDomainAnalysis(ctx, &adProxy.ImportDomainAnalysisReq{
				Name:    randName,
				KnwId:   knId,
				KgId:    graphId,
				File:    file,
				Publish: true,
			})
			if err != nil {
				return errors.Wrap(err, "failed to import graph analysis")
			}
			gAnalysisInfo.ID = importResp.Res
			graphAnalysisCreateRecord[a.FileBaseName] = *gAnalysisInfo
		}

		id := uuid.NewString()
		now := time.Now()
		if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
			ID:        id,
			Name:      gAnalysisInfo.Name,
			Version:   a.Version,
			Type:      KNResourceTypeDomainAnalysis.ToInt32(),
			ConfigID:  a.ID,
			RealID:    gAnalysisInfo.ID,
			CreatedAt: &now,
			UpdatedAt: &now,
		}, &model.KnowledgeNetworkInfoDetail{
			ID:     id,
			Detail: lo.ToPtr(string(lo.T2(json.Marshal(gAnalysisInfo)).A)),
		}); err != nil {
			return err
		}

		s.resCache[a.ID] = gAnalysisInfo
		s.createdRes[a.ID] = struct{}{}
	}

	return nil
}

type cognitiveServiceInfo struct {
	ID      string
	Name    string
	KnId    string
	GraphId string
}

func (s *Server) cognitiveServiceHandle(ctx context.Context) error {
	for _, c := range settings.GetConfig().KnowledgeNetworkBuild.CognitiveService {
		if len(c.ID) < 1 {
			log.WithContext(ctx).Warn("invalid cognitive service cfg id")
			continue
		}

		if _, ok := s.resCache[c.ID]; ok {
			panic(fmt.Sprintf("cognitive service config id conflict, id: %s", c.ID))
		}

		mInfo, err := s.repo.GetInfoByConfigId(ctx, c.ID)
		if err != nil {
			return err
		}
		if mInfo != nil {
			// 认知服务已经存在
			if _, ok := s.createdRes[c.GraphID]; !ok && mInfo.Version >= c.Version {
				// 已存在版本高于要设置的版本，不处理
				graphId, knId := s.getGraphIdAndKNIdFromRecCache(c.GraphID)
				s.resCache[c.ID] = &cognitiveServiceInfo{
					ID:      mInfo.RealID,
					Name:    mInfo.Name,
					KnId:    strconv.Itoa(knId),
					GraphId: strconv.Itoa(graphId),
				}
				continue
			}

			// 版本需要更新，先删除存在的资源
			if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
				return err
			}
		}

		graphId, knId := s.getGraphIdAndKNIdFromRecCache(c.GraphID)

		filePath := settings.GetConfig().KnowledgeNetworkBuild.FilePath(c.FilePath)
		fileData, err := util.FileContent(filePath)
		if err != nil {
			return errors.Wrapf(err, "failed to read cognitive service file: %s", filePath)
		}

		// 替换图谱id
		fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"graph_id": "%s"`, c.OldGraphID)), []byte(fmt.Sprintf(`"graph_id": "%d"`, graphId)))
		fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"graph_id":"%s"`, c.OldGraphID)), []byte(fmt.Sprintf(`"graph_id":"%d"`, graphId)))
		if c.NewLexiconID != "" {
			// 替换图谱id,这里希望AD那边给出统一的ID
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"kg_id": %s`, c.OldGraphID)), []byte(fmt.Sprintf(`"kg_id": %d`, graphId)))
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"kg_id":%s`, c.OldGraphID)), []byte(fmt.Sprintf(`"kg_id":%d`, graphId)))
			// 替换近义词库id
			newLexiconId := s.getLexiconIdFromResCache(c.NewLexiconID)
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"lexicon_id": "%s"`, c.OldLexiconID)), []byte(fmt.Sprintf(`"lexicon_id": "%d"`, newLexiconId)))
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"lexicon_id":"%s"`, c.OldLexiconID)), []byte(fmt.Sprintf(`"lexicon_id":"%d"`, newLexiconId)))
			// 替换停用词库id
			newStopwordsLexiconId := s.getLexiconIdFromResCache(c.NewStopwordsLexiconID)
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"lexicon_id": "%s"`, c.OldStopwordsLexiconID)), []byte(fmt.Sprintf(`"lexicon_id": "%d"`, newStopwordsLexiconId)))
			fileData = bytes.ReplaceAll(fileData, []byte(fmt.Sprintf(`"lexicon_id":"%s"`, c.OldStopwordsLexiconID)), []byte(fmt.Sprintf(`"lexicon_id":"%d"`, newStopwordsLexiconId)))
		}

		//如果是认知搜索，那就单独执行下替换服务
		//if c.ID == settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchConfigId {
		//	fileData, err = s.cognitiveSearchReplace(fileData)
		//	if err != nil {
		//		log.WithContext(ctx).Errorf("cognitive %v replace error %v", err.Error())
		//	}
		//}
		m := make(map[string]any)
		err = json.Unmarshal(fileData, &m)

		randName := genResName(c.Name)
		adResp, err := s.adProxy.AddCognitiveService(ctx, &adProxy.AddCognitiveServiceReq{
			Status:       1,
			KnwId:        strconv.Itoa(knId),
			Name:         randName,
			AccessMethod: []string{"restAPI"},
			Permission:   "appid_login",
			CustomConfig: m,
		})
		if err != nil {
			return errors.Wrap(err, "failed to add cognitive service")
		}

		cognitiveInfo := &cognitiveServiceInfo{
			ID:      adResp.Res,
			Name:    randName,
			KnId:    strconv.Itoa(knId),
			GraphId: strconv.Itoa(graphId),
		}

		id := uuid.NewString()
		now := time.Now()
		if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
			ID:        id,
			Name:      cognitiveInfo.Name,
			Version:   c.Version,
			Type:      KNResourceTypeSearchEngine.ToInt32(),
			ConfigID:  c.ID,
			RealID:    cognitiveInfo.ID,
			CreatedAt: &now,
			UpdatedAt: &now,
		}, &model.KnowledgeNetworkInfoDetail{
			ID:     id,
			Detail: lo.ToPtr(string(lo.T2(json.Marshal(cognitiveInfo)).A)),
		}); err != nil {
			return err
		}

		s.resCache[c.ID] = cognitiveInfo
		s.createdRes[c.ID] = struct{}{}
	}

	return nil
}

// cognitiveSearchReplace 认知搜索替换参数逻辑
func (s *Server) cognitiveSearchReplace(fileData []byte) ([]byte, error) {
	graphAnalysisId := settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId

	entity2ServiceJsonStr, start, end := util.FindValidJsonPart(string(fileData), "entity2service")
	if entity2ServiceJsonStr == "" {
		return nil, fmt.Errorf("missing entity2service config")
	}
	entity2ServiceMap := make(map[string]settings.WeightItem)
	if err := json.Unmarshal([]byte(entity2ServiceJsonStr), &entity2ServiceMap); err != nil {
		return nil, fmt.Errorf("invalid cognitive search entity2service config error: %v", err.Error())
	}
	for entityName, cfg := range entity2ServiceMap {
		key := graphAnalysisId + "-" + entityName
		info, ok := s.resCache[key]
		if !ok {
			return nil, fmt.Errorf("missing graph analysis %v", entityName)
		}
		graphAnalysisConfig, ok := info.(*graphAnalysisInfo)
		cfg.Service = graphAnalysisConfig.ID
		entity2ServiceMap[entityName] = cfg
	}
	bs, _ := json.Marshal(entity2ServiceMap)
	newFileData := make([]byte, 0, len(fileData))
	newFileData = append(newFileData, fileData[:start]...)
	newFileData = append(newFileData, bs...)
	newFileData = append(newFileData, fileData[end:]...)
	return newFileData, nil
}

type SynonymsLexiconInfo struct {
	ID   string
	Name string
	KnId string
}

func (s *Server) synonymsLexiconHandle(ctx context.Context) error {
	for _, c := range settings.GetConfig().KnowledgeNetworkBuild.SynonymsLexicons {
		if len(c.ID) < 1 {
			log.WithContext(ctx).Warn("invalid cognitive service cfg id")
			continue
		}

		if _, ok := s.resCache[c.ID]; ok {
			panic(fmt.Sprintf("cognitive service config id conflict, id: %s", c.ID))
		}

		mInfo, err := s.repo.GetInfoByConfigId(ctx, c.ID)
		if err != nil {
			return err
		}
		if mInfo != nil { // 词库已经构建
			if _, ok := s.createdRes[c.ID]; !ok && mInfo.Version >= c.Version {
				// 已存在版本高于要设置的版本，不处理
				knId := s.getNetworkIDFromRecCache(c.KnowledgeNetworkID)
				s.resCache[c.ID] = &SynonymsLexiconInfo{
					ID:   mInfo.RealID,
					Name: mInfo.Name,
					KnId: strconv.Itoa(knId),
				}
				continue
			}
			// 版本需要更新，先删除存在的资源
			if err = s.repo.DeleteInfoById(ctx, mInfo.ID); err != nil {
				return err
			}
		}

		//读取文件内容
		filePath := settings.GetConfig().KnowledgeNetworkBuild.FilePath(c.FilePath)
		fileData, err := util.FileContentBuffer(filePath)
		if err != nil {
			return errors.Wrapf(err, "failed to read cognitive service file: %s", filePath)
		}

		knId := s.getNetworkIDFromRecCache(c.KnowledgeNetworkID)
		randName := genResName(c.Name)
		adResp, err := s.adProxy.AddSynonymsLexicon(ctx, &adProxy.NewLexiconReq{
			Name:        randName,
			Labels:      []string{},
			Description: "认知搜索近义词库",
			File:        fileData,
			KnowledgeId: strconv.Itoa(knId),
		})
		if err != nil {
			return errors.Wrap(err, "failed to add synonyms lexicon")
		}

		synonymsLexiconInfo := &SynonymsLexiconInfo{
			ID:   strconv.Itoa(adResp.Res),
			Name: randName,
			KnId: strconv.Itoa(knId),
		}

		id := uuid.NewString()
		now := time.Now()
		if err = s.repo.SaveRes(ctx, &model.KnowledgeNetworkInfo{
			ID:        id,
			Name:      synonymsLexiconInfo.Name,
			Version:   c.Version,
			Type:      KNResourceTypeLexiconService.ToInt32(),
			ConfigID:  c.ID,
			RealID:    synonymsLexiconInfo.ID,
			CreatedAt: &now,
			UpdatedAt: &now,
		}, &model.KnowledgeNetworkInfoDetail{
			ID:     id,
			Detail: lo.ToPtr(string(lo.T2(json.Marshal(synonymsLexiconInfo)).A)),
		}); err != nil {
			return err
		}

		s.resCache[c.ID] = synonymsLexiconInfo
		s.createdRes[c.ID] = struct{}{}
	}
	return nil
}

func (s *Server) getNetworkIDFromRecCache(id string) (knId int) {
	kInfoAny, ok := s.resCache[id]
	if !ok {
		panic(fmt.Sprintf("knowledge graph id is invalid, cfg id: %s", id))
	}
	networkInfo := kInfoAny.(*knowledgeNetworkInfo)
	knId, err := strconv.Atoi(networkInfo.ID)
	if err != nil {
		panic(fmt.Sprintf("knowledge network id not is integer, val: %s, name: %s, err: %v", networkInfo.ID, networkInfo.Name, err))
	}
	return knId
}

func (s *Server) getLexiconIdFromResCache(cfgId string) int {
	dsInfoAny, ok := s.resCache[cfgId]
	if !ok {
		panic(fmt.Sprintf("datasource id is invalid, cfg id: %s", cfgId))
	}

	idStr := dsInfoAny.(*SynonymsLexiconInfo).ID
	knId, err := strconv.Atoi(idStr)
	if err != nil {
		panic(fmt.Sprintf("datasource id not is integer, val: %s", idStr))
	}
	return knId
}
