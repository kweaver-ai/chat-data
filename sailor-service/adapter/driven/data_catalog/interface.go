package data_catalog

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
)

type DataCatalog interface {
	GetCatalogFilter(ctx context.Context) (*DataCatalogFilter, error)
	GetCustomerIdList(inputCateTypeId string, inputCateNodeIdList []string, inputCatalogFilter DataCatalogFilter) ([]string, error)
	CheckCatalogFavorite(ctx context.Context, inputCateIds []string) (*CheckCatalogFavoriteResp, error)
	GetResourceFavoriteByID(ctx context.Context, req *CheckV1Req) (*CheckV1Resp, error)
}

func httpGetDo[T any](ctx context.Context, u *url.URL, d *dataCatalog, headers map[string][]string) (*T, error) {

	return httpDo[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, headers, d)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, d *dataCatalog) (*T, error) {
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

	//log.WithContext(ctx).Infof("http req, url: %s, body: %s", req.URL, bodyStr)
	resp, err := d.httpClient.Do(req)
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

func httpPostDo[T any](ctx context.Context, url string, bodyReq any, headers map[string][]string, d *dataCatalog) (*T, error) {
	return httpJsonDo[T](ctx, http.MethodPost, url, bodyReq, headers, d)
}

func httpJsonDo[T any](ctx context.Context, httpMethod, url string, bodyReq any, headers map[string][]string, d *dataCatalog) (*T, error) {
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

	return httpADDo[T](ctx, httpMethod, url, body, headers, true, d)
}

func httpADDo[T any](ctx context.Context, httpMethod, url string, bodyParam any, headers url.Values, needAppKey bool, d *dataCatalog) (*T, error) {
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

	return httpDo[T](ctx, httpMethod, url, body, bodyStr, headers, d)
}
