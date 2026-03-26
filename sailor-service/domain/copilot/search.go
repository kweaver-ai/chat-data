package copilot

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/basic_search"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/data_catalog"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models"

	//"github.com/kweaver-ai/chat-data/sailor-service/common/models"
	"encoding/json"
	"fmt"
	"net/url"
	"strconv"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
)

func (u *useCase) NewCogSearchResp(ctx context.Context, search *CopilotAssetSearchResp, dataVersion string) *CogSearchResp {

	resp := &CogSearchResp{}
	if search == nil || lo.ToPtr(search.Data) == nil || len(search.Data.Entities) == 0 {
		return resp
	}
	uInfo := GetUserInfo(ctx)

	assetsMap := make(map[uint64]*CogSearchSummaryInfo) // key 是 catalog id

	nDataMap := make(map[string]*CogSearchSummaryInfo)
	codesMap := make(map[string]*CogSearchSummaryInfo) // key 是 catalog code
	catalogIds := make([]uint64, 0)
	catalogStringIds := make([]string, 0)
	dataViewIds := make([]string, 0)
	SvcIds := make([]string, 0)
	IndicatorIds := make([]string, 0)
	catalogCodes := make([]string, 0)
	resourceIds := make([]string, 0)

	entries := make([]*CogSearchSummaryInfo, 0, len(search.Data.Entities))
	// 获取资源权限
	//authDataCatalogReq := map[string]any{
	//	"object_type":  "data_catalog",
	//	"subject_id":   uInfo.Uid,
	//	"subject_type": "user",
	//}
	//permissionDataCatalogMap := make(map[string]bool)
	//uResource, err := u.authService.GetUserResource(ctx, authDataCatalogReq)
	//if err != nil {
	//	return resp
	//}
	//for _, entInfo := range uResource.Entries {
	//	permissionDataCatalogMap[entInfo]
	//}

	// resp.NextFlag
	next := []string{"", ""}
	for i, entity := range search.Data.Entities {
		summaryInfo := &CogSearchSummaryInfo{
			// 这里仅初始化entries的id，查询详情、字段信息、高亮放在别处单独处理
			SearchAllSummaryInfo: SearchAllSummaryInfo{
				SearchSummaryInfo: SearchSummaryInfo{ID: ModelID(entity.Entity.DataCatalogId), Code: entity.Entity.Code,
					ResourceId: entity.Entity.ResourceId},
			},
			RecommendDetail: &RecommendDetail{
				Count:  len(entity.Subgraph.Starts),
				Starts: entity.Subgraph.Starts,
				End:    entity.Subgraph.End,
			},
		}
		//fmt.Println("entity type", entity.Entity.AssetType)
		switch entity.Entity.AssetType {
		case "1": // 数据目录详情需要去数据库查

			summaryInfo.Type = "data_catalog"
			summaryInfo.HasPermission = false
			//if entity.Entity.OwnerID == uInfo.Uid {
			//	summaryInfo.HasPermission = true
			//} else {
			//	params := []map[string]interface{}{
			//		{
			//			"action":       "download",
			//			"object_id":    entity.Entity.ResourceId,
			//			"object_type":  "data_catalog",
			//			"subject_id":   uInfo.Uid,
			//			"subject_type": "user",
			//		},
			//	}
			//
			//	enInfo, err := u.authService.GetUserResourceById(ctx, params)
			//	if err != nil {
			//		summaryInfo.HasPermission = false
			//	} else {
			//		summaryInfo.HasPermission = enInfo.Effect == "deny"
			//	}
			//}

			summaryInfo.DepartmentId = entity.Entity.DepartmentId
			summaryInfo.RawDepartmentName = entity.Entity.Department
			summaryInfo.RawDepartmentPath = entity.Entity.DepartmentPath
			//summaryInfo.Code = entity.Entity.DepartmentId
			//summaryInfo.RawTitle = entity.Entity.DataCatalogName
			summaryInfo.RawOrgName = entity.Entity.Department
			summaryInfo.RawOwnerName = entity.Entity.OwnerName
			summaryInfo.InfoSystemID = entity.Entity.InfoSystemId
			summaryInfo.RawInfoSystemName = entity.Entity.InfoSystemName
			summaryInfo.AvailableStatus = entity.Entity.IsPermissions
			summaryInfo.OnlineAt = int64(lo.T2(strconv.Atoi(entity.Entity.OnlineTime)).A) * 1000
			summaryInfo.PublishStatus = entity.Entity.PublishStatus
			summaryInfo.OnlineStatus = entity.Entity.OnlineStatus
			summaryInfo.ResourceType = ""
			if entity.Entity.ResourceType == "1" {
				summaryInfo.ResourceType = AssertLogicalView
			}
			summaryInfo.FavoriteStatus = 0
			if entity.Entity.ResourceType == "2" {
				summaryInfo.ResourceType = AssetInterfaceSvc
			}

			if entity.Entity.SubjectNodes != "" {
				subjectNodesList := []SubjectNodesItem{}
				err := json.Unmarshal([]byte(entity.Entity.SubjectNodes), &subjectNodesList)
				if err != nil {
					fmt.Println("Error parsing JSON:", err)
				}
				subjectInfoItemList := []SubjectInfoItem{}
				for _, item := range subjectNodesList {
					subjectInfoItemList = append(subjectInfoItemList, SubjectInfoItem{item.SubjectId, item.SubjectName, item.SubjectPathId})
				}
				summaryInfo.SubjectInfos = subjectInfoItemList
			}

			if entity.Entity.OwnerID == uInfo.ID {
				summaryInfo.HasPermission = true
			}

			catalogIds = append(catalogIds, summaryInfo.ID.Uint64())
			catalogCodes = append(catalogCodes, entity.Entity.Code)
			catalogStringIds = append(catalogStringIds, summaryInfo.ID.String())
			codesMap[entity.Entity.Code] = summaryInfo
		case "2": // 接口服务详情直接用认知助手返回结果c
			summaryInfo.Type = "interface_svc"
			if entity.Entity.OwnerID == uInfo.ID {
				summaryInfo.HasPermission = true
			} else {
				params := []map[string]interface{}{
					{
						"action":       "read",
						"object_id":    entity.Entity.ResourceId,
						"object_type":  "api",
						"subject_id":   uInfo.ID,
						"subject_type": "user",
					},
				}

				enInfo, err := u.authService.GetUserResourceById(ctx, params)
				if err != nil {
					summaryInfo.HasPermission = false
				} else {
					summaryInfo.HasPermission = enInfo.Effect == "allow"
				}
			}

			fReq := data_catalog.CheckV1Req{ResID: entity.Entity.ResourceId, ResType: "interface-svc", CreatedBy: uInfo.ID}
			favoriteInfo, err := u.dataCatalog.GetResourceFavoriteByID(ctx, &fReq)
			summaryInfo.FavorId = ""
			if err != nil {
				summaryInfo.IsFavored = false

			} else {
				summaryInfo.IsFavored = favoriteInfo.IsFavored
				if favoriteInfo.IsFavored == true {
					summaryInfo.FavorId = strconv.FormatUint(favoriteInfo.FavorID, 10)
				}
			}

			//summaryInfo.RawTitle = entity.Entity.DataCatalogName
			summaryInfo.RawDescription = entity.Entity.Description
			summaryInfo.RawOwnerName = entity.Entity.OwnerName
			summaryInfo.RawOrgName = entity.Entity.Department
			summaryInfo.RawDataSourceName = entity.Entity.Datasource
			summaryInfo.RawTitle = entity.Entity.ResourceName

			summaryInfo.PublishedAt = int64(lo.T2(strconv.Atoi(entity.Entity.PublishedAt)).A) * 1000
			summaryInfo.OwnerName = entity.Entity.OwnerName
			summaryInfo.OwnerID = entity.Entity.OwnerID
			summaryInfo.ResourceId = entity.Entity.ResourceId
			summaryInfo.ResourceName = entity.Entity.ResourceId
			summaryInfo.SubjectId = entity.Entity.SubjectId
			summaryInfo.RawSubjectName = entity.Entity.SubjectName
			summaryInfo.TechnicalName = entity.Entity.TechnicalName
			summaryInfo.DepartmentId = entity.Entity.DepartmentId
			summaryInfo.RawDepartmentName = entity.Entity.Department
			summaryInfo.RawDepartmentPath = entity.Entity.DepartmentPath
			summaryInfo.RawSubjectPath = entity.Entity.SubjectPath
			summaryInfo.OnlineAt = int64(lo.T2(strconv.Atoi(entity.Entity.OnlineAt)).A) * 1000
			summaryInfo.PublishStatus = entity.Entity.PublishStatus
			summaryInfo.OnlineStatus = entity.Entity.OnlineStatus
			//summaryInfo.ID = ModelID(entity.Entity.ResourceId)

			SvcIds = append(SvcIds, summaryInfo.ResourceId)
			resourceIds = append(resourceIds, summaryInfo.ResourceId)

		case "3":

			summaryInfo.Type = "data_view"
			if entity.Entity.OwnerID == uInfo.ID {
				summaryInfo.HasPermission = true
			} else {
				params := []map[string]interface{}{
					{
						"action":       "download",
						"object_id":    entity.Entity.ResourceId,
						"object_type":  "data_view",
						"subject_id":   uInfo.ID,
						"subject_type": "user",
					},
				}

				enInfo, err := u.authService.GetUserResourceById(ctx, params)
				if err != nil {
					summaryInfo.HasPermission = false
				} else {
					summaryInfo.HasPermission = enInfo.Effect == "allow"
				}

			}

			fReq := data_catalog.CheckV1Req{ResID: entity.Entity.ResourceId, ResType: "data-view", CreatedBy: uInfo.ID}
			favoriteInfo, err := u.dataCatalog.GetResourceFavoriteByID(ctx, &fReq)
			summaryInfo.FavorId = ""
			if err != nil {
				summaryInfo.IsFavored = false

			} else {
				summaryInfo.IsFavored = favoriteInfo.IsFavored
				if favoriteInfo.IsFavored == true {
					summaryInfo.FavorId = strconv.FormatUint(favoriteInfo.FavorID, 10)
				}
			}

			dataViewIds = append(dataViewIds, summaryInfo.ResourceId)

			resourceIds = append(resourceIds, summaryInfo.ResourceId)
			//catalogCodes = append(catalogCodes, entity.Entity.Code)
			if entity.Entity.PublishedAt != "" {
				intVal, err := strconv.ParseInt(entity.Entity.PublishedAt, 10, 64)
				if err == nil {
					summaryInfo.PublishedAt = intVal
				}
			}
			summaryInfo.RawTitle = entity.Entity.ResourceName
			summaryInfo.RawDescription = entity.Entity.Description
			summaryInfo.RawOwnerName = entity.Entity.DataOwner
			summaryInfo.RawOrgName = entity.Entity.Department
			summaryInfo.RawDataSourceName = entity.Entity.Datasource

			summaryInfo.OwnerName = entity.Entity.OwnerName
			summaryInfo.OwnerID = entity.Entity.OwnerID
			summaryInfo.ResourceId = entity.Entity.ResourceId
			summaryInfo.ResourceName = entity.Entity.ResourceName
			summaryInfo.SubjectId = entity.Entity.SubjectId
			summaryInfo.RawSubjectName = entity.Entity.SubjectName
			summaryInfo.TechnicalName = entity.Entity.TechnicalName
			summaryInfo.DepartmentId = entity.Entity.DepartmentId
			summaryInfo.RawDepartmentName = entity.Entity.Department
			summaryInfo.RawDepartmentPath = entity.Entity.DepartmentPath
			summaryInfo.PublishedAt = int64(lo.T2(strconv.Atoi(entity.Entity.PublishedAt)).A) * 1000
			summaryInfo.AvailableStatus = entity.Entity.IsPermissions
			summaryInfo.RawSubjectPath = entity.Entity.SubjectPath
			summaryInfo.OnlineAt = int64(lo.T2(strconv.Atoi(entity.Entity.OnlineAt)).A) * 1000
			summaryInfo.PublishStatus = entity.Entity.PublishStatus
			summaryInfo.OnlineStatus = entity.Entity.OnlineStatus

			codesMap[entity.Entity.Code] = summaryInfo
		case "4":
			summaryInfo.Type = "indicator"
			IndicatorIds = append(IndicatorIds, summaryInfo.ResourceId)
			resourceIds = append(resourceIds, summaryInfo.ResourceId)
			//catalogCodes = append(catalogCodes, entity.Entity.Code)
			if entity.Entity.PublishedAt != "" {
				intVal, err := strconv.ParseInt(entity.Entity.PublishedAt, 10, 64)
				if err == nil {
					summaryInfo.PublishedAt = intVal
				}
			}

			fReq := data_catalog.CheckV1Req{ResID: entity.Entity.ResourceId, ResType: "indicator", CreatedBy: uInfo.ID}
			favoriteInfo, err := u.dataCatalog.GetResourceFavoriteByID(ctx, &fReq)
			summaryInfo.FavorId = ""
			if err != nil {
				summaryInfo.IsFavored = false

			} else {
				summaryInfo.IsFavored = favoriteInfo.IsFavored
				if favoriteInfo.IsFavored == true {
					summaryInfo.FavorId = strconv.FormatUint(favoriteInfo.FavorID, 10)
				}
			}

			summaryInfo.RawTitle = entity.Entity.ResourceName
			summaryInfo.RawDescription = entity.Entity.Description
			summaryInfo.RawOwnerName = entity.Entity.DataOwner
			summaryInfo.RawOrgName = entity.Entity.Department
			summaryInfo.RawDataSourceName = entity.Entity.Datasource

			summaryInfo.OwnerName = entity.Entity.OwnerName
			summaryInfo.OwnerID = entity.Entity.OwnerID
			summaryInfo.ResourceId = entity.Entity.ResourceId
			summaryInfo.ResourceName = entity.Entity.ResourceName
			summaryInfo.SubjectId = entity.Entity.SubjectId
			summaryInfo.RawSubjectName = entity.Entity.SubjectName
			summaryInfo.TechnicalName = entity.Entity.TechnicalName
			summaryInfo.DepartmentId = entity.Entity.DepartmentId
			summaryInfo.RawDepartmentName = entity.Entity.Department
			summaryInfo.RawDepartmentPath = entity.Entity.DepartmentPath
			summaryInfo.PublishedAt = int64(lo.T2(strconv.Atoi(entity.Entity.PublishedAt)).A) * 1000
			summaryInfo.AvailableStatus = entity.Entity.IsPermissions
			summaryInfo.RawSubjectPath = entity.Entity.SubjectPath
			summaryInfo.OnlineAt = int64(lo.T2(strconv.Atoi(entity.Entity.OnlineAt)).A) * 1000
			summaryInfo.PublishStatus = entity.Entity.PublishStatus
			summaryInfo.OnlineStatus = entity.Entity.OnlineStatus
			codesMap[entity.Entity.Code] = summaryInfo
		}

		assetsMap[summaryInfo.ID.Uint64()] = summaryInfo
		nDataMap[summaryInfo.ResourceId] = summaryInfo

		entries = append(entries, summaryInfo)
		if i == len(search.Data.Entities)-1 {
			next[0] = fmt.Sprintf("%v", entity.Score)
			next[1] = entity.Entity.DataCatalogId
		}
	}

	resp.TotalCount = int64(search.Data.Total)
	resp.NextFlag = next

	// resp.Synonyms
	stopwords := make([]string, 0)
	cuts := make([]*Cut, 0)
	for _, cut := range search.Data.QueryCuts {
		// 过滤出无效词
		if cut.IsStopword {
			stopwords = append(stopwords, cut.Source)
			stopwords = append(stopwords, cut.Synonym...)
		}
		// source + synonym 即当前分词与它的同义词组。所有分词及同义词组 即 搜索框回显。
		cuts = append(cuts, &Cut{Source: cut.Source, Synonym: cut.Synonym, IsStopWord: cut.IsStopword})
	}
	stopwords = lo.Uniq(stopwords)
	resp.QueryCuts = cuts

	// 过滤条件
	filterObjects := make([]*NameCountFlagEntity, 0)
	for _, info := range search.Data.WordCountInfos {
		if !lo.Contains(stopwords, info.Word) {
			filterObjects = append(filterObjects, &NameCountFlagEntity{
				NameCountEntity: NameCountEntity{Name: info.Word, Count: info.Count},
				SynonymsFlag:    info.IsSynonym,
			})
		}
	}

	filterEntities := make([]*FilterEntity, 0)
	for _, info := range search.Data.ClassCountInfos {
		children := make([]*NameCountEntity, 0)
		for _, countInfo := range info.EntityCountInfos {
			children = append(children, &NameCountEntity{Name: countInfo.Alias, Count: countInfo.Count})
		}
		filterEntities = append(filterEntities, &FilterEntity{ClassName: info.ClassName, Name: info.Alias, Children: children})
	}
	resp.Filter = &FilterCondition{
		Objects:  filterObjects,
		Entities: filterEntities,
	}
	if dataVersion == constant.DataCatalogVersion {
		// 查询data catalog各字段
		u.summaryInfoDetail(ctx, catalogIds, catalogCodes, assetsMap, catalogStringIds)
		// 处理高亮
		addHighlight(assetsMap, search)
		for i, entry := range entries {
			if v, ok := assetsMap[entry.ID.Uint64()]; ok {
				entries[i] = v
			}
		}
	} else {
		u.summaryInfoDetailV2(ctx, dataViewIds, SvcIds, IndicatorIds, resourceIds, nDataMap)
		addHighlightV2(nDataMap, search)
		for i, entry := range entries {
			if v, ok := nDataMap[entry.ResourceId]; ok {
				v.ID = ModelID(entry.ResourceId)
				entries[i] = v
			}
		}
	}

	//fmt.Println("high light")
	resp.Entries = entries

	// 查询data catalog下载状态
	//accessMap, err := u.checkDownload(ctx, catalogIds)
	//if err != nil {
	//	log.WithContext(ctx).Errorf("failed to get data-catalog download status")
	//}
	//resp.addStatus(accessMap)
	//permissionMap := make(map[string]bool)

	//resp.addPermissionStatus(permissionMap)
	return resp
}

