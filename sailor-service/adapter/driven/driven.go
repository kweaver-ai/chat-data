package driven

import (
	"github.com/google/wire"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/ad_rec"
	adpAgentFactory "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/adp_agent_factory/impl"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/af_sailor_agent"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/auth_service"
	basicSearch "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/basic_search/impl"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	cp_proxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/copilot_helper"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/data_catalog"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/data_subject"
	subjectModel "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model/impl"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/assistant"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_datasource"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_network"
	hydra "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/hydra/v6"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_build"
	ad_proxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/opensearch"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/self"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/user_management"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/virtualization_engine"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	trace "github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

var Set = wire.NewSet(
	settings.GetConfig,
	trace.NewOtelHttpClient,

	opensearch.NewOpenSearchClient,
	ad_proxy.NewAD,
	cp_proxy.NewAD,
	large_language_model.NewOpenAI,
	virtualization_engine.NewVirtualizationEngine,
	configuration_center.NewConfigurationCenter,
	hydra.NewHydra,
	user_management.NewUserMgnt,

	ad_rec.NewADRec,
	//anydata_search.NewAnyDataSearchRepo,
	knowledge_build.NewMutex,
	self.NewProxy,
	knowledge_network.NewRepo,
	assistant.NewRepo,
	knowledge_datasource.NewRepo,
	auth_service.NewAuthService,
	data_catalog.NewDataCatalog,
	af_sailor_agent.NewAFSailorAgent,
	basicSearch.NewRepo,
	subjectModel.NewObjSearch,
	adpAgentFactory.NewRepo,
	data_subject.NewDriven,
)
