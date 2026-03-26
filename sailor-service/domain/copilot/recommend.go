package copilot

import (
	"bufio"
	"bytes"
	"context"
	"crypto/md5"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/ad_rec"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/adp_agent_factory"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/af_sailor_agent"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/auth_service"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/basic_search"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/copilot_helper"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/data_catalog"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/data_subject"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/assistant"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_datasource"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/pkg/errors"
	"go.uber.org/zap"

	// "devops.xxx.cn/AISHUDevOps/AnyFabric/_git/cognitive-assistant/common/settings"
	"encoding/json"
	"fmt"

	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
	// "go.uber.org/zap"
	// "strconv"
)

const (
	HISTORYMAXLEN int = 5
	MAXLIMITNUM       = 200
	MAXLIMITNUM2      = 200
)

type useCase struct {
	adProxy         copilot_helper.AD
	afSailorAgent   af_sailor_agent.AFSailorAgent
	adCfgHelper     knowledge_build.Helper
	data            *db.Data
	qaRepo          assistant.Repo
	authService     auth_service.AuthService
	configCenter    configuration_center.DrivenConfigurationCenter
	dataCatalog     data_catalog.DataCatalog
	dataSubject     data_subject.Driven
	basicSearch     basic_search.Repo
	dbRepo          knowledge_datasource.Repo
	esClient        es_subject_model.ESSubjectModel
	adpAgentFactory adp_agent_factory.Repo
}

func NewUseCase(adProxy copilot_helper.AD, afSailorAgent af_sailor_agent.AFSailorAgent, cfgHelper knowledge_build.Helper, data *db.Data, repo assistant.Repo, authService auth_service.AuthService, configCenter configuration_center.DrivenConfigurationCenter, dataCatalog data_catalog.DataCatalog, dataSubject data_subject.Driven, basicSearch basic_search.Repo, dbRepo knowledge_datasource.Repo, esClient es_subject_model.ESSubjectModel, adpAgentFactory adp_agent_factory.Repo) UseCase {
	return &useCase{
		adProxy:         adProxy,
		afSailorAgent:   afSailorAgent,
		adCfgHelper:     cfgHelper,
		data:            data,
		qaRepo:          repo,
		authService:     authService,
		configCenter:    configCenter,
		dataCatalog:     dataCatalog,
		dataSubject:     dataSubject,
		basicSearch:     basicSearch,
		dbRepo:          dbRepo,
		esClient:        esClient,
		adpAgentFactory: adpAgentFactory,
	}
}

func (u *useCase) getGraphId(ctx context.Context, cfgId string) (string, error) {
	srvCfgId, err := u.adCfgHelper.GetGraphId(ctx, cfgId)
	if err != nil {
		return "", err
	}
	if len(srvCfgId) < 1 {
		return "", nil
	}
	return srvCfgId, nil
}

func (u *useCase) CopilotRecommendCode(ctx context.Context, req *CopilotRecommendCodeReq) (*CopilotRecommendCodeResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.CPRecommendCodeReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	//// 获取graphId
	//graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	//if err != nil {
	//	return nil, err
	//}
	//// 获取appid
	//appid, err := u.adProxy.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}

	//包装参数
	args := make(map[string]any)
	args["query"] = adReq
	//args["graph_id"] = graphId //"2914"
	//args["appid"] = appid      // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpRecommendCodeEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	var dag client.CpRecommendCodeDAG
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	//处理返回值
	var resp CopilotRecommendCodeResp
	if err := util.CopyUseJson(&resp, &dag.Res.Answers); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	//标准推荐的返回字段类型被改了，下面的逻辑转换下类型,
	for i := 0; i < len(resp.TableFields); i++ {
		for j := 0; j < len(resp.TableFields[i].RecStds); j++ {
			code, _ := strconv.ParseInt(fmt.Sprintf("%s", resp.TableFields[i].RecStds[j].StdCode), 10, 64)
			resp.TableFields[i].RecStds[j].StdCode = code
		}
	}

	return &resp, nil
}

