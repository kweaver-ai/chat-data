package knowledge_build

import (
	"context"
	"regexp"

	"github.com/jinzhu/copier"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/models/response"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/common/util"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/samber/lo"
)

var emptyStr = ""

type ModelDeleteParam struct {
	ModelDelete `param_type:"uri"`
}

type ModelDelete struct {
	GraphID int `json:"graph_id" form:"graph_id" query:"graph_id" uri:"graph_id"`
}

type ModelDetailParam struct {
	ModelDetail `param_type:"body"`
}

type ModelDetail struct {
	ID              string         `json:"id"`                // 主键ID，uuid
	BusinessName    string         `json:"business_name"`     // 模型名称，业务名称
	TechnicalName   string         `json:"technical_name"`    // 模型技术名称
	CatalogID       string         `json:"catalog_id"`        // 目录的主键ID
	CatalogName     string         `json:"catalog_name"`      //目录的名称
	DataViewID      string         `json:"data_view_id"`      // 目录带的元数据视图ID
	DataViewName    string         `json:"data_view_name"`    // 视图名称
	GraphID         int            `json:"graph_id"`          //当前模型在图谱ID，整数
	SubjectID       string         `json:"subject_id"`        // 业务对象ID
	SubjectName     string         `json:"subject_name"`      // 业务对象名称
	Description     string         `json:"description"`       // 描述
	CreatedAt       int64          `json:"created_at"`        // 创建时间
	UpdatedAt       int64          `json:"updated_at"`        // 更新时间
	HasGraph        bool           `json:"has_graph"`         // 是否构建过图谱
	DisplayFieldKey string         `json:"display_field_key"` // 显示字段的key
	MetaModelSlice  []*ModelDetail `json:"meta_model_slice"`  // 元模型的信息
	Fields          []*TModelField `json:"fields"`            // 元模型字段
	Relations       []*Relation    `json:"relations"`         // 复合模型的关系
}

type Relation struct {
	ID                  string          `json:"id" binding:"omitempty,uuid"`                        // 关系ID
	BusinessName        string          `json:"business_name" binding:"required,VerifyName"`        // 业务名称
	TechnicalName       string          `json:"technical_name" binding:"required,VerifyNameEN"`     // 模型技术名称
	StartDisplayFieldID string          `json:"start_display_field_id" binding:"omitempty,uuid"`    // 起点显示属性
	EndDisplayFieldID   string          `json:"end_display_field_id" binding:"omitempty,uuid"`      // 终点显示属性
	Description         string          `json:"description"  binding:"TrimSpace,omitempty,lte=255"` // 描述
	Links               []*RelationLink `json:"links" binding:"required,gt=0,dive"`                 // 关联关系匹配的字段
}

type RelationLink struct {
	RelationID         string `json:"relation_id"  binding:"omitempty,uuid"`   // 模型关系ID
	StartModelID       string `json:"start_model_id"  binding:"required,uuid"` // 起点元模型ID
	StartModelName     string `json:"start_model_name"`                        // 起点模型名称
	StartModelTechName string `json:"start_model_tech_name"`                   // 起点模型技术名称
	StartFieldID       string `json:"start_field_id"  binding:"required,uuid"` // 起点字段ID
	StartFieldName     string `json:"start_field_name"`                        // 开始字段名称
	StartFieldTechName string `json:"start_field_tech_name"`                   // 开始字段名称
	EndModelID         string `json:"end_model_id"  binding:"required,uuid"`   // 终点元模型ID
	EndModelName       string `json:"end_model_name"`                          // 终点模型名称
	EndModelTechName   string `json:"end_model_tech_name"`                     // 终点模型技术名称
	EndFieldID         string `json:"end_field_id"  binding:"required,uuid"`   // 终点字段ID
	EndFieldName       string `json:"end_field_name"`                          // 终点字段名称
	EndFieldTechName   string `json:"end_field_tech_name"`                     // 终点字段名称
}

// TModelField 元模型字段表
type TModelField struct {
	ID            uint64 `json:"id"`             // 主键ID
	FieldID       string `json:"field_id"`       // 视图字段ID
	ModelID       string `json:"model_id"`       // 元模型ID
	TechnicalName string `json:"technical_name"` // 列技术名称
	BusinessName  string `json:"business_name"`  // 列业务名称
	DataType      string `json:"data_type"`      // 数据类型
	DataLength    int32  `json:"data_length"`    // 数据长度
	DataAccuracy  int32  `json:"data_accuracy"`  // 数据精度
	PrimaryKey    bool   `json:"primary_key"`    // 是否是主键,0不是，1是
	IsNullable    string `json:"is_nullable"`    // 是否为空
	Comment       string `json:"comment"`        // 字段注释
}

