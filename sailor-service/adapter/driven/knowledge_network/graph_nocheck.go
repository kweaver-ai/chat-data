package knowledge_network

import (
	"context"

	"github.com/jinzhu/copier"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
)

type GraphNoCheck struct {
	GraphId       int              `json:"graph_id"`
	GraphBaseInfo GraphBaseInfo    `json:"graph_baseInfo"`
	GraphDs       []int            `json:"graph_ds"`
	GraphOtl      *GraphNoCheckOtl `json:"graph_otl"`
	GraphKMap     *GraphKMap       `json:"graph_KMap"`
}

type GraphNoCheckOtl struct {
	Entity       []*GraphEntity `json:"entity"`
	Edge         []*GraphEdge   `json:"edge"`
	UsedTask     []int          `json:"used_task"`
	Id           int            `json:"id"`
	OntologyId   string         `json:"ontology_id"`
	OntologyName string         `json:"ontology_name"`
	OntologyDes  string         `json:"ontology_des"`
}

type GraphKMEntity struct {
	Name        string           `json:"name"`
	EntityType  string           `json:"entity_type"`
	X           int              `json:"x"`
	Y           float64          `json:"y"`
	PropertyMap []*PropertyKMMap `json:"property_map"`
}

type GraphKMEdge struct {
	Relations   []string      `json:"relations"`
	EntityType  string        `json:"entity_type"`
	PropertyMap []interface{} `json:"property_map"`
	RelationMap *RelationMap  `json:"relation_map"`
}

type GraphKMFile struct {
	DsId         int            `json:"ds_id"`
	DataSource   string         `json:"data_source"`
	DsPath       string         `json:"ds_path"`
	ExtractType  string         `json:"extract_type"`
	ExtractRules []*ExtractRule `json:"extract_rules"`
	X            int            `json:"x"`
	Y            int            `json:"y"`
	Files        []*ExtractFile `json:"files"`
}

type ExtractRule struct {
	EntityType string             `json:"entity_type"`
	Property   []*ExtractRuleProp `json:"property"`
}
type ExtractRuleProp struct {
	ColumnName    string `json:"column_name"`
	PropertyField string `json:"property_field"`
}
type ExtractFile struct {
	FileName   string `json:"file_name"`
	FilePath   string `json:"file_path"`
	FileSource string `json:"file_source"`
}

type RelationMap struct {
	BeginClassProp   string `json:"begin_class_prop"`
	EquationBegin    string `json:"equation_begin"`
	RelationBeginPro string `json:"relation_begin_pro"`
	Equation         string `json:"equation"`
	RelationEndPro   string `json:"relation_end_pro"`
	EquationEnd      string `json:"equation_end"`
	EndClassProp     string `json:"end_class_prop"`
}

type PropertyKMMap struct {
	EntityProp string `json:"entity_prop"`
	OtlProp    string `json:"otl_prop"`
}

type GraphKMap struct {
	Entity []*GraphKMEntity `json:"entity"`
	Edge   []*GraphKMEdge   `json:"edge"`
	Files  []*GraphKMFile   `json:"files"`
}

func (g *GraphNoCheck) MergeGraphEntity(sourceIndex int, newEntity *GraphEntity) {
	if len(g.GraphOtl.Entity) <= 0 {
		return
	}
	sourceEntity := g.GraphOtl.Entity[sourceIndex]
	id := sourceEntity.EntityId
	copier.Copy(sourceEntity, newEntity)
	sourceEntity.EntityId = id
	g.GraphOtl.Entity[sourceIndex] = sourceEntity
}

func (g *GraphNoCheck) MergeGraphEdge(sourceIndex int, newEdge *GraphEdge) {
	if len(g.GraphOtl.Edge) <= 0 {
		return
	}
	sourceEdge := g.GraphOtl.Edge[sourceIndex]
	id := sourceEdge.EdgeId
	copier.Copy(sourceEdge, newEdge)
	sourceEdge.EdgeId = id
	g.GraphOtl.Edge[sourceIndex] = sourceEdge
}

