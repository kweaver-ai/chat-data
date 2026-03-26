package comprehension

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

type ThinkingConfig struct {
	Tag           string      `json:"tag"`            //标签，思考的是那件事情
	ResultKey     string      `json:"result_key"`     //最终结果的key
	CacheKey      string      `json:"cache_key"`      //需要缓存处理的key,  值：id,name,column_infos 表示隐藏ID，使用name去缓存补充column_infos中的ID
	CacheThinking string      `json:"cache_thinking"` //需要缓存的配置节点，逗号分割符
	Thinking      []*Thinking `json:"thinking"`       //思考配置和过程
}

type Thinking struct {
	Parent         *ThinkingConfig `json:"-"`
	Condition      string          `json:"condition"`       //执行该节点的条件
	Inputs         []string        `json:"inputs"`          //输入的数据
	Process        Process         `json:"process"`         //当前节点的思考
	BreakThrough   bool            `json:"break_through"`   //遇到错误，处理为空是否继续，默认不继续
	ParentError    error           `json:"-"`               //父节点的执行状态
	LastThinking   bool            `json:"-"`               //最后的执行节点
	UseLastResult  bool            `json:"-"`               //是否使用了最近一次结果的值
	LoopDataKey    string          `json:"loop_data_key"`   //循环key
	FilterPrevious string          `json:"filter_previous"` //过滤掉的前序指
	CacheKey       string          `json:"-"`               //需要缓存处理的key,  值：id,name,column_infos 表示隐藏ID，使用name去缓存补充column_infos中的ID
	Child          []*Thinking     `json:"child"`           //思路分叉，执行每个分叉是由条件的
}

type Process struct {
	Desc   string   `json:"desc"`   //流程配置名称
	Inputs []string `json:"-"`      //输入的数据
	Config any      `json:"config"` //查询配置
	Format string   `json:"format"` //答案格式
	Way    string   `json:"way"`    //查询方式
}

type OpenapiConfig struct {
	MaxTokenSize   int    `json:"max_token_size"` //单个问题最大长度
	MaxSizeField   string `json:"-"`              //最大尺寸的字段
	MaxFieldSize   int    `json:"-"`              //最大尺寸字段的长度
	QuestionSize   int    `json:"-"`
	Question       string `json:"question"`        //问题字符串
	OmitemptyField string `json:"omitempty_field"` //忽略的字段，逗号分隔
}

func (o OpenapiConfig) SplitSize() int {
	questionWithoutMaxFieldSize := o.QuestionSize - o.MaxFieldSize
	maxFieldInsertSize := o.MaxTokenSize - questionWithoutMaxFieldSize
	return int(o.MaxFieldSize/maxFieldInsertSize) + 1
}

// AnydataConfig AD 查询配置
type AnydataConfig struct {
	SQL       string `json:"sql"`        //AD查询语句
	ServiceID string `json:"service_id"` //邻居查询的查询服务ID
}

// LogicHelperConfig   逻辑帮助函数
type LogicHelperConfig struct {
	FuncStr string `json:"func_str"`
}

// VirtualEngineConfig   虚拟化引擎查询结构
type VirtualEngineConfig struct {
	SQL string `json:"sql"`
}

func (p *Process) FormatKey() string {
	middleData := new(MiddleData)
	if err := json.Unmarshal([]byte(p.Format), middleData); err != nil {
		log.Error("invalid result key", zap.String("format", p.Format))
		return ""
	}
	key := ""
	for k := range *middleData {
		key = k
		break
	}
	return key
}

func (p *Process) IsSlice() bool {
	middleData := new(MiddleData)
	_ = json.Unmarshal([]byte(p.Format), middleData)
	var value any
	for _, value = range *middleData {
		break
	}
	_, err := util.Transfer[[]any](value)
	return err == nil
}

// MiddleData   返回需要的middleData, ds[0]是需要clone的，ds[1]是最新的
func (t *Thinking) MiddleData(ds ...MiddleData) MiddleData {
	if t.UseLastResult && len(ds) >= 2 {
		if len(ds[1]) > 0 {
			return ds[1]
		}
		return ds[0]
	}
	if t.HasChildren() {
		return ds[0].Clone()
	}
	return ds[0]
}

func (t *Thinking) Update(config ThinkingConfig) {
	if key := t.Process.FormatKey(); key == "" {
		log.Panic("invalid format", zap.Any("thinking", t))
	}
	resultKey := config.ResultKey
	t.Parent = &config
	t.LastThinking = t.IsLastThinking(resultKey)
	if strings.Contains(config.CacheThinking, t.Process.Desc) {
		t.CacheKey = config.CacheKey
	}
	for _, think := range t.Child {
		think.Update(config)
	}
}

func (t *Thinking) IsLoop() bool {
	return t.LoopDataKey != ""
}

func (t *Thinking) HasChildren() bool {
	return len(t.Child) > 0
}

func (t *Thinking) IsLastThinking(lastKey string) bool {
	return strings.Contains(lastKey, t.Process.FormatKey())
}

func (t *Thinking) LoopKey() string {
	tag := strings.Trim(t.LoopDataKey, "${}")
	ts := strings.Split(tag, ".")
	if len(ts) == 1 {
		return strings.TrimRight(ts[0], "_slice")
	}
	return strings.TrimRight(ts[1], "_slice")
}

func (t *Thinking) LoopData(data MiddleData) ([]MiddleData, error) {
	_, ds, err1 := GetMiddleDataValue[[]MiddleData](data, t.LoopDataKey)
	if err1 != nil {
		log.Error(err1.Error())
		return nil, err1
	}
	idKey, dsMap := FilterMap(data, t.FilterPrevious)
	//过滤掉不符合条件的
	results := make([]MiddleData, 0, len(*ds))
	for _, d := range *ds {
		if _, ok := dsMap[d.ValueAsKey(idKey)]; ok {
			continue
		}
		results = append(results, d)
	}
	return results, nil
}

func (t *Thinking) Append(ts ...*Thinking) *Thinking {
	t.Child = append(t.Child, ts...)
	return t
}

func FilterMap(data MiddleData, key string) (string, map[string]MiddleData) {
	key = strings.Trim(key, "${}")
	keys := strings.Split(key, ".")
	dsMap := make(map[string]MiddleData)
	if len(keys) != 2 {
		return "", dsMap
	}
	_, dsExcept, err2 := GetMiddleDataValue[[]MiddleData](data, keys[0])
	if err2 == nil {
		for _, d := range *dsExcept {
			if _, ok := d[keys[1]]; !ok {
				continue
			}
			k := d[keys[1]]
			dsMap[fmt.Sprintf("%v", k)] = d
		}
	}
	return keys[1], dsMap
}
