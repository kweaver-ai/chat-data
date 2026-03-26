package copilot

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jinzhu/copier"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/samber/lo"
)

const (
	BaseKey    = "xxx.cn/anyfabric/af-sailor-service/asset-search"
	ExpireTime = 5 * 60 * time.Second
)

type CacheLoader struct {
	query      *client.AssetSearch
	data       *db.Data
	baseKey    string
	expireTime time.Duration
}

func (u *useCase) NewCacheLoader(req *client.AssetSearch) *CacheLoader {
	query := &client.AssetSearch{}
	_ = copier.Copy(&query, &req)
	return &CacheLoader{
		query:      query,
		data:       u.data,
		baseKey:    BaseKey,
		expireTime: ExpireTime,
	}
}

// Key 缓存的key， 输入+停用词+停用实体+过滤，md5
func (c *CacheLoader) Key() string {
	c.query.Limit = 0
	c.query.LastScore = 0
	c.query.LastId = ""
	return c.baseKey + "/" + util.MD5(lo.T2(json.Marshal(*c.query)).A)
}

func (c *CacheLoader) Store(ctx context.Context, data client.AssetSearchData) error {
	key := c.Key()
	content := string(lo.T2(json.Marshal(data)).A)
	return c.data.RedisCli.Set(ctx, key, content, c.expireTime).Err()
}

func (c *CacheLoader) Load(ctx context.Context) (data *client.AssetSearchData, err error) {
	result := c.data.RedisCli.Get(ctx, c.Key())
	if result.Err() != nil {
		return nil, result.Err()
	}
	content := ""
	if err := result.Scan(&content); err != nil {
		return nil, err
	}
	if err = json.Unmarshal([]byte(content), &data); err != nil {
		return nil, err
	}
	return
}

func (c *CacheLoader) Has(ctx context.Context) bool {
	return c.data.RedisCli.Exists(ctx, c.Key()).Val() > 0
}
