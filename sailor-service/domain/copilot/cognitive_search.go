package copilot

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
	"go.uber.org/zap"
)

type CognitiveSearchDataResourceReq struct {
	CognitiveSearchDataResourceReqBody `param_type:"body"`
}

type CognitiveSearchDataResourceReqBody struct {
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

	DepartmentId          []string   `json:"department_id,omitempty"`
	SubjectDomainId       []string   `json:"subject_domain_id,omitempty"`
	DataOwnerId           []string   `json:"data_owner_id,omitempty"`
	InfoSystemId          []string   `json:"info_system_id,omitempty"`
	AvailableOption       int        `json:"available_option" binding:"omitempty,gte=0,lte=2"`
	SearchType            string     `json:"search_type" binding:"omitempty"`
	OnlineAt              *TimeRange `json:"online_at,omitempty" binding:"omitempty"`
	OnlineStatus          []string   `json:"online_status,omitempty"`
	PublishStatusCategory []string   `json:"publish_status_category,omitempty"`
}

func (r *CognitiveSearchDataResourceReqBody) ToCogSearch() *CopilotAssetSearchReqBody {
	var lastScore float64
	var lastID string
	if len(r.NextFlag) == 2 {
		lastScore = float64(lo.T2(strconv.Atoi(r.NextFlag[0])).A)
		lastID = r.NextFlag[1]
	}

	var start int64
	var end int64
	if r.OnlineAt != nil {
		if r.OnlineAt.StartTime != nil {
			start = *r.OnlineAt.StartTime / 1000 // 后端和前端的时间戳精度不同
		}
		if r.OnlineAt.EndTime != nil {
			end = *r.OnlineAt.EndTime / 1000 // 后端和前端的时间戳精度不同
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
		PublishStatusCategory: r.PublishStatusCategory,
		OnlineStatus:          r.OnlineStatus,
	}
}

type CognitiveSearchDataResourceResp client.AssetSearchResp

func (u *useCase) CognitiveSearchDataResource(ctx context.Context, req *CognitiveSearchDataResourceReq) (*CogSearchResp, error) {
	cogSearch, err := u.CognitiveSearchDataResourceStageOne(ctx, req.ToCogSearch())
	if err != nil {
		log.WithContext(ctx).Errorf("failed to do CogSearch, err info: %v", err.Error())
		return &CogSearchResp{}, nil
	}
	log.WithContext(ctx).Infof("\ncogres vo:\n%s", lo.T2(json.Marshal(cogSearch)).A)
	resp := u.NewCogSearchResp(ctx, cogSearch, constant.DataResourceVersion)
	return resp, nil
}

func (u *useCase) CognitiveSearchDataResourceStageOne(ctx context.Context, reqs *CopilotAssetSearchReqBody) (result *CopilotAssetSearchResp, err error) {
	//var err error
	if reqs.SearchType == "" {
		reqs.SearchType = "cognitive_search"
	}
	if reqs.SearchType == "cognitive_search" {
		err = u.UpdateQueryHistory(ctx, reqs.Query)
		if err != nil {
			return nil, err
		}
	}

	log.WithContext(ctx).Infof("\nassert search req vo:\n%s", lo.T2(json.Marshal(reqs)).A)

	req := client.AssetSearch(*reqs)
	req.Init()

	kgConfigId := settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId

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

	myFilter := make(map[string]any)

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
		myFilter["subject_id"] = req.SubjectDomainId
	}
	if len(req.DataOwnerId) == 0 {
		myFilter["owner_id"] = []int{-1}
	} else {
		myFilter["owner_id"] = req.DataOwnerId
	}
	if len(req.PublishStatusCategory) == 0 {
		myFilter["publish_status_category"] = []int{-1}
	} else {
		myFilter["publish_status_category"] = req.PublishStatusCategory
	}
	if len(req.OnlineStatus) == 0 {
		myFilter["online_status"] = []int{-1}
	} else {
		myFilter["online_status"] = req.OnlineStatus
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

	args["filter"] = myFilter

	args["ad_appid"] = appid
	uInfo := GetUserInfo(ctx)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"
	args["available_option"] = req.AvailableOption

	args["kg_id"] = graphId
	args["entity2service"] = map[string]string{}

	// 用户角色
	userRoles, err := u.configCenter.GetUserRoles(ctx)
	if err != nil {
		return nil, err
	}
	rolesList := []string{}
	for _, item := range userRoles {
		// 场景分析特殊处理，如果用户是数据运营工程师傅或者数据开发工程师，那么还是按照数据超市普通用户的逻辑
		if reqs.SearchType == "analysis_cognitive_search" {
			if item.Icon == "data-development-engineer" {
				continue
			}
			if item.Icon == "data-operation-engineer" {
				continue
			}
		}
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
		adResp, err := u.adProxy.CpRecommendAssetSearchEngineV2(ctx, constant.DataResourceVersion, &args, reqs.SearchType)
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

	filter(&req, result)

	fmt.Println("final res num: ", len(result.Data.Entities))

	return result, nil
}

type CognitiveSearchDataCatalogReq struct {
	CognitiveSearchDataCatalogReqBody `param_type:"body"`
}

type CognitiveSearchDataCatalogReqBody struct {
	AssetType string `json:"asset_type" binding:"omitempty,oneof=interface_svc datacatlog data_view all"`
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
}