func (u *useCase) CopilotRecommendTable(ctx context.Context, req *CopilotRecommendTableReq) (*CopilotRecommendTableResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	// req.Table.ResourceTag = req.Table.ResourceTag[0]
	// req.Table.ID = "1"

	var adReq ad_rec.CPRecommendTableReq

	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	if adReq.InfoSystem == nil {
		adReq.InfoSystem = []ad_rec.InfoSystemItem{}
	}
	//adReq.Key = ""
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	// 获取graphId
	graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)
	args["af_query"] = adReq
	args["graph_id"] = graphId //"2914"
	args["appid"] = appid      // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpRecommendTableEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	var dag client.CpRecommendTableDAG
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	//处理返回值
	var resp CopilotRecommendTableResp
	if err := util.CopyUseJson(&resp, &dag.Res.Answers); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) CopilotRecommendFlow(ctx context.Context, req *CopilotRecommendFlowReq) (*CopilotRecommendFlowResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.CPRecommendFlowReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	// 获取graphId
	graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	if err != nil {
		return nil, err
	}

	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)
	args["af_query"] = adReq
	args["graph_id"] = graphId //"2914"
	args["appid"] = appid      // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpRecommendFlowEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	var dag client.CpRecommendFlowDAG
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	//处理返回值
	var resp CopilotRecommendFlowResp
	if err := util.CopyUseJson(&resp, &dag.Res.Answers); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) CopilotRecommendCheckCode(ctx context.Context, req *CopilotRecommendCheckCodeReq) (*CopilotRecommendCheckCodeResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.CPRecommendCheckCodeReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	//// 获取graphId
	//graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	//if err != nil {
	//	return nil, err
	//}
	//// 获取appid
	//appid, err := u.adProxy.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}

	//包装参数
	args := make(map[string]any)
	args["check_af_query"] = adReq.Data
	//args["graph_id"] = graphId //"2914"
	//args["appid"] = appid      // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpRecommendCheckCodeEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	var dag client.CpRecommendCheckCodeDAG
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//处理返回值
	var resp CopilotRecommendCheckCodeResp
	if err := util.CopyUseJson(&resp.Data, &dag.Res.Answers); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) CopilotRecommendSubjectModel(ctx context.Context, req *CopilotRecommendSubjectModelReq) (*CopilotRecommendSubjectModelResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//包装参数
	args := make(map[string]any)
	args["query"] = req.Query

	//请求
	adResp, err := u.adProxy.RecommendSubjectModelEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	//处理返回值
	var resp CopilotRecommendSubjectModelResp
	if err := util.CopyUseJson(&resp.Data, &adResp.Data); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) CopilotRecommendView(ctx context.Context, req *CopilotRecommendViewReq) (*CopilotRecommendViewResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.CPRecommendViewReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	// 获取graphId
	//graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId)
	//if err != nil {
	//	return nil, err
	//}
	//// 获取appid
	//appid, err := u.adProxy.GetAppId(ctx)
	//if err != nil {
	//	return nil, err
	//}

	//包装参数
	args := make(map[string]any)
	args["query"] = adReq
	//args["graph_id"] = graphId //"2914"
	//args["appid"] = appid      // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpRecommendViewEngine(ctx, &args)
	if err != nil {
		return nil, err
	}

	var dag client.CpRecommendViewDAG
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//处理返回值
	var resp CopilotRecommendViewResp
	if err := util.CopyUseJson(&resp, &dag); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) CopilotTestLLM(ctx context.Context, req *CopilotTestLLMReq) (*CopilotTestLLMResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var adReq ad_rec.CPTestLLMReq
	if err := util.CopyUseJson(&adReq, req); err != nil {
		log.WithContext(ctx).Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}
	//log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	//fmt.Println(ctx.Value(constant.UserId), "userid")
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)
	args["appid"] = appid // "NlS6f-QKGPFjTH7zxV7"

	//请求
	adResp, err := u.adProxy.CpTestLLMEngine(ctx, args)
	if err != nil {
		return nil, err
	}

	var dag client.CpTestLLM
	if err = util.CopyUseJson(&dag, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	//处理返回值
	var resp CopilotTestLLMResp
	if err := util.CopyUseJson(&resp, &dag); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

func (u *useCase) QaAnswerLike(ctx context.Context, req *QaAnswerLikeReq) (*QaAnswerLikeResp, error) {
	var err error
	userid := ctx.Value(constant.UserId)
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	// 记录用户对答案是否喜欢
	log.WithContext(ctx).Infof("\nuser_id:%s answer_id:%s like_status:%s", userid, req.AnswerId, req.AnswerLike)
	var resp QaAnswerLikeResp

	resp.Res.Status = "success"

	return &resp, nil
}

func MD5(str string) string {
	data := []byte(str) //切片
	has := md5.Sum(data)
	md5str := fmt.Sprintf("%x", has) //将[]byte转成16进制
	return md5str
}

func (this QaRecordList) Len() int {
	return len(this)
}
func (this QaRecordList) Less(i, j int) bool {
	return this[i].Qdatetime > this[j].Qdatetime
}
func (this QaRecordList) Swap(i, j int) {
	this[i], this[j] = this[j], this[i]
}

func (u *useCase) QaQueryHistory(ctx context.Context, req *QaQueryHistoryReq) (*QaQueryHistoryResp, error) {
	var err error
	userid := fmt.Sprintf("%v", ctx.Value(constant.UserId))
	//userid := "xxxx"
	searchWord := req.SearchWord
	//if searchWord == nil {
	//	searchWord = ""
	//}
	log.Info("QaQueryHistory:" + searchWord)

	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp QaQueryHistoryResp
	resp.Res = []QaRecordOut{}

	queryHistory, err := u.qaRepo.GetQaWordHistory(ctx, userid)
	if queryHistory == nil {

		return &resp, nil
	}

	//data := `{"person_name":"xiaoming","person_age":18}`
	qalist := QaList{}
	qalistStr := queryHistory.QWordList
	err = json.Unmarshal([]byte(*qalistStr), &qalist)
	if err != nil {
		fmt.Println("unmarshal failed!")
		return nil, err
	}
	for _, qa := range qalist.QaRecords {
		if len(searchWord) > 0 {
			if strings.Contains(qa.Qword, searchWord) {
				highLight := strings.Replace(qa.Qword, searchWord, "<em>"+searchWord+"</em>", -1)
				resp.Res = append(resp.Res, QaRecordOut{qa.Qid, qa.Qword, highLight, qa.Qdatetime})
			}
		} else {
			highLight := ""
			resp.Res = append(resp.Res, QaRecordOut{qa.Qid, qa.Qword, highLight, qa.Qdatetime})
		}

	}

	return &resp, nil
}

func (u *useCase) QaQueryHistoryDelete(ctx context.Context, req *QaQueryHistoryDeleteReq) (*QaQueryHistoryDeleteResp, error) {
	var err error
	//userid := fmt.Sprintf("%v", ctx.Value(constant.UserId))
	userid := fmt.Sprintf("%v", ctx.Value(constant.UserId))

	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	var resp QaQueryHistoryDeleteResp
	queryHistory, err := u.qaRepo.GetQaWordHistory(ctx, userid)
	if queryHistory == nil {
		resp.Res.Status = "failure"
		return &resp, nil
	}

	qalist := QaList{}
	//data := `{"person_name":"xiaoming","person_age":18}`
	qalistStr := queryHistory.QWordList
	err = json.Unmarshal([]byte(*qalistStr), &qalist)
	if err != nil {
		fmt.Println("unmarshal failed!")
		return nil, err
	}
	d_index := -1
	for i, item := range qalist.QaRecords {
		if item.Qid == req.Qid {
			d_index = i
			break
		}
	}

	if d_index != -1 {
		qalist.QaRecords = append(qalist.QaRecords[:d_index], qalist.QaRecords[d_index+1:]...)
		qlistStr, er := json.Marshal(qalist)
		if er != nil {
			//fmt.Println("marshal failed!", err)
			return nil, er
		}
		u.qaRepo.UpdateQaWordHistory(ctx, userid, string(qlistStr))
		resp.Res.Status = "success"
	} else {
		resp.Res.Status = "failure"
	}

	//resp.Res = qalist.QaRecords

	return &resp, nil
}

func (u *useCase) SailorText2Sql(ctx context.Context, req *SailorText2SqlReq) (*SailorText2SqlResp, error) {
	var err error
	authorization := fmt.Sprintf("%v", ctx.Value("Authorization"))
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)
	args["user"] = "admin"
	args["appid"] = appid // "NlS6f-QKGPFjTH7zxV7"
	args["query"] = req.Query
	args["search"] = req.Search

	//请求
	adResp, err := u.adProxy.CpText2SqlEngine(ctx, args, authorization)
	if err != nil {
		return nil, err
	}

	log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(args)).A)
	log.WithContext(ctx).Infof("\nresp vo:\n%s", lo.T2(json.Marshal(adResp)).A)

	//处理返回值
	var resp SailorText2SqlResp
	if err := util.CopyUseJson(&resp, &adResp); err != nil {
		log.Error(err.Error())
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	return &resp, nil
}

type Filter struct {
	AssetType       string           `json:"asset_type"`
	DataKind        string           `json:"data_kind"`
	UpdateCycle     string           `json:"update_cycle"`
	SharedType      string           `json:"shared_type"`
	StartTime       string           `json:"start_time"`
	EndTime         string           `json:"end_time"`
	StopEntityInfos []StopEntityInfo `json:"stop_entity_infos" binding:"omitempty"`
}

type StopEntityInfo struct {
	ClassName string   `json:"class_name"`
	Names     []string `json:"names"`
}

type Entity2Service struct {
	Relation string  `json:"relation"`
	Service  string  `json:"service"`
	Weight   float64 `json:"weight"`
}

type Entity2ServiceDict struct {
	BusinessObject     Entity2Service `json:"businessobject"`
	CatalogTag         Entity2Service `json:"catalogtag"`
	DataExploreReport  Entity2Service `json:"data_explore_report"`
	DataCatalog        Entity2Service `json:"datacatalog"`
	DataOwner          Entity2Service `json:"dataowner"`
	DataSource         Entity2Service `json:"datasource"`
	Department         Entity2Service `json:"department"`
	Domain             Entity2Service `json:"domain"`
	InfoSystem         Entity2Service `json:"info_system"`
	MetadataTable      Entity2Service `json:"metadata_table"`
	MetadataTableField Entity2Service `json:"metadata_table_field"`
	MetadataSchema     Entity2Service `json:"metadataschema"`
	Subdomain          Entity2Service `json:"subdomain"`
}

