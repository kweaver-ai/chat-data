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

// AgentConversationLogList 智能助手问答会话日志列表
//
// @Param       Authorization header      string    true "token"
// @Param       offset       query    int   false "页码，从1开始，默认1"
// @Param       limit        query    int   false "每页数量，最大100，默认10"
// @Param       direction    query string false "排序方向：asc/desc，默认desc"
// @Param       sort         query string false "排序字段：create_time/update_time，默认create_time"
// @Param       start_time    query    int   false "开始时间（毫秒时间戳）"
// @Param       end_time      query    int   false "结束时间（毫秒时间戳）"
// @Param       department_id query  string false "部门ID（可选）"
// @Param       user_id       query  string false "用户ID（可选）"
// @Param       keyword       query string false "关键词模糊搜索（问题或答案内容）"
// @Success     200       {object} response.ResResult{Res=domain.AgentConversationLogListResp}    "成功响应参数"
// @Failure     400       {object} rest.HttpError   "失败响应参数"
// @Router      /api/internal/af-sailor-service/v1/tools/large_language_model/agent_log [GET]
func (s *Service) AgentConversationLogList(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.AgentConversationLogListReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.AgentConversationLogList(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, response.ResResult{
		Res: resp,
	})
}
