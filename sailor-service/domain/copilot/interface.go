package copilot

import (
	"context"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/adp_agent_factory"
	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/samber/lo"
)

type UseCase interface {
	CopilotRecommendCode(ctx context.Context, req *CopilotRecommendCodeReq) (*CopilotRecommendCodeResp, error)
	CopilotRecommendTable(ctx context.Context, req *CopilotRecommendTableReq) (*CopilotRecommendTableResp, error)
	CopilotRecommendFlow(ctx context.Context, req *CopilotRecommendFlowReq) (*CopilotRecommendFlowResp, error)
	CopilotRecommendCheckCode(ctx context.Context, req *CopilotRecommendCheckCodeReq) (*CopilotRecommendCheckCodeResp, error)
	CopilotRecommendSubjectModel(ctx context.Context, req *CopilotRecommendSubjectModelReq) (*CopilotRecommendSubjectModelResp, error)
	CopilotRecommendView(ctx context.Context, req *CopilotRecommendViewReq) (*CopilotRecommendViewResp, error)
	CopilotRecommendAssetSearch(ctx context.Context, req *CopilotAssetSearchReq) (*CopilotAssetSearchResp, error)
	CopilotAssistantQa(ctx *gin.Context, req *SSEReq) error
	CopilotTestLLM(ctx context.Context, req *CopilotTestLLMReq) (*CopilotTestLLMResp, error)
	QaAnswerLike(ctx context.Context, req *QaAnswerLikeReq) (*QaAnswerLikeResp, error)
	QaQueryHistory(ctx context.Context, req *QaQueryHistoryReq) (*QaQueryHistoryResp, error)
	QaQueryHistoryDelete(ctx context.Context, req *QaQueryHistoryDeleteReq) (*QaQueryHistoryDeleteResp, error)
	SailorText2Sql(ctx context.Context, req *SailorText2SqlReq) (*SailorText2SqlResp, error)
	CopilotCognitiveSearch(ctx context.Context, req *CognitiveSearchReq, vType string) (*CogSearchResp, error)
	CognitiveSearchDataResource(ctx context.Context, req *CognitiveSearchDataResourceReq) (*CogSearchResp, error)
	//CognitiveSearchDataCatalog(ctx context.Context, req *CognitiveSearchReq) (*CogSearchResp, error)
	ChatGetSession(ctx context.Context, req *ChatGetSessionReq) (*ChatGetSessionResp, error)
	SailorChat(c *gin.Context, req *SailorChatReq) (err error)
	SailorChatPost(c *gin.Context, req *SailorChatPostReq) (err error)
	ChatHistoryList(ctx context.Context, req *ChatGetHistoryListReq) (*ChatGetHistoryListResp, error)
	ChatDeleteHistory(ctx context.Context, req *ChatDeleteHistoryReq, sessionId string) (*ChatDeleteHistoryResp, error)
	ChatHistoryDetail(ctx context.Context, req *ChatGetHistoryDetailReq, sessionId string) (*ChatGetHistoryDetailResp, error)
	ChatFavoriteList(ctx context.Context, req *ChatGetFavoriteListReq) (*ChatGetFavoriteListResp, error)
	ChatFavoriteDetail(ctx context.Context, req *ChatGetFavoriteDetailReq, favoriteId string) (*ChatGetFavoriteDetailResp, error)
	ChatPostFavorite(ctx context.Context, req *ChatPostFavoriteReq, sessionId string) (*ChatPostFavoriteResp, error)
	ChatPutFavorite(ctx context.Context, req *ChatPutFavoriteReq, sessionId string) (*ChatPutFavoriteResp, error)
	ChatDeleteFavorite(ctx context.Context, req *ChatDeleteFavoriteReq, favoriteId string) (*ChatDeleteFavoriteResp, error)
	ChatQaLike(ctx context.Context, req *ChatQaLikeReq, QAId string) (*ChatQaLikeResp, error)
	ChatFeedback(ctx context.Context, req *ChatFeedbackReq, QAId string) (*ChatFeedbackResp, error)
	ChatToChat(ctx context.Context, req *ChatToChatReq) (*ChatToChatResp, error)
	GetDataMarketConfig(ctx context.Context, req *GetDataMarketConfigReq) (*GetDataMarketConfigResp, error)
	UpdateDataMarketConfig(ctx context.Context, req *UpdateDataMarketConfigReq) (*UpdateDataMarketConfigResp, error)
	ResetDataMarketConfig(ctx context.Context, req *ResetDataMarketConfigReq) (*ResetDataMarketConfigResp, error)
	CognitiveResourceAnalysisSearch(ctx context.Context, req *CognitiveResourceAnalysisSearchReq) (*CognitiveResourceAnalysisSearchResp, error)
	CognitiveDataCatalogAnalysisSearch(ctx context.Context, req *CognitiveDataCatalogAnalysisSearchReq) (*CognitiveDataCatalogAnalysisSearchResp, error)
	CognitiveAnalysisSearchAnswerLike(ctx context.Context, qaId string, req *CognitiveAnalysisSearchAnswerLikeReq) (*CognitiveAnalysisSearchAnswerLikeResp, error)
	LogicalViewDataCategorize(ctx context.Context, req *LogicalViewDatacategorizeReq) (*LogicalViewDataCategorizeResp, error)
	FormViewGenerateFakeSamples(ctx context.Context, req *GenerateFakeSamplesReq) (*GenerateFakeSamplesResp, error)
	CognitiveDataCatalogFormViewSearch(ctx context.Context, req *CognitiveDataCatalogFormViewSearchReq) (*CogSearchResp, error)
	GetKgConfig(ctx context.Context, req *GetKgConfigReq) (*GetKgConfigResp, error)
	InitRecommendOpenSearch(ctx context.Context, req *RecommendOpenSearchReq) (*RecommendOpenSearchResp, error)

	GetAFAgentList(ctx context.Context, req *AFAgentListReq) (*AFAgentListResp, error)
	PutOnAFAgent(ctx context.Context, req *PutOnAFAgentReq) (*PutOnAFAgentResp, error)
	PullOffAgent(ctx context.Context, req *PullOffAFAgentReq) (*PullOffAFAgentResp, error)
}