type DepInfo struct {
	OrgCode string `json:"org_code"`
	OrgName string `json:"org_name"`
}

type SubjectNodesItem struct {
	SubjectId     string `json:"subject_id"`
	SubjectName   string `json:"subject_name"`
	SubjectPathId string `json:"subject_path_id"`
}

//type UserInfo struct {
//	Uid      string     `json:"uid"`
//	UserName string     `json:"user_name"`
//	OrgInfos []*DepInfo `json:"org_info"`
//}

func GetUserInfo(ctx context.Context) *models.UserInfo {
	if val := ctx.Value(constant.UserInfoContextKey); val != nil {
		if ret, ok := val.(*models.UserInfo); ok {
			return ret
		}
	}
	return nil
}

type statusTime struct {
	status     int
	expireTime int64
}

const (
	CATALOG_STATUS_DRAFT     = 1 // 草稿
	CATALOG_STATUS_PUBLISHED = 3 // 已发布
	CATALOG_STATUS_ONLINE    = 5 // 已上线
	CATALOG_STATUS_OFFLINE   = 8 // 已下线
)

const (
	CHECK_DOWNLOAD_ACCESS_RESULT_UNAUTHED     = iota + 1 // 无权限下载
	CHECK_DOWNLOAD_ACCESS_RESULT_UNDER_REVIEW            // 审核中
	CHECK_DOWNLOAD_ACCESS_RESULT_AUTHED                  // 有下载权限
)

