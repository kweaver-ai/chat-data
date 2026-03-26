package knowledge_build

import (
	"context"
	"fmt"

	ad_proxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"go.uber.org/atomic"
	"golang.org/x/sync/errgroup"
)

type graphBuildJob struct {
	ctx context.Context
	s   *Server

	isRunning *atomic.Bool
}

func newGraphBuildJob(ctx context.Context, s *Server) *graphBuildJob {
	return &graphBuildJob{
		ctx:       ctx,
		s:         s,
		isRunning: atomic.NewBool(false),
	}
}

func (g *graphBuildJob) run() {
	var err error
	ctx, span := trace.StartInternalSpan(g.ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	log.Infof("start exec graph build scheduled tasks...")
	select {
	case <-ctx.Done():
		return
	default:
	}

	// 检测是否在执行，已存在执行的job就直接结束
	if !g.isRunning.CAS(false, true) {
		log.Warnf("already exist graph build job running, this exec end")
		return
	}
	defer g.isRunning.Store(false)

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	graphInfos, err := g.s.repo.ListInfoByType(ctx, KNResourceTypeKnowledgeGraph.ToInt32())
	if err != nil {
		log.WithContext(ctx).Errorf("failed to list graph info by db, err: %v", err)
		return
	}
	filterKg := ""
	afVersion, err := g.s.configCenter.DataUseType(ctx)
	if err == nil {
		if afVersion.Using == 1 {
			filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
		} else if afVersion.Using == 2 {
			filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
		}
		//fmt.Println("afVersion", afVersion)
	}
	log.WithContext(ctx).Infof("filter knowledge network job, id: %s", filterKg)

	eg, _ := errgroup.WithContext(ctx)
	for _, info := range graphInfos {
		if filterKg == info.ConfigID {
			log.WithContext(ctx).Infof("filter knowledge network job, id: %s", info.ConfigID)
			continue
		}
		info := info
		eg.Go(func() error {
			if err := g.buildGraph(ctx, info); err != nil {
				log.WithContext(ctx).Errorf("failed to exec build graph task, graph id: %v, name: %v, err: %+v", info.ID, info.Name, err)
			}
			return nil
		})
	}

	_ = eg.Wait()
	log.WithContext(ctx).Infof("end exec graph build scheduled tasks")
}

func (g *graphBuildJob) buildGraph(ctx context.Context, graphInfo *model.KnowledgeNetworkInfo) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	resp, err := g.s.adProxy.ListGraphBuildTask(ctx, graphInfo.RealID, &ad_proxy.ListGraphBuildTaskReq{
		GraphName:   "",
		Order:       "desc",
		Page:        1,
		Size:        1,
		Rule:        "start_time",
		Status:      "all",
		TaskType:    "all",
		TriggerType: "all",
	})
	if err != nil {
		return errors.Wrap(err, "list knw graph build task failed from ad")
	}

	if lo.Contains([]string{`running`, `waiting`}, resp.Res.GraphStatus) {
		// 该图谱已经在构建中了，不发起构建任务
		log.WithContext(ctx).Warnf("knw graph already building, graph id: %v, name: %v", graphInfo.RealID, graphInfo.Name)
		return nil
	}

	var curGraphBuildTaskType string
	for _, graphCfg := range settings.GetConfig().KnowledgeNetworkBuild.Graph {
		if graphCfg.ID == graphInfo.ConfigID {
			curGraphBuildTaskType = graphCfg.BuildTaskType
			break
		}
	}

	if len(curGraphBuildTaskType) < 1 {
		return errors.New(fmt.Sprintf("graph build task type is empty, graph id: %v, config id: %v, name: %v", graphInfo.ID, graphInfo.ConfigID, graphInfo.Name))
	}

	if _, err = g.s.adProxy.StartGraphBuildTask(ctx, graphInfo.RealID, &ad_proxy.ExecGraphBuildTaskReq{
		TaskType: curGraphBuildTaskType,
	}); err != nil {
		return errors.Wrap(err, "start graph build task failed")
	}

	return nil
}