// ClearInvalidChar  去除非法字符， 这个也可以使用参数验证器做
func (d *ModelDetail) ClearInvalidChar() {
	//实体类名称
	for i := range d.MetaModelSlice {
		d.MetaModelSlice[i].TechnicalName = clearInvalidTechnicalNameChar(d.MetaModelSlice[i].TechnicalName)
		d.MetaModelSlice[i].BusinessName = clearInvalidBusinessNameChar(d.MetaModelSlice[i].BusinessName)
		for j := range d.MetaModelSlice[i].Fields {
			d.MetaModelSlice[i].Fields[j].TechnicalName = clearInvalidTechnicalNameChar(d.MetaModelSlice[i].Fields[j].TechnicalName)
			d.MetaModelSlice[i].Fields[j].BusinessName = clearInvalidBusinessNameChar(d.MetaModelSlice[i].Fields[j].BusinessName)
		}
		d.MetaModelSlice[i].ClearInvalidChar()
	}
	//关系里面的
	for i := range d.Relations {
		d.Relations[i].BusinessName = clearInvalidBusinessNameChar(d.Relations[i].BusinessName)
		d.Relations[i].TechnicalName = clearInvalidTechnicalNameChar(d.Relations[i].TechnicalName)
		for j := range d.Relations[i].Links {
			d.Relations[i].Links[j].StartModelName = clearInvalidBusinessNameChar(d.Relations[i].Links[j].StartModelName)
			d.Relations[i].Links[j].StartModelTechName = clearInvalidTechnicalNameChar(d.Relations[i].Links[j].StartModelTechName)
			d.Relations[i].Links[j].StartFieldName = clearInvalidBusinessNameChar(d.Relations[i].Links[j].StartFieldName)
			d.Relations[i].Links[j].StartFieldTechName = clearInvalidTechnicalNameChar(d.Relations[i].Links[j].StartFieldTechName)
			d.Relations[i].Links[j].EndModelName = clearInvalidBusinessNameChar(d.Relations[i].Links[j].EndModelName)
			d.Relations[i].Links[j].EndModelTechName = clearInvalidTechnicalNameChar(d.Relations[i].Links[j].EndModelTechName)
			d.Relations[i].Links[j].EndFieldName = clearInvalidBusinessNameChar(d.Relations[i].Links[j].EndFieldName)
			d.Relations[i].Links[j].EndFieldTechName = clearInvalidTechnicalNameChar(d.Relations[i].Links[j].EndFieldTechName)
		}
	}
	for i := range d.Fields {
		d.Fields[i].Comment = cutValidBusinessNameChar(d.Fields[i].BusinessName, 150)
	}
}

// DeleteGraph 删除图谱
func (s *Server) DeleteGraph(ctx context.Context, info *ModelDelete) (*response.IntIDResp, error) {
	knwID := settings.GetConfig().GraphModelConfig.KnwID

	if err := s.adProxy.DeleteGraphOtl(ctx, knwID, info.GraphID); err != nil {
		return nil, err
	}
	return response.NewIntIDResp(info.GraphID), nil
}

// CreateGraphIfNotExist  更新图谱
func (s *Server) createGraphIfNotExist(ctx context.Context, detail *ModelDetail) (*knowledge_network.GraphDetail, error) {
	// AD 创建图谱的接口没有重名校验，特殊情况下容易造成图谱重名，特加锁保持唯一
	s.graphBuilderLock.Lock()
	defer s.graphBuilderLock.Unlock()

	knwID := settings.GetConfig().GraphModelConfig.KnwID
	detail.ClearInvalidChar()
	//没有图谱就建的新的
	if detail.GraphID <= 0 {
		graphID, err := s.adProxy.QueryGraphByName(ctx, knwID, detail.BusinessName)
		if err != nil {
			log.Warnf("QueryGraphByName error %v", err.Error())
		}
		if graphID > 0 {
			//删除原来的
			if err = s.adProxy.DeleteGraphOtl(ctx, knwID, graphID); err != nil {
				return nil, err
			}
		}
		//新建
		if err = s.createEmptyGraph(ctx, detail); err != nil {
			return nil, err
		}
	}
	//查询图谱详情
	graphDetail, err := s.adProxy.GraphDetail(ctx, detail.GraphID)
	if err != nil {
		//如果图谱不存在，重新新建一个
		if errorcode.Contains(err, knowledge_network.GraphNotExistsCode) {
			if err = s.createEmptyGraph(ctx, detail); err != nil {
				return nil, err
			}
		}
		return nil, err
	}
	return graphDetail, nil
}

