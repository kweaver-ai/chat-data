package driver

import (
	"net/http"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/alg_server"
	comprehension "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/comprehension/v1"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/copilot"
	understanding "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/understanding/v1"
	kbDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"

	"github.com/gin-gonic/gin"
	"github.com/google/wire"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/knowledge_build"
	llm "github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/large_language_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/recommend"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	kgDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/alg_server"
	copilotDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/copilot"
	aiDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/intelligence"
	recommendDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/recommend"
	udDomain "github.com/kweaver-ai/chat-data/sailor-service/domain/understanding"
)

var _ IRouter = (*Router)(nil)

var RouterSet = wire.NewSet(wire.Struct(new(Router), "*"), wire.Bind(new(IRouter), new(*Router)))

type IRouter interface {
	Register(r *gin.Engine) error
}

type Router struct {
	Middleware                  middleware.Middleware
	DataComprehensionController *comprehension.Controller
	RecommendSrv                *recommend.Service
	KgSrv                       *alg_server.Service
	LLM                         *llm.Service
	KNBuildSrv                  *knowledge_build.Service
	//DataExplorationController   *exploration.Controller
	CopilotSrv                  *copilot.Service
	DataUnderstandingController *understanding.Controller
}

func (r *Router) Register(engine *gin.Engine) error {
	r.registerApi(engine)
	return nil
}

func Cors() gin.HandlerFunc {
	return func(c *gin.Context) {
		method := c.Request.Method
		origin := c.Request.Header.Get("Origin")
		if origin != "" {
			c.Header("Access-Control-Allow-Origin", "*") // 可将将 * 替换为指定的域名
			c.Header("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE, UPDATE")
			c.Header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization")
			c.Header("Access-Control-Expose-Headers", "Content-Length, Access-Control-Allow-Origin, Access-Control-Allow-Headers, Cache-Control, Content-Language, Content-Type")
			c.Header("Access-Control-Allow-Credentials", "true")
		}
		if method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
		}
		c.Next()
	}
}

