package copilot_helper

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"

	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
)

type PromptResponse struct {
	Res struct {
		Response string `json:"response"`
	} `json:"res"`
}

type CpRecommendCodeResponse struct {
	Res struct {
		Answers struct {
			TableName   string `json:"table_name"`
			TableFields []struct {
				TableFieldName string `json:"table_field_name"`
				RecStds        []struct {
					StdChName string  `json:"std_ch_name"`
					StdCode   string  `json:"std_code"`
					Score     float64 `json:"score"`
				} `json:"rec_stds"`
			} `json:"table_fields"`
		} `json:"answers"`
	} `json:"res"`
}

type CpRecommendTableResponse struct {
	Res struct {
		Answers struct {
			Tables []struct {
				ID       string  `json:"id"`
				HitScore float64 `json:"hit_score"`
				Reason   string  `json:"reason"`
			} `json:"tables"`
		} `json:"answers"`
	} `json:"res"`
}

type CpRecommendFlowResponse struct {
	Res struct {
		Answers struct {
			Flowcharts []struct {
				Id       string  `json:"id"`
				HitScore float64 `json:"hit_score"`
				Reason   string  `json:"reason"`
			} `json:"flowcharts"`
		} `json:"answers"`
	} `json:"res"`
}

type CpRecommendCheckCodeResponse struct {
	Res struct {
		Answers []struct {
			TableId           string `json:"table_id"`
			FieldsCheckResult []struct {
				FieldId    string `json:"field_id"`
				StandardId string `json:"standard_id"`
				Consistent []struct {
					TableId string `json:"table_id"`
					FieldId string `json:"field_id"`
				} `json:"consistent"`
				Inconsistent []struct {
					StandardId string `json:"standard_id"`
					Fields     []struct {
						TableId string `json:"table_id"`
						FieldId string `json:"field_id"`
					} `json:"fields"`
				} `json:"inconsistent"`
			} `json:"fields_check_result"`
		} `json:"answers"`
	} `json:"res"`
}

type RecommendSubjectModelResponse struct {
	Data []struct {
		ID             string `json:"id"`
		BusinessName   string `json:"business_name"`
		DataViewID     string `json:"data_view_id"`
		DisplayFieldID string `json:"display_field_id"`
		TechnicalName  string `json:"technical_name"`
	} `json:"data"`
}

type CpRecommendViewResponse struct {
	Res struct {
		Answers struct {
			Views []struct {
				Id       string  `json:"id"`
				HitScore float64 `json:"hit_score"`
				Reason   string  `json:"reason"`
			} `json:"views"`
		} `json:"answers"`
	} `json:"res"`
}

type CpRecommendAssetSearchResponse struct {
	Res struct {
		Count    int `json:"count"`
		Entities []struct {
			Starts []struct {
				Relation  string `json:"relation"`
				ClassName string `json:"class_name"`
				Name      string `json:"name"`
				Hit       struct {
					Prop  string   `json:"prop"`
					Value string   `json:"value"`
					Keys  []string `json:"keys"`
				} `json:"hit"`
				Alias string `json:"alias"`
			} `json:"starts"`
			Entity struct {
				Id              string `json:"id"`
				Alias           string `json:"alias"`
				Color           string `json:"color"`
				ClassName       string `json:"class_name"`
				Icon            string `json:"icon"`
				DefaultProperty struct {
					Name  string `json:"name"`
					Value string `json:"value"`
					Alias string `json:"alias"`
				} `json:"default_property"`

				Tags       []string `json:"tags"`
				Properties []struct {
					Tag   string `json:"tag"`
					Props []struct {
						Name     string `json:"name"`
						Value    string `json:"value"`
						Alias    string `json:"alias"`
						Type     string `json:"type"`
						Disabled bool   `json:"disabled"`
						Checked  bool   `json:"checked"`
					} `json:"props"`
				} `json:"properties"`
				Score float64 `json:"score"`
			} `json:"entity"`
			Score         float64 `json:"score"`
			IsPermissions string  `json:"is_permissions"`
		} `json:"entities"`

		Answer    string `json:"answer"`
		Subgraphs []struct {
			Starts []string `json:"starts"`
			End    string   `json:"end"`
		} `json:"subgraphs"`
		QueryCuts []struct {
			Source     string   `json:"source"`
			Synonym    []string `json:"synonym"`
			IsStopword bool     `json:"is_stopword"`
		} `json:"query_cuts"`
	} `json:"res"`
}

