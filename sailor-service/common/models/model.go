package models

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
)

type DepInfo struct {
	OrgCode string `json:"org_code"`
	OrgName string `json:"org_name"`
}

type UserInfo struct {
	ID       string     `json:"id"`
	Name     string     `json:"name"`
	UserType int        `json:"user_type"`
	OrgInfos []*DepInfo `json:"org_info"`
}

func (u *UserInfo) GetUId() string {
	if u == nil {
		return ""
	}

	return u.ID
}

func GetUserInfo(ctx context.Context) *UserInfo {
	if val := ctx.Value(constant.UserInfoContextKey); val != nil {
		if ret, ok := val.(*UserInfo); ok {
			return ret
		}
	}
	return nil
}
