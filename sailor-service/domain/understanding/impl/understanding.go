package impl

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/copilot_helper"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/understanding"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
)

type useCase struct {
	afSailor copilot_helper.AD
}

func NewUseCase(afSailor copilot_helper.AD) understanding.UseCase {
	return &useCase{
		afSailor: afSailor,
	}
}

func GetUserInfo(ctx context.Context) *models.UserInfo {
	if val := ctx.Value(constant.UserInfoContextKey); val != nil {
		if ret, ok := val.(*models.UserInfo); ok {
			return ret
		}
	}
	return nil
}

func (u *useCase) TableCompletionTableInfo(ctx context.Context, req *understanding.TableCompletionTableInfoReq) (*understanding.TableCompletionTableInfoResp, error) {
	var err error
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()

	// 获取appid
	//appid, err := u.afSailor.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}
	userInfo := GetUserInfo(ctx)

	//包装参数
	args := make(map[string]any)
	args["query"] = req
	args["user_id"] = userInfo.ID

	//请求
	adResp, err := u.afSailor.SailorTableCompletionTableInfoEngine(ctx, args)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp understanding.TableCompletionTableInfoResp
	if err := util.CopyUseJson(&resp, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) TableCompletion(ctx context.Context, req *understanding.TableCompletionReq) (*understanding.TableCompletionResp, error) {
	var err error
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()

	// 获取appid
	//appid, err := u.afSailor.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}
	userInfo := GetUserInfo(ctx)

	//包装参数
	args := make(map[string]any)
	args["query"] = req
	args["user_id"] = userInfo.ID

	//请求
	adResp, err := u.afSailor.SailorTableCompletionEngine(ctx, args)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp understanding.TableCompletionResp
	if err := util.CopyUseJson(&resp, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}