func CatalogPropertyCheckV1(catalog *model.TDataCatalog) error {
	// 目录不是为上线状态
	//if catalog.State != CATALOG_STATUS_ONLINE {
	//	return errorcode.Detail(errorcode.PublicDatabaseError, "资产已下线")
	//}
	// todo 放到全局静态文件中
	if catalog.OnlineStatus != "online" {
		return errorcode.Detail(errorcode.PublicDatabaseError, "资产已下线")
	}

	// if catalog.State != CATALOG_STATUS_ONLINE ||
	// 	catalog.PublishFlag == nil ||
	// 	(catalog.PublishFlag != nil && *catalog.PublishFlag == 0) {
	// 	return errorcode.Detail(errorcode.ResourcePublishDisabled, "资源已取消发布")
	// }
	// if catalog.SharedType == 3 {
	// 	return errorcode.Detail(errorcode.ResourceShareDisabled, "资源未开放共享")
	// }
	// if catalog.OpenType == 2 {
	// 	return errorcode.Detail(errorcode.ResourceOpenDisabled, "资源未向公众开放")
	// }
	return nil
}

//func (u *useCase) checkDownload(ctx context.Context, catalogIDs []uint64) (accessMap map[string]statusTime, err error) {
//	uInfo := GetUserInfo(ctx)
//	var deps []string
//	if len(uInfo.OrgInfos) > 0 {
//		deps = lo.Map(uInfo.OrgInfos, func(item *models.DepInfo, _ int) string {
//			return item.OrgCode
//		})
//	}
//
//	var catalogs []*model.TDataCatalog
//
//	catalogs, err = u.qaRepo.GetDetailByIds(ctx, []string{}, catalogIDs...)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to get catalog from db, err: %v", err)
//		return nil, errorcode.Detail(errorcode.PublicDatabaseError, err)
//	}
//
//	catalogRels := make([]*model.TDataCatalog, 0)
//	// 如果当前用户属于catalog所属部门，则直接拥有下载权限，否则需要申请
//	accessMap = make(map[string]statusTime, 0)
//	for _, catalog := range catalogs {
//		if err = CatalogPropertyCheckV1(catalog); err != nil {
//			log.WithContext(ctx).Errorf("check catalog (id: %v code: %v user: %v) download access apply forbidden, err: %v", catalog.ID, catalog.Code, uInfo.ID, err)
//			return nil, err
//		}
//
//		if lo.Contains(deps, catalog.DepartmentId) {
//			accessMap[catalog.Code] = statusTime{
//				status: CHECK_DOWNLOAD_ACCESS_RESULT_AUTHED,
//			}
//		} else {
//			catalogRels = append(catalogRels, catalog)
//		}
//	}
//
//	if len(catalogRels) == 0 {
//		return
//	}
//	// 审核通过且在有效期内的catalogs
//	var ucrs []*model.TUserDataCatalogRel
//	codes := lo.Map(catalogRels, func(item *model.TDataCatalog, _ int) string {
//		return item.Code
//	})
//	ucrs, err = u.qaRepo.GetByCodes(ctx, codes, uInfo.ID)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to get user catalog rel data (uid: %v code: %v) from db, err: %v", uInfo.ID, codes, err)
//		return nil, errorcode.Detail(errorcode.PublicDatabaseError, err)
//	}
//	for _, ucr := range ucrs {
//		var exp int64
//		if ucr.ExpiredAt != nil {
//			exp = ucr.ExpiredAt.UnixMilli()
//		}
//		accessMap[ucr.Code] = statusTime{
//			status:     CHECK_DOWNLOAD_ACCESS_RESULT_AUTHED,
//			expireTime: exp,
//		}
//	}
//
//	applies := lo.Filter(codes, func(item string, _ int) bool {
//		ucrCodes := lo.Map(ucrs, func(ucr *model.TUserDataCatalogRel, _ int) string {
//			return ucr.Code
//		})
//		// 过滤出不在审核通过的catalog
//		return !lo.Contains(ucrCodes, item)
//	})
//
//	if len(applies) == 0 {
//		return
//	}
//
//	var apply []*model.TDataCatalogDownloadApply
//	apply, err = u.qaRepo.GetByCodesV2(ctx, applies, uInfo.ID, DOWNLOAD_ACCESS_AUDIT_RESULT_UNDER_REVIEW)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to get download apply data, err info: %v", err.Error())
//		return nil, errorcode.Detail(errorcode.PublicDatabaseError, err)
//	}
//	for _, downloadApply := range apply {
//		accessMap[downloadApply.Code] = statusTime{status: CHECK_DOWNLOAD_ACCESS_RESULT_UNDER_REVIEW}
//	}
//
//	return accessMap, nil
//}

