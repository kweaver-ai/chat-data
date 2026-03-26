package alg_server

import domain "github.com/kweaver-ai/chat-data/sailor-service/domain/alg_server"

type Service struct {
	uc domain.UseCase
}

func NewService(uc domain.UseCase) *Service {
	return &Service{uc: uc}
}
