package auth_service

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
	"unsafe"

	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"go.uber.org/zap"
)

func httpGetDo[T any](ctx context.Context, u *url.URL, a *authService) (*T, error) {

	headers := make(map[string][]string)

	return httpDo[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, headers, a)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, a *authService) (*T, error) {
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

func httpPostDoP[T any](ctx context.Context, url string, bodyReq any, headers map[string][]string, a *authService) (*T, error) {
	return httpJsonDoP[T](ctx, http.MethodPost, url, bodyReq, headers, a)
}

func httpJsonDoP[T any](ctx context.Context, httpMethod, url string, bodyReq any, headers map[string][]string, a *authService) (*T, error) {
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

	return httpADDoP[T](ctx, httpMethod, url, body, headers, a)
}

func httpADDoP[T any](ctx context.Context, httpMethod, url string, bodyParam any, headers url.Values, a *authService) (*T, error) {
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

	return httpDo[T](ctx, httpMethod, url, body, bodyStr, headers, a)
}

func (a *authService) GetUserResource(ctx context.Context, req map[string]any) (*UserResource, error) {

	rawURL := a.baseUrl + "/api/auth-service/v1/subject/objects"
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
	return httpGetDo[UserResource](ctx, u, a)
}

func (a *authService) HTTPGetResponse(ctx context.Context, method, strUrl string, header http.Header, vals url.Values, body io.Reader) (int, []byte, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if vals != nil {
		strUrl = fmt.Sprintf("%s?%s", strUrl, vals.Encode())
	}

	req, err := http.NewRequestWithContext(ctx, method, strUrl, body)
	if err != nil {
		return 0, nil, err
	}

	if header != nil {
		req.Header = header
	}

	resp, err := a.httpClient.Do(req)
	if err != nil {
		return 0, nil, err
	}

	var buf []byte
	defer func() {
		closeErr := resp.Body.Close()
		if closeErr != nil {
			log.WithContext(ctx).Error("DoHttp"+method, zap.Error(closeErr))

		}
	}()
	buf, err = io.ReadAll(resp.Body)
	if err != nil {
		return 0, nil, err
	}

	return resp.StatusCode, buf, nil
}

func BytesToString(b []byte) string {
	return *(*string)(unsafe.Pointer(&b))
}

func (a *authService) doHttp(ctx context.Context, method, strUrl string, header http.Header, vals url.Values, body io.Reader) ([]byte, error) {
	statusCode, buf, err := a.HTTPGetResponse(ctx, method, strUrl, header, vals, body)
	if err != nil {
		return nil, err
	}

	if statusCode != http.StatusOK {
		if statusCode == http.StatusCreated {
			return buf, nil
		}
		return nil, errors.New(BytesToString(buf))
	}

	return buf, nil
}

func (a *authService) DoHttpPost(ctx context.Context, strUrl string, header http.Header, body io.Reader) ([]byte, error) {
	return a.doHttp(ctx, http.MethodPost, strUrl, header, nil, body)
}

func (a *authService) GetUserResourceById(ctx context.Context, req []map[string]interface{}) (*PolicyEnforceRespItem, error) {

	//uri := a.baseUrl + "/api/auth-service/v1/enforce"
	buf, err := json.Marshal(req)
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult json.Marshal error (params: %v)", req)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}
	log.WithContext(ctx).Infof("GetDownloadEnforceResult的Body请求体json====%s", string(buf))

	header := http.Header{
		"Content-Type":  []string{"application/json"},
		"Authorization": []string{ctx.Value(constant.Token).(string)},
	}

	buf, err = a.DoHttpPost(ctx, a.baseUrl+"/api/auth-service/v1/enforce", header, bytes.NewReader(buf))
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult接口报错返回，err is: %v", err)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	var resp []*PolicyEnforceRespItem
	if err = json.Unmarshal(buf, &resp); err != nil {
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	if len(resp) == 1 {
		return resp[0], nil
	}
	return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
}

func (a *authService) GetUserResourceListByIds(ctx context.Context, req []map[string]interface{}) ([]*PolicyEnforceRespItem, error) {
	buf, err := json.Marshal(req)
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult json.Marshal error (params: %v)", req)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}
	log.WithContext(ctx).Infof("GetDownloadEnforceResult的Body请求体json====%s", string(buf))

	header := http.Header{
		"Content-Type":  []string{"application/json"},
		"Authorization": []string{ctx.Value(constant.Token).(string)},
	}

	buf, err = a.DoHttpPost(ctx, a.baseUrl+"/api/auth-service/v1/enforce", header, bytes.NewReader(buf))
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult接口报错返回，err is: %v", err)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	var resp []*PolicyEnforceRespItem
	if err = json.Unmarshal(buf, &resp); err != nil {
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	return resp, nil
	//if len(resp) == 1 {
	//	return resp[0], nil
	//}
	//return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
}

type PolicyEnforceResp struct {
	PolicyEnforceRespStruct []*PolicyEnforceRespItem
}

type PolicyEnforceRespItem struct {
	Action      string `json:"action"`
	Effect      string `json:"effect"`
	ObjectId    string `json:"object_id"`
	ObjectType  string `json:"object_type"`
	SubjectId   string `json:"subject_id"`
	SubjectType string `json:"subject_type"`
}