const (
	MaxLimit = 100
)

////////////////////////// TablePrompt //////////////////////////

type TablePromptReq struct {
	TablePromptReqBody `param_type:"body"`
}

type TablePromptReqBody client.PtTableReq

type TablePromptResp client.PtTableResp

////////////////////////// CopilotRecommendCode //////////////////////////

type CopilotRecommendCodeReq struct {
	CopilotRecommendCodeReqBody `param_type:"body"`
}

type CopilotRecommendCodeReqBody client.RecCodeReq

type CopilotRecommendCodeResp client.RecCodeResp

////////////////////////// CopilotRecommendTable //////////////////////////

type CopilotRecommendTableReq struct {
	CopilotRecommendTableReqBody `param_type:"body"`
}

type CopilotRecommendTableReqBody client.RecTableReq

type CopilotRecommendTableResp client.RecTableResp

////////////////////////// CopilotRecommendFlow //////////////////////////

type CopilotRecommendFlowReq struct {
	CopilotRecommendFlowReqBody `param_type:"body"`
}

type CopilotRecommendFlowReqBody client.RecFlowReq

type CopilotRecommendFlowResp client.RecFlowResp

////////////////////////// CopilotRecommendCheckCode //////////////////////////

type CopilotRecommendCheckCodeReq struct {
	CopilotRecommendCheckCodeReqBody `param_type:"body"`
}

type CopilotRecommendCheckCodeReqBody client.CheckCodeReqV2

type CopilotRecommendCheckCodeResp client.CheckCodeResp

////////////////////////// CopilotRecommendSubjectModel //////////////////////////

type CopilotRecommendSubjectModelReq struct {
	CopilotRecommendSubjectModelReqBody `param_type:"body"`
}

type CopilotRecommendSubjectModelReqBody client.RecSubjectModelReq

type CopilotRecommendSubjectModelResp client.RecSubjectModelResp

// //////////////////////// CopilotRecommendView //////////////////////////////
type CopilotRecommendViewReq struct {
	CopilotRecommendViewReqBody `param_type:"body"`
}

