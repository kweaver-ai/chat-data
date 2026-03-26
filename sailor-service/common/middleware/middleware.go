package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
)

type Middleware interface {
	TokenInterception() gin.HandlerFunc
}

func InternalAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		userId := c.GetHeader("userId")
		userToken := c.GetHeader("userToken")
		c.Set(constant.UserId, userId)
		c.Set(constant.UserTokenKey, userToken)
		c.Next()
	}
}
