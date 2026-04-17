package configuration_center

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/user_management"
)

type DrivenConfigurationCenter interface {
	DataUseType(ctx context.Context) (*DataUserTypeRes, error)
	GetChildrenDepartment(ctx context.Context, departmentId string) (*DepartmentObjectsList, error)
	GetUserRoles(ctx context.Context) ([]*UserRoleItem, error)
	GetDepartmentsByUserID(ctx context.Context, userID string) ([]DepartmentPath, error)
}

type UserInfo = user_management.UserInfo

type DepartmentPath struct {
	ID   string
	Path string
}