type Entity2ServiceDictDataCatalog struct {
	CatalogTag        Entity2Service `json:"catalogtag"`
	DataExploreReport Entity2Service `json:"data_explore_report"`
	FormViewField     Entity2Service `json:"form_view_field"`
	DataCatalog       Entity2Service `json:"datacatalog"`
	DataOwner         Entity2Service `json:"dataowner"`
	DataSource        Entity2Service `json:"datasource"`
	Department        Entity2Service `json:"department"`
	InfoSystem        Entity2Service `json:"info_system"`
	FormView          Entity2Service `json:"form_view"`
	MetadataSchema    Entity2Service `json:"metadataschema"`
}

type Entity2ServiceDictDataResource struct {
	Resource          Entity2Service `json:"resource"`
	ResponseField     Entity2Service `json:"response_field"`
	Field             Entity2Service `json:"field"`
	DataExploreReport Entity2Service `json:"data_explore_report"`
	DataOwner         Entity2Service `json:"dataowner"`
	Department        Entity2Service `json:"department"`
	Domain            Entity2Service `json:"domain"`
	Subdomain         Entity2Service `json:"subdomain"`
	DataSource        Entity2Service `json:"datasource"`
	MetadataSchema    Entity2Service `json:"metadataschema"`
}

type lexiconInfo struct {
	LexiconId string `json:"lexicon_id"`
}

func (u *useCase) getAnalysisId(ctx context.Context, cfgId string) (string, error) {
	srvCfgId, err := u.adCfgHelper.GetGraphAnalysisId(ctx, cfgId)
	if err != nil {
		return "", err
	}
	if len(srvCfgId) < 1 {
		return "", nil
	}
	return srvCfgId, nil
}

func (u *useCase) getAdLexiconId(ctx context.Context, cfgId string) (string, error) {
	srvCfgIds, err := u.adCfgHelper.GetLexiconId(ctx, cfgId)
	if err != nil {
		return "", err
	}
	if len(srvCfgIds) < 1 {
		return "", nil
	}
	return srvCfgIds, nil
}

type BinaryInteger interface {
	int | int32
}

func ArrayToInt[T BinaryInteger](ds []T) T {
	var val T
	for _, d := range ds {
		val += d
	}
	return val
}

const (
	AssetDataCatalog  = "data_catalog"
	AssetInterfaceSvc = "interface_svc"
	AssertLogicalView = "data_view"
	AssertIndicator   = "indicator"
)

func assetTypeCode(asset string) int {
	if asset == AssetInterfaceSvc {
		return 2
	}
	if asset == AssertLogicalView {
		return 3
	}
	if asset == AssertIndicator {
		return 4
	}
	return 1
}
func transferAssetSlice(codes []string) (assets []int) {
	for _, code := range codes {
		assets = append(assets, assetTypeCode(code))
	}
	return assets
}

func dataCatalogResourceTypeCode(resource string) int {
	if resource == AssetInterfaceSvc {
		return 2
	}
	if resource == AssertLogicalView {
		return 1
	}
	return 1
}
func transferDataCatalogResourceTypeSlice(codes []string) (resources []int) {
	for _, code := range codes {
		resources = append(resources, dataCatalogResourceTypeCode(code))
	}
	return resources
}

func (u *useCase) GetEntity2serviceParams(ctx context.Context) (*Entity2ServiceDict, error) {

	entity2service := Entity2ServiceDict{}
	businessobject := Entity2Service{}
	businessobjectServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-businessobject")
	if err != nil {
		return nil, err
	}
	businessobject.Relation = "关联"
	businessobject.Service = businessobjectServiceId
	businessobject.Weight = 1.6
	entity2service.BusinessObject = businessobject

	catalogtag := Entity2Service{}
	catalogtagServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-catalogtag")
	if err != nil {
		return nil, err
	}
	catalogtag.Relation = "打标"
	catalogtag.Service = catalogtagServiceId
	catalogtag.Weight = 1.5
	entity2service.CatalogTag = catalogtag

	data_explore_report := Entity2Service{}
	data_explore_reportServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-data_explore_report")
	if err != nil {
		return nil, err
	}
	data_explore_report.Relation = "包含"
	data_explore_report.Service = data_explore_reportServiceId
	data_explore_report.Weight = 1.7
	entity2service.DataExploreReport = data_explore_report

	datacatalog := Entity2Service{}
	datacatalogServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-datacatalog")
	if err != nil {
		return nil, err
	}
	datacatalog.Relation = ""
	datacatalog.Service = datacatalogServiceId
	datacatalog.Weight = 4
	entity2service.DataCatalog = datacatalog

	dataowner := Entity2Service{}
	dataownerServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-dataowner")
	if err != nil {
		return nil, err
	}
	dataowner.Relation = "管理"
	dataowner.Service = dataownerServiceId
	dataowner.Weight = 1.4
	entity2service.DataOwner = dataowner

	datasource := Entity2Service{}
	datasourceServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-datasource")
	if err != nil {
		return nil, err
	}
	datasource.Relation = "包含"
	datasource.Service = datasourceServiceId
	datasource.Weight = 1
	entity2service.DataSource = datasource

	department := Entity2Service{}
	departmentServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-department")
	if err != nil {
		return nil, err
	}
	department.Relation = "管理"
	department.Service = departmentServiceId
	department.Weight = 1.3
	entity2service.Department = department

	domain := Entity2Service{}
	domainServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-domain")
	if err != nil {
		return nil, err
	}
	domain.Relation = "包含"
	domain.Service = domainServiceId
	domain.Weight = 1.3
	entity2service.Domain = domain

	info_system := Entity2Service{}
	info_systemServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-info_system")
	if err != nil {
		return nil, err
	}
	info_system.Relation = "关联"
	info_system.Service = info_systemServiceId
	info_system.Weight = 1.3
	entity2service.InfoSystem = info_system

	metadata_table := Entity2Service{}
	metadata_tableServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-metadata_table")
	if err != nil {
		return nil, err
	}
	metadata_table.Relation = "编目"
	metadata_table.Service = metadata_tableServiceId
	metadata_table.Weight = 1.9
	entity2service.MetadataTable = metadata_table

	metadata_table_field := Entity2Service{}
	metadata_table_fieldServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-metadata_table_field")
	if err != nil {
		return nil, err
	}
	metadata_table_field.Relation = "包含"
	metadata_table_field.Service = metadata_table_fieldServiceId
	metadata_table_field.Weight = 1.8
	entity2service.MetadataTableField = metadata_table_field

	metadataschema := Entity2Service{}
	metadataschemaServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-metadataschema")
	if err != nil {
		return nil, err
	}
	metadataschema.Relation = "包含"
	metadataschema.Service = metadataschemaServiceId
	metadataschema.Weight = 1
	entity2service.MetadataSchema = metadataschema

	subdomain := Entity2Service{}
	subdomainServiceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetCognitiveSearchGraphAnalysisConfigId+"-subdomain")
	if err != nil {
		return nil, err
	}
	subdomain.Relation = "包含"
	subdomain.Service = subdomainServiceId
	subdomain.Weight = 1
	entity2service.Subdomain = subdomain

	return &entity2service, nil
}

