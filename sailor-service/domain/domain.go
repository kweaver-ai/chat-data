package domain

import (
	"github.com/google/wire"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/alg_server"
	comprehension "github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/tools"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/copilot"
	intelligence "github.com/kweaver-ai/chat-data/sailor-service/domain/intelligence/impl"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/mq"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/recommend"
	understanding "github.com/kweaver-ai/chat-data/sailor-service/domain/understanding/impl"
)

// Set is biz providers.
var Set = wire.NewSet(
	tools.NewOpenAPISource,
	tools.NewAnyDataSearch,
	tools.NewEngineSource,
	comprehension.NewBrain,
	comprehension.NewComprehensionDomain,
	recommend.NewUseCase,
	copilot.NewUseCase,
	alg_server.NewUseCase,
	intelligence.NewUseCase,
	knowledge_build.NewServer,
	knowledge_build.NewHelper,
	//mq.NewConsumer,
	mq.NewMQConsumeService,
	understanding.NewUseCase,
)
