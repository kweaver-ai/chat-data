package copilot

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/client"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"go.uber.org/zap"
)

// HitCounter 认知搜索命中计数器
type HitCounter struct {
	SearchWords          []string //按照分词的顺序记录，用来最后给分词排序
	SearchWordsCountInfo *client.Counter
	SearchWordsMap       map[string]client.WordCountInfo  //分词统计的map
	ClassCountInfoMap    map[string]client.ClassCountInfo //实体类的统计数量集合
	HitKeyCountInfo      *client.Counter                  //每个资产命中的key
	DataAssetHitKeyInfo  *client.Counter                  //每个资产命中的key集合
}

// NewHitCounter   使用分词结果构建
func NewHitCounter(queryCuts []client.QueryCut) *HitCounter {
	hitObj := &HitCounter{}
	hitObj.SearchWords, hitObj.SearchWordsMap = genWordsCountContainer(queryCuts)
	hitObj.ClassCountInfoMap = make(map[string]client.ClassCountInfo)
	hitObj.SearchWordsCountInfo = client.NewCounter()
	hitObj.HitKeyCountInfo = client.NewCounter()
	return hitObj
}

func (h *HitCounter) recordHitKeys(vid string, startInfo client.SearchStartInfo) {
	for _, key := range startInfo.Hit.Keys {
		//记录下每个结果的命中Key
		h.SearchWordsCountInfo.Record(vid, key)
		h.HitKeyCountInfo.Record(key, vid)
	}
}

func (h *HitCounter) recordStartClass(startInfo client.SearchStartInfo) client.ClassCountInfo {
	classCountInfo, ok := h.ClassCountInfoMap[startInfo.Alias]
	if !ok {
		classCountInfo = client.ClassCountInfo{
			ClassName:        startInfo.ClassName,
			Alias:            startInfo.Alias,
			Count:            0,
			EntityCounter:    client.NewCounter(),
			EntityCountInfos: make([]client.EntityCountInfo, 0),
		}
	}
	h.ClassCountInfoMap[startInfo.Alias] = classCountInfo
	return classCountInfo
}

func (h *HitCounter) recordStartEntity(classCountInfo client.ClassCountInfo, startInfo client.SearchStartInfo, vid string) {
	classCountInfo.EntityCounter.Record(startInfo.Name, vid)
}

// Record  根据每个起点的信息，统计命中信息
func (h *HitCounter) Record(vid string, starts []client.SearchStartInfo) {
	for _, startInfo := range starts {
		//统计关键词
		h.recordHitKeys(vid, startInfo)
		//统计实体类命中数量
		classCountInfo := h.recordStartClass(startInfo)
		//统计实体命中数量
		h.recordStartEntity(classCountInfo, startInfo, vid)
	}
}

// WordCountInfos 返回关键词的数量统计
func (h *HitCounter) WordCountInfos() (results []client.WordCountInfo) {
	for _, word := range h.SearchWords {
		info, ok := h.SearchWordsMap[word]
		if !ok {
			info.Word = word
			info.IsSynonym = false
		}
		if ok {
			info.Count = h.HitKeyCountInfo.Count(word)
		}
		if info.Count <= 0 {
			info.Count = h.HitKeyCountInfo.ContainsCount(word)
		}
		//fmt.Println(info, "&&&&&&", h.HitKeyCountInfo)
		if info.Count > 0 {
			results = append(results, info)
		}
	}
	return results
}

// ClassCountInfo 返回实体类的命中统计
func (h *HitCounter) ClassCountInfo() (results []client.ClassCountInfo) {
	results = make([]client.ClassCountInfo, 0)
	for _, classCountInfo := range h.ClassCountInfoMap {
		entityNames := classCountInfo.EntityCounter.Keys()
		for _, entityName := range entityNames {
			entityCountInfo := client.EntityCountInfo{
				Alias: entityName,
				Count: classCountInfo.EntityCounter.Count(entityName),
			}
			classCountInfo.EntityCountInfos = append(classCountInfo.EntityCountInfos, entityCountInfo)
			classCountInfo.Count += entityCountInfo.Count
		}
		sort.Slice(classCountInfo.EntityCountInfos, func(i, j int) bool {
			return classCountInfo.EntityCountInfos[i].Count < classCountInfo.EntityCountInfos[j].Count
		})
		results = append(results, classCountInfo)
	}
	//排序，按照命中数量的多少排序
	sort.Slice(results, func(i, j int) bool {
		return results[i].Count < results[j].Count
	})
	return results
}

func (h *HitCounter) AssetHitKeys(vid string) []string {
	return h.SearchWordsCountInfo.ValueKeys(vid)
}

func genWordsCountContainer(queryCuts []client.QueryCut) ([]string, map[string]client.WordCountInfo) {
	searchWordsMap := make(map[string]client.WordCountInfo)
	searchWords := make([]string, 0)
	for _, info := range queryCuts {
		searchWordsMap[info.Source] = client.WordCountInfo{
			Word:      info.Source,
			Count:     0,
			IsSynonym: false,
		}
		searchWords = append(searchWords, info.Source)
		for _, synonym := range info.Synonym {
			searchWordsMap[synonym] = client.WordCountInfo{
				Word:      synonym,
				Count:     0,
				IsSynonym: true,
			}
			searchWords = append(searchWords, synonym)
		}
	}
	return searchWords, searchWordsMap
}

