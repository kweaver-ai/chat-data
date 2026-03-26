package af_sailor_agent

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"sync"
	"sync/atomic"
	"time"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
)

type afSailorAgent struct {
	baseUrl string

	httpClient *http.Client
	mtx        sync.Mutex
	appIdCache atomic.Value
}

func NewAFSailorAgent(httpClient *http.Client) AFSailorAgent {
	cfg := settings.GetConfig().AfSailorAgentConf
	cli := &http.Client{
		Transport: httpClient.Transport,
		Timeout:   5 * time.Minute,
	}
	return &afSailorAgent{
		baseUrl:    cfg.URL,
		httpClient: cli,
	}
}

type SailorSessionResp struct {
	Res string `json:"res"`
}

func (a *afSailorAgent) SailorGetSessionEngine(ctx context.Context, req map[string]any) (*SailorSessionResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + "/api/af-sailor-agent/v1/assistant/chat/get-session-id"
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

func httpGetDo[T any](ctx context.Context, u *url.URL, a *afSailorAgent) (*T, error) {

	headers := make(map[string][]string)

	return httpDo[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, headers, a)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, a *afSailorAgent) (*T, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req, err := http.NewRequestWithContext(ctx, httpMethod, url, body)
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

	log.WithContext(ctx).Infof("http req, url: %s, body: %s", req.URL, bodyStr)
	resp, err := a.httpClient.Do(req)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to request ad, err: %v", err)
		return nil, errorcode.Detail(errorcode.AFSailorAgentConnectionError, err)
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
