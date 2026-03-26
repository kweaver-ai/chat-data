package call

import (
	"bytes"
	"context"
	"errors"
	"io"
	"net/http"
	"strconv"

	jsoniter "github.com/json-iterator/go"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest"
	"go.uber.org/zap"
)

func StatusCodeNotOK(errorMsg string, statusCode int, body []byte, code ...string) error { //code为了Upward Call透传错误码
	if statusCode == http.StatusBadRequest || statusCode == http.StatusInternalServerError || statusCode == http.StatusUnauthorized || statusCode == http.StatusForbidden {
		res := new(errorcode.ErrorCodeFullInfo)
		if err := jsoniter.Unmarshal(body, res); err != nil {
			log.Error(errorMsg+"400 error jsoniter.Unmarshal", zap.Error(err))
			if code != nil && code[0] != "" {
				return errorcode.Detail(code[0], err.Error())
			}
			return err
		}
		log.Error(errorMsg+"400 error", zap.String("code", res.Code), zap.String("description", res.Description))
		return errorcode.New(res.Code, res.Description, res.Cause, res.Solution, res.Detail, "")
	} else {
		log.Error(errorMsg+"http status error", zap.Int("status", statusCode))
		return errors.New("http status error: " + strconv.Itoa(statusCode))
	}
}

// DOWithToken 根据 context 设置 HTTP Header Authorization，发送 HTTP 请求
func DOWithToken(ctx context.Context, errorMsg string, method string, urlStr string, client *http.Client, req any) (int, []byte, error) {
	head := http.Header{}
	auth, err := middleware.AuthFromContextCompatible(ctx)
	head.Set("Authorization", auth)
	if err != nil {
		return 0, nil, err
	}
	var reqBody io.Reader
	switch method {
	case http.MethodGet:
		reqBody = nil
	case http.MethodDelete:
		reqBody = nil
	case http.MethodPost:
		jsonReq, err := jsoniter.Marshal(req)
		if err != nil {
			return 0, nil, err
		}
		reqBody = bytes.NewReader(jsonReq)
		head.Set("Content-Type", "application/json")
	}

	request, _ := http.NewRequest(method, urlStr, reqBody)
	request.Header = head

	resp, err := client.Do(request.WithContext(ctx))
	if err != nil {
		log.Error(errorMsg+"client.Do error", zap.Error(err))
		return 0, nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Error(errorMsg+"io.ReadAll", zap.Error(err))
		return 0, nil, err
	}
	return resp.StatusCode, body, nil
}

// DOWithOutToken 发送 HTTP 请求, 内部接口无token
func DOWithOutToken(ctx context.Context, errorMsg string, method string, urlStr string, client *http.Client, req any) (int, []byte, error) {
	head := http.Header{}
	var reqBody io.Reader
	switch method {
	case http.MethodGet:
		reqBody = nil
	case http.MethodDelete:
		reqBody = nil
	case http.MethodPost:
		jsonReq, err := jsoniter.Marshal(req)
		if err != nil {
			return 0, nil, err
		}
		reqBody = bytes.NewReader(jsonReq)
		head.Set("Content-Type", "application/json")
	}

	request, _ := http.NewRequest(method, urlStr, reqBody)
	request.Header = head

	resp, err := client.Do(request.WithContext(ctx))
	if err != nil {
		log.Error(errorMsg+"client.Do error", zap.Error(err))
		return 0, nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Error(errorMsg+"io.ReadAll", zap.Error(err))
		return 0, nil, err
	}
	return resp.StatusCode, body, nil
}

func Unmarshal(ctx context.Context, body []byte, drivenMsg string) error {
	var res rest.HttpError
	if err := jsoniter.Unmarshal(body, &res); err != nil {
		log.WithContext(ctx).Error(drivenMsg+" jsoniter.Unmarshal error", zap.Error(err))
		return err
	}
	log.WithContext(ctx).Errorf("%+v", res)
	return errorcode.New(res.Code, res.Description, res.Cause, res.Solution, res.Detail, "")
}