func (u *useCase) summaryInfoDetail(ctx context.Context, ids []uint64, codes []string, assetsMap map[uint64]*CogSearchSummaryInfo, idString []string) {

	// 资产详情
	catalogs, err := u.qaRepo.GetDetailByIds(ctx, nil, ids...)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get catalog by ids, err: %s", err.Error())
	}
	for _, catalog := range catalogs {
		if v, ok := assetsMap[catalog.ID]; ok {
			v.Code = catalog.Code
			v.RawTitle = catalog.Title
			v.RawDescription = catalog.Description
			//v.RawOwnerName = catalog.OwnerName
			//v.RawOrgName = catalog.DepartmentName
			if catalog.PublishedAt != nil {
				v.PublishedAt = catalog.PublishedAt.UnixMilli()
			}

		}
	}

	//catalogFavoriteInfos, err := u.dataCatalog.CheckCatalogFavorite(ctx, idString)
	//if err != nil {
	//	log.WithContext(ctx).Errorf("failed to get catalog favorite by ids, err: %s", err.Error())
	//}
	////catalogFavoriteItems := *catalogFavoriteInfos
	//for _, catalogF := range *catalogFavoriteInfos {
	//	if catalogF.ResType == "data-catalog" {
	//		for _, catalogFItem := range catalogF.Resources {
	//			catalogId := ModelID(catalogFItem.ResId)
	//			if v, ok := assetsMap[catalogId.Uint64()]; ok {
	//				if catalogFItem.IsFavored {
	//					v.FavoriteStatus = 1
	//				} else {
	//					v.FavoriteStatus = 0
	//				}
	//			}
	//		}
	//	}
	//}

	// 字段信息
	columns, err := u.qaRepo.GetByCatalogIDs(ctx, ids)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get columns by ids, err: %s", err.Error())
	}
	for _, column := range columns {
		if v, ok := assetsMap[column.CatalogID]; ok {
			v.Fields = append(v.Fields, &Field{RawFieldNameZH: column.BusinessName, RawFieldNameEN: column.TechnicalName})
		}
	}
	// 信息系统
	//infoSys, err := u.qaRepo.GetData(ctx, []int8{4}, ids)
	//if err != nil {
	//	log.WithContext(ctx).Errorf("failed to get info-system by ids, err: %s", err.Error())
	//}
	//for _, info := range infoSys {
	//	if v, ok := assetsMap[info.CatalogID]; ok {
	//		v.InfoSystemID = info.InfoKey
	//		v.RawInfoSystemName = info.InfoValue
	//	}
	//}
	// 元数据信息-数据源、schema、表名称
	mounts, err := u.qaRepo.GetByCodesV4(ctx, ids)
	//fmt.Println("*****", mounts)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get mounts by code, err: %s", err.Error())
	}

	//fmt.Println("*****", mounts)
	//tableIds := make([]uint64, 0)
	for _, mount := range mounts {
		if v, ok := assetsMap[mount.CatalogId]; ok {
			v.RawTableName = mount.TechnicalName

		}
	}
	//tableIds = lo.Uniq(tableIds)
	////fmt.Println("*****", tableIds)
	//tableInfo, err := GetTableInfo(ctx, tableIds, 1)
	//if err != nil {
	//	log.WithContext(ctx).Errorf("failed to get tableInfo by tableIds, err: %s", err.Error())
	//}
	//log.WithContext(ctx).Infof("req table info succeed, ids: %s, result: %s", ids, lo.T2(json.Marshal(tableInfo)).A)
	//tableMap := lo.SliceToMap(tableInfo, func(item *TableInfo) (uint64, *TableInfo) {
	//	return item.ID, item
	//})
	////fmt.Println("tableMap", tableMap)
	//if len(tableMap) > 0 {
	//	for _, summaryInfo := range assetsMap {
	//		if v, ok := tableMap[summaryInfo.TableID]; ok {
	//			summaryInfo.RawDataSourceName = v.DataSourceName
	//			summaryInfo.RawSchemaName = v.SchemaName
	//		}
	//	}
	//}
}