func (r *Router) registerApi(engine *gin.Engine) {
	engine.Use(Cors())
	//licenseValidator := r.MWCommon.CreateProductAuthorizationValidator(auth.ANYFABRIC_ENTERPRISE2, auth.COGNITIVE_ASSISTANT, 30, nil)
	//anydataLicenseValidator := r.MWCommon.CreateProductAuthorizationValidator(auth.ANYFABRIC_ENTERPRISE2, auth.ANYDATA_BASIC_SUITE, 30, nil)
	// external
	{
		cognitiveAssistantRouter := engine.Group("/api/af-sailor-service/v1")

		comprehensionRouter := cognitiveAssistantRouter.Group("/comprehension")
		{
			comprehensionRouter.GET("", r.DataComprehensionController.AI)
			comprehensionRouter.GET("/config", r.DataComprehensionController.DimensionConfigs)
			comprehensionRouter.PUT("/config", r.DataComprehensionController.SetAIConfig)
		}

		knRouter := cognitiveAssistantRouter.Group("/tools/knowledge-network")
		{
			knRouter.GET("/graph/iframe", middleware.GinReqParamValidator[kgDomain.IframeReq], r.KgSrv.Iframe)
			knRouter.POST("/graph/analysis", middleware.GinReqParamValidator[kgDomain.GraphAnalysisReq], r.KgSrv.GraphAnalysis)

			knRouter.GET("/list", middleware.GinReqParamValidator[recommendDomain.ListKnowledgeNetworkReq], r.Middleware.TokenInterception(), r.RecommendSrv.ListKnowledgeNetwork)
			knRouter.GET("/graph/list", middleware.GinReqParamValidator[recommendDomain.ListKnowledgeGraphReq], r.Middleware.TokenInterception(), r.RecommendSrv.ListKnowledgeGraph)
			knRouter.GET("/lexicon/list", middleware.GinReqParamValidator[recommendDomain.ListKnowledgeLexiconReq], r.Middleware.TokenInterception(), r.RecommendSrv.ListKnowledgeLexicon)
		}

		llmRouter := cognitiveAssistantRouter.Group("/tools/large_language_model")
		{
			llmRouter.GET("/agent_log", middleware.GinReqParamValidator[aiDomain.AgentConversationLogListReq], r.LLM.AgentConversationLogList)
		}

		copilotQaRouter := cognitiveAssistantRouter.Group("/assistant")
		{
			//copilotRouter.POST("/prompt", middleware.GinReqParamValidator[copilotDomain.TablePromptReq], r.CopilotSrv.TablePrompt)
			//copilotQaRouter.POST("/qa", middleware.GinReqParamValidator[copilotDomain.CopilotAssistantQaReq], r.CopilotSrv.CopilotRecommendCode)
			copilotQaRouter.GET("/qa", middleware.GinReqParamValidator[copilotDomain.SSEReq], r.Middleware.TokenInterception(), r.CopilotSrv.SSE)
			copilotQaRouter.GET("/test-llm", middleware.GinReqParamValidator[copilotDomain.CopilotTestLLMReq], r.CopilotSrv.CopilotTestLLM)
			copilotQaRouter.POST("/answer-like", middleware.GinReqParamValidator[copilotDomain.QaAnswerLikeReq], r.Middleware.TokenInterception(), r.CopilotSrv.QaAnswerLike)
			copilotQaRouter.GET("/query/history", middleware.GinReqParamValidator[copilotDomain.QaQueryHistoryReq], r.Middleware.TokenInterception(), r.CopilotSrv.QaQueryHistory)
			copilotQaRouter.DELETE("/query/history/:qid", middleware.GinReqParamValidator[copilotDomain.QaQueryHistoryDeleteReq], r.Middleware.TokenInterception(), r.CopilotSrv.QaQueryHistoryDelete)
			copilotQaRouter.POST("/utils/text2sql", middleware.GinReqParamValidator[copilotDomain.SailorText2SqlReq], r.Middleware.TokenInterception(), r.CopilotSrv.SailorText2Sql)

			copilotQaRouter.GET("/chat/session_id", middleware.GinReqParamValidator[copilotDomain.ChatGetSessionReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatGetSession) // 获取chat session id
			copilotQaRouter.GET("/chat", middleware.GinReqParamValidator[copilotDomain.SailorChatReq], r.Middleware.TokenInterception(), r.CopilotSrv.SailorChat)
			copilotQaRouter.POST("/chat", middleware.GinReqParamValidator[copilotDomain.SailorChatPostReq], r.Middleware.TokenInterception(), r.CopilotSrv.SailorChatPost)                                // 多轮问答
			copilotQaRouter.GET("/chat/history", middleware.GinReqParamValidator[copilotDomain.ChatGetHistoryListReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatGetHistoryList)                 // 查看历史列表
			copilotQaRouter.GET("/chat/history/:session_id", middleware.GinReqParamValidator[copilotDomain.ChatGetHistoryDetailReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatGetHistoryDetail) // 获取历史记录详情
			copilotQaRouter.DELETE("/chat/history/:session_id", middleware.GinReqParamValidator[copilotDomain.ChatDeleteHistoryReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatDeleteHistory)
			copilotQaRouter.GET("/chat/favorite", middleware.GinReqParamValidator[copilotDomain.ChatGetFavoriteListReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatGetFavoriteList) //
			copilotQaRouter.GET("/chat/favorite/:favorite_id", middleware.GinReqParamValidator[copilotDomain.ChatGetFavoriteDetailReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatGetFavoriteDetail)
			copilotQaRouter.POST("/chat/:session_id/favorite", middleware.GinReqParamValidator[copilotDomain.ChatPostFavoriteReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatPostFavorite)
			copilotQaRouter.PUT("/chat/:session_id/favorite", middleware.GinReqParamValidator[copilotDomain.ChatPutFavoriteReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatPutFavorite)
			copilotQaRouter.DELETE("/chat/favorite/:favorite_id", middleware.GinReqParamValidator[copilotDomain.ChatDeleteFavoriteReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatDeleteFavorite)
			copilotQaRouter.PUT("/chat/qa/:qa_id/like", middleware.GinReqParamValidator[copilotDomain.ChatQaLikeReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatQaLike)          // 点赞 点踩
			copilotQaRouter.POST("/chat/qa/:qa_id/feedback", middleware.GinReqParamValidator[copilotDomain.ChatFeedbackReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatFeedback) // 反馈不满意原因
			copilotQaRouter.PUT("/chat/tochat", middleware.GinReqParamValidator[copilotDomain.ChatToChatReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatToChat)

			//copilotQaRouter.PUT("/form_view/generate_fake_samples", middleware.GinReqParamValidator[copilotDomain.ChatToChatReq], r.Middleware.TokenInterception(), r.CopilotSrv.ChatToChat)
			copilotQaRouter.GET("/data-market/configs", middleware.GinReqParamValidator[copilotDomain.GetDataMarketConfigReq], r.Middleware.TokenInterception(), r.CopilotSrv.GetDataMarketConfig)
			copilotQaRouter.POST("/data-market/configs", middleware.GinReqParamValidator[copilotDomain.UpdateDataMarketConfigReq], r.Middleware.TokenInterception(), r.CopilotSrv.UpdateDataMarketConfig)
			copilotQaRouter.PUT("/data-market/configs/reset", middleware.GinReqParamValidator[copilotDomain.ResetDataMarketConfigReq], r.Middleware.TokenInterception(), r.CopilotSrv.ResetDataMarketConfig)

			copilotQaRouter.POST("/agent/list", middleware.GinReqParamValidator[copilotDomain.AFAgentListReq], r.Middleware.TokenInterception(), r.CopilotSrv.AFAgentList)
			copilotQaRouter.PUT("/agent/put-on", middleware.GinReqParamValidator[copilotDomain.PutOnAFAgentReq], r.Middleware.TokenInterception(), r.CopilotSrv.PutOnAFAgent)
			copilotQaRouter.PUT("/agent/pull-off", middleware.GinReqParamValidator[copilotDomain.PullOffAFAgentReq], r.Middleware.TokenInterception(), r.CopilotSrv.PullOffAFAgent)
		}

		logicalRouter := cognitiveAssistantRouter.Group("/logical-view")
		{
			logicalRouter.POST("/recommend/metadata-view", middleware.GinReqParamValidator[recommendDomain.MetaDataViewRecommendReq], r.Middleware.TokenInterception(), r.RecommendSrv.MetaDataViewRecommend)
		}

		FormViewRouter := cognitiveAssistantRouter.Group("/form-view")
		{
			FormViewRouter.POST("/generate_fake_samples", middleware.GinReqParamValidator[copilotDomain.GenerateFakeSamplesReq], r.Middleware.TokenInterception(), r.CopilotSrv.FormViewGenerateFakeSamples)
		}

		cognitiveRouter := cognitiveAssistantRouter.Group("/cognitive")
		{
			cognitiveRouter.POST("/datacatalog/search", middleware.GinReqParamValidator[copilotDomain.CognitiveSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveDataCatalogSearch)
			cognitiveRouter.POST("/resource/search", middleware.GinReqParamValidator[copilotDomain.CognitiveSearchDataResourceReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveDataResourceSearch)
			cognitiveRouter.POST("/datacatalog/formview_search", middleware.GinReqParamValidator[copilotDomain.CognitiveDataCatalogFormViewSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveDataCatalogFormViewSearch)
			//cognitiveRouter.POST("/resource/search", middleware.GinReqParamValidator[copilotDomain.CognitiveSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveDataResourceSearch)
			cognitiveRouter.POST("/resource/formview_analysis_search", middleware.GinReqParamValidator[copilotDomain.CognitiveResourceAnalysisSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveResourceAnalysisSearch)
			cognitiveRouter.POST("/data_catalog/formview_analysis_search", middleware.GinReqParamValidator[copilotDomain.CognitiveDataCatalogAnalysisSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveDataCatalogAnalysisSearch)
			cognitiveRouter.PUT("/search/qa/:qa_id/like", middleware.GinReqParamValidator[copilotDomain.CognitiveAnalysisSearchAnswerLikeReq], r.Middleware.TokenInterception(), r.CopilotSrv.CognitiveAnalysisSearchAnswerLike)
		}

		cogRecommendRouter := cognitiveAssistantRouter.Group("/recommend")
		{
			cogRecommendRouter.POST("/subject_model", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendSubjectModelReq], r.CopilotSrv.CopilotRecommendSubjectModel)
		}
	}

	// internal
	{
		cognitiveAssistantRouter := engine.Group("/api/internal/af-sailor-service/v1", middleware.InternalAuth())

		//recommendRouter := cognitiveAssistantRouter.Group("/recommend")
		//{
		//	recommendRouter.POST("/table_bk", middleware.GinReqParamValidator[recommendDomain.TableRecommendationReq], r.RecommendSrv.TableRecommendation)
		//	recommendRouter.POST("/flow_bk", middleware.GinReqParamValidator[recommendDomain.FlowRecommendationReq], r.RecommendSrv.FlowRecommendation)
		//	recommendRouter.POST("/code_bk", middleware.GinReqParamValidator[recommendDomain.FieldStandardRecommendationReq], r.RecommendSrv.FieldStandardRecommendation)
		//	recommendRouter.POST("/check/code_bk", middleware.GinReqParamValidator[recommendDomain.CheckCodeReq], r.RecommendSrv.CheckCode)
		//	recommendRouter.POST("/asset/search_bk", middleware.GinReqParamValidator[recommendDomain.AssetSearchReq], r.RecommendSrv.AssetSearch)
		//}

		copilotRouter := cognitiveAssistantRouter.Group("/recommend")
		{
			//copilotRouter.POST("/prompt", middleware.GinReqParamValidator[copilotDomain.TablePromptReq], r.CopilotSrv.TablePrompt)
			copilotRouter.POST("/code", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendCodeReq], r.CopilotSrv.CopilotRecommendCode)
			copilotRouter.POST("/table", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendTableReq], r.CopilotSrv.CopilotRecommendTable)
			copilotRouter.POST("/flow", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendFlowReq], r.CopilotSrv.CopilotRecommendFlow)
			copilotRouter.POST("/check/code", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendCheckCodeReq], r.CopilotSrv.CopilotRecommendCheckCode)
			copilotRouter.POST("/view", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendViewReq], r.CopilotSrv.CopilotRecommendView)

			//copilotRouter.POST("/subject/code", middleware.GinReqParamValidator[copilotDomain.CopilotRecommendSubjectCodeReq], r.CopilotSrv.CopilotRecommendSubjectCode)
			//copilotRouter.POST("/asset/search", middleware.GinReqParamValidator[copilotDomain.CopilotAssetSearchReq], r.Middleware.TokenInterception(), r.CopilotSrv.CopilotRecommendAssetSearch)
			// copilotRouter.GET("", r.CopilotController.DimensionConfigs)
			// copilotRouter.POST("", middleware.GinReqParamValidator[copilotDomain.CPromptReq], r.CopilotController.CPrompt)
		}
		// 逻辑视图算法
		interLogicalRouter := cognitiveAssistantRouter.Group("/logical-view")
		{
			interLogicalRouter.POST("/data-categorize", middleware.GinReqParamValidator[copilotDomain.LogicalViewDatacategorizeReq], r.CopilotSrv.LogicalViewDatacategorize)
		}

		kgRouter := cognitiveAssistantRouter.Group("/tools/knowledge-network/alg-server")
		{
			kgRouter.POST("/graph-search/kgs/full-text", middleware.GinReqParamValidator[kgDomain.FullTextReq], r.KgSrv.FullText)
			kgRouter.POST("/explore/kgs/neighbors", middleware.GinReqParamValidator[kgDomain.NeighborsReq], r.KgSrv.Neighbors)
		}

		llmRouter := cognitiveAssistantRouter.Group("/tools/large_language_model")
		{
			llmRouter.POST("/sample_data", middleware.GinReqParamValidator[aiDomain.SampleDataReq], r.LLM.SampleData)
			llmRouter.GET("/agent_log", middleware.GinReqParamValidator[aiDomain.AgentConversationLogListReq], r.LLM.AgentConversationLogList)
		}
		{
			cognitiveAssistantRouter.POST("/knowledge-build/model/graph", middleware.GinReqParamValidator[kbDomain.ModelDetailParam], r.KNBuildSrv.UpdateSchema)            //将图模型导入到某个图谱
			cognitiveAssistantRouter.DELETE("/knowledge-build/model/graph/:graph_id", middleware.GinReqParamValidator[kbDomain.ModelDeleteParam], r.KNBuildSrv.DeleteGraph) //删除某个图谱
			cognitiveAssistantRouter.POST("/knowledge-build/model/graph/task", middleware.GinReqParamValidator[kbDomain.GraphBuildTaskParam], r.KNBuildSrv.GraphBuildTask)  //删除图谱中某个图模型分组
		}
		cognitiveAssistantRouter.POST("/knowledge-build/reset", r.KNBuildSrv.Reset)
		cognitiveAssistantRouter.POST("/knowledge-build/re-election", r.KNBuildSrv.ReElection)
		cognitiveAssistantRouter.GET("/knowledge/configs", middleware.GinReqParamValidator[copilotDomain.GetKgConfigReq], r.CopilotSrv.GetKgConfig)
		cognitiveAssistantRouter.GET("/recommend/initialization", middleware.GinReqParamValidator[copilotDomain.RecommendOpenSearchReq], r.CopilotSrv.InitRecommendOpenSearch)

		understandRouter := cognitiveAssistantRouter.Group("/understanding")
		{
			understandRouter.POST("/table/completion", middleware.GinReqParamValidator[udDomain.TableCompletionReq], r.Middleware.TokenInterception(), r.DataUnderstandingController.TableCompletion)
			understandRouter.POST("/table/completion/table_info", middleware.GinReqParamValidator[udDomain.TableCompletionTableInfoReq], r.Middleware.TokenInterception(), r.DataUnderstandingController.TableCompletionTableInfo)
		}
	}
}
