package middleware

import (
	"context"
	"errors"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models"
)

// contextKeyBearerToken 是从 context.Context 获取 BearerToken 的 key。
//
// 对于 HTTP Header "Authorization: Bearer ory_at_xxxx"，BearerToken 是其中的
// "ory_at_xxxx"
const contextKeyBearerToken = "GoCommon/interception.BearerToken"
const contextKeyUser = "GoCommon/interception.User"
const VirtualEngineApp = "af-virtual-engine-gateway"
const contextKeyAuth = "GoCommon/interception.Auth"

var (
	ErrNotExist       = errors.New("value does not exist")
	ErrUnexpectedType = errors.New("unexpected value type for context key")
)

// NewContextWithBearerToken 生成一个包含 BearerToken 的 context.Context
func NewContextWithBearerToken(parent context.Context, t string) context.Context {
	return context.WithValue(parent, contextKeyBearerToken, t)
}

// SetGinContextWithBearerToken 把 BearerToken 保存在 gin.Context
func SetGinContextWithBearerToken(c *gin.Context, t string) {
	c.Set(contextKeyBearerToken, t)
}

// BearerTokenFromContext 从 context.Context 获取 BearerToken，如果未找到或类型不符返回 error
func BearerTokenFromContext(ctx context.Context) (string, error) {
	v := ctx.Value(contextKeyBearerToken)
	if v == nil {
		return "", ErrNotExist
	}

	t, ok := v.(string)
	if !ok {
		return "", ErrUnexpectedType
	}

	return t, nil
}

func SetGinContextWithUser(c *gin.Context, u *models.UserInfo) {
	c.Set(contextKeyUser, u)
}

// AuthFromContextCompatible 从 context.Context 获取 BearerToken，如果未找到或类型不符返回 error
func AuthFromContextCompatible(ctx context.Context) (string, error) {
	return get(ctx, contextKeyAuth)
}

func get(ctx context.Context, key string) (string, error) {
	v := ctx.Value(key)
	if v == nil {
		if key != constant.Token { //兼容token处理
			return get(ctx, constant.Token)
		}
		return "", ErrNotExist
	}
	t, ok := v.(string)
	if !ok {
		return "", ErrUnexpectedType
	}

	return t, nil
}
