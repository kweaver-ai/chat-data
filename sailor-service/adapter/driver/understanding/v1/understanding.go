package v1

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/understanding"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

type Controller struct {
	dc understanding.UseCase
}

func NewController(dc understanding.UseCase) *Controller {
	return &Controller{dc: dc}
}

func (s *Controller) errResp(c *gin.Context, err error) {
	c.Writer.WriteHeader(http.StatusBadRequest)
	ginx.ResErrJson(c, err)
}

func (s *Controller) TableCompletionTableInfo(c *gin.Context) {
	req, err := middleware.GetReqParam[understanding.TableCompletionTableInfoReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.dc.TableCompletionTableInfo(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Controller) TableCompletion(c *gin.Context) {
	req, err := middleware.GetReqParam[understanding.TableCompletionReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.dc.TableCompletion(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}
