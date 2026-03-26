package impl

import (
	"context"
	"fmt"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/tools"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

type DataTool interface {
	Search(ctx context.Context, p comprehension.Process, data comprehension.MiddleData) (comprehension.MiddleData, error)
}

type Brain struct {
	tools   map[string]DataTool
	OpenAPI tools.OpenAPISource
}

func NewBrain(
	adSource tools.AnyDataSearch,
	openapiSource tools.OpenAPISource,
	engineSource tools.EngineSource) *Brain {
	return &Brain{
		OpenAPI: openapiSource,
		tools: map[string]DataTool{
			OpenAPIProcess: openapiSource,
			ADProcess:      adSource,
			EngineProcess:  engineSource,
			LogicTools:     tools.NewLogicHelper(),
		},
	}
}

type BigBrain struct {
	tools          map[string]DataTool
	OpenAPI        tools.OpenAPISource
	MiddleDataPool []comprehension.MiddleData
	CachedDataPool map[string]comprehension.MiddleData
}

func (b *Brain) Clone() *BigBrain {
	return &BigBrain{
		MiddleDataPool: make([]comprehension.MiddleData, 0),
		CachedDataPool: make(map[string]comprehension.MiddleData),
		tools:          b.tools,
		OpenAPI:        b.OpenAPI,
	}
}

func (b *BigBrain) Loop(ctx context.Context, think *comprehension.Thinking, data comprehension.MiddleData) (err error) {
	ds, err := think.LoopData(think.MiddleData(data, b.UpToDate()))
	if err != nil {
		log.WithContext(ctx).Errorf("获取循环数据错误：%v", err)
		return err
	}
	hasRight := false

	key := think.LoopKey()
	log.WithContext(ctx).Info("循环数据", zap.Any("ds", ds))
	for _, d := range ds {
		log.WithContext(ctx).Info("单次循环数据", zap.String("loop_name", think.Process.Desc), zap.Any("d", d))
		newData := think.MiddleData(data)
		newData.Set(key, d)
		if err := b.Flow(ctx, think, newData); err != nil && think.BreakThrough {
			log.WithContext(ctx).Info("循环终止", zap.String("loop_name", think.Process.Desc), zap.Error(err), zap.Any("data", d))
			continue
		}
		hasRight = true
		if len(think.Child) > 0 {
			if err := b.Flows(ctx, think.Child, newData); err != nil {
				log.WithContext(ctx).Info("循环错误", zap.Error(err), zap.Any("data", d))
			}
		}
		b.Append(think, newData)
	}
	if !hasRight && think.BreakThrough {
		return fmt.Errorf("%s, empty results ", think.Process.Desc)
	}
	return nil
}

func (b *BigBrain) Flows(ctx context.Context, ts []*comprehension.Thinking, data comprehension.MiddleData) (err error) {
	for _, think := range ts {
		log.WithContext(ctx).Info(think.Process.Desc)
		//检查是否满足执行条件
		if !CheckCondition(think.Condition, think.ParentError) {
			continue
		}
		//将所有数据作为一个参数
		if !think.IsLoop() {
			if err := b.Flow(ctx, think, data); err != nil {
				log.WithContext(ctx).Info("no search results", zap.Error(err))
				if think.BreakThrough {
					return err
				}
			}
			if len(think.Child) > 0 {
				err = b.Flows(ctx, think.Child, data)
			}
		}
		//循环将所有数据slice，一条条执行下去
		if think.IsLoop() {
			if err := b.Loop(ctx, think, data); err != nil {
				log.WithContext(ctx).Info(err.Error())
				if think.BreakThrough {
					return err
				} else {
					continue
				}
			}
		}
		//收集结果
		b.Append(think, data)
	}
	return nil
}

func (b *BigBrain) Flow(ctx context.Context, t *comprehension.Thinking, data comprehension.MiddleData) error {
	tool, ok := b.tools[t.Process.Way]
	if !ok {
		return fmt.Errorf("no this kind search tool, '%v'", t.Process.Way)
	}
	t.Process.Inputs = t.Inputs
	middleData, err := tool.Search(ctx, t.Process, data)
	if middleData.IsEmpty() {
		err = fmt.Errorf("no search result")
	}
	if err != nil {
		log.WithContext(ctx).Info("no search result", zap.Error(err))
	}
	if len(t.Child) > 0 {
		var parentError error
		if middleData.IsEmpty() {
			parentError = fmt.Errorf("no search result")
		}
		for _, child := range t.Child {
			child.ParentError = parentError
		}
	}
	if t.CacheKey != "" {
		if t.Process.Way != OpenAPIProcess {
			b.Cache(middleData, t.CacheKey)
		}
		if t.Process.Way == OpenAPIProcess {
			b.FixMiddleData(middleData, t.CacheKey)
		}
	}
	data.Merge(middleData, strings.Split(t.Parent.CacheKey, ",")...)
	return err
}

func (b *BigBrain) Empty() {
	b.MiddleDataPool = make([]comprehension.MiddleData, 0)
}

func (b *BigBrain) UpToDate() comprehension.MiddleData {
	ll := len(b.MiddleDataPool)
	if ll <= 0 {
		return comprehension.NewMiddleData()
	}
	return b.MiddleDataPool[len(b.MiddleDataPool)-1]
}

func (b *BigBrain) Append(t *comprehension.Thinking, d comprehension.MiddleData) {
	if !t.LastThinking {
		return
	}
	b.MiddleDataPool = append(b.MiddleDataPool, d)
}

func (b *BigBrain) Result(resultKey string) any {
	result := comprehension.MiddleData(make(map[string]any))
	if len(b.MiddleDataPool) <= 0 {
		return []string{}
	}
	for _, d := range b.MiddleDataPool {
		value := d.GetWithResultKey(resultKey)
		if value == nil {
			continue
		}
		if len(result) <= 0 {
			result[resultKey] = value
			continue
		}
		result.Merge(map[string]any{
			resultKey: value,
		})
	}
	return result.Get(resultKey)
}

// Cache 缓存数据
func (b *BigBrain) Cache(data comprehension.MiddleData, cacheKeys string) {
	for _, d := range data {
		ds, err := util.Transfer[[]comprehension.MiddleData](d)
		if err == nil {
			b.cache(*ds, cacheKeys)
			return
		}
		singleData, err := util.Transfer[comprehension.MiddleData](d)
		if err == nil {
			b.cache([]comprehension.MiddleData{*singleData}, cacheKeys)
			return
		}
	}
}

// Cache 缓存数据
func (b *BigBrain) cache(ds []comprehension.MiddleData, cacheKeys string) {
	keys := strings.Split(cacheKeys, ",")
	cacheKey, key, dataKey := keys[0], keys[1], keys[2]

	cache, ok := b.CachedDataPool[dataKey]
	if !ok {
		cache = make(map[string]any, 0)
	}
	for _, d := range ds {
		cv, cok := d[cacheKey]
		kv, kok := d[key]
		if cok && kok {
			cache[fmt.Sprintf("%v", kv)] = cv
		}
	}
	b.CachedDataPool[dataKey] = cache
}

func (b *BigBrain) fix(data comprehension.MiddleData, cacheKeys string) bool {
	keys := strings.Split(cacheKeys, ",")
	cacheKey, key, dataKey := keys[0], keys[1], keys[2]

	cache, ok := b.CachedDataPool[dataKey]
	if !ok {
		return false
	}
	kv := data.Get(key)
	if kv != nil {
		d := cache.Get(fmt.Sprintf("%v", kv))
		if d == nil {
			return false
		}
		data[cacheKey] = fmt.Sprintf("%v", d)
	}
	return true
}

func (b *BigBrain) fixMiddleData(data comprehension.MiddleData, cacheKeys string) bool {
	keys := strings.Split(cacheKeys, ",")
	dataKey := keys[2]

	fixValue, ok := data[dataKey]
	if !ok {
		return false
	}
	ds, err := util.Transfer[[]comprehension.MiddleData](fixValue)
	if err == nil {
		nds := make([]comprehension.MiddleData, 0)
		for _, di := range *ds {
			if b.fix(di, cacheKeys) {
				nds = append(nds, di)
			}
		}
		if len(nds) > 0 {
			data[dataKey] = nds
			return true
		}
	}
	singleData, err := util.Transfer[comprehension.MiddleData](fixValue)
	if err == nil {
		data[dataKey] = *singleData
		return b.fix(*singleData, cacheKeys)
	}
	return false
}

// FixMiddleData 通过缓存数据中的name，补充返回数据中缺失的ID
func (b *BigBrain) FixMiddleData(data comprehension.MiddleData, cacheKeys string) {
	keys := strings.Split(cacheKeys, ",")
	dataKey := keys[2]

	for resultKey, d := range data {
		ds, err := util.Transfer[[]comprehension.MiddleData](d)
		if err == nil {
			nds := make([]comprehension.MiddleData, 0)
			for _, di := range *ds {
				if dataKey == resultKey {
					if b.fix(di, cacheKeys) {
						nds = append(nds, di)
					} else {
						log.Warn("fix value error", zap.String("fixKeys", cacheKeys), zap.Any("fixData", di))
					}
				} else {
					if b.fixMiddleData(di, cacheKeys) {
						nds = append(nds, di)
					} else {
						log.Warn("fix value error", zap.String("fixKeys", cacheKeys), zap.Any("fixData", di))
					}
				}
				data[resultKey] = nds
			}
			return
		}
		singleData, err := util.Transfer[comprehension.MiddleData](d)
		if err == nil {
			if dataKey == resultKey {
				if !b.fix(*singleData, cacheKeys) {
					log.Warn("fix value error", zap.String("fixKeys", cacheKeys), zap.Any("fixData", *singleData))
				}
			} else {
				if !b.fixMiddleData(*singleData, cacheKeys) {
					log.Warn("fix value error", zap.String("fixKeys", cacheKeys), zap.Any("fixData", *singleData))
				}
			}
			data[resultKey] = *singleData
			return
		}
	}
	return
}

func CheckCondition(condition string, err error) bool {
	return (condition == "") || (condition == "parent.success" && err == nil) ||
		(condition == "parent.fail" && err != nil)
}