// UpdateGraph  更新图谱
func (s *Server) UpdateGraph(ctx context.Context, detail *ModelDetail) (*response.IntIDResp, error) {
	//查询图谱信息，没有就创建一个新的
	graphDetail, err := s.createGraphIfNotExist(ctx, detail)
	if err != nil {
		return nil, err
	}
	//调用全局的savenocheck
	graphNoCheck := genGraphNoCheck(graphDetail, detail)
	if err = s.adProxy.SchemeSaveNoCheck(ctx, graphNoCheck); err != nil {
		return nil, err
	}
	//全部更新
	graphSchema := genNewGraphDetail(graphNoCheck)
	if err = s.adProxy.UpdateSchema(ctx, detail.GraphID, graphSchema); err != nil {
		return nil, err
	}
	return response.NewIntIDResp(detail.GraphID), nil
}

func (s *Server) createEmptyGraph(ctx context.Context, detail *ModelDetail) (err error) {
	knwID := settings.GetConfig().GraphModelConfig.KnwID
	dsid := settings.GetConfig().GraphModelConfig.AfDatasourceID

	//基础信息
	baseInfoReq := &knowledge_network.CreateGraphReq{
		GraphProcess: &knowledge_network.CreateGraphProcess{
			GraphDes:  &detail.Description,
			GraphName: &detail.BusinessName,
		},
		GraphStep: "graph_baseInfo",
		KnwId:     knwID,
	}
	detail.GraphID, err = s.adProxy.CreateGraphOtl(ctx, baseInfoReq)
	if err != nil {
		return err
	}
	//add,不知道干啥的，但是必须有
	otlAddReq := &knowledge_network.CreateGraphReq{
		GraphProcess: []*knowledge_network.CreateGraphProcess{
			{
				OntologyName: &emptyStr,
				OntologyDes:  &emptyStr,
			},
		},
		GraphStep:   "graph_otl",
		Updateoradd: "add",
	}
	if err = s.adProxy.UpdateGraphOtl(ctx, detail.GraphID, otlAddReq); err != nil {
		return err
	}
	//数据源
	graphDataSource := &knowledge_network.CreateGraphReq{
		GraphProcess: []int{dsid},
		GraphStep:    "graph_ds",
	}
	if err = s.adProxy.UpdateGraphOtl(ctx, detail.GraphID, graphDataSource); err != nil {
		return err
	}
	//初始化未分组
	subGraphInfoSlice, err := s.adProxy.GetSubGraph(ctx, detail.GraphID, "")
	if err != nil {
		return err
	}
	if len(subGraphInfoSlice) <= 0 {
		emptyUngroupData := []*knowledge_network.SubGraphBody{
			{
				SubgraphId: subGraphInfoSlice[0].ID,
				Name:       "ungrouped",
				Entity:     make([]*knowledge_network.GraphEntity, 0),
				Edge:       make([]*knowledge_network.GraphEdge, 0),
			},
		}
		if err = s.adProxy.UpdateSubGraph(ctx, detail.GraphID, emptyUngroupData); err != nil {
			return err
		}
	}
	return nil
}

