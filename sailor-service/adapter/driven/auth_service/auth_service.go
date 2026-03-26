package auth_service

import (
	"time"

	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"

	"context"
	"net/http"
	"sync"
	//"time"
)

type AuthService interface {
	GetUserResource(ctx context.Context, req map[string]any) (*UserResource, error)
	GetUserResourceById(ctx context.Context, req []map[string]interface{}) (*PolicyEnforceRespItem, error)
	GetUserResourceListByIds(ctx context.Context, req []map[string]interface{}) ([]*PolicyEnforceRespItem, error)
}

type authService struct {
	baseUrl string

	httpClient *http.Client
	mtx        sync.Mutex
}

func NewAuthService(httpClient *http.Client) AuthService {
	cfg := settings.GetConfig().DepServicesConf
	cli := &http.Client{
		Transport: httpClient.Transport,
		Timeout:   5 * time.Minute,
	}
	return &authService{
		baseUrl:    cfg.AuthServiceHost,
		httpClient: cli,
	}
}

// 访问者拥有的资源
type UserResource struct {
	PageResult[Object]
}

type PageResult[T any] struct {
	Entries    []*T  `json:"entries" binding:"required"`                       // 对象列表
	TotalCount int64 `json:"total_count" binding:"required,gte=0" example:"3"` // 当前筛选条件下的对象数量
}

type Object struct {
	ObjectId    string        `json:"object_id"`   // 资源id
	ObjectType  string        `json:"object_type"` // 资源类型 domain 主题域 data_catalog 数据目录 data_view 数据表视图 api 接口
	Permissions []*Permission `json:"permissions"` // 权限。不需要判断哪种类型权限，只要出现在响应结果列表，一定有最基础的view权限
}

type Permission struct {
	Action string `json:"action"` // 请求动作 view 查看 read 读取 download 下载
	Effect string `json:"effect"` // 策略结果 allow 允许 deny 拒绝
}
