package knowledge_build

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/models/response"
)

type GraphBuildTaskParam struct {
	GraphBuildTaskReq `param_type:"body"`
}

type GraphBuildTaskReq struct {
	GraphID  int    `json:"graph_id"`
	TaskType string `json:"task_type"`
}

func (s *Server) GraphBuildTask(ctx context.Context, req *GraphBuildTaskReq) (*response.IntIDResp, error) {
	graphTaskID, err := s.adProxy.CreateGraphTask(ctx, req.GraphID, req.TaskType)
	if err != nil {
		return nil, err
	}
	return response.NewIntIDResp(graphTaskID), nil
}