type CopilotRecommendViewReqBody client.RecViewReq

type CopilotRecommendViewResp client.RecViewResp

////////////////////////// CopilotRecommendAssetSearch //////////////////////////

type CopilotAssetSearchReq struct {
	CopilotAssetSearchReqBody `param_type:"body"`
}

type CopilotAssetSearchReqBody client.AssetSearch

type CopilotAssetSearchResp client.AssetSearchResp

////////////////////////// CopilotAssistantQa //////////////////////////

type CopilotAssistantQaReq struct {
	CopilotAssistantQaReqBody `param_type:"body"`
}

type CopilotAssistantQaReqBody client.AssistantQa

type CopilotAssistantQaResp client.AssetSearchResp

////////////////////////// SSE //////////////////////////

type SSEReq struct {
	//SSEReqBody `param_type:"body"`
	SSEReqBody `param_type:"query"`
}

type SSEReqBody struct {
	Query       string `json:"query" form:"query" binding:"required"`
	AssetType   string `json:"asset_type" form:"asset_type"`
	DataVersion string `json:"data_version" form:"data_version"`
}

////////////////////////// TestLLM //////////////////////////

type CopilotTestLLMReq struct {
	//SSEReqBody `param_type:"body"`
	//CopilotTestLLMBody `param_type:"query"`
}

//
//type CopilotTestLLMBody struct {
//}

type CopilotTestLLMResp client.TestLLMResp

////////////////////////// answer like  //////////////////////////

type QaAnswerLikeReq struct {
	QaAnswerLikeBody `param_type:"body"`
	//CopilotTestLLMBody `param_type:"query"`
}

type QaAnswerLikeBody struct {
	AnswerId   string `json:"answer_id" binding:"required"`
	AnswerLike string `json:"answer_like" binding:"required"`
}

type QaAnswerLikeResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

////////////////////////// query history  //////////////////////////

type QaQueryHistoryReq struct {
	QaQueryHistoryGet `param_type:"query"`
}

type QaQueryHistoryGet struct {
	SearchWord string `json:"search_word" form:"search_word"`
}

type QaList struct {
	QaRecords []QaRecord `json:"qlist"`
}
type QaRecord struct {
	Qid       string `json:"qid"`
	Qword     string `json:"qword"`
	Qdatetime int64  `json:"qdatetime"`
}

type QaRecordOut struct {
	Qid        string `json:"qid"`
	Qword      string `json:"qword"`
	QHighLight string `json:"qhighlight"`
	Qdatetime  int64  `json:"qdatetime"`
}

type QaRecordList []QaRecord

type QaQueryHistoryResp struct {
	Res []QaRecordOut `json:"res"`
}

////////////////////////// delete history  //////////////////////////

type QaQueryHistoryDeleteReq struct {
	Qid string `json:"qid"`
	//QaQueryHistoryDeleteBody `param_type:"body"`
}

//type QaQueryHistoryDeleteBody struct {
//	Qid string `json:"qid"`
//}

type QaQueryHistoryDeleteResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

////////////////////////// Text2Sql //////////////////////////

type SailorText2SqlReq struct {
	SailorText2SqlBody `param_type:"body"`
}

type SConditions struct {
	Index  string `json:"index"`
	Title  string `json:"title"`
	Schema string `json:"schema"`
	Source string `json:"source"`
}

type SailorText2SqlBody struct {
	Query  string        `json:"query"`
	Search []SConditions `json:"search"`
}

type SailorText2SqlResp struct {
	Res struct {
		Text  string `json:"text"`
		Table string `json:"table"`
	} `json:"res"`
}

////////////////////////////// CogSearch //////////////////////////////

type CogSearchResp struct {
	QueryCuts  []*Cut                  `json:"query_cuts"` // 输入框回显
	Entries    []*CogSearchSummaryInfo `json:"entries"`
	TotalCount int64                   `json:"total_count"`

	Filter *FilterCondition `json:"filter"` // 过滤条件

	NextFlag []string `json:"next_flag" example:"0.987,03c0a78d5ab7200cfce7db664cd32c5e"`
}