// testEngine   自定义认知服务，表单推荐等接口
func (a *ad) PromptEngine(ctx context.Context, content any) (*PromptResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/text2sql"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[PromptResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendCodeEngine(ctx context.Context, content any) (*CpRecommendCodeResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/recommend/code"
	//uri := "http://10.4.117.180:9798/api/copilot/v1/recommend/code"
	//fmt.Print(a.baseCUrl, "baseurl")
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendCodeResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendTableEngine(ctx context.Context, content any) (*CpRecommendTableResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/recommend/table"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendTableResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendFlowEngine(ctx context.Context, content any) (*CpRecommendFlowResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/recommend/flow"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendFlowResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendCheckCodeEngine(ctx context.Context, content any) (*CpRecommendCheckCodeResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/recommend/check/code"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendCheckCodeResponse](ctx, uri, content, headers, a)
}

// SearchEngine   主题模型推荐
func (a *ad) RecommendSubjectModelEngine(ctx context.Context, content any) (*RecommendSubjectModelResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/internal/recommend/subject_model"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[RecommendSubjectModelResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，view推荐等接口
func (a *ad) CpRecommendViewEngine(ctx context.Context, content any) (*CpRecommendViewResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/recommend/view"
	// uri := "http://10.4.117.180:9798/api/copilot/v1/text2sql"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendViewResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendAssetSearchEngine(ctx context.Context, content any) (*CpRecommendAssetSearchResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/asset_search"
	//uri := "http://127.0.0.1:9797/api/copilot/v1/search/cognitive_search/asset_search"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	return httpPostDoP[CpRecommendAssetSearchResponse](ctx, uri, content, headers, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpRecommendAssetSearchEngineV2(ctx context.Context, vType string, content any, searchType string) (*CpRecommendAssetSearchResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/resource_search"
	if vType == constant.DataCatalogVersion {
		uri = a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/catalog_search"

	}

	//uri := "http://127.0.0.1:9797/api/copilot/v1/search/cognitive_search/asset_search"
	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[CpRecommendAssetSearchResponse](ctx, uri, content, headers, a)
}

func (a *ad) CpRecommendAssetSearchEngineV3(ctx context.Context, content any) (*CpRecommendAssetSearchResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/formview_search_catalog"

	headers := make(map[string][]string)
	headers["source-type"] = []string{"2"}
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[CpRecommendAssetSearchResponse](ctx, uri, content, headers, a)
}

//// SearchEngine   自定义认知服务，表单推荐等接口
//func (a *ad) SailorCognitiveDataCatalogSearchNew(ctx context.Context, content any) (*CpRecommendAssetSearchResponse, error) {
//	uri := a.baseCUrl + "/api/af-sailor//v1/search/cognitive_search/formview_search_catalog"
//
//	headers := make(map[string][]string)
//	headers["source-type"] = []string{"2"}
//	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
//	return httpPostDoP[CpRecommendAssetSearchResponse](ctx, uri, content, headers, a)
//}

type CpTestLLMReq struct {
	Appid string `json:"appid"` // appid
}

type CpTestLLMResp struct {
	Res bool `json:"res"` // appid
}

type CpText2SqlResp struct {
	Res struct {
		Text  string `json:"text"`
		Table string `json:"table"`
	} `json:"res"` // appid
}

type SailorSessionResp struct {
	Res string `json:"res"`
}

func (a *ad) CpTestLLMEngine(ctx context.Context, req map[string]any) (*CpTestLLMResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseCUrl + "/api/af-sailor/v1/assistant/test-llm"
	u, err := url.Parse(rawURL)
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

	return httpGetDo[CpTestLLMResp](ctx, u, a)
}

// SearchEngine   自定义认知服务，表单推荐等接口
func (a *ad) CpText2SqlEngine(ctx context.Context, content any, authorization string) (*CpText2SqlResp, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/utils/text2sql"
	//uri := "http://127.0.0.1:9797/api/copilot/v1/search/cognitive_search/asset_search"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{authorization}
	return httpPostDoP[CpText2SqlResp](ctx, uri, content, headers, a)
}

type SailorLogicalViewDataCategorizeResp struct {
	Res struct {
		Answers struct {
			ViewId     string `json:"view_id"`
			ViewFields []struct {
				ViewFieldId string `json:"view_field_id"`
				RelSubjects []struct {
					SubjectId string `json:"subject_id"`
					Score     string `json:"score"`
				} `json:"rel_subjects"`
			} `json:"view_fields"`
		} `json:"answers"`
	} `json:"res"`
}

func (a *ad) SailorLogicalViewDataCategorizeEngine(ctx context.Context, content any) (*SailorLogicalViewDataCategorizeResp, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/data_categorize"
	//uri := "http://127.0.0.1:9797/api/copilot/v1/search/cognitive_search/asset_search"
	headers := make(map[string][]string)
	return httpPostDoP[SailorLogicalViewDataCategorizeResp](ctx, uri, content, headers, a)
}

type SailorCognitiveResourceAnalysisSearchResponse struct {
	Res struct {
		Count    int `json:"count"`
		Entities []struct {
			Starts []interface{} `json:"starts"`
			Entity struct {
				Id              string `json:"id"`
				Alias           string `json:"alias"`
				Color           string `json:"color"`
				ClassName       string `json:"class_name"`
				Icon            string `json:"icon"`
				DefaultProperty struct {
					Name  string `json:"name"`
					Value string `json:"value"`
					Alias string `json:"alias"`
				} `json:"default_property"`
				Tags       []string `json:"tags"`
				Properties []struct {
					Tag   string `json:"tag"`
					Props []struct {
						Name     string `json:"name"`
						Value    string `json:"value"`
						Alias    string `json:"alias"`
						Type     string `json:"type"`
						Disabled bool   `json:"disabled"`
						Checked  bool   `json:"checked"`
					} `json:"props"`
				} `json:"properties"`
				Score float64 `json:"score"`
			} `json:"entity"`
			IsPermissions string `json:"is_permissions"`
			Score         int    `json:"score"`
		} `json:"entities"`
		Answer              string        `json:"answer"`
		Subgraphs           []interface{} `json:"subgraphs"`
		QueryCuts           []interface{} `json:"query_cuts"`
		ExplanationFormView string        `json:"explanation_formview"`
	} `json:"res"`
	ResStatus         string `json:"res_status"`
	ExplanationStatus string `json:"explanation_status"`
}

func (a *ad) SailorCognitiveResourceAnalysisSearchEngine(ctx context.Context, content any) (*SailorCognitiveResourceAnalysisSearchResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/formview_analysis_search"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[SailorCognitiveResourceAnalysisSearchResponse](ctx, uri, content, headers, a)
}

type SailorCognitiveDataCatalogAnalysisSearchResponse struct {
	Res struct {
		Count    int `json:"count"`
		Entities []struct {
			Starts []interface{} `json:"starts"`
			Entity struct {
				Id              string `json:"id"`
				Alias           string `json:"alias"`
				Color           string `json:"color"`
				ClassName       string `json:"class_name"`
				Icon            string `json:"icon"`
				DefaultProperty struct {
					Name  string `json:"name"`
					Value string `json:"value"`
					Alias string `json:"alias"`
				} `json:"default_property"`
				Tags       []string `json:"tags"`
				Properties []struct {
					Tag   string `json:"tag"`
					Props []struct {
						Name     string `json:"name"`
						Value    string `json:"value"`
						Alias    string `json:"alias"`
						Type     string `json:"type"`
						Disabled bool   `json:"disabled"`
						Checked  bool   `json:"checked"`
					} `json:"props"`
				} `json:"properties"`
				Score float64 `json:"score"`
			} `json:"entity"`
			IsPermissions string `json:"is_permissions"`
			Score         int    `json:"score"`
		} `json:"entities"`
		Answer              string        `json:"answer"`
		Subgraphs           []interface{} `json:"subgraphs"`
		QueryCuts           []interface{} `json:"query_cuts"`
		ExplanationFormView string        `json:"explanation_formview"`
	} `json:"res"`
	ResStatus         string `json:"res_status"`
	ExplanationStatus string `json:"explanation_status"`
}

func (a *ad) SailorCognitiveDataCatalogAnalysisSearchEngine(ctx context.Context, content any) (*SailorCognitiveDataCatalogAnalysisSearchResponse, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/search/cognitive_search/formview_analysis_catalog"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[SailorCognitiveDataCatalogAnalysisSearchResponse](ctx, uri, content, headers, a)
}

func (a *ad) SailorGetSessionEngine(ctx context.Context, req map[string]any) (*SailorSessionResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseCUrl + "/api/af-sailor/v1/assistant/chat/get-session-id"
	u, err := url.Parse(rawURL)
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

	return httpGetDo[SailorSessionResp](ctx, u, a)
}

type SamplesItem struct {
	ColumnName  string      `json:"column_name"`
	ColumnValue interface{} `json:"column_value"`
}

type SamplesItemList [][]*SamplesItem

func (a *ad) SailorFormViewGenerateFakeSamples(ctx context.Context, content map[string]any) (*SamplesItemList, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/generate_fake_samples"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[SamplesItemList](ctx, uri, content, headers, a)
}

type SailorTableCompletionTableInfoResp struct {
	Res struct {
		TaskId string `json:"task_id"`
	} `json:"res"`
}

func (a *ad) SailorTableCompletionTableInfoEngine(ctx context.Context, req map[string]any) (*SailorTableCompletionTableInfoResp, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/understanding/table/completion/only"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[SailorTableCompletionTableInfoResp](ctx, uri, req, headers, a)
}

type SailorTableCompletionResp struct {
	Res struct {
		TaskId string `json:"task_id"`
	} `json:"res"`
}

func (a *ad) SailorTableCompletionEngine(ctx context.Context, req map[string]any) (*SailorTableCompletionResp, error) {
	uri := a.baseCUrl + "/api/af-sailor/v1/understanding/table/completion"
	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	return httpPostDoP[SailorTableCompletionResp](ctx, uri, req, headers, a)
}