func (u *useCase) GetEntity2serviceParamsV2(ctx context.Context) (*Entity2ServiceDictDataResource, error) {

	entity2service := Entity2ServiceDictDataResource{}
	resource := Entity2Service{}
	resourceId, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-resource")
	if err != nil {
		return nil, err
	}
	resource.Relation = ""
	resource.Service = resourceId // "4798cd6bc8ec414a842d6837d54825b1"
	resource.Weight = 4
	entity2service.Resource = resource

	response_field := Entity2Service{}
	response_field_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-response_field")
	if err != nil {
		return nil, err
	}
	response_field.Relation = "包含"
	response_field.Service = response_field_id // "eb287c37566049e799f330cfb8f2dcde"
	response_field.Weight = 1.9
	entity2service.ResponseField = response_field

	field := Entity2Service{}
	field_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-field")
	if err != nil {
		return nil, err
	}
	field.Relation = "包含"
	field.Service = field_id // "eb287c37566049e799f330cfb8f2dcde"
	field.Weight = 1.8
	entity2service.Field = field

	data_explore_report := Entity2Service{}
	data_explore_report_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-data_explore_report")
	if err != nil {
		return nil, err
	}
	data_explore_report.Relation = "包含"
	data_explore_report.Service = data_explore_report_id // "eb287c37566049e799f330cfb8f2dcde"
	data_explore_report.Weight = 1.8
	entity2service.DataExploreReport = data_explore_report

	data_owner := Entity2Service{}
	data_owner_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-data_owner")
	if err != nil {
		return nil, err
	}
	data_owner.Relation = "管理"
	data_owner.Service = data_owner_id //"eb287c37566049e799f330cfb8f2dcde"
	data_owner.Weight = 1.3
	entity2service.DataOwner = data_owner

	department := Entity2Service{}
	department_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-department")
	if err != nil {
		return nil, err
	}
	department.Relation = "管理"
	department.Service = department_id // "eb287c37566049e799f330cfb8f2dcde"
	department.Weight = 1.3
	entity2service.Department = department

	domain := Entity2Service{}
	domain_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-domain")
	if err != nil {
		return nil, err
	}
	domain.Relation = "包含"
	domain.Service = domain_id // "bfc6d0163fff453586d171fcb70244ee"
	domain.Weight = 1.3
	entity2service.Domain = domain

	subdomain := Entity2Service{}
	subdomain_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-subdomain")
	if err != nil {
		return nil, err
	}
	subdomain.Relation = "包含"
	subdomain.Service = subdomain_id // "eb287c37566049e799f330cfb8f2dcde"
	subdomain.Weight = 1
	entity2service.Subdomain = subdomain

	datasource := Entity2Service{}
	datasource_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-datasource")
	if err != nil {
		return nil, err
	}
	datasource.Relation = "包含"
	datasource.Service = datasource_id // "bfc6d0163fff453586d171fcb70244ee"
	datasource.Weight = 1
	entity2service.DataSource = datasource

	metadataschema := Entity2Service{}
	metadataschema_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId+"-metadataschema")
	if err != nil {
		return nil, err
	}
	metadataschema.Relation = "包含"
	metadataschema.Service = metadataschema_id // "eb287c37566049e799f330cfb8f2dcde"
	metadataschema.Weight = 1
	entity2service.MetadataSchema = metadataschema

	return &entity2service, nil
}

func (u *useCase) GetCognitiveSearchConfigV2(ctx context.Context, dataType string) (*map[string]Entity2Service, error) {
	cognitiveSearchConfigs := settings.GetCognitiveSearchResourceConfig()
	if dataType == constant.DataCatalogVersion {
		cognitiveSearchConfigs = settings.GetCognitiveSearchCatalogConfig()
	}

	cognitiveSearchOutConfigs := map[string]Entity2Service{}
	graphAnalysisConfig, err := u.adCfgHelper.GetGraphAnalysisInfo(ctx)
	if err != nil {
		return nil, err
	}

	for _, item := range cognitiveSearchConfigs {

		configName := settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchResourceGraphAnalysisConfigId + "-" + item.Name
		if dataType == constant.DataCatalogVersion {
			configName = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId + "-" + item.Name
		}
		serviceId := graphAnalysisConfig[configName]
		entity2Service := Entity2Service{item.Relation, serviceId, item.Weight}
		cognitiveSearchOutConfigs[item.RequestName] = entity2Service
	}

	return &cognitiveSearchOutConfigs, nil
}

func (u *useCase) GetEntity2serviceParamsV3(ctx context.Context) (*Entity2ServiceDictDataCatalog, error) {
	entity2service := Entity2ServiceDictDataCatalog{}
	catalogtag := Entity2Service{}
	catalogtag_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-catalogtag")
	if err != nil {
		return nil, err
	}
	catalogtag.Relation = "打标"
	catalogtag.Service = catalogtag_id // "70d93bcd0e674999965b6c379c9397d5"
	catalogtag.Weight = 1.5
	entity2service.CatalogTag = catalogtag

	data_explore_report := Entity2Service{}
	data_explore_report_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-catalogtag")
	if err != nil {
		return nil, err
	}
	data_explore_report.Relation = "包含"
	data_explore_report.Service = data_explore_report_id // "9d6df565351849c293b46fdd163518b1"
	data_explore_report.Weight = 1.8
	entity2service.DataExploreReport = data_explore_report

	form_view_field := Entity2Service{}
	form_view_field_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-form_view_field")
	if err != nil {
		return nil, err
	}
	form_view_field.Relation = "包含"
	form_view_field.Service = form_view_field_id //"9d6df565351849c293b46fdd163518b1"
	form_view_field.Weight = 1.8
	entity2service.FormViewField = form_view_field

	datacatalog := Entity2Service{}
	datacatalog_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-datacatalog")
	if err != nil {
		return nil, err
	}
	datacatalog.Relation = ""
	datacatalog.Service = datacatalog_id // "9526e7c87764437a84c5b0e9251fc854"
	datacatalog.Weight = 4
	entity2service.DataCatalog = datacatalog

	data_owner := Entity2Service{}
	data_owner_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-data_owner")
	if err != nil {
		return nil, err
	}
	data_owner.Relation = "管理"
	data_owner.Service = data_owner_id // "70d93bcd0e674999965b6c379c9397d5"
	data_owner.Weight = 1.4
	entity2service.DataOwner = data_owner

	datasource := Entity2Service{}
	datasource_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-datasource")
	if err != nil {
		return nil, err
	}
	datasource.Relation = "包含"
	datasource.Service = datasource_id // "78ad28c8c4514ad6b47a04a0306b66d7"
	datasource.Weight = 1
	entity2service.DataSource = datasource

	department := Entity2Service{}
	department_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-department")
	if err != nil {
		return nil, err
	}
	department.Relation = "管理"
	department.Service = department_id // "70d93bcd0e674999965b6c379c9397d5"
	department.Weight = 1.3
	entity2service.Department = department

	info_system := Entity2Service{}
	info_system_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-info_system")
	if err != nil {
		return nil, err
	}
	info_system.Relation = "关联"
	info_system.Service = info_system_id // "70d93bcd0e674999965b6c379c9397d5"
	info_system.Weight = 1.2
	entity2service.InfoSystem = info_system

	form_view := Entity2Service{}
	form_view_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-form_view")
	if err != nil {
		return nil, err
	}
	form_view.Relation = "编目"
	form_view.Service = form_view_id // "70d93bcd0e674999965b6c379c9397d5"
	form_view.Weight = 1.9
	entity2service.FormView = form_view

	metadataschema := Entity2Service{}
	metadataschema_id, err := u.getAnalysisId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphAnalysisConfigId+"-metadataschema")
	if err != nil {
		return nil, err
	}
	metadataschema.Relation = "包含"
	metadataschema.Service = metadataschema_id // "9d6df565351849c293b46fdd163518b1"
	metadataschema.Weight = 1
	entity2service.MetadataSchema = metadataschema

	return &entity2service, nil
}