type Cut struct {
	Source     string   `json:"source"`
	Synonym    []string `json:"synonym"`
	IsStopWord bool     `json:"is_stopword"`
}

type FilterCondition struct {
	Objects  []*NameCountFlagEntity `json:"objects"`  // 智能搜索对象名称及计数
	Entities []*FilterEntity        `json:"entities"` // 智能搜索维度名称及计数
}

type FilterEntity struct {
	Name      string             `json:"name"`       // 智能搜索维度-实体类型，展示名
	ClassName string             `json:"class_name"` // 分组类型
	Children  []*NameCountEntity `json:"children"`   // 智能搜索维度-实体类型-下属子节点
}

type NameCountEntity struct {
	Name  string `json:"name"`  // 智能搜索对象/维度名称
	Count int    `json:"count"` // 智能搜索对象/维度计数
}

type NameCountFlagEntity struct {
	NameCountEntity
	SynonymsFlag bool `json:"synonyms_flag"` // 当前智能搜索对象是否为同义词。true | false
}

type CogSearchSummaryInfo struct {
	SearchAllSummaryInfo
	RecommendDetail *RecommendDetail `json:"recommend_detail"` // 推荐详情
}

type RecommendDetail struct {
	Count  int      `json:"count"`  // 推荐详情旁边的计数
	Starts []string `json:"starts"` // 起始实体id
	End    string   `json:"end"`
}

type SearchAllSummaryInfo struct {
	Type string `json:"type"` // 数据资产类型 data_catalog | interface_svc
	SearchSummaryInfo
	//Fields    []*Field `json:"fields"`     // 字段列表，仅在数据资产类型为data_catalog时生效
	//TableName string   `json:"table_name"` // 表名称，仅在数据资产类型为data_catalog时生效
}

type SearchSummaryInfo struct {
	ID             ModelID `json:"id"`                     // 数据目录ID
	Code           string  `json:"code"`                   // 数据目录编码
	Title          string  `json:"title"`                  // 数据目录名称，可能存在高亮标签
	RawTitle       string  `json:"raw_title"`              // 数据目录名称，不会存在高亮标签
	Description    string  `json:"description"`            // 数据目录描述，可能存在高亮标签
	RawDescription string  `json:"raw_description"`        // 数据目录描述，不会存在高亮标签
	DataKind       []int   `json:"data_kind"`              // 基础信息分类
	DataRange      *int    `json:"data_range,omitempty"`   // 数据范围
	UpdateCycle    *int    `json:"update_cycle,omitempty"` // 更新频率
	SharedType     int     `json:"shared_type"`            // 共享条件
	OrgCode        string  `json:"orgcode"`                // 组织架构ID
	OrgName        string  `json:"orgname"`                // 组织架构名称
	RawOrgName     string  `json:"raw_orgname"`            // 组织架构名称
	GroupID        string  `json:"group_id"`               // 资源分类ID
	TableRows      *int64  `json:"table_rows,omitempty"`   // 数据量
	DataUpdatedAt  *int64  `json:"updated_at,omitempty"`   // 数据更新时间
	PublishedAt    int64   `json:"published_at"`           // 上线发布时间

	VID string `json:"vid"` // vid

	BusinessObjects []*IDNameEntity `json:"business_objects"`

	InfoSystemName    string `json:"system_name"`     // 信息系统名称
	RawInfoSystemName string `json:"raw_system_name"` // 信息系统名称
	InfoSystemID      string `json:"system_id"`       // 信息系统ID

	DataSourceName    string `json:"data_source_name,omitempty" binding:"omitempty"` // 数据源名称，可能存在高亮标签
	RawDataSourceName string `json:"raw_data_source_name"`                           // 原始数据源名称，不会存在高亮标签
	DataSourceID      string `json:"data_source_id,omitempty" binding:"omitempty"`   // 数据源ID
	SchemaName        string `json:"schema_name,omitempty" binding:"omitempty"`      // schema名称，可能存在高亮标签
	RawSchemaName     string `json:"raw_schema_name"`                                // 原始schema名称，不会存在高亮标签
	SchemaID          string `json:"schema_id,omitempty" binding:"omitempty"`        // schema ID
	OwnerName         string `json:"owner_name"`                                     // 数据Owner名称
	RawOwnerName      string `json:"raw_owner_name"`                                 // 原始数据Owner名称，不会存在高亮标签
	OwnerID           string `json:"owner_id"`                                       // 数据OwnerID
	TableName         string `json:"table_name"`
	RawTableName      string `json:"raw_table_name"`
	TableID           uint64 `json:"-"`

	ResourceId     string `json:"resource_id"`
	ResourceName   string `json:"resource_name"`
	SubjectId      string `json:"subject_domain_id"`
	RawSubjectName string `json:"raw_subject_domain_name"`
	SubjectName    string `json:"subject_domain_name"`
	SubjectPath    string `json:"subject_domain_path"`
	RawSubjectPath string `json:"raw_subject_domain_path"`
	TechnicalName  string `json:"technical_name"`

	DepartmentId      string `json:"department_id"`
	RawDepartmentName string `json:"raw_department_name"`
	DepartmentName    string `json:"department_name"`
	RawDepartmentPath string `json:"raw_department_path"`
	DepartmentPath    string `json:"department_path"`

	OnlineAt      int64             `json:"online_at"`
	OnlineStatus  string            `json:"online_status"`
	PublishStatus string            `json:"publish_status"`
	SubjectInfos  []SubjectInfoItem `json:"subject_infos"`
	ResourceType  string            `json:"resource_type"`

	Fields []*Field `json:"fields"`

	DownloadAccessResult     int    `json:"download_access"`                // 结果 1 无下载权限  2 审核中  3 有下载权限
	DownloadAccessExpireTime int64  `json:"download_expire_time,omitempty"` // 数据下载有效期，时间戳毫秒
	HasPermission            bool   `json:"has_permission"`                 // 数据资源，
	AvailableStatus          string `json:"available_status"`               // 数据资源是否可讀 “0” 不 “1” 可

	FavoriteStatus int `json:"favorite_status"` // 收藏状态 0 未收藏 1 收藏

	IsFavored bool   `json:"is_favored"` // 是否收藏
	FavorId   string `json:"favor_id"`   // 收藏id

	Owners []OwnerItem `json:"owners"` // owner 信息
}

