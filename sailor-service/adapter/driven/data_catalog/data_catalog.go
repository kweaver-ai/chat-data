package data_catalog

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/pkg/errors"
	"github.com/samber/lo"
)

//type DataCatalog interface {
//	GetUserResource(ctx context.Context, req map[string]any) (*UserResource, error)
//	GetUserResourceById(ctx context.Context, req []map[string]interface{}) (*PolicyEnforceRespItem, error)
//	GetUserResourceListByIds(ctx context.Context, req []map[string]interface{}) ([]*PolicyEnforceRespItem, error)
//}

type dataCatalog struct {
	baseUrl string

	httpClient *http.Client
	mtx        sync.Mutex
}

func NewDataCatalog(httpClient *http.Client) DataCatalog {
	cfg := settings.GetConfig().DepServicesConf
	cli := &http.Client{
		Transport: httpClient.Transport,
		Timeout:   5 * time.Minute,
	}
	return &dataCatalog{
		baseUrl:    cfg.DataCatalogHost,
		httpClient: cli,
	}
}

type DataCatalogFilter struct {
	Entries []struct {
		Id        string       `json:"id"`
		Name      string       `json:"name"`
		Describe  string       `json:"describe"`
		Using     bool         `json:"using"`
		Required  bool         `json:"required"`
		Type      string       `json:"type"`
		CreatedAt int64        `json:"created_at"`
		UpdatedAt int64        `json:"updated_at"`
		CreatedBy string       `json:"created_by"`
		UpdatedBy string       `json:"updated_by"`
		TreeNode  []FilterNode `json:"tree_node"`
	} `json:"entries"`
	TotalCount int `json:"total_count"`
}

type FilterNode struct {
	Id        string       `json:"id"`
	ParentId  string       `json:"parent_id"`
	Name      string       `json:"name"`
	Owner     string       `json:"owner"`
	OwnnerUid string       `json:"ownner_uid"`
	Children  []FilterNode `json:"children,omitempty"`
}

func (d *dataCatalog) GetCatalogFilter(ctx context.Context) (*DataCatalogFilter, error) {
	rawURL := d.baseUrl + "/api/data-catalog/v1/category"
	u, err := url.Parse(rawURL)
	req := map[string]any{}
	headers := make(map[string][]string)
	headers["Authorization"] = []string{ctx.Value(constant.Token).(string)}

	if err != nil {
		//log.WithContext(ctx).Errorf("failed to parse url: %s, err: %v", rawURL, err)
		return nil, errors.Wrap(err, "parse url failed")
	}

	var m map[string]string
	if err = json.Unmarshal(lo.T2(json.Marshal(req)).A, &m); err != nil {
		//log.WithContext(ctx).Errorf("json.Unmarshal(lo.T2(json.Marshal(req)).A, &m) failed, err: %v", err)
		return nil, errors.Wrap(err, `req param marshal json failed`)
	}

	values := url.Values{}
	for k, v := range m {
		values.Add(k, v)
	}

	u.RawQuery = values.Encode()
	return httpGetDo[DataCatalogFilter](ctx, u, d, headers)
}

func collectSpecificNodes(node FilterNode, targetIdList []string, nodesId *[]string, isAdd bool) {
	innerIsAdd := false
	if isAdd {
		*nodesId = append(*nodesId, node.Id)
		innerIsAdd = true
	} else {
		for _, nid := range targetIdList {
			if node.Id == nid {
				innerIsAdd = true
				break
			}
		}
		if innerIsAdd {
			*nodesId = append(*nodesId, node.Id)
		}
	}

	for _, child := range node.Children {
		collectSpecificNodes(child, targetIdList, nodesId, innerIsAdd)
	}
}

func (d *dataCatalog) GetCustomerIdList(inputCateTypeId string, inputCateNodeIdList []string, inputCatalogFilter DataCatalogFilter) ([]string, error) {
	res := []string{}
	for _, item := range inputCatalogFilter.Entries {
		if item.Type != "customize" {
			continue
		}

		if item.Id != inputCateTypeId {
			continue
		}
		for _, subItem := range item.TreeNode {
			collectSpecificNodes(subItem, inputCateNodeIdList, &res, false)
		}

	}

	return res, nil
}

type CatalogFavoriteItem struct {
	ResType string   `json:"res_type"`
	ResIds  []string `json:"res_ids"`
}

type CheckCatalogFavoriteReq struct {
	Resources []CatalogFavoriteItem `json:"resources"`
}

type CheckCatalogFavoriteResp []CheckCatalogFavoriteItem

type CheckCatalogFavoriteItem struct {
	ResType   string `json:"res_type"`
	Resources []struct {
		ResId     string `json:"res_id"`
		IsFavored bool   `json:"is_favored"`
	} `json:"resources"`
}

func (d *dataCatalog) CheckCatalogFavorite(ctx context.Context, inputCateIds []string) (*CheckCatalogFavoriteResp, error) {
	uri := d.baseUrl + "/api/data-catalog/frontend/v1/favorite/check"

	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	req := CheckCatalogFavoriteReq{}
	req.Resources = append(req.Resources, CatalogFavoriteItem{"data-catalog", inputCateIds})
	return httpPostDo[CheckCatalogFavoriteResp](ctx, uri, req, headers, d)
}

type CheckV1Resp struct {
	IsFavored bool   `json:"is_favored"`                // 是否已收藏
	FavorID   uint64 `json:"favor_id,string,omitempty"` // 收藏项ID，仅已收藏时返回该字段
}

type CheckV1Req struct {
	CreatedBy string `form:"created_by" json:"created_by"`
	ResType   string `form:"res_type" json:"res_type" binding:"TrimSpace,required,oneof=data-catalog info-catalog elec-licence-catalog data-view interface-svc indicator" example:"data-catalog"` // 收藏资源类型 data-catalog 数据资源目录 info-catalog 信息资源目录 elec-licence-catalog 电子证照目录
	ResID     string `form:"res_id" json:"res_id" binding:"TrimSpace,required,min=1,max=64" example:"544217704094017271"`                                                                         // 收藏资源ID
}

func (d *dataCatalog) GetResourceFavoriteByID(ctx context.Context, req *CheckV1Req) (*CheckV1Resp, error) {
	uri := d.baseUrl + "/api/internal/data-catalog/v1/data-catalog/favorite"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDo[CheckV1Resp](ctx, uri, req, headers, d)
}
