package v1

import (
	"context"
	"net/http"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/hydra"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/user_management"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models"

	af_trace "github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
)

type Middleware struct {
	hydra   hydra.Hydra
	userMgm user_management.DrivenUserMgnt
}

func NewMiddleware(
	hydra hydra.Hydra,
	userMgm user_management.DrivenUserMgnt,
) middleware.Middleware {
	return &Middleware{
		hydra:   hydra,
		userMgm: userMgm,
	}
}

func (m *Middleware) TokenInterception() gin.HandlerFunc {
	return func(c *gin.Context) {
		var err error
		newCtx, span := af_trace.StartInternalSpan(c.Request.Context())
		defer func() { af_trace.TelemetrySpanEnd(span, err) }()
		tokenID := c.GetHeader("Authorization")
		token := strings.TrimPrefix(tokenID, "Bearer ")
		if tokenID == "" || token == "" {
			ginx.AbortResponseWithCode(c, http.StatusUnauthorized, errorcode.Desc(errorcode.NotAuthentication))
			return
		}
		info, err := m.hydra.Introspect(newCtx, token)
		if err != nil {
			log.WithContext(c.Request.Context()).Error("TokenInterception Introspect", zap.Error(err))
			ginx.AbortResponseWithCode(c, http.StatusBadRequest, errorcode.Desc(errorcode.HydraException))
			return
		}
		if !info.Active {
			ginx.AbortResponseWithCode(c, http.StatusUnauthorized, errorcode.Desc(errorcode.AuthenticationFailure))
			return
		}

		// 保存 Bearer token 用于身份认证
		middleware.SetGinContextWithBearerToken(c, token)

		if info.VisitorID == info.ClientID || info.VisitorTyp == hydra.App {

			// 根据名称判断是不是虚拟化引擎的内部账号，如果是，后面不检查权限
			client_name, err := m.hydra.GetClientNameById(newCtx, info.VisitorID)
			if err != nil {
				log.WithContext(c.Request.Context()).Error("TokenInterception GetUserFromHydarWrong", zap.Error(err))
				ginx.AbortResponseWithCode(c, http.StatusBadRequest, errorcode.Desc(errorcode.HydraException))
				return
			}
			if client_name == middleware.VirtualEngineApp {
				c.Set(constant.Token, tokenID)
				c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), constant.Token, tokenID))
				c.Set(constant.TokenType, constant.TokenTypeClient)
				c.Next()
				return
			}

			var id, name string
			userInfoApp, err := m.userMgm.GetAppInfo(c, info.VisitorID)
			if err != nil {
				log.WithContext(c.Request.Context()).Error("TokenInterception userMgm GetAppInfo", zap.Error(err))
				ginx.AbortResponseWithCode(c, http.StatusBadRequest, errorcode.Desc(errorcode.GetProtonAppInfoFailure))
				return
			}
			id = userInfoApp.ID
			name = userInfoApp.Name
			//}

			userInfo := &models.UserInfo{ID: id, Name: name, UserType: constant.TokenTypeClient}
			// 保存访问者到 Context 用于鉴权
			c.Set(constant.InfoName, userInfo)
			c.Set(constant.Token, tokenID)
			c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), constant.InfoName, userInfo))
			c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), constant.Token, tokenID))
			c.Set(constant.TokenType, constant.TokenTypeClient)
			c.Next()
			return
		}
		name, _, depInfos, err := m.userMgm.GetUserNameByUserID(newCtx, info.VisitorID)
		if err != nil {
			log.WithContext(c.Request.Context()).Error("userMgm GetUserNameByUserID err", zap.Error(err))
			ginx.AbortResponseWithCode(c, http.StatusBadRequest, errorcode.Desc(errorcode.GetUserInfoFailure))
			return
		}
		userInfo := &models.UserInfo{ID: info.VisitorID, Name: name, OrgInfos: depInfos, UserType: constant.TokenTypeUser}
		c.Set(constant.InfoName, userInfo)
		c.Set(constant.Token, tokenID)
		c.Set(constant.TokenType, constant.TokenTypeUser)
		c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), constant.InfoName, userInfo))
		c.Request = c.Request.WithContext(context.WithValue(c.Request.Context(), constant.Token, tokenID))
		middleware.SetGinContextWithUser(c, &models.UserInfo{ID: userInfo.ID, Name: userInfo.Name, OrgInfos: userInfo.OrgInfos, UserType: userInfo.UserType})
		c.Next()
	}
}