func genGraphNoCheck(graphDetail *knowledge_network.GraphDetail, modelDetail *ModelDetail) *knowledge_network.GraphNoCheck {

	//复制详情的数据
	graphNoCheck := graphDetail.GenNoCheckWithDeleteInfo()
	graphNoCheck.GraphBaseInfo.GraphName = modelDetail.BusinessName
	graphNoCheck.GraphBaseInfo.GraphDes = modelDetail.Description
	//处理新增和更新的
	graphEntityDict := lo.SliceToMap(graphNoCheck.GraphOtl.Entity, func(item *knowledge_network.GraphEntity) (string, int) {
		return item.Name, lo.IndexOf(graphNoCheck.GraphOtl.Entity, item)
	})
	graphEdgeDict := lo.SliceToMap(graphNoCheck.GraphOtl.Edge, func(item *knowledge_network.GraphEdge) (string, int) {
		return item.Name, lo.IndexOf(graphNoCheck.GraphOtl.Edge, item)
	})
	metaModelDict := lo.SliceToMap(modelDetail.MetaModelSlice, func(item *ModelDetail) (string, *ModelDetail) {
		return item.ID, item
	})
	//处理实体
	for _, metaModelInfo := range modelDetail.MetaModelSlice {
		//实体
		entity := genGraphEntity(metaModelDict, metaModelInfo.ID)
		if entity == nil {
			continue
		}
		if index, ok := graphEntityDict[metaModelInfo.TechnicalName]; !ok {
			graphNoCheck.GraphOtl.Entity = append(graphNoCheck.GraphOtl.Entity, entity)
			graphNoCheck.GraphKMap.Entity = append(graphNoCheck.GraphKMap.Entity, otlEntity2KMapEntity(entity))
		} else {
			graphNoCheck.MergeGraphEntity(index, entity)
			graphNoCheck.MergeGraphKMEntity(index, otlEntity2KMapEntity(entity))
		}
		//file
		file := genKMFileByMetaModel(metaModelInfo)
		graphNoCheck.GraphKMap.Files = append(graphNoCheck.GraphKMap.Files, file)
	}
	//过滤，保证唯一
	graphNoCheck.GraphKMap.Files = lo.UniqBy(graphNoCheck.GraphKMap.Files, func(item *knowledge_network.GraphKMFile) string {
		if len(item.Files) <= 0 {
			return ""
		}
		return item.Files[0].FileSource
	})
	//处理关系
	for _, relation := range modelDetail.Relations {
		for _, link := range relation.Links {
			//关系
			graphEdge := genGraphEdge(relation, link)
			if graphEdge == nil {
				continue
			}
			if index, ok := graphEdgeDict[relation.TechnicalName]; !ok {
				graphNoCheck.GraphOtl.Edge = append(graphNoCheck.GraphOtl.Edge, graphEdge)
				graphNoCheck.GraphKMap.Edge = append(graphNoCheck.GraphKMap.Edge, otlEdge2KMapEdge(graphEdge, link))
			} else {
				graphNoCheck.MergeGraphEdge(index, graphEdge)
				graphNoCheck.MergeGraphKMEdge(index, otlEdge2KMapEdge(graphEdge, link))
			}
		}
	}
	return graphNoCheck
}

func genKMFileByMetaModel(metaModelInfo *ModelDetail) *knowledge_network.GraphKMFile {
	return &knowledge_network.GraphKMFile{
		DsId:        settings.GetConfig().GraphModelConfig.AfDatasourceID,
		DataSource:  "AnyFabric",
		DsPath:      "",
		ExtractType: "standardExtraction",
		ExtractRules: []*knowledge_network.ExtractRule{
			{
				EntityType: metaModelInfo.BusinessName,
				Property: lo.Times(len(metaModelInfo.Fields), func(index int) *knowledge_network.ExtractRuleProp {
					return &knowledge_network.ExtractRuleProp{
						ColumnName:    metaModelInfo.Fields[index].TechnicalName,
						PropertyField: metaModelInfo.Fields[index].TechnicalName,
					}
				}),
			},
		},
		Files: []*knowledge_network.ExtractFile{
			{
				FileName:   metaModelInfo.BusinessName,
				FilePath:   "",
				FileSource: metaModelInfo.DataViewID,
			},
		},
		X: 0,
		Y: 0,
	}
}

func genNewGraphDetail(graphDetailNoCheck *knowledge_network.GraphNoCheck) *knowledge_network.GraphSchema {
	graphSchema := &knowledge_network.GraphSchema{
		GraphStep: "graph_KMap",
		GraphProcess: knowledge_network.GraphProcess{
			Entity: make([]*knowledge_network.GraphKMEntity, 0),
			Edge:   make([]*knowledge_network.GraphKMEdge, 0),
			Files:  make([]*knowledge_network.GraphKMFile, 0),
		},
	}
	copier.Copy(&graphSchema.GraphProcess.Entity, &graphDetailNoCheck.GraphKMap.Entity)
	copier.Copy(&graphSchema.GraphProcess.Edge, &graphDetailNoCheck.GraphKMap.Edge)
	copier.Copy(&graphSchema.GraphProcess.Files, &graphDetailNoCheck.GraphKMap.Files)
	return graphSchema
}

