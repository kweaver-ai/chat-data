package knowledge_network

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"mime/multipart"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
)

type AD interface {
	Services(ctx context.Context, serviceId string, content any) (*CustomSearchResp, error)
	//SearchEngine 自定义认知服务
	SearchEngine(ctx context.Context, serviceId string, content any) (*SearchEngineResponse, error)
	//GraphAnalysis 图分析服务
	GraphAnalysis(ctx context.Context, serviceId string, content any) (*GraphAnalysisResp, error)

	//GetKnowledgeNetwork(ctx context.Context, id string) (*GetKnowledgeNetworkResp, bool, error)

	CreateKnowledgeNetwork(ctx context.Context, req *CreateKnowledgeNetworkReq) (*CreateKnowledgeNetworkResp, error)

	//GetDataSource(ctx context.Context, id string) (*GetDatasourceResp, bool, error)

	CreateDataSource(ctx context.Context, req *CreateDatasourceReq) (*CreateDatasourceResp, error)

	//GetKnowledgeGraph(ctx context.Context, id string) (*GetKnowledgeGraphResp, bool, error)

	ImportKnowledgeGraph(ctx context.Context, req *ImportKnowledgeGraphReq) (*ImportKnowledgeGraphResp, error)

	//GetDomainAnalysis(ctx context.Context, id string) (*GetDomainAnalysisResp, bool, error)

	ImportDomainAnalysis(ctx context.Context, req *ImportDomainAnalysisReq) (*ImportDomainAnalysisResp, error)

	AddCognitiveService(ctx context.Context, req *AddCognitiveServiceReq) (*AddCognitiveServiceResp, error)

	AddSynonymsLexicon(ctx context.Context, req *NewLexiconReq) (*NewLexiconReqResp, error)

	StartGraphBuildTask(ctx context.Context, graphId string, req *ExecGraphBuildTaskReq) (*ExecGraphBuildTaskResp, error)

	ListGraphBuildTask(ctx context.Context, graphId string, req *ListGraphBuildTaskReq) (*ListGraphBuildTaskResp, error)

	FulltextSearch(ctx context.Context, kgID string, query string, config []*SearchConfig) (*ADLineageFulltextResp, error)
	FulltextSearchV2(ctx context.Context, kgID string, query string, config []*SearchConfig) (*ADLineageFulltextV2Resp, error)
	NeighborSearch(ctx context.Context, vid string, steps int, kgId string) (*ADLineageNeighborsResp, error)

	GetAppId(ctx context.Context) (string, error)

	DeleteKnowledgeNetwork(ctx context.Context, knwId int) (err error)
	DeleteDataSource(ctx context.Context, ids []int) (err error)
	DeleteKnowledgeGraph(ctx context.Context, knwId int, graphIds []int) (err error)
	DeleteSynonymsLexicon(ctx context.Context, ids []int) (err error)
	DeleteGraphAnalysis(ctx context.Context, serviceId string) (err error)
	DeleteCognitionService(ctx context.Context, serviceId string) (err error)

	GraphAnalysisCancelRelease(ctx context.Context, serviceId string) (err error)
	CognitionServiceCancelRelease(ctx context.Context, serviceId string) (err error)

	EntitySearchByEngine(ctx context.Context, entityId string, kgId string) (*ADFullResp, error)
	NeighborSearchByEngine(ctx context.Context, vid string, steps int, kgId string) (*ADLineageNeighborsRespV2, error)
	NeighborSearchByEngineV2(ctx context.Context, vid string, steps int, kgId string) (*ADLineageNeighborsRespV2, error)
	InsertEntity(ctx context.Context, dataType string, graphData []map[string]any, kgId int, entityName string) (*InsertGraphResp, error)
	InsertSide(ctx context.Context, dataType string, graphData []map[string]map[string]string, kgId int, sideName string) (*InsertGraphResp, error)
	DeleteEntity(ctx context.Context, graphData []map[string]string, entityName string, kgId int) (*InsertGraphResp, error)
	DeleteEdge(ctx context.Context, graphData []map[string]map[string]string, entityName string, kgId int) (*InsertGraphResp, error)
	GetSearchConfig(tagName string, propertyName string, propertyValue string) ([]*SearchConfig, error)
	//GetSearchConfigV2(tagName string, propertyName string, propertyValue string) ([]*SearchConfig, error)

	ListKnowledgeNetwork(ctx context.Context, req *ListKnowledgeNetworkReq) (*ListKnowledgeNetworkResp, error)
	ListKnowledgeGraph(ctx context.Context, req *ListKnowledgeGraphReq) (*ListKnowledgeGraphResp, error)
	ListKnowledgeLexicon(ctx context.Context, req *ListKnowledgeLexiconReq) (*ListKnowledgeLexiconResp, error)
	GraphSchemaInterface
}