type OwnerItem struct {
	OwnerId   string `json:"owner_id"`
	OwnerName string `json:"owner_name"`
}

type SubjectInfoItem struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Path string `json:"path"`
}

type IDNameEntity struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type Field struct {
	FieldNameZH    string `json:"field_name_zh"`
	RawFieldNameZH string `json:"raw_field_name_zh"`
	FieldNameEN    string `json:"field_name_en"`
	RawFieldNameEN string `json:"raw_field_name_en"`
}

const (
	DOWNLOAD_ACCESS_AUDIT_RESULT_UNDER_REVIEW = iota + 1 // 审核中
	DOWNLOAD_ACCESS_AUDIT_RESULT_PASS                    // 审核通过
	DOWNLOAD_ACCESS_AUDIT_RESULT_REJECT                  // 审核不通过
)

func (resp *CogSearchResp) addStatus(status map[string]statusTime) {
	if resp != nil {
		for _, info := range resp.Entries {
			if info.Type == "data_catalog" {
				if state, ok := status[info.Code]; ok {
					info.DownloadAccessResult = state.status
					if state.status == DOWNLOAD_ACCESS_AUDIT_RESULT_PASS {
						info.DownloadAccessExpireTime = state.expireTime
					}
				} else {
					info.DownloadAccessResult = CHECK_DOWNLOAD_ACCESS_RESULT_UNAUTHED
				}
			}
		}
	}
}

func (resp *CogSearchResp) addPermissionStatus(status map[string]bool) {
	if resp != nil {
		for _, info := range resp.Entries {
			if state, ok := status[info.Code]; ok {
				info.HasPermission = state
			} else {
				info.HasPermission = false
			}
		}
	}
}