type AnalysisDims struct {
	AnalysisDimList []*AnalysisDim
}

type AnalysisDim struct {
	TableId       string `json:"table_id"`
	FieldId       string `json:"field_id"`
	BusinessName  string `json:"business_name"`
	TechnicalName string `json:"technical_name"`
	DataType      string `json:"data_type"`
}

func (u useCase) summaryInfoDetailV2(ctx context.Context, dataViewIds []string, svcIds []string, indicatorIds []string, resourceIds []string, assetsMap map[string]*CogSearchSummaryInfo) {
	fields, err := u.qaRepo.GetFieldByResourceIDs(ctx, dataViewIds)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get columns by ids, err: %s", err.Error())
	}
	for _, field := range fields {
		if v, ok := assetsMap[field.FormViewId]; ok {
			v.Fields = append(v.Fields, &Field{RawFieldNameZH: field.BusinessName, RawFieldNameEN: field.TechnicalName})
		}
	}

	ioParams, err := u.qaRepo.GetSVCFieldByResourceIDs(ctx, svcIds)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get columns by ids, err: %s", err.Error())
	}
	for _, ioParam := range ioParams {
		if v, ok := assetsMap[ioParam.ServiceId]; ok {
			v.Fields = append(v.Fields, &Field{RawFieldNameZH: ioParam.CnName, RawFieldNameEN: ioParam.EnName})
		}
	}

	analysisDims, err := u.qaRepo.GetIndicatorByResourceIDs(ctx, indicatorIds)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to get columns by ids, err: %s", err.Error())
	}
	for _, analysisDim := range analysisDims {
		if v, ok := assetsMap[analysisDim.Id]; ok {
			analysisDimVal := AnalysisDims{}
			err = json.Unmarshal([]byte(analysisDim.AnalysisDimension), &analysisDimVal.AnalysisDimList)
			if err != nil {
				continue
			}
			for _, analysisItem := range analysisDimVal.AnalysisDimList {
				v.Fields = append(v.Fields, &Field{RawFieldNameZH: analysisItem.BusinessName, RawFieldNameEN: analysisItem.TechnicalName})
			}

		}
	}
	if len(resourceIds) > 0 {
		// owner 信息
		basicSearchReq := basic_search.SearchDataResourceRequest{IDs: resourceIds, Size: 100}
		resourceInfos, err := u.basicSearch.SearchDataResource(ctx, &basicSearchReq)
		if err == nil {
			for _, resourceItem := range resourceInfos.Entries {
				subOwnerInfo := []OwnerItem{}
				for _, subOwner := range strings.Split(resourceItem.OwnerID, ",") {
					if subOwner != "" {
						subOwnerInfo = append(subOwnerInfo, OwnerItem{OwnerId: subOwner, OwnerName: ""})
					}

				}
				if v, ok := assetsMap[resourceItem.ID]; ok {
					v.Owners = subOwnerInfo
				}

			}
		}
	}

}

