package understanding

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/client"
)

type UseCase interface {
	TableCompletionTableInfo(ctx context.Context, req *TableCompletionTableInfoReq) (*TableCompletionTableInfoResp, error)
	TableCompletion(ctx context.Context, req *TableCompletionReq) (*TableCompletionResp, error)
}

// ///// 数据表格补全 只补全表格信息///////////
type TableCompletionTableInfoReq struct {
	TableCompletionTableInfoReqBody `param_type:"body"`
}

type TableCompletionTableInfoReqBody client.TableCompletionTableInfoReqBody

type TableCompletionTableInfoResp client.TableCompletionTableInfoResp

// ///// 数据表格补全 补全表格、字段信息///////////
type TableCompletionReq struct {
	TableCompletionReqBody `param_type:"body"`
}

type TableCompletionReqBody struct {
	Id            string `json:"id"`
	TechnicalName string `json:"technical_name"`
	BusinessName  string `json:"business_name"`
	Desc          string `json:"desc"`
	Database      string `json:"database"`
	Subject       string `json:"subject"`
	Columns       []struct {
		Id            string `json:"id"`
		TechnicalName string `json:"technical_name"`
		BusinessName  string `json:"business_name"`
		DataType      string `json:"data_type"`
		Comment       string `json:"comment"`
	} `json:"columns"`
	RequestType int      `json:"request_type"`
	GenFieldIds []string `json:"gen_field_ids"`
}

type TableCompletionResp struct {
	Res struct {
		TaskId string `json:"task_id"`
	} `json:"res"`
}
