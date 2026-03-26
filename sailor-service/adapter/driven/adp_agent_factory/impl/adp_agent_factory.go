package impl

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/pkg/errors"

	"github.com/samber/lo"
	"go.uber.org/zap"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/adp_agent_factory"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/kweaver-ai/idrm-go-frame/core/utils/httpclient"
)

type repo struct {
	httpclient    httpclient.HTTPClient
	rawHttpClient *http.Client
}

func NewRepo(client httpclient.HTTPClient, rawHttpClient *http.Client) adp_agent_factory.Repo {
	return &repo{
		httpclient:    client,
		rawHttpClient: rawHttpClient,
	}
}

func (r *repo) AgentList(ctx context.Context, req adp_agent_factory.AgentListReq) (resp *adp_agent_factory.AgentListResp, err error) {

	ctx, span := trace.StartInternalSpan(ctx)
	defer span.End()

	log := log.WithContext(ctx)

	urlStr := fmt.Sprintf("%s/api/agent-factory/v3/published/agent", settings.GetConfig().DepServicesConf.ADPAgentFactoryHost)
	headers := map[string]string{
		"x-business-domain": "bd_public",
		"Content-Type":      "application/json",
		"Authorization":     ctx.Value(constant.Token).(string),
	}
	log.Infof("adp agent list req info: %s", lo.T2(json.Marshal(req)).A)
	code, response, err := r.httpclient.Post(ctx, urlStr, headers, req)
	if err != nil {
		log.Error("send request fail", zap.String("url", urlStr), zap.String("method", http.MethodPost), zap.Any("body", req))
		return nil, newErrorCode(err)
	}

	if code != http.StatusOK {
		log.Error("adp agent list return unsupported status code", zap.Int("statusCode", code), zap.Any("body", req))
		return nil, errorcode.Detail(errorcode.PublicInternalError, fmt.Sprintf("unsupported basic-search status code: %d, body: %v", code, response))
	}

	bytes, _ := json.Marshal(response)
	log.Infof("adp agent list resp info: %v", string(bytes))
	_ = json.Unmarshal(bytes, &resp)
	return resp, nil
}

func (r *repo) AgentListV2(ctx context.Context, req adp_agent_factory.AgentListReq) (resp *adp_agent_factory.AgentListResp, err error) {

	uri := fmt.Sprintf("%s/api/agent-factory/v3/published/agent", settings.GetConfig().DepServicesConf.ADPAgentFactoryHost)

	headers := make(map[string][]string)
	headers["x-business-domain"] = []string{"bd_public"}
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}
	headers["Content-Type"] = []string{"application/json"}
	//req := CheckCatalogFavoriteReq{}
	//nReq := map[string]any{}
	//nReq["size"] = 1

	//req.Resources = append(req.Resources, CatalogFavoriteItem{"data-catalog", inputCateIds})
	return httpPostDo[adp_agent_factory.AgentListResp](ctx, uri, req, headers, r)
}

func httpPostDo[T any](ctx context.Context, url string, bodyReq any, headers map[string][]string, r *repo) (*T, error) {
	return httpJsonDo[T](ctx, http.MethodPost, url, bodyReq, headers, r)
}

func httpJsonDo[T any](ctx context.Context, httpMethod, url string, bodyReq any, headers map[string][]string, r *repo) (*T, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var body string
	if bodyReq != nil {
		b, err := json.Marshal(bodyReq)
		if err != nil {
			log.WithContext(ctx).Errorf("json.Marshal failed, body: %v, err: %v", bodyReq, err)
			return nil, errorcode.Detail(errorcode.PublicInternalError, err)
		}
		body = string(b)
	}

	return httpADDo[T](ctx, httpMethod, url, body, headers, true, r)
}

func httpADDo[T any](ctx context.Context, httpMethod, url string, bodyParam any, headers url.Values, needAppKey bool, r *repo) (*T, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var bodyStr string
	var body io.Reader
	bodyStr, ok := bodyParam.(string)
	if ok {
		if len(bodyStr) > 0 {
			body = strings.NewReader(bodyStr)
		}
	} else if body, ok = bodyParam.(io.Reader); !ok {
		return nil, errors.New("invalid req body param")
	}

	// for k, vv := range headers {
	// 	for _, v := range vv {
	// 		appHeaders.Add(k, v)
	// 	}
	// }

	return httpDo[T](ctx, httpMethod, url, body, bodyStr, headers, r)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, r *repo) (*T, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req, err := http.NewRequestWithContext(ctx, httpMethod, url, body)
	//req, err := http.Post(url, "application/json" body)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to build http req, err: %v", err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	for k, vv := range headers {
		for _, v := range vv {
			log.WithContext(ctx).Infof("header: %s: %s", k, v)
			req.Header.Add(k, v)
		}
	}

	//log.WithContext(ctx).Infof("http req, url: %s, body: %s", req.URL, bodyStr)
	resp, err := r.rawHttpClient.Do(req)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to request ad, err: %v", err)
		return nil, errorcode.Detail(errorcode.AnyDataConnectionError, err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to read resp data in post ad, url: %s, err: %v", req.URL.String(), err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	if resp.StatusCode >= http.StatusInternalServerError {
		log.WithContext(ctx).Errorf("failed to send req in post ad, url: %s, resp: %s", req.URL.String(), b)
		return nil, errorcode.Detail(errorcode.PublicServiceInternalError, string(b))
	}
	if resp.StatusCode >= http.StatusBadRequest {
		log.WithContext(ctx).Errorf("failed to send req in post ad, url: %s, resp: %s", req.URL.String(), b)
		return nil, errorcode.Detail(errorcode.PublicBadRequestError, string(b))
	}

	log.WithContext(ctx).Infof("http req, url: %s, body: %s, data: %s", req.URL, bodyStr, b)
	var ret T

	decoder := json.NewDecoder(bytes.NewBuffer(b))
	decoder.UseNumber() // 指定使用 Number 类型
	if err := decoder.Decode(&ret); err != nil {
		log.WithContext(ctx).Errorf("failed to read resp data in post ad, url: %s, err: %v", req.URL.String(), err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	return &ret, nil
}
