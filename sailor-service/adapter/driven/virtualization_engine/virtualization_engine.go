package virtualization_engine

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"time"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type VirtualizationEngine interface {
	Raw(ctx context.Context, selectSQL string) (*RawResult, error)
	RawWithTimeOut(ctx context.Context, selectSQL string, timeOut time.Duration) (*RawResult, error)
	Columns(ctx context.Context, catalog string, schema string, table string) (*ColumnsResult, error)
}

type virtualizationEngine struct {
	url        string
	httpClient *http.Client
}

func NewVirtualizationEngine(httpClient *http.Client) VirtualizationEngine {
	return &virtualizationEngine{url: settings.GetConfig().DepServicesConf.VirtualizationEngineUrl, httpClient: httpClient}
}

type RawResult struct {
	Columns []struct {
		Name string `json:"name"`
		Type string `json:"type"`
	} `json:"columns"`
	Data [][]any `json:"data"`
}

type ColumnsResult struct {
	Columns []struct {
		Name     string `json:"name"`
		Type     string `json:"type"`
		OrigType string `json:"origType"`
		Comment  string `json:"comment"`
	} `json:"data"`
}

func (v *virtualizationEngine) Raw(ctx context.Context, selectSQL string) (*RawResult, error) {
	return v.RawWithTimeOut(ctx, selectSQL, 0)
}

func (v *virtualizationEngine) RawWithTimeOut(ctx context.Context, selectSQL string, timeOut time.Duration) (*RawResult, error) {
	url := v.url + "/api/virtual_engine_service/v1/fetch"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, strings.NewReader(selectSQL))
	if err != nil {
		log.WithContext(ctx).Errorf("failed to create req in post vir engine, sql: %v, err: %v", selectSQL, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	req.Header.Add("Content-Type", "text/plain")
	req.Header.Add("X-Presto-User", "admin")

	httpClient := v.httpClient
	if timeOut != 0 {
		httpClient = trace.NewOtelHttpClient()
		httpClient.Timeout = timeOut
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to send req in post vir engine, sql: %v, url: %s, err: %v", selectSQL, req.URL.String(), err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to read resp data in post vir engine, sql: %v, url: %s, err: %v", selectSQL, req.URL.String(), err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	if resp.StatusCode >= http.StatusInternalServerError {
		log.WithContext(ctx).Errorf("failed to send req in post vir engine, sql: %v, url: %s, resp: %s", selectSQL, req.URL.String(), b)
		return nil, errorcode.Detail(errorcode.PublicInternalError, string(b))
	}

	if resp.StatusCode >= http.StatusBadRequest {
		log.WithContext(ctx).Errorf("failed to send req in post vir engine, sql: %v, url: %s, resp: %s", selectSQL, req.URL.String(), b)
		return nil, errorcode.Detail(errorcode.PublicInternalError, string(b))
	}

	var ret RawResult
	if err = json.Unmarshal(b, &ret); err != nil {
		log.WithContext(ctx).Errorf("failed to send req in post vir engine, sql: %v, utl: %s, resp: %s, json.Unmarshal err: %v", selectSQL, req.URL.String(), b, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &ret, nil
}

func (v *virtualizationEngine) Columns(ctx context.Context, catalog string, schema string, table string) (*ColumnsResult, error) {
	url := fmt.Sprintf(v.url+"/api/virtual_engine_service/v1/metadata/columns/%s/%s/%s", catalog, schema, table)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		log.Errorf("failed to create req in post vir engine, err: %v", err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	req.Header.Add("Content-Type", "text/plain")
	req.Header.Add("X-Presto-User", "admin")
	httpClient := trace.NewOtelHttpClient()
	httpClient.Timeout = 2 * time.Minute

	resp, err := httpClient.Do(req)

	if err != nil {
		log.Errorf("failed to send req in post vir engine, url: %s, err: %v", url, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Errorf("failed to read resp data in post vir engine url: %s, err: %v", url, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	if resp.StatusCode >= http.StatusInternalServerError {
		log.Errorf("failed to send req in post vir engine url: %s, resp: %s", url, b)
		return nil, errorcode.Detail(errorcode.PublicInternalError, string(b))
	}

	if resp.StatusCode >= http.StatusBadRequest {
		log.Errorf("failed to send req in post vir engine url: %s, resp: %s", url, b)
		return nil, errorcode.Detail(errorcode.PublicVEngineRequestBad, string(b))
	}

	var ret ColumnsResult
	if err = json.Unmarshal(b, &ret); err != nil {
		log.Errorf("failed to send req in post vir engine url: %s, resp: %s, json.Unmarshal err: %v", url, b, err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &ret, nil
}