type CogSearchReqBodyParam struct {
	AssetType string `json:"asset_type" binding:"omitempty,oneof=data_catalog interface_svc"`
	Size      int    `json:"size,omitempty" binding:"omitempty,gt=0" default:"20" example:"20"` // 要获取到的记录条数

	NextFlag []string `json:"next_flag"` // 分页参数，从该参数后面开始获取数据

	Keyword      string   `json:"keyword" binding:"TrimSpace,omitempty,min=1"` // 关键字查询，字符无限制
	Stopwords    []string `json:"stopwords" binding:"omitempty,unique"`        // 智能搜索对象，停用词
	StopEntities []string `json:"stop_entities"`                               // 智能搜索维度，停用的实体

	DataKind    []int `json:"data_kind,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"1,2"`    // 基础信息分类
	UpdateCycle []int `json:"update_cycle,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"3,7"` // 更新频率
	SharedType  []int `json:"shared_type,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"2"`    // 共享条件
	Department  []int `json:"department,omitempty"`
	Domain      []int `json:"domain,omitempty"`
	DataOwner   []int `json:"data_owner,omitempty"`
	InfoSystem  []int `json:"info_system,omitempty"`

	PublishedAt     *TimeRange         `json:"published_at,omitempty" binding:"omitempty"` // 上线发布时间
	StopEntityInfos []*StopEntityInfos `json:"stop_entity_infos" binding:"omitempty"`
}

type StopEntityInfos struct {
	ClassName string   `json:"class_name"`
	Names     []string `json:"names"`
}

type TimeRange struct {
	StartTime *int64 `json:"start_time" binding:"omitempty,gte=0" example:"1682586655000"` // 开始时间，毫秒时间戳
	EndTime   *int64 `json:"end_time" binding:"omitempty,gte=0"  example:"1682586655000"`  // 结束时间，毫秒时间戳
}

////////////////////////// CognitiveSearch //////////////////////////

type CognitiveSearchReq struct {
	CognitiveSearchReqBody `param_type:"body"`
}

type CognitiveSearchReqBody struct {
	AssetType string `json:"asset_type" binding:"omitempty"`
	Size      int    `json:"size,omitempty" binding:"omitempty,gt=0" default:"20" example:"20"` // 要获取到的记录条数

	NextFlag []string `json:"next_flag"` // 分页参数，从该参数后面开始获取数据

	Keyword      string   `json:"keyword" binding:"TrimSpace,min=1"`    // 关键字查询，字符无限制
	Stopwords    []string `json:"stopwords" binding:"omitempty,unique"` // 智能搜索对象，停用词
	StopEntities []string `json:"stop_entities"`                        // 智能搜索维度，停用的实体

	DataKind    []int `json:"data_kind,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"1,2"`    // 基础信息分类
	UpdateCycle []int `json:"update_cycle,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"3,7"` // 更新频率
	SharedType  []int `json:"shared_type,omitempty" binding:"omitempty,max=10,unique,dive,gt=0" example:"2"`    // 共享条件

	PublishedAt     *TimeRange              `json:"published_at,omitempty" binding:"omitempty"` // 上线发布时间
	StopEntityInfos []client.StopEntityInfo `json:"stop_entity_infos" binding:"omitempty"`

	DepartmentId    []string `json:"department_id,omitempty"`
	SubjectDomainId []string `json:"subject_domain_id,omitempty"`
	DataOwnerId     []string `json:"data_owner_id,omitempty"`
	InfoSystemId    []string `json:"info_system_id,omitempty"`
	AvailableOption int      `json:"available_option" binding:"omitempty,gte=0,lte=2"`
	SearchType      string   `json:"search_type" binding:"omitempty"`

	OnlineStatus          []string              `json:"online_status,omitempty"`
	PublishStatus         []string              `json:"publish_status,omitempty"`
	CateNodeId            []client.CateNodeItem `json:"cate_node_id,omitempty"`
	SubjectId             []string              `json:"subject_id,omitempty"`
	ResourceType          []string              `json:"resource_type,omitempty"`
	PublishStatusCategory []string              `json:"publish_status_category,omitempty"`
}

type CognitiveSearchResp client.AssetSearchResp

