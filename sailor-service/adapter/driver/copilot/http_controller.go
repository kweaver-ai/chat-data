package copilot

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/middleware"
	domain "github.com/kweaver-ai/chat-data/sailor-service/domain/copilot"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest/ginx"
)

// CopilotRecommendation 表单推荐
func (s *Service) CopilotRecommendCode(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendCodeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendCode(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

// CopilotRecommendation 表单推荐
func (s *Service) CopilotRecommendTable(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendTableReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendTable(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CopilotRecommendFlow(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendFlowReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendFlow(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CopilotRecommendCheckCode(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendCheckCodeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendCheckCode(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CopilotRecommendView(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendViewReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendView(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CopilotRecommendSubjectModel(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotRecommendSubjectModelReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotRecommendSubjectModel(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CopilotRecommendAssetSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotAssetSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CopilotRecommendAssetSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveDataCatalogSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CopilotCognitiveSearch(c, req, constant.DataCatalogVersion)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveDataCatalogFormViewSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveDataCatalogFormViewSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CognitiveDataCatalogFormViewSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveDataResourceSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveSearchDataResourceReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CognitiveSearchDataResource(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveResourceAnalysisSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveResourceAnalysisSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CognitiveResourceAnalysisSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveDataCatalogAnalysisSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveDataCatalogAnalysisSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.GetHeader("Authorization"), "Authorization")

	resp, err := s.uc.CognitiveDataCatalogAnalysisSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) CognitiveAnalysisSearchAnswerLike(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CognitiveAnalysisSearchAnswerLikeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	qaId := c.Param("qa_id")

	resp, err := s.uc.CognitiveAnalysisSearchAnswerLike(c, qaId, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) SSE(c *gin.Context) {

	req, err := middleware.GetReqParam[domain.SSEReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	err = s.uc.CopilotAssistantQa(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

}

func (s *Service) CopilotTestLLM(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.CopilotTestLLMReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.CopilotTestLLM(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) QaAnswerLike(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.QaAnswerLikeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//fmt.Println(c.Value(constant.UserId), "userid")

	resp, err := s.uc.QaAnswerLike(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) QaQueryHistory(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.QaQueryHistoryReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.QaQueryHistory(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) QaQueryHistoryDelete(c *gin.Context) {
	//req, err := middleware.GetReqParam[domain.QaQueryHistoryDeleteReq](c)
	//if err != nil {
	//	s.errResp(c, err)
	//	return
	//}
	qid := c.Param("qid")

	//fmt.Println(c.Value(constant.UserId), "userid")
	req := domain.QaQueryHistoryDeleteReq{qid}

	resp, err := s.uc.QaQueryHistoryDelete(c, &req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) SailorText2Sql(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.SailorText2SqlReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	//authorization := c.GetHeader("Authorization")
	c.Set("Authorization", c.GetHeader("Authorization"))

	resp, err := s.uc.SailorText2Sql(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatGetSession(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatGetSessionReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.ChatGetSession(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) SailorChat(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.SailorChatReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	err = s.uc.SailorChat(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}
}

func (s *Service) SailorChatPost(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.SailorChatPostReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	err = s.uc.SailorChatPost(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}
}

func (s *Service) ChatGetHistoryList(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatGetHistoryListReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.ChatHistoryList(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatDeleteHistory(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatDeleteHistoryReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	SessionId := c.Param("session_id")

	resp, err := s.uc.ChatDeleteHistory(c, req, SessionId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatGetHistoryDetail(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatGetHistoryDetailReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}
	sessionId := c.Param("session_id")

	resp, err := s.uc.ChatHistoryDetail(c, req, sessionId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatGetFavoriteList(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatGetFavoriteListReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.ChatFavoriteList(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatGetFavoriteDetail(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatGetFavoriteDetailReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	favoriteId := c.Param("favorite_id")

	resp, err := s.uc.ChatFavoriteDetail(c, req, favoriteId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatPostFavorite(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatPostFavoriteReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	SessionId := c.Param("session_id")

	resp, err := s.uc.ChatPostFavorite(c, req, SessionId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatPutFavorite(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatPutFavoriteReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	SessionId := c.Param("session_id")

	resp, err := s.uc.ChatPutFavorite(c, req, SessionId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatDeleteFavorite(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatDeleteFavoriteReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	favoriteId := c.Param("favorite_id")

	resp, err := s.uc.ChatDeleteFavorite(c, req, favoriteId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatQaLike(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatQaLikeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	QAId := c.Param("qa_id")

	resp, err := s.uc.ChatQaLike(c, req, QAId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatFeedback(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatFeedbackReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	QAId := c.Param("qa_id")

	resp, err := s.uc.ChatFeedback(c, req, QAId)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ChatToChat(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ChatToChatReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.ChatToChat(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) GetDataMarketConfig(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.GetDataMarketConfigReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.GetDataMarketConfig(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) UpdateDataMarketConfig(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.UpdateDataMarketConfigReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.UpdateDataMarketConfig(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) ResetDataMarketConfig(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.ResetDataMarketConfigReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.ResetDataMarketConfig(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) LogicalViewDatacategorize(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.LogicalViewDatacategorizeReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.LogicalViewDataCategorize(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) FormViewGenerateFakeSamples(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.GenerateFakeSamplesReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.FormViewGenerateFakeSamples(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) GetKgConfig(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.GetKgConfigReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.GetKgConfig(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) InitRecommendOpenSearch(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.RecommendOpenSearchReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.InitRecommendOpenSearch(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) AFAgentList(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.AFAgentListReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.GetAFAgentList(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) PutOnAFAgent(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.PutOnAFAgentReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.PutOnAFAgent(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) PullOffAFAgent(c *gin.Context) {
	req, err := middleware.GetReqParam[domain.PullOffAFAgentReq](c)
	if err != nil {
		s.errResp(c, err)
		return
	}

	resp, err := s.uc.PullOffAgent(c, req)
	if err != nil {
		s.errResp(c, err)
		return
	}

	ginx.ResOKJson(c, resp)
}

func (s *Service) errResp(c *gin.Context, err error) {
	c.Writer.WriteHeader(http.StatusBadRequest)
	ginx.ResErrJson(c, err)
}
