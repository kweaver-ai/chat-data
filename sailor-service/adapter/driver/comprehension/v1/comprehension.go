package v1

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/form_validator"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models/response"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

var _ response.NameIDResp

type Controller struct {
	dc comprehension.Domain
}

func NewController(dc comprehension.Domain) *Controller {
	return &Controller{dc: dc}
}

// DimensionConfigs 数据理解智能配置文件
// @Description 数据理解智能配置文件
// @Tags        数据理解
// @Summary     数据理解智能配置文件
// @Accept      plain
// @Produce     json
// @Success     200       {array} comprehension.ThinkingConfig    "成功响应参数"
// @Router      /api/af-sailor-service/v1/comprehension/config [get]
func (controller *Controller) DimensionConfigs(c *gin.Context) {
	ginx.ResOKJson(c, controller.dc.AIComprehensionConfig())
}

// SetAIConfig 设置数据理解的AD查询服务ID
// @Description 数据理解智能配置文件
// @Tags        数据理解
// @Summary     数据理解智能配置文件
// @Accept      plain
// @Produce     json
// @Success     200      {object} string    "成功响应参数"
// @Router      /api/af-sailor-service/v1/comprehension/config [put]
func (controller *Controller) SetAIConfig(c *gin.Context) {
	ginx.ResOKJson(c, response.NameIDResp2{ID: controller.dc.SetAIComprehensionConfig("")})
}

// AI 数据理解智能填充
// @Description 获取数据理解
// @Tags        数据理解
// @Summary     获取数据理解
// @Accept      plain
// @Produce     json
// @Param       Authorization header      string    true "token"
// @Param       catalogID     path        string    true "目录的ID"
// @Success     200       {object} string    "成功响应参数"
// @Failure     400       {object} rest.HttpError            "失败响应参数"
// @Router      /api/af-sailor-service/v1/comprehension [get]
func (controller *Controller) AI(c *gin.Context) {
	req := new(comprehension.ReqArgs)
	if _, err := form_validator.BindQueryAndValid(c, &req); err != nil {
		err = errorcode.Detail(errorcode.PublicInvalidParameter, err)
		c.Writer.WriteHeader(http.StatusBadRequest)
		ginx.ResErrJson(c, err)
		return
	}
	detail, err := controller.dc.AIComprehension(c, req.CatalogID, req.Dimension)

	if err != nil {
		c.Writer.WriteHeader(http.StatusBadRequest)
		ginx.ResErrJson(c, err)
		return
	}
	ginx.ResOKJson(c, detail)
}

// func (controller *Controller) Test(c *gin.Context) {
// 	//req := &comprehension.Q{}
// 	b, _ := c.GetRawData()
// 	query := string(b)
// 	// if _, err := form_validator.BindJsonAndValid(c, req); err != nil {
// 	// 	form_validator.ReqParamErrorHandle(c, err)
// 	// 	return
// 	// }
// 	detail, err := controller.dc.Test(c, query)
// 	if err != nil {
// 		c.Writer.WriteHeader(http.StatusBadRequest)
// 		ginx.ResErrJson(c, err)
// 		return
// 	}
// 	ginx.ResOKJson(c, detail)
// }