type GraphSchemaInterface interface {
	//本体

	QueryGraphByName(ctx context.Context, knwID int, graphName string) (graphID int, err error)
	CreateGraphOtl(ctx context.Context, req *CreateGraphReq) (graphID int, err error)
	UpdateGraphOtl(ctx context.Context, graphID int, req *CreateGraphReq) (err error)
	DeleteGraphOtl(ctx context.Context, knwID int, graphID int) (err error)

	UpdateSchema(ctx context.Context, knwId int, schema *GraphSchema) (err error)
	SchemeSaveNoCheck(ctx context.Context, schema *GraphNoCheck) (err error)
	GraphDetail(ctx context.Context, knwId int) (detail *GraphDetail, err error)

	//分组

	CreateSubGraph(ctx context.Context, subGraph *SubGraphReq) (id int, err error)
	UpdateSubGraph(ctx context.Context, knid int, subGraphs []*SubGraphBody) (err error)
	GetSubGraph(ctx context.Context, knid int, subGraphName string) (subGraphSlice []*SubGraphInfo, err error)

	//任务

	CreateGraphTask(ctx context.Context, graphID int, taskType string) (id int, err error)
	GraphTaskList(ctx context.Context, graphID int, req *GraphGroupTaskListReq) (data *TaskDetailListRes, err error)
	DeleteTask(ctx context.Context, graphID int, taskIDSlice []int) (err error)
}

const (
	accountTypeEmail    = "email"
	accountTypeUsername = "username"
)

type ad struct {
	baseUrl     string
	accountType string
	user        string
	password    string

	httpClient *http.Client
	mtx        sync.Mutex
	appIdCache atomic.Value
}

func NewAD(httpClient *http.Client) AD {
	cfg := settings.GetConfig().AnyDataConf
	cli := &http.Client{
		Transport: httpClient.Transport,
		Timeout:   5 * time.Minute,
	}
	return &ad{
		baseUrl:     cfg.URL,
		accountType: cfg.AccountType,
		user:        cfg.User,
		password:    cfg.Password,
		httpClient:  cli,
	}
}

func (a *ad) appId(ctx context.Context) (string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	uri := a.baseUrl + "/api/rbac/v1/user/appId"
	body := map[string]any{
		"isRefresh": 0,
		"password":  base64.StdEncoding.EncodeToString([]byte(a.password)),
	}
	switch a.accountType {
	case accountTypeEmail:
		body["email"] = a.user

	case accountTypeUsername:
		body["username"] = a.user

	default:
		log.WithContext(ctx).Errorf("unsupported ad account type: %s", a.accountType)
		return "", fmt.Errorf("unsupported account type: %s", a.accountType)
	}

	ret, err := httpDo[map[string]string](ctx, http.MethodPost, uri, bytes.NewReader(lo.T2(json.Marshal(body)).A), string(lo.T2(json.Marshal(body)).A), map[string][]string{"type": {a.accountType}}, a)
	if err != nil {
		return "", err
	}

	return (*ret)["res"], nil
}

func (a *ad) GetAppId(ctx context.Context) (string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	//val := a.appIdCache.Load()
	//if val != nil {
	//	return val.(string), nil
	//}
	//
	//a.mtx.Lock()
	//defer a.mtx.Unlock()
	//
	//val = a.appIdCache.Load()
	//if val != nil {
	//	return val.(string), nil
	//}

	appId, err := a.appId(ctx)
	if err != nil {
		if errorcode.IsSameErrorCode(err, errorcode.PublicBadRequestError) {
			log.Error(err.Error())
			return "", errorcode.Desc(errorcode.AnyDataAuthError)
		}
		return "", err
	}

	//a.appIdCache.Store(appId)
	return appId, nil
}