func (r *CognitiveSearchReqBody) ToCogSearch() *CopilotAssetSearchReqBody {
	var lastScore float64
	var lastID string
	if len(r.NextFlag) == 2 {
		lastScore = float64(lo.T2(strconv.Atoi(r.NextFlag[0])).A)
		lastID = r.NextFlag[1]
	}

	var start int64
	var end int64
	if r.PublishedAt != nil {
		if r.PublishedAt.StartTime != nil {
			start = *r.PublishedAt.StartTime / 1000 // 后端和前端的时间戳精度不同
		}
		if r.PublishedAt.EndTime != nil {
			end = *r.PublishedAt.EndTime / 1000 // 后端和前端的时间戳精度不同
		}
	}
	types := make([]string, 0)

	if r.AssetType != "" && r.AssetType != "all" {
		assetTypeList := strings.Split(r.AssetType, ",")
		for _, assetType := range assetTypeList {
			types = append(types, strings.TrimSpace(assetType))
		}

	}

	return &CopilotAssetSearchReqBody{
		Query:        r.Keyword,
		Limit:        r.Size,
		AssetType:    types,
		LastScore:    lastScore,
		LastId:       lastID,
		Stopwords:    r.Stopwords,
		StopEntities: r.StopEntities,
		DataKind:     r.DataKind,
		UpdateCycle:  r.UpdateCycle,
		SharedType:   r.SharedType,

		StartTime: &start,
		EndTime:   &end,
		StopEntityInfos: lo.Map(r.StopEntityInfos, func(item client.StopEntityInfo, index int) client.StopEntityInfo {
			return client.StopEntityInfo{ClassName: item.ClassName, Names: item.Names}
		}),
		DepartmentId:          r.DepartmentId,
		SubjectDomainId:       r.SubjectDomainId,
		DataOwnerId:           r.DataOwnerId,
		InfoSystemId:          r.InfoSystemId,
		AvailableOption:       r.AvailableOption,
		SearchType:            r.SearchType,
		OnlineStatus:          r.OnlineStatus,
		PublishStatus:         r.PublishStatus,
		CateNodeId:            r.CateNodeId,
		SubjectId:             r.SubjectId,
		ResourceType:          r.ResourceType,
		PublishStatusCategory: r.PublishStatusCategory,
	}
}

// /  大模型分析性认知搜索   ///
type CognitiveResourceAnalysisSearchReq struct {
	CognitiveResourceAnalysisSearchReqBody `param_type:"body"`
}

type CognitiveResourceAnalysisSearchReqBody struct {
	Query           string `json:"query" binding:"required,TrimSpace,min=1,max=500"`
	Size            int    `json:"size" binding:"required,gte=1"`
	AvailableOption int    `json:"available_option" binding:"omitempty,gte=1,lte=2"`
}

type AnalysisEntity struct {
	Id              string `json:"id"`
	Type            string `json:"type"`
	Title           string `json:"title"`
	SerialNumber    int    `json:"serial_number"`
	AvailableStatus string `json:"available_status"`
	TechnicalName   string `json:"technical_name"`
	Code            string `json:"code"`
}

type CognitiveResourceAnalysisSearchResp struct {
	Res struct {
		Entities            []AnalysisEntity `json:"entities"`
		Count               int              `json:"count"`
		QaId                string           `json:"qa_id"`
		ExplanationFormView string           `json:"explanation_formview"`
	} `json:"res"`
	ExplanationStatus string `json:"explanation_status"`
	ResStatus         string `json:"res_status"`
}

type CognitiveDataCatalogAnalysisSearchReq struct {
	CognitiveDataCatalogAnalysisSearchReqBody `param_type:"body"`
}

type CognitiveDataCatalogAnalysisSearchReqBody struct {
	Query           string `json:"query" binding:"required,TrimSpace,min=1,max=500"`
	Size            int    `json:"size" binding:"required,gte=1"`
	AvailableOption int    `json:"available_option" binding:"omitempty,gte=1,lte=2"`
}

type CognitiveDataCatalogAnalysisSearchResp struct {
	Res struct {
		Entities            []AnalysisEntity `json:"entities"`
		Count               int              `json:"count"`
		QaId                string           `json:"qa_id"`
		ExplanationFormView string           `json:"explanation_formview"`
	} `json:"res"`
	ExplanationStatus string `json:"explanation_status"`
	ResStatus         string `json:"res_status"`
}

