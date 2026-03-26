package large_language_model

import (
	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models/response"
	domain "github.com/kweaver-ai/chat-data/sailor-service/domain/intelligence"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

// SampleData 样例数据
// @Description 样例数据
// @Tags        认知工具
// @Summary     样例数据
// @Accept      json
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       reqData    body        domain.SampleDataReq    true "样例数据参数"
// @Success     200       {object} response.ResResult{Res=domain.SampleDataResp}    "成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/internal/af-sailor-service/v1/tools/large_language_model/sample_data [POST]
func (s *Service) SampleData(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.SampleDataReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.TableSampleData(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}
	ginx.ResOKJson(c, response.ResResult{
		Res: resp,
	})
}