func (a *ad) getAppKey(reqParams, timestamp, appid string) string {
	hmacInst := hmac.New(sha256.New, []byte(appid))
	sha := sha256.New()
	sha.Write([]byte(timestamp))
	timestamp16str := hex.EncodeToString(sha.Sum(nil))
	sha.Reset()
	sha.Write([]byte(reqParams))
	reqParams16str := hex.EncodeToString(sha.Sum(nil))
	hmacInst.Write([]byte(timestamp16str))
	hmacInst.Write([]byte(reqParams16str))
	return base64.StdEncoding.EncodeToString([]byte(hex.EncodeToString(hmacInst.Sum(nil))))
}

type CustomSearchResp struct {
	Res []struct {
		VerticesParsedList []struct {
			Vid        string   `json:"vid"`
			Tags       []string `json:"tags"`
			Properties []struct {
				Tag   string `json:"tag"`
				Props []struct {
					Name  string `json:"name"`
					Alias string `json:"alias"`
					Value string `json:"value"`
					Type  string `json:"type"`
				} `json:"props"`
			} `json:"properties"`
			Type            string `json:"type"`
			Color           string `json:"color"`
			Alias           string `json:"alias"`
			DefaultProperty struct {
				N string `json:"n"`
				A string `json:"a"`
				V string `json:"v"`
			} `json:"default_property"`
			Icon string `json:"icon"`
		} `json:"vertices_parsed_list"`
		Statement string `json:"statement"`
	} `json:"res"`
}

func (a *ad) Services(ctx context.Context, serviceId string, content any) (*CustomSearchResp, error) {
	uri := a.baseUrl + "/api/cognitive-service/v1/open/custom-search/services/" + serviceId
	return httpPostDo[CustomSearchResp](ctx, uri, content, nil, a)
}

func (a *ad) getAppIdKeyHeaders(ctx context.Context, body *string) (url.Values, error) {
	appId, err := a.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	timestamp := strconv.FormatInt(time.Now().Unix(), 10)

	ret := url.Values{}

	//if body != nil {
	//	appKey := a.getAppKey(*body, timestamp, appId)
	//	ret.Set("appkey", appKey)
	//}

	ret.Set("appid", appId)
	ret.Set("timestamp", timestamp)
	return ret, nil
}

func httpPostDo[T any](ctx context.Context, url string, bodyReq any, headers map[string][]string, a *ad) (*T, error) {
	return httpJsonDo[T](ctx, http.MethodPost, url, bodyReq, headers, a)
}

//func httpGetDo[T any](ctx context.Context, url string, bodyReq any, headers map[string][]string, a *ad) (*T, error) {
//	return httpJsonDo[T](ctx, http.MethodGet, url, bodyReq, headers, a)
//}

func httpJsonDo[T any](ctx context.Context, httpMethod, url string, bodyReq any, headers map[string][]string, a *ad) (*T, error) {
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

	return httpADDo[T](ctx, httpMethod, url, body, headers, true, a)
}

func httpADDo[T any](ctx context.Context, httpMethod, url string, bodyParam any, headers url.Values, needAppKey bool, a *ad) (*T, error) {
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

	appHeaders, err := a.getAppIdKeyHeaders(ctx, lo.Ternary(needAppKey, &bodyStr, nil))
	if err != nil {
		return nil, err
	}

	for k, vv := range headers {
		for _, v := range vv {
			appHeaders.Add(k, v)
		}
	}

	return httpDo[T](ctx, httpMethod, url, body, bodyStr, appHeaders, a)
}

func httpGetDo[T any](ctx context.Context, u *url.URL, a *ad) (*T, error) {
	appHeaders, err := a.getAppIdKeyHeaders(ctx, &u.RawQuery)
	if err != nil {
		return nil, err
	}

	return httpDo[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, appHeaders, a)
}

func httpGetDoV2[T any](ctx context.Context, u *url.URL, a *ad) (*T, error) {
	appHeaders, err := a.getAppIdKeyHeaders(ctx, &u.RawQuery)
	if err != nil {
		return nil, err
	}

	return httpDoV2[T](ctx, http.MethodGet, u.String(), nil, u.RawQuery, appHeaders, a)
}