func (u *useCase) CopilotRecommendAssetSearch(ctx context.Context, reqs *CopilotAssetSearchReq) (result *CopilotAssetSearchResp, err error) {
	//var err error
	err = u.UpdateQueryHistory(ctx, reqs.Query)
	if err != nil {
		return nil, err
	}

	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req := client.AssetSearch(reqs.CopilotAssetSearchReqBody)
	req.Init()

	//var adReq ad_rec.CPRecommendAssetSearchReq
	//if err := util.CopyUseJson(&adReq, req); err != nil {
	//	log.WithContext(ctx).Error(err.Error())
	//	return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	//}
	//log.WithContext(ctx).Infof("\nreq vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(req)).A, lo.T2(json.Marshal(adReq)).A)

	// 获取graphId
	graphId, err := u.getGraphId(ctx, settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetsGraphConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)

	args["query"] = req.Query
	args["limit"] = req.Limit
	args["stopwords"] = req.Stopwords
	args["stop_entities"] = req.StopEntities

	myFilter := make(map[string]any)
	myFilter["data_kind"] = ArrayToInt(req.DataKind)
	if len(req.UpdateCycle) == 0 {
		myFilter["update_cycle"] = []int{-1}
	} else {
		//myFilter["update_cycle"] = strings.Replace(fmt.Sprint(req.UpdateCycle), " ", ",", -1)
		myFilter["update_cycle"] = req.UpdateCycle
	}

	if len(req.SharedType) == 0 {
		myFilter["shared_type"] = []int{-1}
	} else {
		myFilter["shared_type"] = req.SharedType
	}
	myFilter["start_time"] = "0"
	if req.StartTime != nil {
		myFilter["start_time"] = fmt.Sprintf("%d", *req.StartTime)
	}

	myFilter["end_time"] = "0"
	if req.EndTime != nil {
		myFilter["end_time"] = fmt.Sprintf("%d", *req.EndTime)
	}

	if len(req.AssetType) == 0 {
		myFilter["asset_type"] = []int{-1}
	} else {
		myFilter["asset_type"] = transferAssetSlice(req.AssetType)
	}
	myFilter["stop_entity_infos"] = req.StopEntityInfos

	//sEntityInfo := StopEntityInfo{}
	//
	//myFilter.StopEntityInfos

	args["filter"] = myFilter

	args["ad_appid"] = appid
	args["kg_id"] = graphId
	entity2service, err := u.GetEntity2serviceParams(ctx)
	if err != nil {
		return nil, err
	}
	//args["entity2service"] = make(map[string]any)

	args["entity2service"] = &entity2service

	// 这里暂时写死
	required_resource := make(map[string]any)
	lexicon_actrieId, err := u.getAdLexiconId(ctx, "cognitive_search_synonyms")
	if err != nil {
		return nil, err
	}
	required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

	// 这里暂时写死
	stopwordsId, err := u.getAdLexiconId(ctx, "cognitive_search_stopwords")
	if err != nil {
		return nil, err
	}
	required_resource["stopwords"] = lexiconInfo{stopwordsId}

	args["required_resource"] = required_resource

	result = &CopilotAssetSearchResp{}

	cache := u.NewCacheLoader(&req)
	if cache.Has(ctx) {
		cacheData := &result.Data
		cacheData, err = cache.Load(ctx)
		if err != nil {
			log.Warnf("load query from cache error %v", err.Error())
		}
		result.Data = *cacheData
		fmt.Println("load cache success")
	}

	if result == nil || len(result.Data.QueryCuts) <= 0 {
		//请求
		adResp, err := u.adProxy.CpRecommendAssetSearchEngine(ctx, &args)
		if err != nil {
			return nil, err
		}

		log.WithContext(ctx).Infof("\nassert search req vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(args)).A, lo.T2(json.Marshal(adResp)).A)

		var dag client.GraphSynSearchDAG
		if err = util.CopyUseJson(&dag.Outputs, &adResp.Res); err != nil {
			log.Error(err.Error())
			return nil, errorcode.Detail(errorcode.PublicInternalError, err)
		}

		//处理返回值
		result = readProperties(dag.Outputs)

		//当有结果时才缓存
		if result != nil && len(result.Data.Entities) > 0 {
			if err := cache.Store(ctx, result.Data); err != nil {
				log.Warn("cache query error", zap.Error(err), zap.Any("query", *reqs), zap.Any("data", result.Data))
			}
		}
	}

	//if err := util.CopyUseJson(&resp.Data, &dag.Res); err != nil {
	//	log.Error(err.Error())
	//	return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	//}
	//
	//resp.Data.Total = dag.Res.Count

	filter(&req, result)

	fmt.Println("final res num: ", len(result.Data.Entities))

	return result, nil
}

func MakeSailorCognitiveSearchReq() {

}

func (u *useCase) CopilotRecommendAssetSearchV2(ctx context.Context, reqs *CopilotAssetSearchReqBody, vType string) (result *CopilotAssetSearchResp, err error) {
	//var err error
	searchType := reqs.SearchType
	if searchType == "" {
		searchType = "cognitive_search"
	}
	if searchType == "cognitive_search" {
		err = u.UpdateQueryHistory(ctx, reqs.Query)
		if err != nil {
			return nil, err
		}
	}

	log.WithContext(ctx).Infof("\nassert search req vo:\n%s", lo.T2(json.Marshal(reqs)).A)

	req := client.AssetSearch(*reqs)
	req.Init()

	kgConfigId := ""
	if vType == constant.DataCatalogVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	} else if vType == constant.DataResourceVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	}

	// 获取graphId
	graphId, err := u.getGraphId(ctx, kgConfigId)
	if err != nil {
		return nil, err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(ctx)
	if err != nil {
		return nil, err
	}

	//包装参数
	args := make(map[string]any)

	args["query"] = req.Query
	if req.AvailableOption == 0 {
		args["limit"] = MAXLIMITNUM
	} else {
		args["limit"] = MAXLIMITNUM2
	}

	args["stopwords"] = req.Stopwords
	args["stop_entities"] = req.StopEntities
	//args["stop_entity_infos"] = req.StopEntityInfos

	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	myFilter["data_kind"] = ArrayToInt(req.DataKind)
	if len(req.UpdateCycle) == 0 {
		myFilter["update_cycle"] = []int{-1}
	} else {
		//myFilter["update_cycle"] = strings.Replace(fmt.Sprint(req.UpdateCycle), " ", ",", -1)
		myFilter["update_cycle"] = req.UpdateCycle
	}

	if len(req.SharedType) == 0 {
		myFilter["shared_type"] = []int{-1}
	} else {
		myFilter["shared_type"] = req.SharedType
	}
	if len(req.DepartmentId) == 0 {
		myFilter["department_id"] = []int{-1}
	} else {
		newDepartmentId := make([]string, 0)
		for _, itemId := range req.DepartmentId {
			newDepartmentId = append(newDepartmentId, itemId)
			itemIdSubId, err0 := u.configCenter.GetChildrenDepartment(ctx, itemId)
			if err0 != nil {
				//return nil, err0
				continue
			}
			//fmt.Println("department_id", itemIdSubId)
			for _, subItem := range itemIdSubId.Entries {
				newDepartmentId = append(newDepartmentId, subItem.Id)
			}
		}

		myFilter["department_id"] = newDepartmentId
	}
	if len(req.SubjectDomainId) == 0 {
		myFilter["subject_id"] = []int{-1}
	} else {
		subjectDomainList := []string{}
		for _, subId := range req.SubjectDomainId {
			subjectDomainList = append(subjectDomainList, subId)
			subRes, err := u.dataSubject.GetSubjectList(ctx, subId, "")
			if err != nil {
				return nil, err
			}
			for _, item := range subRes.Entries {
				if item.Type != "business_object" && item.Type != "subject_domain" {
					continue
				}
				subjectDomainList = append(subjectDomainList, item.Id)
			}
		}
		myFilter["subject_id"] = subjectDomainList
	}
	if len(req.DataOwnerId) == 0 {
		myFilter["owner_id"] = []int{-1}
	} else {
		myFilter["owner_id"] = req.DataOwnerId
	}
	if len(req.InfoSystemId) == 0 {
		myFilter["info_system_id"] = []int{-1}
	} else {
		myFilter["info_system_id"] = req.InfoSystemId
	}

	if len(req.OnlineStatus) == 0 {
		myFilter["online_status"] = []int{-1}
	} else {
		myFilter["online_status"] = req.OnlineStatus
	}

	if len(req.CateNodeId) == 0 {
		myFilter["cate_node_id"] = []int{-1}
	} else {
		catalogFilter, err := u.dataCatalog.GetCatalogFilter(ctx)
		if err != nil {
			return nil, err
		}
		log.Infof("cata num %d", catalogFilter.TotalCount)

		cateNodeId := []string{}
		for _, item := range req.CateNodeId {
			cateNodeList, err := u.dataCatalog.GetCustomerIdList(item.CategoryId, item.SelectedIds, *catalogFilter)
			if err != nil {
				log.WithContext(ctx).Error(err.Error())
				continue
			}
			for _, subItem := range cateNodeList {
				cateNodeId = append(cateNodeId, subItem)
			}
		}
		log.WithContext(ctx).Infof("cate node num %d", len(cateNodeId))
		myFilter["cate_node_id"] = cateNodeId
	}

	if len(req.ResourceType) == 0 {
		myFilter["resource_type"] = []int{-1}
	} else {
		myFilter["resource_type"] = transferDataCatalogResourceTypeSlice(req.ResourceType)
	}

	if len(req.PublishStatusCategory) == 0 {
		myFilter["publish_status_category"] = []int{-1}
	} else {
		myFilter["publish_status_category"] = req.PublishStatusCategory
	}

	myFilter["start_time"] = "0"
	if req.StartTime != nil {
		myFilter["start_time"] = fmt.Sprintf("%d", *req.StartTime)
	}
	myFilter["end_time"] = "0"
	if req.EndTime != nil {
		myFilter["end_time"] = fmt.Sprintf("%d", *req.EndTime)
	}

	//myFilter["asset_type"] = strings.Replace(fmt.Sprint(req.AssetType), " ", ",", -1)

	if len(req.AssetType) == 0 {
		myFilter["asset_type"] = []int{-1}
	} else {
		myFilter["asset_type"] = transferAssetSlice(req.AssetType)
	}
	myFilter["stop_entity_infos"] = req.StopEntityInfos

	//sEntityInfo := StopEntityInfo{}
	//
	//myFilter.StopEntityInfos

	args["filter"] = myFilter

	args["ad_appid"] = appid
	//fmt.Printf(ctx.Value("info"))
	uInfo := GetUserInfo(ctx)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"
	args["available_option"] = req.AvailableOption

	//entity2service, err := u.GetCognitiveSearchConfig(ctx, vType)
	//if err != nil {
	//	return nil, err
	//}
	log.Info(graphId)
	args["kg_id"] = graphId
	args["entity2service"] = map[string]string{}

	// 用户角色
	userRoles, err := u.configCenter.GetUserRoles(ctx)
	if err != nil {
		return nil, err
	}
	rolesList := []string{}
	for _, item := range userRoles {
		rolesList = append(rolesList, item.Icon)
	}

	args["roles"] = rolesList

	// 这里暂时写死
	required_resource := make(map[string]any)
	lexicon_actrieId, err := u.getAdLexiconId(ctx, "cognitive_search_synonyms")
	if err != nil {
		return nil, err
	}
	required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

	// 这里暂时写死
	stopwordsId, err := u.getAdLexiconId(ctx, "cognitive_search_stopwords")
	if err != nil {
		return nil, err
	}
	required_resource["stopwords"] = lexiconInfo{stopwordsId}

	args["required_resource"] = required_resource

	result = &CopilotAssetSearchResp{}

	cache := u.NewCacheLoader(&req)
	if cache.Has(ctx) && req.LastScore > 0 {
		cacheData := &result.Data
		cacheData, err = cache.Load(ctx)
		if err != nil {
			log.Warnf("load query from cache error %v", err.Error())
		}
		result.Data = *cacheData
		log.Info("load cache success")
	}

	if result == nil || len(result.Data.QueryCuts) <= 0 {

		//请求
		adResp, err := u.adProxy.CpRecommendAssetSearchEngineV2(ctx, vType, &args, searchType)
		if err != nil {
			return nil, err
		}

		log.WithContext(ctx).Infof("\nassert search req vo:\n%s\nreq dto:\n%s", lo.T2(json.Marshal(args)).A, lo.T2(json.Marshal(adResp)).A)

		var dag client.GraphSynSearchDAG
		if err = util.CopyUseJson(&dag.Outputs, &adResp.Res); err != nil {
			log.Error(err.Error())
			return nil, errorcode.Detail(errorcode.PublicInternalError, err)
		}

		//fmt.Print(dag, "*************dag\n")
		//处理返回值
		result = readProperties(dag.Outputs)

		//当有结果时才缓存
		if result != nil && len(result.Data.Entities) > 0 {
			if err := cache.Store(ctx, result.Data); err != nil {
				log.Warn("cache query error", zap.Error(err), zap.Any("query", *reqs), zap.Any("data", result.Data))
			}
		}
	}

	//if err := util.CopyUseJson(&resp.Data, &dag.Res); err != nil {
	//	log.Error(err.Error())
	//	return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	//}
	//
	//resp.Data.Total = dag.Res.Count
	//uInfo := GetUserInfo(ctx)
	//availableInfo := make(map[string]bool)
	//params := []map[string]interface{}{}
	//if req.AvailableOption == 2 {
	//	for _, entity := range result.Data.Entities {
	//		if entity.Entity.OwnerID == uInfo.Uid {
	//			availableInfo[entity.Entity.ResourceId] = true
	//		} else if entity.Entity.Type == "2" {
	//			params = append(params, map[string]interface{}{
	//				"action":       "read",
	//				"object_id":    entity.Entity.ResourceId,
	//				"object_type":  "api",
	//				"subject_id":   uInfo.Uid,
	//				"subject_type": "user",
	//			})
	//		} else if entity.Entity.Type == "3" {
	//			params = append(params, map[string]interface{}{
	//				"action":       "read",
	//				"object_id":    entity.Entity.ResourceId,
	//				"object_type":  "data_view",
	//				"subject_id":   uInfo.Uid,
	//				"subject_type": "user",
	//			})
	//		} else {
	//			availableInfo[entity.Entity.ResourceId] = true
	//		}
	//	}
	//}

	//if req.AvailableOption == 2 && len(params) > 0 {
	//	enInfo, err := u.authService.GetUserResourceListByIds(ctx, params)
	//	if err != nil {
	//		return nil, err
	//	}
	//	for _, eninfo := range enInfo {
	//		availableInfo[eninfo.ObjectId] = eninfo.Effect == "allow"
	//	}
	//
	//}
	//filterData(&req, result, req.AvailableOption, availableInfo)
	filter(&req, result)

	fmt.Println("final res num: ", len(result.Data.Entities))

	return result, nil
}

