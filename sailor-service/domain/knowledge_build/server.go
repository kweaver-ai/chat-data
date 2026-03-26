package knowledge_build

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"sync"
	"time"

	"github.com/go-co-op/gocron"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	repo "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_build"
	ad_proxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/self"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"
	"go.uber.org/atomic"
)

type KNResourceType int32

const (
	_ KNResourceType = iota
	KNResourceTypeKnowledgeNetwork
	KNResourceTypeDataSource
	KNResourceTypeKnowledgeGraph
	KNResourceTypeDomainAnalysis
	KNResourceTypeSearchEngine
	KNResourceTypeLexiconService
)

const (
	IdsCacheKey           = "xxx.cn/anyfabric/af-sailor-service/ad-resource-delete/delete-ids-key"
	IdsCacheKeyExpireTime = 6 * time.Hour
)

func (t KNResourceType) ToInt32() int32 {
	return int32(t)
}

type Server struct {
	masterMtx    *knowledge_build.Mutex
	adProxy      ad_proxy.AD
	repo         repo.Repo
	selfProxy    self.Proxy
	configCenter configuration_center.DrivenConfigurationCenter

	resCache    map[string]any
	createdRes  map[string]struct{}
	deleteCache *KnCache
	isMaster    atomic.Bool

	resetCh chan time.Time

	mtx    sync.Mutex
	cancel context.CancelFunc

	scheduler *gocron.Scheduler

	buildStatus bool

	graphBuilderLock *sync.Mutex
}

func NewServer(masterMtx *knowledge_build.Mutex, adProxy ad_proxy.AD, repo repo.Repo, selfProxy self.Proxy, configCenter configuration_center.DrivenConfigurationCenter) *Server {
	return &Server{
		masterMtx:        masterMtx,
		adProxy:          adProxy,
		repo:             repo,
		selfProxy:        selfProxy,
		configCenter:     configCenter,
		resetCh:          make(chan time.Time, 1),
		buildStatus:      false,
		graphBuilderLock: &sync.Mutex{},
	}
}

func (s *Server) Reset(ctx context.Context) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if !s.isMaster.Load() {
		// 不是主节点，转发到主节点执行
		log.WithContext(ctx).Info("reset ad init req forward to master exec")
		return s.forwardToMaster(ctx)
	}

	// 是主节点，通知对应线程开始执行
	now := time.Now()
	log.WithContext(ctx).Infof("is master, start reset ad init, time: %v", now)
	select {
	case s.resetCh <- now:
	default:
		log.WithContext(ctx).Warn("exist unexecuted reset tasks")
	}

	return nil
}

// DeleteLock 删除锁缓存
func (s *Server) DeleteLock(ctx context.Context) error {
	return s.masterMtx.DelLock(ctx)
}

func (s *Server) Start(ctx context.Context) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	s.mtx.Lock()
	s.cancel = cancel
	s.mtx.Unlock()

	s.initScheduler()
	defer s.stopScheduled()

	for {
		select {
		case <-ctx.Done():
			log.WithContext(ctx).Info("start exec done")
			return nil
		default:
		}

		func() {
			defer func() {
				_ = s.masterMtx.Release(context.Background())
				s.isMaster.Store(false)
			}()

			// 是否为主
			ctx = s.electMaster(ctx)
			if ctx.Err() != nil {
				return
			}

			s.isMaster.Store(true)

			// 为主，执行逻辑
			s.run(ctx)
		}()
	}
}

func (s *Server) Stop(_ context.Context) error {
	s.mtx.Lock()
	s.cancel()
	s.mtx.Unlock()

	return nil
}

func (s *Server) electMaster(ctx context.Context) context.Context {
	return s.masterMtx.LoopLock(ctx)
}