func (g *GraphNoCheck) MergeGraphKMEntity(sourceIndex int, newEntity *GraphKMEntity) {
	if len(g.GraphKMap.Entity) <= 0 {
		return
	}
	sourceEntity := g.GraphKMap.Entity[sourceIndex]
	copier.Copy(sourceEntity, newEntity)
	g.GraphKMap.Entity[sourceIndex] = sourceEntity
}

func (g *GraphNoCheck) MergeGraphKMEdge(sourceIndex int, newEdge *GraphKMEdge) {
	if len(g.GraphKMap.Edge) <= 0 {
		return
	}
	sourceEdge := g.GraphKMap.Edge[sourceIndex]
	copier.Copy(sourceEdge, newEdge)
	g.GraphKMap.Edge[sourceIndex] = sourceEdge
}

func (g *GraphNoCheck) RemoveGraphEntity(removedEntitySlice []*GraphEntity) {
	needRemovedSubGraphEntityDict := lo.SliceToMap(removedEntitySlice, func(item *GraphEntity) (string, *GraphEntity) {
		return item.EntityId, item
	})
	keepGraphEntitySlice := make([]*GraphEntity, 0)
	for i := range g.GraphOtl.Entity {
		entity := g.GraphOtl.Entity[i]
		if _, ok := needRemovedSubGraphEntityDict[entity.EntityId]; !ok {
			keepGraphEntitySlice = append(keepGraphEntitySlice, entity)
		}
	}
	g.GraphOtl.Entity = keepGraphEntitySlice
}

func (g *GraphNoCheck) RemoveGraphEdge(entitySlice []*GraphEdge) {
	needRemovedSubGraphEdgeDict := lo.SliceToMap(entitySlice, func(item *GraphEdge) (string, *GraphEdge) {
		return item.EdgeId, item
	})
	keepGraphEdgeSlice := make([]*GraphEdge, 0)
	for i := range g.GraphOtl.Edge {
		edge := g.GraphOtl.Edge[i]
		if _, ok := needRemovedSubGraphEdgeDict[edge.EdgeId]; !ok {
			keepGraphEdgeSlice = append(keepGraphEdgeSlice, edge)
		}
	}
	g.GraphOtl.Edge = keepGraphEdgeSlice
}

func (g *GraphNoCheck) RemoveGraphKMEntity(removedEntitySlice []*GraphEntity) {
	needRemovedSubGraphEntityDict := lo.SliceToMap(removedEntitySlice, func(item *GraphEntity) (string, *GraphEntity) {
		return item.Name, item
	})
	keepGraphKMEntitySlice := make([]*GraphKMEntity, 0)
	for i := range g.GraphKMap.Entity {
		entity := g.GraphKMap.Entity[i]
		if _, ok := needRemovedSubGraphEntityDict[entity.Name]; !ok {
			keepGraphKMEntitySlice = append(keepGraphKMEntitySlice, entity)
		}
	}
	g.GraphKMap.Entity = keepGraphKMEntitySlice
}

func (g *GraphNoCheck) RemoveGraphKMEdge(entitySlice []*GraphEdge) {
	needRemovedSubGraphEdgeDict := lo.SliceToMap(entitySlice, func(item *GraphEdge) (string, *GraphEdge) {
		return item.Name, item
	})
	keepGraphKMEdgeSlice := make([]*GraphKMEdge, 0)
	for i := range g.GraphKMap.Edge {
		edge := g.GraphKMap.Edge[i]
		if len(edge.Relations) != 3 {
			continue
		}
		if _, ok := needRemovedSubGraphEdgeDict[edge.Relations[1]]; !ok {
			keepGraphKMEdgeSlice = append(keepGraphKMEdgeSlice, edge)
		}
	}
	g.GraphKMap.Edge = keepGraphKMEdgeSlice
}

func (a *ad) SchemeSaveNoCheck(ctx context.Context, schema *GraphNoCheck) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + `/api/builder/v1/graph/savenocheck`

	if _, err = httpPostDo[commonSimpleResp](ctx, rawURL, schema, nil, a); err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return nil
		}
		log.Error(err.Error())
		return err
	}
	return nil
}