func filterData(reqData *client.AssetSearch, data *CopilotAssetSearchResp, availableFilter int, availableInfo map[string]bool) {
	if data == nil || len(data.Data.Entities) <= 0 {
		return
	}
	entities := make([]client.AssetSearchAnswerEntity, 0, reqData.Limit)
	for _, entity := range data.Data.Entities {
		if entity.Score < reqData.LastScore || len(entities) >= reqData.Limit || entity.Entity.VID == reqData.LastId {
			continue
		}
		if availableFilter == 2 {
			if availableInfo[entity.Entity.ResourceId] == false {
				continue
			}
		}

		entities = append(entities, entity)
	}
	data.Data.Entities = entities
	return
}

func filter(reqData *client.AssetSearch, data *CopilotAssetSearchResp) {
	if data == nil || len(data.Data.Entities) <= 0 {
		return
	}

	entities := make([]client.AssetSearchAnswerEntity, 0, reqData.Limit)
	for _, entity := range data.Data.Entities {
		if entity.Score < reqData.LastScore || len(entities) >= reqData.Limit || entity.Entity.VID == reqData.LastId {
			continue
		}

		entities = append(entities, entity)
	}
	data.Data.Entities = entities
	return
}

var ifChannelsMapInit = false
var channelsMap = map[string]chan string{}

