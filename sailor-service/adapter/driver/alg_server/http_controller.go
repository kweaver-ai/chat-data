package alg_server

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models/response"
	domain "github.com/kweaver-ai/chat-data/sailor-service/domain/alg_server"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

// FullText AD图谱全文搜索
// @Description AD图谱全文搜索
// @Tags        认知工具
// @Summary     AD图谱全文搜索
// @Accept      json
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       reqData     query        domain.FullTextReq    true "AD图谱全文搜索参数"
// @Success     200       {object} 		 domain.FullTextResp   	 	"成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/internal/af-sailor-service/v1/tools/knowledge-network/alg-server/graph-search/kgs/full-text [POST]
func (s *Service) FullText(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.FullTextReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.FullText(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// Neighbors AD图谱邻居搜索
// @Description AD图谱邻居搜索
// @Tags        认知工具
// @Summary     AD图谱邻居搜索
// @Accept      json
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       reqData     query        domain.NeighborsReq    true "AD图谱邻居搜索参数"
// @Success     200       {object} 		 domain.NeighborsResp    		"成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/internal/af-sailor-service/v1/tools/knowledge-network/alg-server/explore/kgs/neighbors [POST]
func (s *Service) Neighbors(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.NeighborsReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.Neighbors(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// Iframe 数据资产图谱呈现
// @Description 数据资产图谱呈现
// @Tags        认知工具
// @Summary     数据资产图谱呈现
// @Accept      plain
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       reqData     query        domain.IframeReq    true "数据资产图谱呈现请求参数"
// @Success     200       {object} string    		"成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/af-sailor-service/v1/tools/knowledge-network/graph/iframe  [GET]
func (s *Service) Iframe(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.IframeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	redirectURL, err := s.uc.Iframe(c, req)
	if err != nil {
		log.Error(err.Error())
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataConfigError) {
			s.errResp(c, errorcode.Desc(errorcode.AnyDataConfigError))
			return
		}
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataAuthError) {
			s.errResp(c, errorcode.Desc(errorcode.AnyDataAuthError))
			return
		}
		if errorcode.IsSameErrorCode(err, errorcode.FullTextSearchEmptyError) {
			s.errResp(c, errorcode.Desc(errorcode.FullTextSearchEmptyError))
			return
		}
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataServiceError) {
			s.errResp(c, errorcode.Desc(errorcode.AnyDataServiceError))
			return
		}
		if errorcode.IsSameErrorCode(err, errorcode.AnyDataConnectionError) {
			s.errResp(c, errorcode.Desc(errorcode.AnyDataConnectionError))
			return
		}
		s.errResp(c, errorcode.Desc(errorcode.CurrentEmptyDataError))
		return
	}
	log.Info(redirectURL)
	c.PureJSON(http.StatusOK, response.ResResult{
		Res: redirectURL,
	})
	return
}

// GraphAnalysis 图分析结果查询
// @Description 图分析结果查询
// @Tags        认知工具
// @Summary     数据资产图谱呈现
// @Accept      plain
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       reqData     query        domain.IframeReq    true "数据资产图谱呈现请求参数"
// @Success     200       {object} string    		"成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/af-sailor-service/v1/tools/knowledge-network/graph/iframe  [GET]
func (s *Service) GraphAnalysis(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.GraphAnalysisReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	resp, err := s.uc.GraphAnalysis(c, req)
	if err != nil {
		log.Error(err.Error())
		s.errResp(c, errorcode.Desc(errorcode.CurrentEmptyDataError))
		return
	}
	c.PureJSON(http.StatusOK, resp)
	return

}

func (s *Service) errResp(c *gin.Context, err error) {
	c.Writer.WriteHeader(http.StatusBadRequest)
	ginx.ResErrJson(c, err)
}