func addHighlight(assetsMap map[uint64]*CogSearchSummaryInfo, search *CopilotAssetSearchResp) {
	for _, entity := range search.Data.Entities {
		totalKeys := entity.TotalKeys
		entityId := uint64(lo.T2(strconv.Atoi(entity.Entity.DataCatalogId)).A)
		if v, ok := assetsMap[entityId]; ok {
			v.Title = processHighlight(totalKeys, v.RawTitle)
			v.TableName = processHighlight(totalKeys, v.RawTableName)
			v.Description = processHighlight(totalKeys, v.RawDescription)
			for _, field := range v.Fields {
				field.FieldNameZH = processHighlight(totalKeys, field.RawFieldNameZH)
				field.FieldNameEN = processHighlight(totalKeys, field.RawFieldNameEN)
			}
			v.InfoSystemName = processHighlight(totalKeys, v.RawInfoSystemName)
			v.DataSourceName = processHighlight(totalKeys, v.RawDataSourceName)
			v.SchemaName = processHighlight(totalKeys, v.RawSchemaName)
			v.OrgName = processHighlight(totalKeys, v.RawOrgName)
			v.OwnerName = processHighlight(totalKeys, v.RawOwnerName)
			v.DepartmentName = processHighlight(totalKeys, v.RawDepartmentName)
		}
	}
}

