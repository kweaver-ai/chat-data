package configuration_center

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"time"
	"unsafe"

	"github.com/jinzhu/copier"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/kweaver-ai/idrm-go-frame/core/utils/httpclient"
	"github.com/pkg/errors"
	"go.uber.org/zap"
)

type ConfigurationCenter struct {
	baseURL       string
	RawHttpClient httpclient.HTTPClient

	httpClient *http.Client
}

func NewConfigurationCenter(rawHttpClient httpclient.HTTPClient, httpClient *http.Client) DrivenConfigurationCenter {
	ccHost := settings.GetConfig().DepServicesConf.ConfigCenterHost
	return &ConfigurationCenter{baseURL: ccHost, RawHttpClient: rawHttpClient, httpClient: httpClient}
}

func (c *ConfigurationCenter) GetStandardizationAddr(ctx context.Context, token string) (string, error) {
	return c.getThirdPartyAddr(ctx, token, "Standardization")
}

func (c *ConfigurationCenter) getThirdPartyAddr(ctx context.Context, token string, thirdPartyName string) (string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	url := fmt.Sprintf("%s/api/configuration-center/v1/third_party_addr?name=%s", c.baseURL, thirdPartyName)
	resp, err := c.RawHttpClient.Get(ctx, url, map[string]string{"Authorization": token})
	if err != nil {
		log.WithContext(ctx).Errorf("DrivenConfigurationCenter getThirdPartyAddr client.Do error, %v", err)
		return "", errorcode.Detail(errorcode.PublicInternalError, err)
	}

	m := make([]map[string]any, 0)
	if err = copier.Copy(&m, resp); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return "", errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return m[0]["addr"].(string), nil
}

type DataUserTypeRes struct {
	Using int `json:"using"`
}

type DepartmentObjectsList struct {
	Entries []struct {
		Id     string `json:"id"`
		Name   string `json:"name"`
		Type   string `json:"type"`
		Path   string `json:"path"`
		PathId string `json:"path_id"`
		Expand bool   `json:"expand"`
	} `json:"entries"`
	TotalCount int `json:"total_count"`
}

type UserRolesList []UserRoleItem

type UserRoleItem struct {
	Id        string    `json:"id"`
	Name      string    `json:"name"`
	Color     string    `json:"color"`
	Icon      string    `json:"icon"`
	System    int       `json:"system"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	DeletedAt int       `json:"deleted_at"`
}

func (c *ConfigurationCenter) GetChildrenDepartment(ctx context.Context, departmentId string) (*DepartmentObjectsList, error) {
	var err error
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := c.baseURL + "/api/configuration-center/v1/objects"
	u, err := url.Parse(rawURL)
	if err != nil {
		//log.WithContext(ctx).Errorf("failed to parse url: %s, err: %v", rawURL, err)
		return nil, errors.Wrap(err, "parse url failed")
	}

	headers := make(map[string][]string)
	headers["Authorization"] = []string{fmt.Sprintf("%v", ctx.Value(constant.UserTokenKey))}

	m := make(map[string]string)
	m["id"] = departmentId
	m["is_all"] = "true"

	values := url.Values{}
	for k, v := range m {
		values.Add(k, v)
	}

	u.RawQuery = values.Encode()

	return httpGetDo[DepartmentObjectsList](ctx, u, headers, c)
}

func (c *ConfigurationCenter) DataUseType(ctx context.Context) (*DataUserTypeRes, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := c.baseURL + "/api/internal/configuration-center/v1/data/using"
	u, err := url.Parse(rawURL)
	if err != nil {
		//log.WithContext(ctx).Errorf("failed to parse url: %s, err: %v", rawURL, err)
		return nil, errors.Wrap(err, "parse url failed")
	}

	headers := make(map[string][]string)

	var m map[string]string

	values := url.Values{}
	for k, v := range m {
		values.Add(k, v)
	}

	u.RawQuery = values.Encode()

	return httpGetDo[DataUserTypeRes](ctx, u, headers, c)
}

func (a *ConfigurationCenter) GetUserRoles(ctx context.Context) ([]*UserRoleItem, error) {
	req := []map[string]interface{}{}
	buf, err := json.Marshal(req)
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult json.Marshal error (params: %v)", req)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}
	//log.WithContext(ctx).Infof("GetDownloadEnforceResult的Body请求体json====%s", string(buf))

	header := http.Header{
		"Content-Type":  []string{"application/json"},
		"Authorization": []string{ctx.Value(constant.Token).(string)},
	}

	buf, err = a.DoHttpGet(ctx, a.baseURL+"/api/configuration-center/v1/users/roles", header, bytes.NewReader(buf))
	if err != nil {
		log.WithContext(ctx).Errorf("GetDownloadEnforceResult接口报错返回，err is: %v", err)
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	var resp []*UserRoleItem
	if err = json.Unmarshal(buf, &resp); err != nil {
		return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
	}

	return resp, nil
	//if len(resp) == 1 {
	//	return resp[0], nil
	//}
	//return nil, errorcode.Detail(errorcode.TokenAuditFailed, err)
}

func (a *ConfigurationCenter) DoHttpPost(ctx context.Context, strUrl string, header http.Header, body io.Reader) ([]byte, error) {
	return a.doHttp(ctx, http.MethodPost, strUrl, header, nil, body)
}

func (a *ConfigurationCenter) DoHttpGet(ctx context.Context, strUrl string, header http.Header, body io.Reader) ([]byte, error) {
	return a.doHttp(ctx, http.MethodGet, strUrl, header, nil, body)
}

func BytesToString(b []byte) string {
	return *(*string)(unsafe.Pointer(&b))
}

func (a *ConfigurationCenter) doHttp(ctx context.Context, method, strUrl string, header http.Header, vals url.Values, body io.Reader) ([]byte, error) {
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

func (a *ConfigurationCenter) HTTPGetResponse(ctx context.Context, method, strUrl string, header http.Header, vals url.Values, body io.Reader) (int, []byte, error) {
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

func httpGetDo[T any](ctx context.Context, u *url.URL, headers map[string][]string, a *ConfigurationCenter) (*T, error) {

	//headers := make(map[string][]string)

	return httpDo[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, headers, a)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, c *ConfigurationCenter) (*T, error) {
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
	resp, err := c.httpClient.Do(req)
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