func initChannelsMap() {
	channelsMap = make(map[string]chan string)
}

func AddChannel(traceId string) {
	if !ifChannelsMapInit {
		initChannelsMap()
		ifChannelsMapInit = true
	}
	var newChannel = make(chan string)
	channelsMap[traceId] = newChannel
	log.Infof("Build SSE connection for trace id = " + traceId)

}

type QaAnswerInfo struct {
	Status   string `json:"status"`
	AnswerId string `json:"answer_id"`
}

//type QaAnswerSSE struct {
//	//tagjson序列化后是小写
//	Result struct {
//		Status string `json:"answer_id"`
//
//	} `json:"name"`
//}

// func UpdateQueryHisotry(userId )
func (u *useCase) UpdateQueryHistory(ctx context.Context, inputQuery string) (err error) {
	userid := fmt.Sprintf("%v", ctx.Value(constant.UserId))
	// 取不到user
	if len(userid) == 0 {
		log.WithContext(ctx).Infof("user id can not extract")
		return nil
	}
	qaInfo, err := u.qaRepo.GetQaWordHistory(ctx, userid)
	if err != nil {
		return err
	}
	if qaInfo == nil {
		qlist := QaList{}
		//append({""})
		qlist.QaRecords = append(qlist.QaRecords, QaRecord{MD5(inputQuery), inputQuery, time.Now().UnixNano() / 1e6})
		qlistStr, er := json.Marshal(qlist)
		if er != nil {
			//fmt.Println("marshal failed!", err)
			return er
		}
		//fmt.Println("qlist", string(qlistStr))
		err := u.qaRepo.InsertQaWordHistory(ctx, userid, string(qlistStr))
		if err != nil {
			return err
		}
	} else {
		qalist := QaList{}
		//data := `{"person_name":"xiaoming","person_age":18}`
		qalistStr := qaInfo.QWordList
		err := json.Unmarshal([]byte(*qalistStr), &qalist)
		if err != nil {
			fmt.Println("unmarshal failed!")
			return err
		}
		//qwordLen := len(qalist.QaRecords
		ntime := time.Now().UnixNano() / 1e6
		status := 1
		for i, item := range qalist.QaRecords {
			if item.Qword == inputQuery {
				status = 0
				qalist.QaRecords[i].Qdatetime = ntime

			}
		}
		if status == 1 {
			qalist.QaRecords = append(qalist.QaRecords, QaRecord{MD5(inputQuery), inputQuery, ntime})
		}
		sort.Sort(QaRecordList(qalist.QaRecords))

		if len(qalist.QaRecords) > HISTORYMAXLEN {
			qalist.QaRecords = qalist.QaRecords[:HISTORYMAXLEN]
		}

		qlistStr, er := json.Marshal(qalist)
		if er != nil {
			//fmt.Println("marshal failed!", err)
			return er
		}
		err1 := u.qaRepo.UpdateQaWordHistory(ctx, userid, string(qlistStr))
		if err1 != nil {
			return err1
		}

	}
	return nil
}

