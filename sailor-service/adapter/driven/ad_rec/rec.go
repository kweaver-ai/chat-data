package ad_rec

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type ADRec interface {
	RecForm(ctx context.Context, req *TableReq, userId string) (*TableResp, error)
	CheckFields(ctx context.Context, req []*CheckFieldsReq) ([]*CheckFieldsResp, error)
	RecFlowcharts(ctx context.Context, req *FlowReq, userId string) (*FlowResp, error)
	RecFieldStandardization(ctx context.Context, req *FieldStandardizationReq) (*FieldStandardizationResp, error)
}

type adRec struct {
	client  *http.Client
	baseUrl string
}

func NewADRec(client *http.Client) ADRec {
	return &adRec{
		client:  client,
		baseUrl: settings.GetConfig().DepServicesConf.AnyDataRecUrl,
	}
}

// RecForm AD搜索/推荐表单
func (a *adRec) RecForm(ctx context.Context, req *TableReq, userId string) (*TableResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//http://10.4.117.180:7000/recommend/table
	urlStr := fmt.Sprintf("%s/recommend/table", a.baseUrl)

	jsonReq, _ := json.Marshal(req)
	reader := bytes.NewReader(jsonReq)

	log.WithContext(ctx).Infof("RecForm req: %s", jsonReq)
	request, _ := http.NewRequestWithContext(ctx, http.MethodPost, urlStr, reader)

	request.Header.Set("userToken", userId)

	resp, err := a.client.Do(request)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Desc(errorcode.ADUrlError)
	}

	// 延时关闭
	defer resp.Body.Close()

	// 返回的结果resp.Body
	body, err := io.ReadAll(resp.Body)
	log.WithContext(ctx).Infof("RecForm resp: %s", body)
	//fmt.Println(body)
	if resp.StatusCode != http.StatusOK {
		if resp.StatusCode == http.StatusNotFound {
			return nil, errorcode.Desc(errorcode.ADUrlError)
		} else {
			return nil, errorcode.Desc(errorcode.ModelTaskCenterProjectNotFound)
		}
	}

	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err.Error())
	}

	res := new(TableResp)
	// 把请求到的数据Unmarshal到res中
	err = json.Unmarshal(body, res)
	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.ADDataError, err.Error())
	}

	return res, nil
}

func (a *adRec) CheckFields(ctx context.Context, req []*CheckFieldsReq) ([]*CheckFieldsResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//http://10.2.196.57:7000/check/code
	urlStr := fmt.Sprintf("%s/check/code", a.baseUrl)

	jsonReq, err := json.Marshal(req)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Desc(errorcode.ReportJsonMarshalError)
	}
	reader := bytes.NewReader(jsonReq)

	log.WithContext(ctx).Infof("CheckFields req: %s", jsonReq)
	request, _ := http.NewRequestWithContext(ctx, http.MethodPost, urlStr, reader)
	resp, err := a.client.Do(request)

	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Desc(errorcode.ADUrlError)
	}

	// 延时关闭
	defer resp.Body.Close()

	// 返回的结果resp.Body
	body, err := io.ReadAll(resp.Body)
	log.WithContext(ctx).Infof("CheckFields resp: %s", body)
	//fmt.Println(body)
	if resp.StatusCode != http.StatusOK {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		if resp.StatusCode == http.StatusNotFound {
			return nil, errorcode.Desc(errorcode.ADUrlError)
		} else {
			return nil, errorcode.Desc(errorcode.ADDataError)
		}
	}

	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err.Error())
	}
	res := make([]*CheckFieldsResp, 0)
	// 把请求到的数据Unmarshal到res中
	err = json.Unmarshal(body, &res)
	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.ADDataError, err.Error())
	}

	return res, nil
}

// RecFlowcharts AD搜索/推荐流程
func (a *adRec) RecFlowcharts(ctx context.Context, req *FlowReq, userId string) (*FlowResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//http://10.4.117.180:7000/recommend/flow
	urlStr := fmt.Sprintf("%s/recommend/flow", a.baseUrl)

	jsonReq, _ := json.Marshal(req)
	reader := bytes.NewReader(jsonReq)

	log.WithContext(ctx).Infof("RecFlowcharts req: %s", jsonReq)
	request, _ := http.NewRequestWithContext(ctx, http.MethodPost, urlStr, reader)

	request.Header.Set("userToken", userId)

	resp, err := a.client.Do(request)

	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, err
	}

	// 延时关闭
	defer resp.Body.Close()

	// 返回的结果resp.Body
	body, err := io.ReadAll(resp.Body)
	log.WithContext(ctx).Infof("RecFlowcharts resp: %s", body)
	//fmt.Println(body)
	if resp.StatusCode != http.StatusOK {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		if resp.StatusCode == http.StatusNotFound {
			// todo err
			return nil, err
		} else {
			return nil, errorcode.Desc(errorcode.ADUrlError)
		}
	}

	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err.Error())
	}

	res := new(FlowResp)
	// 把请求到的数据Unmarshal到res中
	err = json.Unmarshal(body, res)
	if err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", request.URL.String(), jsonReq, body)
		log.WithContext(ctx).Error(err.Error())
		// todo err
		return nil, errorcode.Detail(errorcode.PublicInternalError, err.Error())
	}

	return res, nil
}

func (a *adRec) RecFieldStandardization(ctx context.Context, req *FieldStandardizationReq) (*FieldStandardizationResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	url := fmt.Sprintf("%s/recommend/code", a.baseUrl)

	b, err := json.Marshal(req)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Desc(errorcode.ReportJsonMarshalError)
	}

	log.WithContext(ctx).Infof("RecFieldStandardization req: %s", b)
	adReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(b))
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	adResp, err := a.client.Do(adReq)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Desc(errorcode.ADUrlError)
	}
	defer func() {
		_ = adResp.Body.Close()
	}()

	respData, err := io.ReadAll(adResp.Body)
	if err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.ADDataError, err.Error())
	}

	if adResp.StatusCode != http.StatusOK {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", adReq.URL.String(), b, respData)
		if adResp.StatusCode == http.StatusNotFound {
			return nil, errorcode.Desc(errorcode.ADUrlError)
		} else {
			return nil, errorcode.Desc(errorcode.ADDataError)
		}
	}

	log.WithContext(ctx).Infof("RecFieldStandardization resp: %s", respData)
	var resp FieldStandardizationResp
	if err = json.Unmarshal(respData, &resp); err != nil {
		log.WithContext(ctx).Errorf("url: %s\nreq: %s\nresp:%s", adReq.URL.String(), b, respData)
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.ADDataError, err.Error())
	}

	return &resp, nil
}