func (s *Server) run(ctx context.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	// 创建定时任务调度，定时构建图谱数据
	job, err := s.addGraphBuildTaskScheduled(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to start schedule, err: %+v", err)
		panic(err)
	}
	defer func() {
		s.scheduler.RemoveByReference(job)
	}()

	for {
		if err := func() error {
			//defer func() {
			//	if err := recover(); err != nil {
			//		log.WithContext(ctx).Errorf("recover err: %v", err)
			//	}
			//}()

			log.WithContext(ctx).Infof("start knowledge network handle...")
			s.resCache = make(map[string]any)
			s.createdRes = map[string]struct{}{}

			select {
			case <-ctx.Done():
				return ctx.Err()

			case t := <-s.resetCh:
				log.WithContext(ctx).Infof("exec reset ad init, time: %v", t)
				if err = s.reset(ctx); err != nil {
					log.WithContext(ctx).Errorf("failed to reset ad init record, err: %+v\nsrc err: %v", err, errors.Cause(err))
					return errors.Cause(err)
				}

			default:
			}
			//执行各种构建, 让构建图谱任务只有一个在执行
			//buildStatus, err := s.masterMtx.Get(ctx, "buildStatus")
			//if err != nil {
			//	log.Errorf("build error: %v", err.Error())
			//	s.buildStatus = false
			//	return err
			//}
			//buildStatusString := string(buildStatus)
			//if buildStatusString == "end" || len(buildStatusString) == 0 {
			//	err := s.masterMtx.Set(ctx, "building", "buildStatus", 24*time.Hour)
			//	if err != nil {
			//		log.Errorf("build error: %v", err.Error())
			//		s.buildStatus = false
			//		return err
			//	}
			//	if err = s.build(ctx); err != nil {
			//		log.Errorf("build error: %v", err.Error())
			//		s.buildStatus = false
			//		return err
			//	}
			//	err = s.masterMtx.Set(ctx, "end", "buildStatus", 24*time.Hour)
			//	if err != nil {
			//		log.Errorf("build error: %v", err.Error())
			//		s.buildStatus = false
			//		return err
			//	}
			//}
			if s.buildStatus == false {
				s.buildStatus = true
				if err = s.build(ctx); err != nil {
					log.Errorf("build error: %v", err.Error())
					s.buildStatus = false
					return err
				}
				s.buildStatus = false
			}

			log.WithContext(ctx).Infof("end knowledge network handle")
			select {
			case <-ctx.Done():
				return ctx.Err()

			case t := <-s.resetCh:
				log.WithContext(ctx).Infof("exec reset ad init, time: %v", t)
				if err = s.reset(ctx); err != nil {
					log.WithContext(ctx).Errorf("failed to reset ad init record, err: %+v\nsrc err: %v", err, errors.Cause(err))
					return errors.Cause(err)
				}

				//initType = InitiatorTypeManual
			}

			return nil
		}(); err != nil {
			// ctx被取消，表示当前节点不是主，需要重新尝试获取锁
			if errors.Is(err, context.Canceled) {
				log.WithContext(ctx).Warn("lose mtx, lose master")
				return
			}

			// 有错误就sleep一段时间
			select {
			case t := <-s.resetCh:
				log.WithContext(ctx).Infof("exec reset ad init, time: %v", t)
				if err = s.reset(ctx); err != nil {
					log.WithContext(ctx).Errorf("failed to reset ad init record, err: %+v\nsrc err: %v", err, errors.Cause(err))
					return
				}
			case <-ctx.Done():
				return
			case <-time.After(10 * time.Minute):
			}
		}
	}
}

func (s *Server) reset(ctx context.Context) error {
	// 1.缓存将要被删除的数据
	if err := s.cacheDeleteData(ctx); err != nil {
		return err
	}
	// 2.删除已记录的资源信息
	if err := s.repo.DeleteResAll(ctx); err != nil {
		return err
	}
	return nil
}

func (s *Server) forwardToMaster(ctx context.Context) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	masterIP, err := s.masterMtx.GetMasterIP(ctx)
	if err != nil {
		return err
	}

	if err = s.selfProxy.ResetADInit(ctx, masterIP); err != nil {
		return errors.WithMessage(err, "failed to call self to reset ad init")
	}

	return nil
}

func (s *Server) initScheduler() {
	s.scheduler = gocron.NewScheduler(time.Local)
	scheduledCronExpression := settings.GetConfig().KnowledgeNetworkBuild.GraphScheduledCron
	if _, err := cron.ParseStandard(scheduledCronExpression); err != nil {
		panic(err)
	}

	s.scheduler.StartAsync()
}