func (u *useCase) CopilotAssistantQa(c *gin.Context, req *SSEReq) (err error) {
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()
	inputQuery := strings.TrimSpace(req.Query)

	if len(inputQuery) == 0 {
		errors.Wrap(err, "input query can not be empty string")
		return err
	}

	//err = u.UpdateQueryHistory(c, inputQuery)
	//if err != nil {
	//	return err
	//}

	method := c.Request.Method
	c.Header("Access-Control-Allow-Origin", "*")
	c.Header("Access-Control-Allow-Headers", "Content-Type,AccessToken,X-CSRF-Token, Authorization, Token, x-token") //x-token 为我们自己定义的一种header信息，名称为x-token
	c.Header("Access-Control-Allow-Methods", "POST, GET, OPTIONS, DELETE, PATCH, PUT")                               //或者直接* 允许所有请求
	c.Header("Access-Control-Expose-Headers", "Content-Length, Access-Control-Allow-Origin, Access-Control-Allow-Headers, Content-Type")
	c.Header("Access-Control-Allow-Credentials", "true")

	if method == "OPTIONS" {
		c.AbortWithStatus(http.StatusNoContent)
	}
	dataVersion := ""
	afVersion, err := u.configCenter.DataUseType(c)
	if err == nil {
		if afVersion.Using == 1 {
			dataVersion = constant.DataCatalogVersion
		} else if afVersion.Using == 2 {
			dataVersion = constant.DataResourceVersion
		}
	}

	traceId := "helloworld"
	AddChannel(traceId)
	//fmt.Println(req, "========")
	//log.WithContext(c).Infof("CopilotQa-Input:" + req.Query)

	w := c.Writer
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	args := make(map[string]any)
	//args["check_af_query"] = adReq

	args["query"] = req.Query
	args["limit"] = 100
	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}

	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	myFilter["data_kind"] = "0"
	myFilter["update_cycle"] = "[-1]"
	myFilter["shared_type"] = "[-1]"
	myFilter["department_id"] = "[-1]"
	myFilter["info_system_id"] = "[-1]"
	myFilter["owner_id"] = "[-1]"
	myFilter["subject_id"] = "[-1]"
	myFilter["start_time"] = "1600122122"
	myFilter["end_time"] = "1800122122"
	if req.AssetType == "all" {
		myFilter["asset_type"] = "[-1]"
	} else if req.AssetType == "data_catalog" {
		myFilter["asset_type"] = "[1]"
	} else if req.AssetType == "interface_svc" {
		myFilter["asset_type"] = "[2]"
	} else if req.AssetType == "data_view" {
		myFilter["asset_type"] = "[3]"
	} else {
		myFilter["asset_type"] = "[-1]"
	}

	myFilter["stop_entity_infos"] = []StopEntityInfo{}

	//sEntityInfo := StopEntityInfo{}
	//
	//myFilter.StopEntityInfos

	args["filter"] = myFilter

	// 获取graphId
	kgConfigId := ""
	if dataVersion == constant.DataCatalogVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	} else if dataVersion == constant.DataResourceVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	} else {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	}

	graphId, err := u.getGraphId(c, kgConfigId)
	if err != nil {
		return err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(c)
	if err != nil {
		return err
	}

	args["ad_appid"] = appid
	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}
	args["kg_id"] = graphIdInt
	//args["entity2service"] = make(map[string]any)
	if dataVersion == constant.DataCatalogVersion {
		//args["kg_id"] = graphId
		entity2service, err := u.GetEntity2serviceParamsV3(c)
		if err != nil {
			return err
		}
		//args["entity2service"] = make(map[string]any)

		args["entity2service"] = &entity2service
	} else {
		//args["kg_id"] = graphId
		entity2service, err := u.GetEntity2serviceParamsV2(c)
		if err != nil {
			return err
		}
		//args["entity2service"] = make(map[string]any)

		args["entity2service"] = &entity2service
	}
	//args["entity2service"] = make(map[string]any)

	// 这里暂时写死
	required_resource := make(map[string]any)
	lexicon_actrieId, err := u.getAdLexiconId(c, "cognitive_search_synonyms")
	if err != nil {
		return err
	}
	required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

	// 这里暂时写死
	stopwordsId, err := u.getAdLexiconId(c, "cognitive_search_stopwords")
	if err != nil {
		return err
	}
	required_resource["stopwords"] = lexiconInfo{stopwordsId}

	args["required_resource"] = required_resource
	args["stream"] = true
	uInfo := GetUserInfo(c)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"

	if dataVersion == constant.DataCatalogVersion {
		args["af_editions"] = "catalog"
	} else {
		args["af_editions"] = "resource"
	}

	log.WithContext(c).Infof("\nreq vo:\n%s\n", lo.T2(json.Marshal(args)).A)

	//var bodyStr string
	var body = bytes.NewReader(lo.T2(json.Marshal(args)).A)

	//reqsse, _ := http.NewRequest("POST", "http://10.4.119.109:5006/api/copilot/v1/assistant/qa", body)
	//fmt.Println(settings.GetConfig().CopilotConf.URL)
	reqsse, _ := http.NewRequest("POST", settings.GetConfig().AfSailorConf.URL+"/api/af-sailor/v1/assistant/qa", body)
	reqsse.Header.Set("Accept", "text/event-stream")
	authorization := c.GetHeader("Authorization")
	//fmt.Println("Authorization:" + authorization)
	reqsse.Header.Set("Authorization", authorization)
	client := &http.Client{}

	res, err := client.Do(reqsse)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	reader := bufio.NewReader(res.Body)
	closeNotify := c.Request.Context().Done()
	go func() {
		<-closeNotify
		delete(channelsMap, traceId)
		//log.Infof("SSE close for trace id = " + traceId)
		fmt.Println("SSE close for trace id = " + traceId)
		return
	}()
	answerId, err := uuid.NewRandom()
	if err != nil {
		fmt.Printf("%v\n", err)
	}
	log.WithContext(c).Infof("\nCopilotQa-Input: answer_id:%s query:%s", answerId, req.Query)

	for {
		//fmt.Println("status", w.Status(), c.Request.Response)
		line, _ := reader.ReadString('\n')
		if line == "\n" || line == "\r\n" || line == "" {
			// 一个完整的事件读取完成
			break
		}
		//fmt.Println(line)
		fields := strings.SplitN(line, ":", 2)
		if len(fields) < 2 {
			continue
		}
		//log.WithContext(c).Infof("CopilotQa-Output:" + line)
		log.WithContext(c).Infof("\nCopilotQa-Output: answer_id:%s answer:%s", answerId, line)

		switch fields[0] {
		case "event":
			fmt.Fprintf(w, "event: %s\n", fields[1])
		case "data":

			dataInfo := make(map[string]map[string]any)
			err := json.Unmarshal([]byte(fields[1]), &dataInfo)
			if err != nil {
				fmt.Println("unjson 失败")
				continue
			}
			if dataInfo["result"]["status"] == "search" {
				dataInfo["result"]["answer_id"] = answerId.String()
				dataInfoStr, er := json.Marshal(dataInfo)
				if er != nil {
					//fmt.Println("marshal failed!", err)
					continue
				}
				fmt.Fprintf(w, "data: %s\n\n", dataInfoStr)
			} else {
				fmt.Fprintf(w, "data: %s\n", fields[1])
			}

		case "id":
			fmt.Fprintf(w, "id: %s\n", fields[1])
		case "retry":
			fmt.Fprintf(w, "retry: %s\n", fields[1])
		}

		w.(http.Flusher).Flush()
	}
	fmt.Println("event end")

	return nil
}

func (u *useCase) CopilotCognitiveSearch(ctx context.Context, req *CognitiveSearchReq, vType string) (*CogSearchResp, error) {
	cogSearch, err := u.CopilotRecommendAssetSearchV2(ctx, req.ToCogSearch(), vType)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to do CogSearch, err info: %v", err.Error())
		return &CogSearchResp{}, nil
	}
	log.WithContext(ctx).Infof("\ncogres vo:\n%s", lo.T2(json.Marshal(cogSearch)).A)
	//fmt.Println("cogres", cogSearch)
	resp := u.NewCogSearchResp(ctx, cogSearch, vType)
	return resp, nil
}