func addHighlightV2(assetsMap map[string]*CogSearchSummaryInfo, search *CopilotAssetSearchResp) {
	for _, entity := range search.Data.Entities {
		totalKeys := entity.TotalKeys
		//entityId := uint64(lo.T2(strconv.Atoi(entity.Entity.DataCatalogId)).A)
		entityId := entity.Entity.ResourceId
		if v, ok := assetsMap[entityId]; ok {
			v.Title = processHighlight(totalKeys, v.RawTitle)
			v.TableName = processHighlight(totalKeys, v.RawTableName)
			v.Description = processHighlight(totalKeys, v.RawDescription)
			for _, field := range v.Fields {
				field.FieldNameZH = processHighlight(totalKeys, field.RawFieldNameZH)
				field.FieldNameEN = processHighlight(totalKeys, field.RawFieldNameEN)
			}
			v.InfoSystemName = processHighlight(totalKeys, v.RawInfoSystemName)
			v.DataSourceName = processHighlight(totalKeys, v.RawDataSourceName)
			v.SchemaName = processHighlight(totalKeys, v.RawSchemaName)
			v.OrgName = processHighlight(totalKeys, v.RawOrgName)
			v.OwnerName = processHighlight(totalKeys, v.RawOwnerName)
			v.SubjectName = processHighlight(totalKeys, v.RawSubjectName)
			v.DepartmentName = processHighlight(totalKeys, v.RawDepartmentName)
			v.DepartmentPath = processHighlight(totalKeys, v.RawDepartmentPath)
			v.SubjectPath = processHighlight(totalKeys, v.RawSubjectPath)
		}
	}
}