////////////////////////// analysis search answer like  //////////////////////////

type CognitiveAnalysisSearchAnswerLikeReq struct {
	CognitiveAnalysisSearchAnswerLikeBody `param_type:"body"`
}

type CognitiveAnalysisSearchAnswerLikeBody struct {
	Action string `json:"action" binding:"required,oneof=like unlike cancel"`
}

type CognitiveAnalysisSearchAnswerLikeResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

////////////////////////// logical-view 数据分类 //////////////////////////

type LogicalViewDatacategorizeReq struct {
	LogicalViewDatacategorizeReqBody `param_type:"body"`
}

type LogicalViewDatacategorizeReqBody struct {
	ViewId            string `json:"view_id"`
	ViewTechnicalName string `json:"view_technical_name"`
	ViewBusinessName  string `json:"view_business_name"`
	ViewDesc          string `json:"view_desc"`
	SubjectId         string `json:"subject_id"`
	ViewFields        []struct {
		ViewFieldId            string `json:"view_field_id"`
		ViewFieldTechnicalName string `json:"view_field_technical_name"`
		ViewFieldBusinessName  string `json:"view_field_business_name"`
		StandardCode           string `json:"standard_code"`
	} `json:"view_fields"`
	ExploreSubjectIds     []string `json:"explore_subject_ids"`
	ViewSourceCatalogName string   `json:"view_source_catalog_name"`
}

type LogicalViewDataCategorizeResp struct {
	Res struct {
		Answers struct {
			ViewId     string `json:"view_id"`
			ViewFields []struct {
				ViewFieldId string `json:"view_field_id"`
				RelSubjects []struct {
					SubjectId string `json:"subject_id"`
					Score     string `json:"score"`
				} `json:"rel_subjects"`
			} `json:"view_fields"`
		} `json:"answers"`
	} `json:"res"`
}

////////////////////////// AgentList //////////////////////////

type AFAgentListReq struct {
	AFAgentListReqBody `param_type:"body"`
}

type AFAgentListReqBody struct {
	Name                string `json:"name"`
	Size                int    `json:"size"`
	PaginationMarkerStr string `json:"pagination_marker_str"`
	ListFlag            int    `json:"list_flag"`
}
type AgentItem struct {
	Id              string `json:"id"`
	Key             string `json:"key"`
	IsBuiltIn       int    `json:"is_built_in"`
	IsSystemAgent   int    `json:"is_system_agent"`
	Name            string `json:"name"`
	Profile         string `json:"profile"`
	Version         string `json:"version"`
	AvatarType      int    `json:"avatar_type"`
	Avatar          string `json:"avatar"`
	PublishedAt     int64  `json:"published_at"`
	PublishedBy     string `json:"published_by"`
	PublishedByName string `json:"published_by_name"`
	PublishInfo     struct {
		IsApiAgent      int `json:"is_api_agent"`
		IsSdkAgent      int `json:"is_sdk_agent"`
		IsSkillAgent    int `json:"is_skill_agent"`
		IsDataFlowAgent int `json:"is_data_flow_agent"`
	} `json:"publish_info"`
	BusinessDomainId string `json:"business_domain_id"`
	ListStatus       string `json:"list_status"`
	AFAgentID        string `json:"af_agent_id"`
}

type AFAgentListResp struct {
	Entries             []adp_agent_factory.AgentItem `json:"entries"`
	PaginationMarkerStr string                        `json:"pagination_marker_str"`
	IsLastPage          bool                          `json:"is_last_page"`
}

////////////////////////// PUTOnAgent //////////////////////////

type PutOnAFAgentReq struct {
	PutOnAFAgentReqBody `param_type:"body"`
}

type PutOnAFAgentReqBody struct {
	AgentList []struct {
		AgentKey string `json:"agent_key"`
	} `json:"agent_list"`
}

type PutOnAFAgentResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

////////////////////////// PullOffAgent //////////////////////////

type PullOffAFAgentReq struct {
	PullOffAFAgentReqBody `param_type:"body"`
}

type PullOffAFAgentReqBody struct {
	AfAgentId string `json:"af_agent_id"`
}

type PullOffAFAgentResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}