func genGraphEntity(metaModelDict map[string]*ModelDetail, modelID string) *knowledge_network.GraphEntity {
	modelDetail, ok := metaModelDict[modelID]
	if !ok {
		return nil
	}
	primaryKey := ""
	for _, prop := range modelDetail.Fields {
		if prop.PrimaryKey {
			primaryKey = prop.TechnicalName
		}
	}
	allFieldName := lo.Times(len(modelDetail.Fields), func(index int) string {
		return modelDetail.Fields[index].TechnicalName
	})
	newEntity := &knowledge_network.GraphEntity{
		EntityId:           modelDetail.ID,
		EntityType:         modelDetail.BusinessName,
		Name:               modelDetail.TechnicalName,
		Description:        modelDetail.Description,
		Alias:              modelDetail.BusinessName,
		Synonym:            make([]any, 0),
		DefaultTag:         modelDetail.DisplayFieldKey,
		PropertiesIndex:    allFieldName,
		SearchProp:         modelDetail.DisplayFieldKey,
		PrimaryKey:         []string{primaryKey},
		VectorGeneration:   []string{},
		X:                  float64(200 + util.RandomInt(200)),
		Y:                  float64(200 + util.RandomInt(200)),
		Icon:               "empty",
		Shape:              "circle",
		Size:               "0.5x",
		FillColor:          "rgba(84,99,156,1)",
		StrokeColor:        "rgba(84,99,156,1)",
		TextColor:          "rgba(0,0,0,1)",
		TextPosition:       "top",
		TextWidth:          15,
		IndexDefaultSwitch: false,
		TextType:           "adaptive",
		SourceType:         "manual",
		Model:              "",
		TaskId:             "",
		IconColor:          "#ffffff",
	}
	for _, field := range modelDetail.Fields {
		newEntity.Properties = append(newEntity.Properties, knowledge_network.EntityProperty{
			Name:        field.TechnicalName,
			Description: field.Comment,
			Alias:       field.BusinessName,
			DataType:    typeMapping(field.DataType),
		})
	}
	return newEntity
}

func genGraphEdge(relation *Relation, link *RelationLink) *knowledge_network.GraphEdge {
	return &knowledge_network.GraphEdge{
		Relations:          []string{link.StartModelTechName, relation.TechnicalName, link.EndModelTechName},
		EdgeId:             relation.ID,
		Name:               relation.TechnicalName,
		Description:        relation.Description,
		Alias:              relation.BusinessName,
		PropertiesIndex:    make([]string, 0),
		PrimaryKey:         make([]string, 0),
		DefaultTag:         "",
		Properties:         make([]any, 0),
		Colour:             "rgba(240,227,79,1)",
		Shape:              "line",
		Width:              "0.25x",
		SourceType:         "manual",
		IndexDefaultSwitch: false,
		Model:              "",
	}
}

func otlEntity2KMapEntity(entity *knowledge_network.GraphEntity) *knowledge_network.GraphKMEntity {
	kmEntity := &knowledge_network.GraphKMEntity{
		Name:        entity.Name,
		EntityType:  entity.EntityType,
		X:           200,
		Y:           200,
		PropertyMap: make([]*knowledge_network.PropertyKMMap, 0),
	}
	for _, prop := range entity.Properties {
		kmEntity.PropertyMap = append(kmEntity.PropertyMap, &knowledge_network.PropertyKMMap{
			EntityProp: prop.Name,
			OtlProp:    prop.Name,
		})
	}
	return kmEntity
}

func otlEdge2KMapEdge(entity *knowledge_network.GraphEdge, link *RelationLink) *knowledge_network.GraphKMEdge {
	return &knowledge_network.GraphKMEdge{
		Relations:   entity.Relations,
		PropertyMap: make([]any, 0),
		EntityType:  "",
		RelationMap: &knowledge_network.RelationMap{
			BeginClassProp: link.StartFieldTechName,
			Equation:       "等于",
			EndClassProp:   link.EndFieldTechName,
		},
	}
}

func typeMapping(viewType string) string {
	switch viewType {
	case "int":
		return "integer"
	case "bool":
		return "boolean"
	case "char", "varchar", "time":
		return "string"
	case "float", "decimal", "date", "datetime":
		return viewType
	default:
		return "string"
	}
}

// clearInvalidBusinessNameChar 去除中英文，数字，及下划线 外的字符
func clearInvalidBusinessNameChar(input string) string {
	// 匹配中文、英文、数字和下划线以外的字符
	reg := regexp.MustCompile(`[^\p{Han}a-zA-Z0-9_]`)
	return reg.ReplaceAllString(input, "")
}

func cutValidBusinessNameChar(input string, n int) string {
	input = clearInvalidBusinessNameChar(input)
	cmts := []rune(input)
	if len(cmts) <= n {
		return input
	}
	return string(cmts[:n])
}

// clearInvalidTechnicalNameChar  去除英文，数字，及下划线 外的字符
func clearInvalidTechnicalNameChar(input string) string {
	// 匹配非英文、数字、下划线的字符
	reg := regexp.MustCompile(`[^a-zA-Z0-9_]`)
	return reg.ReplaceAllString(input, "")
}