func httpDo[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, a *ad) (*T, error) {
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
			//log.WithContext(ctx).Infof("header: %s: %s", k, v)
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

func httpDoV2[T any](ctx context.Context, httpMethod, url string, body io.Reader, bodyStr string, headers url.Values, a *ad) (*T, error) {
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
			//log.WithContext(ctx).Infof("header: %s: %s", k, v)
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

	log.WithContext(ctx).Infof("http req, url: %s, body: %s", req.URL, bodyStr)
	var ret T

	decoder := json.NewDecoder(bytes.NewBuffer(b))
	decoder.UseNumber() // 指定使用 Number 类型
	if err := decoder.Decode(&ret); err != nil {
		log.WithContext(ctx).Errorf("failed to read resp data in post ad, url: %s, err: %v", req.URL.String(), err)
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	return &ret, nil
}

//type GetKnowledgeNetworkResp struct {
//}
//
//func (a *ad) GetKnowledgeNetwork(ctx context.Context, id string) (*GetKnowledgeNetworkResp, bool, error) {
//	url := a.baseUrl + "/" + id
//	resp, err := httpGetDo[GetKnowledgeNetworkResp](ctx, url, nil, nil, a)
//	if err != nil {
//		return nil, false, err
//	}
//
//	// 检测是否存在
//	_ = resp
//
//	panic(nil)
//}

type CreateKnowledgeNetworkReq struct {
	KnwName  string `json:"knw_name,omitempty"`  // 知识网络名称
	KnwDes   string `json:"knw_des,omitempty"`   // 知识网络描述
	KnwColor string `json:"knw_color,omitempty"` // 知识网络颜色 #126EE3
}

type CreateKnowledgeNetworkResp struct {
	Data    int    `json:"data"` // 知识网络id
	Message string `json:"message"`
}

func (a *ad) CreateKnowledgeNetwork(ctx context.Context, req *CreateKnowledgeNetworkReq) (*CreateKnowledgeNetworkResp, error) {
	uri := a.baseUrl + "/api/builder/v1/open/knw/network"
	return httpPostDo[CreateKnowledgeNetworkResp](ctx, uri, req, nil, a)
}

type AddCognitiveServiceReq struct {
	Status       int      `json:"status"`
	KnwId        string   `json:"knw_id"`
	Name         string   `json:"name"`
	AccessMethod []string `json:"access_method"`
	Permission   string   `json:"permission"`
	Description  string   `json:"description"`
	CustomConfig any      `json:"custom_config"`
}

type AddCognitiveServiceResp struct {
	Res string `json:"res"`
}

func (a *ad) AddCognitiveService(ctx context.Context, req *AddCognitiveServiceReq) (*AddCognitiveServiceResp, error) {
	uri := a.baseUrl + "/api/cognition-search/v1/open/custom-services"
	return httpPostDo[AddCognitiveServiceResp](ctx, uri, req, http.Header{"Content-Type": []string{"application/json"}}, a)
}

type NewLexiconReq struct {
	Name        string    `json:"name"`
	Labels      []string  `json:"labels"`
	File        io.Reader `json:"-"`
	Description string    `json:"description"`
	KnowledgeId string    `json:"knowledge_id"`
}

type NewLexiconReqResp struct {
	Res int `json:"res"`
}

// AddSynonymsLexicon 创建词库
func (a *ad) AddSynonymsLexicon(ctx context.Context, req *NewLexiconReq) (*NewLexiconReqResp, error) {
	uri := a.baseUrl + "/api/builder/v1/open/lexicon/create"

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	fFieldErr1 := writer.WriteField("name", req.Name)
	fFieldErr2 := writer.WriteField("labels", string(lo.T2(json.Marshal(req.Labels)).A))
	fFieldErr3 := writer.WriteField("description", req.Description)
	fFieldErr4 := writer.WriteField("knowledge_id", req.KnowledgeId)
	formFile, fFieldErr5 := writer.CreateFormFile("file", "synonyms_lexicon.txt")
	if err := FirstError(fFieldErr1, fFieldErr2, fFieldErr3, fFieldErr4, fFieldErr5); err != nil {
		log.Errorf("failed to create form field, err: %v", err)
		return nil, errors.Wrap(err, "create form field failed")
	}

	if _, err := io.Copy(formFile, req.File); err != nil {
		log.Errorf("failed to write file to form, err: %v", err)
		return nil, errors.Wrap(err, "write file to form failed")
	}

	if err := writer.Close(); err != nil {
		log.Errorf("failed to close multipart write, err: %v", err)
		return nil, errors.Wrap(err, "close multipart write failed")
	}

	log.Infof("http req uri: %s, body: %s", uri, lo.T2(json.Marshal(req)).A)

	headers := url.Values{"Content-Type": []string{writer.FormDataContentType()}}
	headers.Add("roles", "data_admin")
	return httpADDo[NewLexiconReqResp](ctx, http.MethodPost, uri, body, headers, false, a)
}

func newLexiconAuthReq(userId, lexiconId string) any {
	authItems := make([]any, 0)
	authItem := make(map[string]any)
	authItem["userId"] = userId
	authItem["dataId"] = lexiconId
	authItem["dataType"] = "lexicon"
	authItem["codes"] = []string{"LEXICON_VIEW", "LEXICON_EDIT", "LEXICON_DELETE", "LEXICON_EDIT_PERMISSION"}
	authItems = append(authItems, authItem)
	return authItems
}

type AddSynonymsLexiconAuthResp struct {
	Res string `json:"res"`
}

// AddSynonymsLexiconAuth 创建词库
func (a *ad) AddSynonymsLexiconAuth(ctx context.Context, lexiconId string) (*AddSynonymsLexiconAuthResp, error) {
	userInfo, err := a.GetLoginInfo(ctx)
	if err != nil {
		return nil, err
	}
	if userInfo != nil && userInfo.Res.UUID == "" {
		return nil, fmt.Errorf("get userId from ad error: empty userInfo")
	}
	userId := userInfo.Res.UUID
	req := newLexiconAuthReq(userId, lexiconId)
	uri := a.baseUrl + "/api/data-auth/v1/open/data-permission/assign"

	headers := http.Header{"Content-Type": []string{"application/json"}}
	headers.Add("roles", "data_admin")
	return httpPostDo[AddSynonymsLexiconAuthResp](ctx, uri, req, headers, a)
}

type ADLoginInfoResp struct {
	Res struct {
		ID       int    `json:"id"`
		Username string `json:"username"`
		Email    string `json:"email"`
		Status   int    `json:"status"`
		UUID     string `json:"uuid"`
		Roles    []struct {
			ID   int    `json:"id"`
			Name string `json:"name"`
		} `json:"roles"`
	} `json:"res"`
}

// GetLoginInfo 获取登录信息
func (a *ad) GetLoginInfo(ctx context.Context) (*ADLoginInfoResp, error) {
	path := a.baseUrl + "/api/rbac/v1/user/login/info"
	uri, _ := url.Parse(path)
	return httpGetDo[ADLoginInfoResp](ctx, uri, a)
}

//type GetDatasourceResp struct {
//}
//
//func (a *ad) GetDataSource(ctx context.Context, id string) (*GetDatasourceResp, bool, error) {
//	url := a.baseUrl + "/" + id
//	resp, err := httpGetDo[GetDatasourceResp](ctx, url, nil, nil, a)
//	if err != nil {
//		return nil, false, err
//	}
//
//	// 检测是否存在
//	_ = resp
//
//	return resp, false, nil
//}

type CreateDatasourceReq struct {
	DSName      string  `json:"dsname"`       // 数据源名称
	DataSource  string  `json:"data_source"`  // 数据源类型
	DataType    string  `json:"dataType"`     // structured、unstructured	rabbitmq是structured
	DSAddress   string  `json:"ds_address"`   // IP
	DSPort      int     `json:"ds_port"`      // 端口
	DSUser      string  `json:"ds_user"`      // 用户
	DSPassword  string  `json:"ds_password"`  // 密码
	DSPath      string  `json:"ds_path"`      // 路径
	ExtractType string  `json:"extract_type"` // 抽取类型
	KnwId       int     `json:"knw_id"`       // 知识网络ID
	ConnectType string  `json:"connect_type"` // 连接类型
	VHost       *string `json:"vhost"`        // Vhost名称，仅rabbitmq数据源使用，接口必须传这个字段，要不然报错
	Queue       *string `json:"queue"`        // 队列名称，仅rabbitmq数据源使用，接口必须传这个字段，要不然报错
	JSONSchema  *string `json:"json_schema"`  // json模板，仅rabbitmq数据源使用，接口必须传这个字段，要不然报错
}

type CreateDatasourceResp struct {
	DSId int    `json:"ds_id"`
	Res  string `json:"res"`
}

func (a *ad) CreateDataSource(ctx context.Context, req *CreateDatasourceReq) (*CreateDatasourceResp, error) {
	uri := a.baseUrl + "/api/builder/v1/open/ds"
	return httpPostDo[CreateDatasourceResp](ctx, uri, req, nil, a)
}

//type GetKnowledgeGraphResp struct {
//}
//
//func (a *ad) GetKnowledgeGraph(ctx context.Context, id string) (*GetKnowledgeGraphResp, bool, error) {
//	url := a.baseUrl + "/" + id
//	resp, err := httpGetDo[GetKnowledgeGraphResp](ctx, url, nil, nil, a)
//	if err != nil {
//		return nil, false, err
//	}
//
//	// 检测是否存在
//	_ = resp
//
//	return resp, false, nil
//}

type ImportKnowledgeGraphReq struct {
	KnwId   int       `json:"knw_id"`    // 知识网络id，上传内部调用时不需要传递本参数，前端调用时需要传递
	Rename  string    `json:"rename"`    // 重命名
	File    io.Reader `json:"-"`         // 上传的数据文件（只能是单个文件）
	DSIdMap string    `json:"ds_id_map"` // 新旧数据源ID映射
}

type ImportKnowledgeGraphResp struct {
	GraphId []int `json:"graph_id"`
}

func (a *ad) ImportKnowledgeGraph(ctx context.Context, req *ImportKnowledgeGraphReq) (*ImportKnowledgeGraphResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	uri := a.baseUrl + "/api/builder/v1/open/graph/input"

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	fFieldErr1 := writer.WriteField("rename", req.Rename)
	fFieldErr2 := writer.WriteField("knw_id", strconv.Itoa(req.KnwId))
	fFieldErr3 := writer.WriteField("ds_id_map", req.DSIdMap)
	formFile, fFieldErr4 := writer.CreateFormFile("file", "graph.json")
	if err := FirstError(fFieldErr1, fFieldErr2, fFieldErr3, fFieldErr4); err != nil {
		log.WithContext(ctx).Errorf("failed to create form field, err: %v", err)
		return nil, errors.Wrap(err, "create form field failed")
	}

	if _, err := io.Copy(formFile, req.File); err != nil {
		log.WithContext(ctx).Errorf("failed to write file to form, err: %v", err)
		return nil, errors.Wrap(err, "write file to form failed")
	}

	if err := writer.Close(); err != nil {
		log.WithContext(ctx).Errorf("failed to close multipart write, err: %v", err)
		return nil, errors.Wrap(err, "close multipart write failed")
	}

	log.WithContext(ctx).Infof("http req uri: %s, body: %s", uri, lo.T2(json.Marshal(req)).A)
	return httpADDo[ImportKnowledgeGraphResp](ctx, http.MethodPost, uri, body, url.Values{"Content-Type": []string{writer.FormDataContentType()}}, false, a)
}

//type GetDomainAnalysisResp struct {
//}
//
//func (a *ad) GetDomainAnalysis(ctx context.Context, id string) (*GetDomainAnalysisResp, bool, error) {
//	url := a.baseUrl + "/" + id
//	resp, err := httpGetDo[GetDomainAnalysisResp](ctx, url, nil, nil, a)
//	if err != nil {
//		return nil, false, err
//	}
//
//	// 检测是否存在
//	_ = resp
//
//	return resp, false, nil
//}

type ImportDomainAnalysisReq struct {
	Name    string    `json:"name"`    // 图分析服务名称
	KnwId   int       `json:"knw_id"`  // 知识网络id
	KgId    int       `json:"kg_id"`   // 知识图谱id
	File    io.Reader `json:"file"`    // 导入文件数据
	Publish bool      `json:"publish"` // 是否发布
}

type ImportDomainAnalysisResp struct {
	Res string `json:"res"` // 图分析服务id
}

func (a *ad) ImportDomainAnalysis(ctx context.Context, req *ImportDomainAnalysisReq) (*ImportDomainAnalysisResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	uri := a.baseUrl + "/api/engine/v1/open/services/import-service/file"

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	fFieldErr1 := writer.WriteField("knw_id", strconv.Itoa(req.KnwId))
	fFieldErr2 := writer.WriteField("kg_id", strconv.Itoa(req.KgId))
	fFieldErr3 := writer.WriteField("publish", fmt.Sprintf("%v", req.Publish))
	fFieldErr4 := writer.WriteField("name", req.Name)
	formFile, fFieldErr5 := writer.CreateFormFile("file", "graph_analysis.json")
	if err := FirstError(fFieldErr1, fFieldErr2, fFieldErr3, fFieldErr4, fFieldErr5); err != nil {
		log.WithContext(ctx).Errorf("failed to create form field, err: %v", err)
		return nil, errors.Wrap(err, "create form field failed")
	}

	if _, err := io.Copy(formFile, req.File); err != nil {
		log.WithContext(ctx).Errorf("failed to write file to form, err: %v", err)
		return nil, errors.Wrap(err, "write file to form failed")
	}

	if err := writer.Close(); err != nil {
		log.WithContext(ctx).Errorf("failed to close multipart write, err: %v", err)
		return nil, errors.Wrap(err, "close multipart write failed")
	}

	return httpADDo[ImportDomainAnalysisResp](ctx, http.MethodPost, uri, body, url.Values{"Content-Type": []string{writer.FormDataContentType()}}, false, a)
}

type ExecGraphBuildTaskReq struct {
	TaskType string `json:"tasktype"` // 任务构建类型，full(全量构建)，increment(增量构建)
}

type ExecGraphBuildTaskResp struct {
	Res any `json:"res"`
}

func (a *ad) StartGraphBuildTask(ctx context.Context, graphId string, req *ExecGraphBuildTaskReq) (*ExecGraphBuildTaskResp, error) {
	uri := a.baseUrl + "/api/builder/v1/open/task/" + graphId
	return httpPostDo[ExecGraphBuildTaskResp](ctx, uri, req, nil, a)
}

type ListGraphBuildTaskReq struct {
	GraphName   string `json:"graph_name"`   // 对图谱名称进行模糊搜索，默认不填，返回所有数据
	Order       string `json:"order"`        // 默认按照开始时间从新至旧排序，接受参数为：'desc'（从新到旧），'asc'（从旧到新）
	Page        int    `json:"page,string"`  // 页码
	Size        int    `json:"size,string"`  // 每页数量
	Rule        string `json:"rule"`         // 排序字段，可选start_time, end_time
	Status      string `json:"status"`       // 默认all ,查询所有的，'normal'(正常), 'running'(运行中), 'waiting'(待运行), 'failed'(失败), 'stop'(中止)
	TaskType    string `json:"task_type"`    // 任务类型，默认all ,查询所有的，full(全量构建)，increment(增量构建)
	TriggerType string `json:"trigger_type"` // 图谱触发方式，默认all 查询所有的，0：手动触发的图谱，1：定时自动触发的图谱，2：实时触发的图谱
}

type ListGraphBuildTaskResp struct {
	Res struct {
		Count int `json:"count"`
		Df    []struct {
			GraphId     int    `json:"graph_id"`
			GraphName   string `json:"graph_name"`
			KgId        int    `json:"kg_id"`
			StartTime   string `json:"start_time"`
			SubgraphId  int    `json:"subgraph_id"`
			TaskId      int    `json:"task_id"`
			TaskName    string `json:"task_name"`
			TaskStatus  string `json:"task_status"`
			TaskType    string `json:"task_type"`
			TriggerType int    `json:"trigger_type"`
		} `json:"df"`
		GraphStatus string `json:"graph_status"`
	} `json:"res"`
}

func (a *ad) ListGraphBuildTask(ctx context.Context, graphId string, req *ListGraphBuildTaskReq) (*ListGraphBuildTaskResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/open/task/` + graphId
	u, err := url.Parse(rawURL)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to parse url: %s, err: %v", rawURL, err)
		return nil, errors.Wrap(err, "parse url failed")
	}

	var m map[string]string
	if err = json.Unmarshal(lo.T2(json.Marshal(req)).A, &m); err != nil {
		log.WithContext(ctx).Errorf("json.Unmarshal(lo.T2(json.Marshal(req)).A, &m) failed, err: %v", err)
		return nil, errors.Wrap(err, `req param marshal json failed`)
	}

	values := url.Values{}
	for k, v := range m {
		values.Add(k, v)
	}

	u.RawQuery = values.Encode()

	return httpGetDoV2[ListGraphBuildTaskResp](ctx, u, a)
}

func FirstError(errs ...error) error {
	for _, err := range errs {
		if err != nil {
			return err
		}
	}

	return nil
}
