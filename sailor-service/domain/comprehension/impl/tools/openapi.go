package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"

	"go.uber.org/zap"
)

type OpenAPISource struct {
	Client large_language_model.OpenAI
}

func NewOpenAPISource(c large_language_model.OpenAI) OpenAPISource {
	return OpenAPISource{
		Client: c,
	}
}
func (o OpenAPISource) split(config *comprehension.OpenapiConfig, data comprehension.MiddleData, tags []string) ([]string, error) {
	question := config.Question
	if len(tags) <= 0 {
		reg, _ := regexp.Compile("\\${[\\w|\\.]+}")
		tags = reg.FindAllString(question, -1)
	}
	for _, tag := range tags {
		if tag == config.MaxSizeField {
			continue
		}
		key, value := data.OmitFieldValue(tag, config.OmitemptyField)
		question = strings.Replace(question, fmt.Sprintf("${%v}", key), strValue(value), -1)
	}
	//处理需要循环的字段
	key, value := data.OmitFieldValue(config.MaxSizeField, config.OmitemptyField)
	datas, err := util.Transfer[[]any](value)
	if err != nil {
		return nil, fmt.Errorf("invalid max size field %v", config.MaxSizeField)
	}
	questions := make([]string, 0)
	splitNumber := config.SplitSize()
	partNumber := len(*datas) / splitNumber
	for k := 0; k < len(*datas); {
		start := k
		end := start + partNumber
		k = end
		if end > len(*datas) {
			end = len(*datas) - 1
		}
		questions = append(questions, strings.Replace(question, fmt.Sprintf("${%v}", key), strValue((*datas)[start:end]), -1))
	}
	return questions, nil
}

func (o OpenAPISource) MultiPromote(config *comprehension.OpenapiConfig, data comprehension.MiddleData, tags []string) ([]string, error) {
	question := config.Question
	if len(tags) <= 0 {
		reg, _ := regexp.Compile("\\${[\\w|\\.]+}")
		tags = reg.FindAllString(question, -1)
	}

	for _, tag := range tags {
		ts := strings.Split(tag, "|")
		key, value := data.OmitFieldValue(ts[0], config.OmitemptyField)
		bytes := strValue(value)
		if len(bytes) > config.MaxTokenSize {
			config.MaxFieldSize = len(bytes)
			config.MaxSizeField = tag
		}
		if len(ts) > 1 && ts[1] != "" {
			key = strings.TrimSpace(ts[1])
		}
		question = strings.Replace(question, fmt.Sprintf("${%v}", key), strValue(value), -1)
	}
	//如果问题的最大尺寸超出限制，那就将问题切分
	if config.MaxTokenSize > 0 && config.MaxSizeField != "" && len(question) > config.MaxTokenSize {
		return o.split(config, data, tags)
	}
	return []string{question}, nil
}

func (o OpenAPISource) SinglePromote(config comprehension.OpenapiConfig, data comprehension.MiddleData, tags []string) (string, error) {
	question := config.Question
	if len(tags) <= 0 {
		reg, _ := regexp.Compile("\\${[\\w|\\.]+}")
		tags = reg.FindAllString(question, -1)
	}

	for _, tag := range tags {
		key, value := data.OmitFieldValue(tag, config.OmitemptyField)
		question = strings.Replace(question, fmt.Sprintf("${%v}", key), strValue(value), -1)
	}
	return question, nil
}

func (o OpenAPISource) format(answer string, format string) (comprehension.MiddleData, error) {
	log.Infof("openapi result %v", answer)
	first := strings.Index(answer, "{")
	last := strings.LastIndex(answer, "}")
	if first < 0 || last < 0 {
		return nil, fmt.Errorf("empty or invalid answer")
	}
	answer = answer[first : last+1]
	if answer == format {
		return nil, fmt.Errorf("empty or invalid answer")
	}
	result := new(comprehension.MiddleData)
	if err := json.Unmarshal([]byte(answer), result); err != nil {
		return nil, err
	}
	if result.IsEmpty() {
		return nil, fmt.Errorf("empty openapi answer")
	}
	resultFormat := comprehension.NewMiddleData()
	if err := json.Unmarshal([]byte(format), &resultFormat); err != nil {
		return nil, err
	}
	if err := util.CopyStruct(*result, resultFormat); err != nil {
		return nil, err
	}
	log.Infof("openapi format result %v", answer)
	return resultFormat, nil
}

func (o OpenAPISource) Concepts(ctx context.Context, concept string) error {
	result, err := o.Client.ChatGPT35(ctx, concept)
	log.WithContext(ctx).Info("openapi result", zap.Any("concept", result))
	return err
}

func (o OpenAPISource) SearchQ(ctx context.Context, q string) (string, error) {

	// q := `请严格按照json报文格式回复：判断那个字段最能表示表的时间范围？ 表名称为罚款通知书，包含以下字段：
	// 主键编号，备注，创建人，创建时间，附件，缴费金额，缴费时间，模板编号	` +
	// 	` 答案格式为:{"column_name":"表字段名称","reason":"理由"}`
	fmt.Println(q)
	promotes := []string{q}
	var answers string

	for _, promote := range promotes {
		answer, _ := o.Client.ChatGPT35(ctx, promote)

		answers = answers + answer
	}
	return answers, nil
}

// Search 大模型回答问题
func (o OpenAPISource) Search(ctx context.Context, p comprehension.Process, middleData comprehension.MiddleData) (comprehension.MiddleData, error) {
	promoteConfig, err := util.Transfer[comprehension.OpenapiConfig](p.Config)
	if err != nil {
		return nil, err
	}

	//结果格式检查
	if strings.Contains(promoteConfig.Question, "${format}") {
		promoteConfig.Question = strings.Replace(promoteConfig.Question, "${format}", p.Format, -1)
	}
	promotes, err := o.MultiPromote(promoteConfig, middleData, p.Inputs)
	if err != nil {
		return nil, err
	}
	log.WithContext(ctx).Info("openapi search promote", zap.Any("promotes", promotes))

	if len(promotes) == 0 {
		return nil, fmt.Errorf("empty prompts")
	}

	var answers *comprehension.MiddleData
	for _, promote := range promotes {
		answer, err := o.Client.ChatGPT35(ctx, promote)
		if err != nil {
			return nil, err
		}
		if answer == "" {
			return nil, fmt.Errorf("openapi no answer")
		}
		if strings.Contains(answer, "${") {
			return nil, fmt.Errorf("openapi answer error")
		}
		obj, err := o.format(answer, p.Format)
		if err != nil {
			log.WithContext(ctx).Infof("format %v result error %v", answer, err)
		}
		if answers == nil {
			answers = &obj
		} else {
			answers.Merge(obj)
		}
	}
	return *answers, nil
}

func strValue(value any) string {
	bytes, _ := json.Marshal(value)
	valueStr := string(bytes)
	if valueStr == "null" {
		return "[]"
	}
	return valueStr
}
