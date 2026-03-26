package data_change_mq

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model"

	"strconv"
	"strings"

	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	//"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	//"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	//"fmt"
	//"github.com/pkg/errors"
	//"strconv"
)

// 业务分组
func (c *consumer) createEntityDomainGroup(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityDomainGroup(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}

	graphData := []map[string]any{
		{
			"model_id":        entity.ModelId,
			"business_system": entity.BusinessSystem,
			"department_id":   entity.DepartmentId,
			"path_id":         entity.PathId,
			"path":            entity.Path,
			"description":     entity.Description,
			"name":            entity.Name,
			"id":              entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_domain_group")
	if err != nil {
		return err
	}

	// domain
	//domainGroup2Domain, err := c.dbRepo.GetRelationDomainGroup2DomainByDomainGroup(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(domainGroup2Domain) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range domainGroup2Domain {
	//		addItem := map[string]map[string]string{
	//			"start":     {"id": entityId, "_start_entity": "entity_domain_group"},
	//			"end":       {"id": item.Id, "_end_entity": "entity_domain"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "relation_domain_group_2_domain")
	//	if err != nil {
	//		return err
	//	}
	//}

	return nil
}

//func (c *consumer) index

// 业务域
func (c *consumer) createEntityDomain(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityDomain(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"model_id":        entity.ModelId,
			"business_system": entity.BusinessSystem,
			"department_id":   entity.DepartmentId,
			"path_id":         entity.PathId,
			"path":            entity.Path,
			"description":     entity.Description,
			"name":            entity.Name,
			"id":              entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_domain")
	if err != nil {
		return err
	}

	// entity_domain_group
	//domainGroup2Domain, err := c.dbRepo.GetRelationDomainGroup2DomainByDomain(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(domainGroup2Domain) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range domainGroup2Domain {
	//		addItem := map[string]map[string]string{
	//			"start":     {"id": item.ParentId, "_start_entity": "entity_domain_group"},
	//			"end":       {"id": entityId, "_end_entity": "entity_domain"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "relation_domain_group_2_domain")
	//	if err != nil {
	//		return err
	//	}
	//}

	// self
	// entity_domain_flow

	return nil
}

// 业务流程
func (c *consumer) createEntityDomainFlow(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityDomainFlow(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"model_id":        entity.ModelId,
			"business_system": entity.BusinessSystem,
			"department_id":   entity.DepartmentId,
			"path_id":         entity.PathId,
			"path":            entity.Path,
			"description":     entity.Description,
			"name":            entity.Name,
			"id":              entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_domain_flow")
	if err != nil {
		return err
	}

	// entity_domain
	// entity_infomation_system
	// entity_department
	// entity_business_model

	return nil
}

// 信息系统
func (c *consumer) createEntityInfomationSystem(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityInfomationSystem(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_infomation_system")
	if err != nil {
		return err
	}

	// entity_domain_flow
	return nil
}

// 部门
func (c *consumer) createEntityDepartment(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityDepartment(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"path_id": entity.PathId,
			"path":    entity.Path,
			"name":    entity.Name,
			"id":      entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_department")
	if err != nil {
		return err
	}

	// entity_domain_flow
	// self
	return nil
}

// 业务模型
func (c *consumer) createEntityBusinessModel(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityBusinessModel(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"domain_id":   entity.DomainId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_business_model")
	if err != nil {
		return err
	}

	// entity_domain_flow
	// entity_flowchart
	// entity_form
	return nil
}

// 流程图
func (c *consumer) createEntityFlowchart(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityFlowchart(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"path_id":     entity.PathId,
			"path":        entity.Path,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_flowchart")
	if err != nil {
		return err
	}

	// entity_business_model
	// self
	// entity_flowchart_node
	return nil
}

// 流程图
func (c *consumer) createEntityFlowchartV2(ctx context.Context, entityId string, name string, description string, path string, pathID string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}
	//
	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}
	//
	//entity, err := c.dbRepo.GetEntityFlowchart(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if entity == nil {
	//	errors.Wrap(err, "can not find entity "+entityId)
	//	return err
	//}

	//indexData := es_subject_model.EntityFlowchart{
	//	DocID:       entityId,
	//	ID:          entityId,
	//	Name:        name,
	//	Description: description,
	//	Path:        path,
	//	PathID:      pathID,
	//}

	//err = c.esClient.IndexEntityFlowchart(ctx, &indexData)
	//if err != nil {
	//	return err
	//}

	return nil
}

// 流程节点
func (c *consumer) createEntityFlowchartNode(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityFlowchartNode(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"mxcell_id":    entity.MxcellId,
			"target":       entity.Target,
			"source":       entity.Source,
			"id":           entity.Id,
			"flowchart_id": entity.FlowchartId,
			"name":         entity.Name,
			"description":  entity.Description,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_flowchart_node")
	if err != nil {
		return err
	}

	// entity_business_model
	// self
	// entity_flowchart_node
	return nil
}

// 业务表
func (c *consumer) createEntityForm(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityForm(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"description":       entity.Description,
			"business_model_id": entity.BusinessModelId,
			"name":              entity.Name,
			"id":                entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_form")
	if err != nil {
		return err
	}

	// entity_business_model
	// self
	// entity_field
	return nil
}

func (c *consumer) createEntityFormV2(ctx context.Context, entityId string, name string, businessModelId string, description string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}

	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}

	//entity, err := c.dbRepo.GetEntityForm(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if entity == nil {
	//	errors.Wrap(err, "can not find entity "+entityId)
	//	return err
	//}
	//graphData := []map[string]any{
	//	{
	//		"description":       entity.Description,
	//		"business_model_id": entity.BusinessModelId,
	//		"name":              entity.Name,
	//		"id":                entity.Id,
	//	},
	//}
	indexData := es_subject_model.EntityFormDoc{
		DocID:           entityId,
		ID:              entityId,
		Name:            name,
		BusinessModelID: businessModelId,
		Description:     description,
	}

	err = c.esClient.IndexEntityFormDoc(ctx, &indexData)
	if err != nil {
		return err
	}

	// entity_business_model
	// self
	// entity_field
	return nil
}

// 业务表字段
func (c *consumer) createEntityField(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityField(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"standard_id":        entity.StandardId,
			"name_en":            entity.NameEn,
			"business_form_name": entity.BusinessFormName,
			"business_form_id":   entity.BusinessFormId,
			"name":               entity.Name,
			"id":                 entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_field")
	if err != nil {
		return err
	}

	// entity_form
	// entity_data_element
	return nil
}

// 业务表字段
func (c *consumer) createEntityFieldV2(ctx context.Context, entityId string, name string, businessFormID string, businessFormName string, nameEn string, standardID string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}
	//
	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}

	//entity, err := c.dbRepo.GetEntityField(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if entity == nil {
	//	errors.Wrap(err, "can not find entity "+entityId)
	//	return err
	//}
	//graphData := []map[string]any{
	//	{
	//		"standard_id":        entity.StandardId,
	//		"name_en":            entity.NameEn,
	//		"business_form_name": entity.BusinessFormName,
	//		"business_form_id":   entity.BusinessFormId,
	//		"name":               entity.Name,
	//		"id":                 entity.Id,
	//	},
	//}

	indexData := es_subject_model.EntityField{
		DocID:            entityId,
		ID:               entityId,
		Name:             name,
		BusinessFormID:   businessFormID,
		BusinessFormName: businessFormName,
		NameEn:           nameEn,
		StandardID:       standardID,
	}

	err = c.esClient.IndexEntityField(ctx, &indexData)
	if err != nil {
		return err
	}

	// entity_form
	// entity_data_element
	return nil
}

// 标准数据元
func (c *consumer) createEntityDataElement(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityDataElement(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	if entity.State == 0 {
		err = c.deleteEntity(ctx, graphConfigName, entityId, "id", "entity_data_element")
		return err
	}

	graphData := []map[string]any{
		{
			"std_type":       entity.StdType,
			"name_cn":        entity.NameCn,
			"name_en":        entity.NameEn,
			"code":           entity.Code,
			"department_ids": entity.DepartmentIds,
			"id":             entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_data_element")
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

// 标准数据元 v2
func (c *consumer) createEntityDataElementV2(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}
	//
	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}

	entity, err := c.dbRepo.GetEntityDataElement(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	//if entity.State == 0 {
	//	err = c.esClient.DeleteIndex(ctx, entityId, "af_subject_model_idx")
	//	return err
	//}

	//graphData := []map[string]any{
	//	{
	//		"std_type":       entity.StdType,
	//		"name_cn":        entity.NameCn,
	//		"name_en":        entity.NameEn,
	//		"code":           entity.Code,
	//		"department_ids": entity.DepartmentIds,
	//		"id":             entity.Id,
	//	},
	//}
	indexData := es_subject_model.EntityDataElement{
		DocID:         entityId,
		ID:            entityId,
		DepartmentIds: entity.DepartmentIds,
		Code:          entity.Code,
		NameCn:        entity.NameCn,
		NameEN:        entity.NameEn,
		StdType:       entity.StdType,
	}

	err = c.esClient.IndexEntityDataElement(ctx, &indexData)
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

// 逻辑视图字段
func (c *consumer) createEntityFormViewField(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityFormViewField(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"code_table_id":  entity.CodeTableId,
			"standard":       entity.Standard,
			"standard_code":  entity.StandardCode,
			"name":           entity.Name,
			"technical_name": entity.TechnicalName,
			"form_view_id":   entity.FormViewId,
			"id":             entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_form_view_field")
	if err != nil {
		return err
	}

	// entity_data_element
	// entity_form_view
	return nil
}

// 逻辑视图
func (c *consumer) createEntityFormView(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityFormView(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"description":    entity.Description,
			"subject_id":     entity.SubjectId,
			"datasource_id":  entity.DatasourceId,
			"type":           entity.Type,
			"name":           entity.Name,
			"technical_name": entity.TechnicalName,
			"id":             entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_form_view")
	if err != nil {
		return err
	}

	// entity_form_view_field
	return nil
}

func (c *consumer) createEntityFormViewV2(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}
	//
	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}

	entity, err := c.dbRepo.GetEntityFormView(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}

	indexData := es_subject_model.EntityFormView{
		DocID:         entityId,
		ID:            entityId,
		TechnicalName: entity.TechnicalName,
		Name:          entity.Name,
		Type:          entity.Type,
		DatasourceID:  entity.DatasourceId,
		SubjectID:     entity.SubjectId,
		Description:   entity.Description,
	}

	err = c.esClient.IndexEntityFormView(ctx, &indexData)
	if err != nil {
		return err
	}

	// entity_form_view_field
	return nil
}

func (c *consumer) updateEntitySubjectModelLabel(ctx context.Context, entityId string, name string, relatedModelIds string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	objBase := es_subject_model.SubjectModelLabelDoc{
		DocID:           entityId,
		ID:              entityId,
		Name:            name,
		RelatedModelIds: strings.Split(relatedModelIds, ","),
	}

	err = c.esClient.IndexLabel(ctx, &objBase)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) deleteEntitySubjectModelLabel(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	err = c.esClient.DeleteLabel(ctx, entityId)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) deleteEntityIndex(ctx context.Context, entityId string, indexName string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	err = c.esClient.DeleteIndex(ctx, entityId, indexName)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) upsertEntitySubjectModel(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	entity, err := c.dbRepo.GetEntitySubjectModel(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	objBase := es_subject_model.BaseObj{
		ID:             entityId,
		BusinessName:   entity.BusinessName,
		TechnicalName:  entity.TechnicalName,
		DataViewID:     entity.DataViewId,
		DisplayFieldID: "",
	}
	subjectModel := es_subject_model.SubjectModelDoc{
		DocID:   entityId,
		BaseObj: objBase,
	}

	err = c.esClient.Index(ctx, &subjectModel)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) deleteEntitySubjectModel(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	err = c.esClient.Delete(ctx, entityId)
	if err != nil {
		return err
	}

	return nil
}

// 逻辑实体属性
func (c *consumer) createEntitySubjectProperty(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntitySubjectProperty(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"standard_id": entity.StandardId,
			"path":        entity.Path,
			"path_id":     entity.PathId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_subject_property")
	if err != nil {
		return err
	}

	// entity_data_element
	// entity_subject_entity
	return nil
}

func (c *consumer) createEntitySubjectPropertyV2(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	//if err != nil {
	//	return err
	//}

	//graphIdInt, err := strconv.Atoi(graphId)
	//if err != nil {
	//	return err
	//}

	entity, err := c.dbRepo.GetEntitySubjectProperty(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	indexData := es_subject_model.EntitySubjectProperty{
		DocID:       entityId,
		ID:          entityId,
		Name:        entity.Name,
		Description: entity.Description,
		PathID:      entity.PathId,
		Path:        entity.Path,
		StandardID:  entity.StandardId,
	}

	err = c.esClient.IndexEntitySubjectProperty(ctx, &indexData)
	if err != nil {
		return err
	}

	return nil
}

// 逻辑实体
func (c *consumer) createEntitySubjectEntity(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntitySubjectEntity(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"path":        entity.Path,
			"path_id":     entity.PathId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_subject_entity")
	if err != nil {
		return err
	}

	// entity_subject_property
	// entity_subject_object
	return nil
}

// 业务对象
func (c *consumer) createEntitySubjectObject(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntitySubjectObject(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"ref_id":      entity.RefId,
			"path":        entity.Path,
			"path_id":     entity.PathId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_subject_object")
	if err != nil {
		return err
	}

	// entity_subject_entity
	// self
	// entity_subject_domain
	return nil
}

// 主题域
func (c *consumer) createEntitySubjectDomain(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntitySubjectDomain(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"path":        entity.Path,
			"path_id":     entity.PathId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_subject_domain")
	if err != nil {
		return err
	}

	// entity_subject_object
	// entity_subject_group
	return nil
}

// 主题域分组
func (c *consumer) createEntitySubjectGroup(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntitySubjectGroup(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"path":        entity.Path,
			"path_id":     entity.PathId,
			"description": entity.Description,
			"name":        entity.Name,
			"id":          entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_subject_group")
	if err != nil {
		return err
	}

	// entity_subject_domain
	return nil
}

func (c *consumer) deleteEntitySubjectDomainType(ctx context.Context, graphConfigName string, entityName string, entityId string, entityIdPath string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	graphData := []map[string]string{
		{"id": entityId},
	}

	_, err = c.adProxy.DeleteEntity(ctx, graphData, entityName, graphIdInt)
	if err != nil {
		return err
	}

	// 检查剩余节点
	subjectDomainInfos, err := c.dbRepo.GetTableSubjectDomainByPathId(ctx, entityIdPath)
	if err != nil {
		return err
	}

	for _, item := range subjectDomainInfos {
		switch item.Type {
		case 2:
			itemGraphData := []map[string]string{
				{"id": item.Id},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "entity_subject_domain", graphIdInt)
		case 3:
			itemGraphData := []map[string]string{
				{"id": item.Id},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "entity_subject_object", graphIdInt)
		case 5:
			itemGraphData := []map[string]string{
				{"id": item.Id},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "entity_subject_entity", graphIdInt)
		case 6:
			itemGraphData := []map[string]string{
				{"id": item.Id},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "entity_subject_property", graphIdInt)
		default:
			continue
		}

	}

	return nil
}

func (c *consumer) createEntityLabel(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityLabel(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"sort":                 entity.FSort,
			"path":                 entity.FPath,
			"category_description": entity.CategoryDescription,
			"category_range_type":  entity.CategoryRangeType,
			"category_name":        entity.CategoryName,
			"category_id":          entity.CategoryId,
			"name":                 entity.Name,
			"id":                   entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_label")
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

//func (c *consumer) createEntityLabelV2(ctx context.Context, entityId string) error {
//	var err error
//	ctx, span := trace.StartInternalSpan(ctx)
//	defer func() { trace.TelemetrySpanEnd(span, err) }()
//
//	entity, err := c.dbRepo.GetEntityLabel(ctx, entityId)
//	if err != nil {
//		return err
//	}
//	if entity == nil {
//		errors.Wrap(err, "can not find entity "+entityId)
//		return err
//	}
//
//	indexData := es_subject_model.EntityLabel{
//		DocID:               entityId,
//		ID:                  entity.Id,
//		Name:                entity.Name,
//		CategoryID:          entity.CategoryId,
//		CategoryName:        entity.CategoryName,
//		CategoryRangeType:   entity.CategoryRangeType,
//		CategoryDescription: entity.CategoryDescription,
//		Path:                entity.FPath,
//		Sort:                entity.FSort,
//	}
//
//	err = c.esClient.IndexEntityLabel(ctx, &indexData)
//	if err != nil {
//		return err
//	}
//
//	return nil
//}

func (c *consumer) createEntityLabelByCategory(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entityList, err := c.dbRepo.GetEntityLabelsByCategory(ctx, entityId)
	if err != nil {
		return err
	}
	//if entity == nil {
	//	errors.Wrap(err, "can not find entity "+entityId)
	//	return err
	//}
	for _, entity := range entityList {
		graphData := []map[string]any{
			{
				"sort":                 entity.FSort,
				"path":                 entity.FPath,
				"category_description": entity.CategoryDescription,
				"category_range_type":  entity.CategoryRangeType,
				"category_name":        entity.CategoryName,
				"category_id":          entity.CategoryId,
				"name":                 entity.Name,
				"id":                   entity.Id,
			},
		}

		_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_label")
		if err != nil {
			return err
		}
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

func (c *consumer) deleteEntityLabelByCategory(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entityList, err := c.dbRepo.GetEntityLabelsByCategoryIgnoreFState(ctx, entityId)
	if err != nil {
		return err
	}

	graphData := []map[string]string{}
	for _, entity := range entityList {
		item := map[string]string{}
		entityIdString := strconv.FormatInt(entity.Id, 10)
		item["id"] = entityIdString
		graphData = append(graphData, item)
	}

	if len(graphData) == 0 {
		errors.Wrap(err, "can not find entity label "+entityId)
		return err
	}

	_, err = c.adProxy.DeleteEntity(ctx, graphData, "entity_label", graphIdInt)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) createEntityLabelByMessage(ctx context.Context, graphConfigName string, entity TLabel) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entityInfo := entity.Payload.Content.Entities[0]
	if entityInfo.DeletedAt != 0 {
		return nil
	}

	graphData := []map[string]any{
		{
			"sort":                 entityInfo.FSort,
			"path":                 entityInfo.Path,
			"category_description": "",
			"category_range_type":  "",
			"category_name":        "entityInfo.CategoryName",
			"category_id":          entityInfo.CategoryId,
			"name":                 entityInfo.Name,
			"id":                   entityInfo.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_label")
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

func (c *consumer) createEntityBusinessIndicator(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityBusinessIndicator(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"statistical_caliber": entity.StatisticalCaliber,
			"statistics_cycle":    entity.StatisticsCycle,
			"unit":                entity.Unit,
			"calculation_formula": entity.CalculationFormula,
			"description":         entity.Description,
			"business_model_id":   entity.BusinessModelId,
			"name":                entity.Name,
			"id":                  entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_business_indicator")
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

//func (c *consumer) createEntityBusinessIndicatorV2(ctx context.Context, entityId string) error {
//	var err error
//	ctx, span := trace.StartInternalSpan(ctx)
//	defer func() { trace.TelemetrySpanEnd(span, err) }()
//
//	entity, err := c.dbRepo.GetEntityBusinessIndicator(ctx, entityId)
//	if err != nil {
//		return err
//	}
//	if entity == nil {
//		errors.Wrap(err, "can not find entity "+entityId)
//		return err
//	}
//
//	indexData := es_subject_model.EntityBusinessIndicator{
//		DocID:              entityId,
//		ID:                 entityId,
//		Name:               entity.Name,
//		BusinessModelID:    entity.BusinessModelId,
//		Description:        entity.Description,
//		CalculationFormula: entity.CalculationFormula,
//		Unit:               entity.Unit,
//		StatisticsCycle:    entity.StatisticsCycle,
//		StatisticalCaliber: entity.StatisticalCaliber,
//	}
//
//	err = c.esClient.IndexEntityBusinessIndicator(ctx, &indexData)
//	if err != nil {
//		return err
//	}
//
//	// entity_field
//	// entity_form_view_field
//	// entity_subject_property
//	return nil
//}

func (c *consumer) createEntityRule(ctx context.Context, graphConfigName string, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	entity, err := c.dbRepo.GetEntityRule(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"department_ids": entity.DepartmentIds,
			"expression":     entity.Expression,
			"rule_type":      entity.RuleType,
			"description":    entity.Description,
			"org_type":       entity.OrgType,
			"category_id":    entity.CategoryId,
			"name":           entity.Name,
			"id":             entity.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "entity_rule")
	if err != nil {
		return err
	}

	// entity_field
	// entity_form_view_field
	// entity_subject_property
	return nil
}

func (c *consumer) createEntityRuleV2(ctx context.Context, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	entity, err := c.dbRepo.GetEntityRule(ctx, entityId)
	if err != nil {
		return err
	}
	if entity == nil {
		errors.Wrap(err, "can not find entity "+entityId)
		return err
	}

	indexData := es_subject_model.EntityRuleDoc{
		DocID:         entityId,
		ID:            entityId,
		Name:          entity.Name,
		CatalogId:     entity.CategoryId,
		OrgType:       entity.OrgType,
		Description:   entity.Description,
		RuleType:      entity.RuleType,
		Expression:    entity.Expression,
		DepartmentIds: entity.DepartmentIds,
	}
	err = c.esClient.IndexEntityRule(ctx, &indexData)
	if err != nil {
		return err
	}

	return nil
}
