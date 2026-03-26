package knowledge_build

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
	"github.com/pkg/errors"
)

type Service struct {
	uc *knowledge_build.Server
}

func NewService(uc *knowledge_build.Server) *Service {
	return &Service{uc: uc}
}

func (s *Service) Reset(c *gin.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(c)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if err := s.uc.Reset(ctx); err != nil {
		log.WithContext(c).Errorf("failed to reset knowledge build, err:\n%+v", err)
		s.errResp(c, errors.Cause(err))
		return
	}

	ginx.ResOKJson(c, "accept")
}

// ReElection 清除缓存，重新选举
func (s *Service) ReElection(c *gin.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(c)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if err := s.uc.DeleteLock(ctx); err != nil {
		log.WithContext(c).Errorf("failed to ReElection err:\n%+v", err)
		s.errResp(c, errors.Cause(err))
		return
	}

	ginx.ResOKJson(c, "deleted")
}

// UpdateSchema 更新本体
func (s *Service) UpdateSchema(c *gin.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(c)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req, err := middleware.GetReqParam[knowledge_build.ModelDetailParam](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.UpdateGraph(ctx, &req.ModelDetail)
	if err != nil {
		log.WithContext(c).Errorf("failed to ReElection err:\n%+v", err)
		s.errResp(c, errors.Cause(err))
		return
	}

	ginx.ResOKJson(c, resp)
}

// DeleteGraph 删除本体
func (s *Service) DeleteGraph(c *gin.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(c)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req, err := middleware.GetReqParam[knowledge_build.ModelDeleteParam](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.DeleteGraph(ctx, &req.ModelDelete)
	if err != nil {
		log.WithContext(c).Errorf("failed to ReElection err:\n%+v", err)
		s.errResp(c, errors.Cause(err))
		return
	}

	ginx.ResOKJson(c, resp)
}

// GraphBuildTask  构建
func (s *Service) GraphBuildTask(c *gin.Context) {
	var err error
	ctx, span := trace.StartInternalSpan(c)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req, err := middleware.GetReqParam[knowledge_build.GraphBuildTaskParam](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.GraphBuildTask(ctx, &req.GraphBuildTaskReq)
	if err != nil {
		log.WithContext(c).Errorf("failed to ReElection err:\n%+v", err)
		s.errResp(c, errors.Cause(err))
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) errResp(c *gin.Context, err error) {
	c.Writer.WriteHeader(http.StatusBadRequest)
	ginx.ResErrJson(c, err)
}