func (s *Server) addGraphBuildTaskScheduled(ctx context.Context) (*gocron.Job, error) {
	buildJob := newGraphBuildJob(ctx, s)
	job, err := s.scheduler.Cron(settings.GetConfig().KnowledgeNetworkBuild.GraphScheduledCron).Do(buildJob.run)
	if err != nil {
		return nil, errors.Wrap(err, "build graph updated scheduled job failed")
	}

	return job, nil
}

func (s *Server) stopScheduled() {
	s.scheduler.Stop()
}

func (s *Server) checkGraphBuildNormal(ctx context.Context, graphId int) error {
	startTime := time.Now()
	var err error
	var resp *ad_proxy.ListGraphBuildTaskResp

	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	ticker := time.NewTicker(time.Second * 10)
	defer ticker.Stop()

	for {
		if time.Now().Sub(startTime) > time.Minute*2880 {
			if err == nil {
				err = fmt.Errorf("check graph build normal timeout, graph id: %v", graphId)
			}

			log.WithContext(ctx).Errorf("check graph build normal timeout, graph id: %v, err: %v", graphId, err)
			return err
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}

		log.WithContext(ctx).Errorf("this is new version")

		resp, err = s.adProxy.ListGraphBuildTask(ctx, strconv.Itoa(graphId), &ad_proxy.ListGraphBuildTaskReq{
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
			log.WithContext(ctx).Infof("list graph build task failed, err: %v", err)
		} else if resp.Res.GraphStatus == "normal" {
			return nil
		} else if resp.Res.GraphStatus == "failed" {
			return errors.New(fmt.Sprintf("graph: %v build task exec failed", graphId))
		}
	}
}

// cacheDeleteData 缓存要被删除的数据
func (s *Server) cacheDeleteData(ctx context.Context) error {
	// 1.查询所有的配置信息
	records, err := s.repo.SelectResAll(ctx)
	if err != nil {
		return err
	}
	//初始化缓存
	cache := NewKnCache()
	cache.AnyDataAddress = settings.GetConfig().AnyDataConf.URL
	for _, record := range records {
		t := KNResourceType(record.Type)
		if t == KNResourceTypeKnowledgeGraph {
			id, err := parseKnwId(*record.Detail)
			if err != nil {
				return err
			}
			cache.NetworkID = id
		}
		cs := cache.Get(t)
		cache.Set(t, append(cs, record.RealID))
	}
	//将要删除的缓存起来
	if err := s.masterMtx.Set(ctx, cache, IdsCacheKey, IdsCacheKeyExpireTime); err != nil {
		return err
	}
	return nil
}

// loadDeleteCacheData 加载要被删除的数据的
func (s *Server) loadDeleteCacheData(ctx context.Context) error {
	s.deleteCache = NewKnCache()
	bs, err := s.masterMtx.Get(ctx, IdsCacheKey)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(bs, s.deleteCache); err != nil {
		return err
	}
	return nil
}

func (s *Server) canDelete(ctx context.Context) error {
	if err := s.loadDeleteCacheData(ctx); err != nil {
		return err
	}
	//AD的地址已经修改了，无法删除资源直接退出了
	if s.deleteCache.AnyDataAddress != settings.GetConfig().AnyDataConf.URL {
		return fmt.Errorf("anydata address changed from %s to %s, can not clear deleted resources",
			s.deleteCache.AnyDataAddress, settings.GetConfig().AnyDataConf.URL)
	}
	return nil
}

func (s *Server) refreshDeleteCacheData(ctx context.Context, resourceType KNResourceType) {
	if s.deleteCache == nil || !s.needDelete(resourceType) {
		return
	}
	s.deleteCache.Set(resourceType, []string{})
	if s.deleteCache.IsEmpty() {
		if err := s.masterMtx.Del(ctx, IdsCacheKey); err != nil {
			log.Warnf("delete cache error: %v", err)
		}
		return
	}
	if err := s.masterMtx.Set(ctx, s.deleteCache, IdsCacheKey, IdsCacheKeyExpireTime); err != nil {
		log.Warnf("refresh cache error: %v", err)
	}
}
