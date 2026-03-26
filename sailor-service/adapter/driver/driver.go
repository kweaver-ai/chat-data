package driver

import (
	"github.com/google/wire"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/alg_server"
	comprehension "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/comprehension/v1"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/copilot"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/data_change_mq"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/knowledge_build"
	llm "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/recommend"
	understanding "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/understanding/v1"
	middleware_impl "github.com/kweaver-ai/chat-data/sailor-service/common/middleware/v1"
	"github.com/kweaver-ai/idrm-go-frame/core/utils/httpclient"
)

var Set = wire.NewSet(
	//http provider
	httpclient.NewMiddlewareHTTPClient,
	NewHttpServer,
	//controller
	comprehension.NewController,
	copilot.NewService,
	//data_catalog.NewConsumer,
	//interface_svc.NewConsumer,
	//data_view.NewConsumer,
	data_change_mq.NewConsumer,
	//exploration.NewController,
	recommend.NewService,
	alg_server.NewService,
	llm.NewService,
	knowledge_build.NewService,
	understanding.NewController,
	middleware_impl.NewMiddleware,
)