func processHighlight(totalKeys []string, field string) string {
	prefix := "<span style=\"color:#FF6304;\">"
	suffix := "</span>"
	// 目前名称仅支持中英文、数字、中划线下划线，所以使用两个特殊符号作为占位符。
	prefixPlaceholder := `@`
	suffixPlaceholder := `!`
	if len(field) > 0 {
		result := field
		for _, key := range totalKeys {
			if strings.Contains(result, key) {
				buffer := prefixPlaceholder + key + suffixPlaceholder
				result = strings.ReplaceAll(result, key, buffer)
			}
		}
		result = strings.ReplaceAll(result, prefixPlaceholder, prefix)
		result = strings.ReplaceAll(result, suffixPlaceholder, suffix)
		return result
	}
	return field
}

type TableInfo struct {
	ID                 uint64         `json:"id,string"`
	Name               string         `json:"name"`                  // 表名称
	DataSourceType     int8           `json:"data_source_type"`      // 数据源类型
	DataSourceTypeName string         `json:"data_source_type_name"` // 数据源类型名称
	DataSourceID       string         `json:"data_source_id"`        // 数据源ID
	DataSourceName     string         `json:"data_source_name"`      // 数据源名称
	SchemaID           string         `json:"schema_id"`             // schema ID
	SchemaName         string         `json:"schema_name"`           // schema名称
	RowNum             int64          `json:"table_rows,string"`
	AdvancedParams     string         `json:"advanced_params"`
	AdvancedDataSlice  []AdvancedData `json:"advanced_data_slice"`
	CreateTime         int64          `json:"create_time_stamp,string"`
	UpdateTime         int64          `json:"update_time_stamp,string"`
}

type AdvancedData struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}
type IntUintFloat interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 | ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~float32 | ~float64
}

func CombineToString[T IntUintFloat | ~string](in []T, sep string) string {
	if in == nil {
		return ""
	}

	ret := ""
	for i := range in {
		if i == 0 {
			ret = fmt.Sprintf("%v", in[i])
			continue
		}

		ret = fmt.Sprintf("%s%s%v", ret, sep, in[i])
	}
	return ret
}

func GetTableInfo(ctx context.Context, tableIDs []uint64, offset int) ([]*TableInfo, error) {
	val := url.Values{}
	val.Add("ids", CombineToString(tableIDs, ","))
	val.Add("offset", strconv.Itoa(offset))
	val.Add("limit", "1000")
	//fmt.Println(settings.GetConfig().DepServicesConf.MetaDataMgmHost+"/api/metadata-manage/v1/table", "*********")
	buf, err := util.DoHttpGet(settings.GetConfig().DepServicesConf.MetaDataMgmHost+"/api/metadata-manage/v1/table", nil, val)
	if err != nil {
		return nil, err
	}

	//fmt.Println(buf, "*************")
	var tables struct {
		Data []*TableInfo `json:"data"`
	}
	if err = json.Unmarshal(buf, &tables); err != nil {
		return nil, err
	}
	for _, data := range tables.Data {
		if data.AdvancedParams != "" {
			if err := json.Unmarshal([]byte(data.AdvancedParams), &data.AdvancedDataSlice); err != nil {
				log.WithContext(ctx).Error(err.Error())
			}
		}
	}
	return tables.Data, nil
}