// readProperties 从实体节点中读取需要的属性
func readProperties(outputs client.GraphSynSearchDAGOutputs) *CopilotAssetSearchResp {
	//子图vid结构map
	subgraphDict := make(map[string]client.GraphSynSearchSubgraphPath)
	for _, path := range outputs.Subgraphs {
		subgraphDict[path.End] = path
	}
	hitObj := NewHitCounter(outputs.QueryCuts)

	itemList := make([]client.AssetSearchAnswerEntity, 0, len(outputs.Entities))
	for _, entity := range outputs.Entities {
		//生成结果对象
		obj, err := readEntityObj(entity.Entity)
		if err != nil {
			log.Warnf("read entity error %v", err)
			continue
		}
		obj.IsPermissions = entity.IsPermissions

		//获取起点
		infos := make([]client.SearchStartInfo, 0)
		for _, en := range entity.SearchStartInfos {
			infos = append(infos, en)
		}
		//记录统计数据
		hitObj.Record(entity.Entity.Id, infos)

		item := client.AssetSearchAnswerEntity{
			SearchStartInfos: infos,
			Entity:           *obj,
			Subgraph:         subgraphDict[entity.Entity.Id],
			Score:            util.RoundWithPrecision(entity.Score, 2),
			TotalKeys:        hitObj.AssetHitKeys(obj.VID),
		}
		itemList = append(itemList, item)
	}
	return &CopilotAssetSearchResp{
		Data: client.AssetSearchData{
			Total:           len(outputs.Entities),
			Entities:        itemList,
			QueryCuts:       outputs.QueryCuts,
			WordCountInfos:  hitObj.WordCountInfos(),
			ClassCountInfos: hitObj.ClassCountInfo(),
		},
	}
}

func readPropertiesFormView(outputs client.GraphSynSearchDAGOutputs) *CopilotAssetSearchResp {
	//子图vid结构map
	subgraphDict := make(map[string]client.GraphSynSearchSubgraphPath)
	for _, path := range outputs.Subgraphs {
		subgraphDict[path.End] = path
	}
	hitObj := NewHitCounter(outputs.QueryCuts)

	itemList := make([]client.AssetSearchAnswerEntity, 0, len(outputs.Entities))
	for _, entity := range outputs.Entities {
		//生成结果对象
		obj, err := readEntityObj(entity.Entity)
		if err != nil {
			log.Warnf("read entity error %v", err)
			continue
		}
		obj.IsPermissions = entity.IsPermissions
		obj.AssetType = "3"
		obj.ResourceName = obj.BusinessName
		obj.ResourceId = obj.FormViewUuid
		obj.Code = obj.FormViewCode

		//获取起点
		infos := make([]client.SearchStartInfo, 0)
		for _, en := range entity.SearchStartInfos {
			infos = append(infos, en)
		}
		//记录统计数据
		hitObj.Record(entity.Entity.Id, infos)

		item := client.AssetSearchAnswerEntity{
			SearchStartInfos: infos,
			Entity:           *obj,
			Subgraph:         subgraphDict[entity.Entity.Id],
			Score:            util.RoundWithPrecision(entity.Score, 2),
			TotalKeys:        hitObj.AssetHitKeys(obj.VID),
		}
		itemList = append(itemList, item)
	}
	return &CopilotAssetSearchResp{
		Data: client.AssetSearchData{
			Total:           len(outputs.Entities),
			Entities:        itemList,
			QueryCuts:       outputs.QueryCuts,
			WordCountInfos:  hitObj.WordCountInfos(),
			ClassCountInfos: hitObj.ClassCountInfo(),
		},
	}
}

func readEntityObj(entity client.Entity) (*client.AssetSearchEntity, error) {
	props := make(map[string]any)
	if len(entity.Properties) <= 0 {
		return nil, fmt.Errorf("empty prop entity %v", entity)
	}
	for _, prop := range entity.Properties[0].Props {
		props[prop.Name] = prop.Value
	}
	obj := new(client.AssetSearchEntity)
	bs, _ := json.Marshal(props)
	if err := json.Unmarshal(bs, obj); err != nil {
		log.Error("copy props error", zap.Error(err), zap.Any("source", string(bs)))
		return nil, fmt.Errorf("copy props error")
	}
	obj.VID = entity.Id
	obj.Type = entity.Alias
	//处理下资产描述
	obj.DescriptionName = ""
	if strings.Contains(obj.Description, "NULL") {
		obj.Description = ""
	}
	if strings.Contains(obj.MetadataSchema, "NULL") {
		obj.MetadataSchema = ""
	}
	if strings.Contains(obj.Datasource, "NULL") {
		obj.Datasource = ""
	}
	if strings.Contains(obj.Department, "NULL") {
		obj.Department = ""
	}
	if strings.Contains(obj.DepartmentPath, "NULL") {
		obj.DepartmentPath = ""
	}
	if strings.Contains(obj.SubjectId, "NULL") {
		obj.SubjectId = ""
	}
	if strings.Contains(obj.SubjectName, "NULL") {
		obj.SubjectName = ""
	}
	if strings.Contains(obj.SubjectPath, "NULL") {
		obj.SubjectPath = ""
	}
	if strings.Contains(obj.TechnicalName, "NULL") {
		obj.TechnicalName = ""
	}
	if strings.Contains(obj.OwnerID, "NULL") {
		obj.OwnerID = ""
	}
	if strings.Contains(obj.DepartmentId, "NULL") {
		obj.DepartmentId = ""
	}
	if strings.Contains(obj.InfoSystemId, "NULL") {
		obj.InfoSystemId = ""
	}
	if strings.Contains(obj.InfoSystemName, "NULL") {
		obj.InfoSystemName = ""
	}
	if strings.Contains(obj.PublishStatus, "NULL") {
		obj.PublishStatus = ""
	}
	return obj, nil
}
