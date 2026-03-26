package data_subject

import (
	"context"
	"fmt"
	"net/http"
	"net/url"

	"github.com/kweaver-ai/chat-data/sailor-service/common/call"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"

	jsoniter "github.com/json-iterator/go"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

type DrivenImpl struct {
	baseURL    string
	httpClient *http.Client
}

func NewDriven(httpClient *http.Client) Driven {
	cfg := settings.GetConfig().DepServicesConf
	return &DrivenImpl{
		baseURL:    util.FixSchema(cfg.DataSubjectHost),
		httpClient: httpClient,
	}
}

func (d *DrivenImpl) GetDataSubjectByPath(ctx context.Context, paths *GetDataSubjectByPathReq) (res *GetDataSubjectByPathRes, err error) {
	errorMsg := "DataViewDriven GetDataSubjectByPath "

	urlStr := fmt.Sprintf("%s/api/internal/data-subject/v1/subject-domain/paths", d.baseURL)

	log.Infof(errorMsg+" url:%s \n req : %v", urlStr, paths)

	statusCode, body, err := call.DOWithToken(ctx, errorMsg, http.MethodPost, urlStr, d.httpClient, paths)
	if err != nil {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, err.Error())
	}

	if statusCode != http.StatusOK {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, call.StatusCodeNotOK(errorMsg, statusCode, body).Error())
	}

	res = &GetDataSubjectByPathRes{}
	if err = jsoniter.Unmarshal(body, &res); err != nil {
		log.Error(errorMsg+" json.Unmarshal error", zap.Error(err))
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, err.Error())
	}
	return res, nil
}

func (d *DrivenImpl) GetDataSubjectByID(ctx context.Context, ids []string) (res *DataSubjectListObject, err error) {
	var u *url.URL
	errorMsg := "DataViewDriven GetDataSubjectByID "

	urlStr := fmt.Sprintf("%s/api/internal/data-subject/v1/subject-domain/precision", d.baseURL)

	u, err = url.Parse(urlStr)
	if err != nil {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByIDError, err.Error())
	}
	u.RawQuery = url.Values{
		"object_id": ids,
	}.Encode()
	log.Infof(errorMsg+" url:%s \n req : %v", u.String())
	statusCode, body, err := call.DOWithOutToken(ctx, errorMsg, http.MethodGet, u.String(), d.httpClient, nil)
	if err != nil {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByIDError, err.Error())
	}

	if statusCode != http.StatusOK {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByIDError, call.StatusCodeNotOK(errorMsg, statusCode, body).Error())
	}

	res = &DataSubjectListObject{}
	if err = jsoniter.Unmarshal(body, &res); err != nil {
		log.Error(errorMsg+" json.Unmarshal error", zap.Error(err))
		return nil, errorcode.Detail(errorcode.GetDataSubjectByIDError, err.Error())
	}
	return res, nil
}

func (d *DrivenImpl) GetSubjectList(ctx context.Context, parentId, subjectType string) (*DataSubjectListRes, error) {
	var res = &DataSubjectListRes{}

	// 至少获取一次，如果已经获取到的主题域数量小于总数，则继续获取
	for offset := 1; offset == 1 || len(res.Entries) < res.TotalCount; offset++ {
		pageRes, err := d.GetSubjectListWithOffset(ctx, parentId, subjectType, offset)
		if err != nil {
			return nil, err
		}
		res.Entries, res.TotalCount = append(res.Entries, pageRes.Entries...), pageRes.TotalCount
	}

	return res, nil
}

func (d *DrivenImpl) GetSubjectListWithOffset(ctx context.Context, parentId, subjectType string, offset int) (*DataSubjectListRes, error) {
	errorMsg := "DrivenDataSubject GetSubjectList "
	urlStr := fmt.Sprintf("%s/api/data-subject/v1/subject-domains?parent_id=%s&type=%s&is_all=true&need_count=true&offset=%d", d.baseURL, parentId, subjectType, offset)
	log.Infof(errorMsg+"%s", urlStr)

	statusCode, body, err := call.DOWithToken(ctx, errorMsg, http.MethodGet, urlStr, d.httpClient, nil)
	if err != nil {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, err.Error())
	}

	if statusCode != http.StatusOK {
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, call.StatusCodeNotOK(errorMsg, statusCode, body).Error())
	}

	res := &DataSubjectListRes{}
	if err = jsoniter.Unmarshal(body, &res); err != nil {
		log.Error(errorMsg+" json.Unmarshal error", zap.Error(err))
		return nil, errorcode.Detail(errorcode.GetDataSubjectByPathError, err.Error())
	}
	return res, nil
}
