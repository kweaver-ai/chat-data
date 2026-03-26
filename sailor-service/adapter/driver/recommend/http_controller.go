package recommend

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	domain "github.com/kweaver-ai/chat-data/sailor-service/domain/recommend"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

// TableRecommendation 表单推荐
// @Description 表单推荐
// @Tags        智能推荐
// @Summary     表单推荐
// @Accept      json
// @Produce     json
// @Param       reqData   body      domain.TableRecommendationReq    true "表单推荐请求参数"
// @Success     200       {object}  domain.TableRecommendationResp    "成功响应参数"
// @Router      /api/internal/af-sailor-service/v1/recommend/table [post]
func (s *Service) TableRecommendation(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.TableRecommendationReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.TableRecommendation(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// FlowRecommendation 流程图推荐
// @Description 流程图推荐
// @Tags        智能推荐
// @Summary     流程图推荐
// @Accept      json
// @Produce     json
// @Param       reqData   body      domain.FlowRecommendationReq    true "流程图推荐请求参数"
// @Success     200       {object}  domain.FlowRecommendationResp    "成功响应参数"
// @Router      /api/internal/af-sailor-service/v1/recommend/flow [post]
func (s *Service) FlowRecommendation(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.FlowRecommendationReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.FlowRecommendation(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// FieldStandardRecommendation 字段标准推荐
// @Description 字段标准推荐
// @Tags        智能推荐
// @Summary     字段标准推荐
// @Accept      json
// @Produce     json
// @Param       reqData   body      domain.FieldStandardRecommendationReq    true "字段标准推荐请求参数"
// @Success     200       {object}  domain.FieldStandardRecommendationResp    "成功响应参数"
// @Router      /api/internal/af-sailor-service/v1/recommend/code [post]
func (s *Service) FieldStandardRecommendation(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.FieldStandardRecommendationReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.FieldStandardRecommendation(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// CheckCode 字段标准一致性校验
// @Description 字段标准一致性校验
// @Tags        智能推荐
// @Summary     字段标准一致性校验
// @Accept      json
// @Produce     json
// @Param       reqData   body       domain.CheckCodeReq    true "字段标准一致性校验请求参数"
// @Success     200       {object}   domain.CheckCodeResp    "成功响应参数"
// @Router      /api/internal/af-sailor-service/v1/recommend/check/code [post]
func (s *Service) CheckCode(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CheckCodeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CheckCode(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// AssetSearch 资产认知搜索
// @Description AF数据资产认知搜索
// @Tags        智能搜索
// @Summary     AF数据资产认知搜索
// @Accept      json
// @Produce     json
// @Param       reqData   body       domain.AssetSearchReq    true "资产认知搜索请求参数"
// @Success     200       {object}   domain.AssetSearchResp    "成功响应参数"
// @Router      /api/internal/af-sailor-service/v1/recommend/asset/search [GET]
func (s *Service) AssetSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.AssetSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.AssetSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) MetaDataViewRecommend(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.MetaDataViewRecommendReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.MetaDataViewRecommend(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ListKnowledgeNetwork(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ListKnowledgeNetworkReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.ListKnowledgeNetwork(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ListKnowledgeGraph(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ListKnowledgeGraphReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.ListKnowledgeGraph(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ListKnowledgeLexicon(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ListKnowledgeLexiconReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.ListKnowledgeLexicon(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) errResp(c *gin.Context, err error) {
	c.Writer.WriteHeader(http.StatusBadRequest)
	ginx.ResErrJson(c, err)
}
