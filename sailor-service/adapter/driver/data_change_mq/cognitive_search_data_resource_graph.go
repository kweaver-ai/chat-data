package data_change_mq

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
)

func (c *consumer) createSource(ctx context.Context, graphConfigName string, entityId string, entityType string) error {
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

	entityDataSource, err := c.dbRepo.GetEmptyEntityDataResource()
	//dataViewInfo, err := c.dbRepo.GetDataViewInfo(ctx, entityId)
	if err != nil {
		return err
	}
	switch entityType {
	case "FormView":
		entityDataSource, err = c.dbRepo.GetDataViewInfo(ctx, entityId)
	case "Service":
		entityDataSource, err = c.dbRepo.GetInterfaceServiceInfo(ctx, entityId)
	case "Indicator":
		entityDataSource, err = c.dbRepo.GetIndicatorInfo(ctx, entityId)
	default:
		log.Infof("entity type can not match %s", entityType)
		errors.Wrap(err, "entity type can not match "+entityType)
		return err

	}
	if entityDataSource == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}

	mainSearchCfg, err := c.adProxy.GetSearchConfig("resource", "resourceid", entityId)
	mainEntityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", mainSearchCfg)

	if err != nil {
		return err
	}

	oInfoSystemId := ""
	oDepartmentId := ""
	oOwnerId := ""
	oSubjectId := ""
	if len(mainEntityInfo.Res.Nodes) > 0 {
		node := mainEntityInfo.Res.Nodes[0]
		if len(node.Properties) > 0 {
			for _, property := range node.Properties[0].Props {
				if property.Name == "owner_id" && property.Value != "__NULL__" {
					oOwnerId = property.Value
				}
				if property.Name == "info_system_id" && property.Value != "__NULL__" {
					oInfoSystemId = property.Value
				}
				if property.Name == "department_id" && property.Value != "__NULL__" {
					oDepartmentId = property.Value
				}
				if property.Name == "subject_id" && property.Value != "__NULL__" {
					oSubjectId = property.Value
				}
			}
		}

	}
	log.Infof("entity resource graph property InfoSystemId:%s, DepartmentId:%s, OwnerId:%s, SubjectId:%s", oInfoSystemId, oDepartmentId, oOwnerId, oSubjectId)

	graphData := []map[string]any{
		{
			"resourceid":              entityDataSource.ID,
			"code":                    entityDataSource.Code,
			"technical_name":          entityDataSource.TechnicalName,
			"resourcename":            entityDataSource.Name,
			"description":             entityDataSource.Description,
			"asset_type":              entityDataSource.AssetType,
			"color":                   entityDataSource.Color,
			"published_at":            entityDataSource.PublishedAt,
			"owner_id":                entityDataSource.OwnerId,
			"owner_name":              entityDataSource.OwnerName,
			"department_id":           entityDataSource.DepartmentId,
			"department":              entityDataSource.DepartmentName,
			"department_path_id":      entityDataSource.DepartmentPathId,
			"department_path":         entityDataSource.DepartmentPath,
			"subject_id":              entityDataSource.SubjectId,
			"subject_name":            entityDataSource.SubjectName,
			"subject_path_id":         entityDataSource.SubjectPathId,
			"subject_path":            entityDataSource.SubjectPath,
			"online_at":               entityDataSource.OnlineAt,
			"publish_status":          entityDataSource.PublishStatus,
			"online_status":           entityDataSource.OnlineStatus,
			"publish_status_category": entityDataSource.PublishStatusCategory,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "resource")
	if err != nil {
		return err
	}

	// 主題域
	if oSubjectId != "" && entityDataSource.SubjectId != oSubjectId {
		deleteSideInfo1 := []map[string]map[string]string{
			{
				"start": {"subdomainid": oSubjectId, "_start_entity": "subdomain"},
				"end":   {"resourceid": entityId, "_end_entity": "resource"},
			},
		}
		_, err = c.adProxy.DeleteEdge(ctx, deleteSideInfo1, "subdomain_2_dataresource", graphIdInt)
	}
	if entityDataSource.SubjectId != "" {
		if entityDataSource.SubjectId != oSubjectId {

			sideInfo1 := []map[string]map[string]string{
				{
					"start":     {"subdomainid": entityDataSource.SubjectId, "_start_entity": "subdomain"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				},
			}
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "subdomain_2_dataresource")
			if err != nil {
				return err
			}
		}

	}

	// department
	// 删除不同的department
	if oDepartmentId != "" && oDepartmentId != entityDataSource.DepartmentId {
		deleteSideInfo1 := []map[string]map[string]string{
			{
				"start": {"departmentid": oDepartmentId, "_start_entity": "department"},
				"end":   {"resourceid": entityId, "_end_entity": "resource"},
			},
		}
		_, err = c.adProxy.DeleteEdge(ctx, deleteSideInfo1, "department_2_datacatalog", graphIdInt)
	}
	if entityDataSource.DepartmentId != "" {
		if entityDataSource.DepartmentId != oDepartmentId {
			err = c.upsertDepartmentResourceEntity(ctx, graphId, entityDataSource.DepartmentId, entityDataSource.DepartmentName)

			sideInfo2 := []map[string]map[string]string{
				{
					"start":     {"departmentid": entityDataSource.DepartmentId, "_start_entity": "department"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				},
			}
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo2, graphIdInt, "department_2_datacatalog")
			if err != nil {
				return err
			}
		}
	}

	// data owner
	// 删除不同的data owner
	if oOwnerId != "" && oOwnerId != entityDataSource.OwnerId {
		deleteSideInfo1 := []map[string]map[string]string{
			{
				"start": {"dataownerid": oDepartmentId, "_start_entity": "dataowner"},
				"end":   {"resourceid": entityId, "_end_entity": "resource"},
			},
		}
		_, err = c.adProxy.DeleteEdge(ctx, deleteSideInfo1, "dataowner_2_datacatalog", graphIdInt)
	}
	if entityDataSource.OwnerId != "" {
		if entityDataSource.OwnerId != oOwnerId {
			err = c.upsertDataOwnerResourceEntity(ctx, graphId, entityDataSource.OwnerId, entityDataSource.OwnerName)

			sideInfo3 := []map[string]map[string]string{
				{
					"start":     {"dataownerid": entityDataSource.OwnerId, "_start_entity": "dataowner"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				},
			}
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo3, graphIdInt, "dataowner_2_datacatalog")
			if err != nil {
				return err
			}
		}

	}

	if entityType == "FormView" {
		// data_explore_report
		dataView2DataExploreReport, err := c.dbRepo.GetDataView2DataExploreReport(ctx, entityId)
		if err != nil {
			return err
		}
		if len(dataView2DataExploreReport) > 0 {
			sideInfo4 := []map[string]map[string]string{}
			for _, item := range dataView2DataExploreReport {
				addItem := map[string]map[string]string{
					"start": {
						"column_id":      item.ColumnId,
						"explore_item":   item.ExploreItem,
						"explore_result": item.ExploreResult,
						"_start_entity":  "data_explore_report"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				}
				sideInfo4 = append(sideInfo4, addItem)

				err = c.upsertExploreReportResourceEntity(ctx, graphId, item.ColumnId)
			}
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo4, graphIdInt, "data_explore_report_2_resource")
			if err != nil {
				return err
			}
		}

		// field
		//DataView2Filed, err := c.dbRepo.GetDataView2Filed(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//if len(DataView2Filed) > 0 {
		//	sideInfo6 := []map[string]map[string]string{}
		//	for _, item := range DataView2Filed {
		//		addItem := map[string]map[string]string{
		//			"start":     {"column_id": item.ColumnId, "_start_entity": "field"},
		//			"end":       {"resourceid": entityId, "_end_entity": "resource"},
		//			"edge_pros": {},
		//		}
		//		sideInfo6 = append(sideInfo6, addItem)
		//
		//		searchCfg, err := c.adProxy.GetSearchConfig("field", "column_id", item.ColumnId)
		//		if err != nil {
		//			continue
		//		}
		//		entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
		//		if len(entityInfo.Res.Nodes) == 0 {
		//			dataViewFields, err := c.dbRepo.GetDataViewFields(ctx, item.ColumnId)
		//			if err != nil {
		//				return err
		//			}
		//			if dataViewFields == nil {
		//				//errors.Wrap(err, "can not find data_view "+entityId)
		//				//return err
		//				continue
		//			}
		//			dataViewFieldsData := []map[string]any{
		//				{
		//					"datatype":       dataViewFields.DataType,
		//					"technical_name": dataViewFields.TechnicalName,
		//					"formviewid":     dataViewFields.FormviewUuid,
		//					"field_name":     dataViewFields.FieldName,
		//					"column_id":      dataViewFields.ColumnId,
		//				},
		//			}
		//			_, err = c.adProxy.InsertEntity(ctx, "entity", dataViewFieldsData, graphIdInt, "field")
		//			if err != nil {
		//				return err
		//			}
		//		}
		//	}
		//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo6, graphIdInt, "field_2_resource")
		//	if err != nil {
		//		return err
		//	}
		//}

		// metadataschema
		DataView2MetadataSchema, err := c.dbRepo.GetDataView2MetadataSchemaV2(ctx, entityId)
		if err != nil {
			return err
		}
		if len(DataView2MetadataSchema) > 0 {
			sideInfo7 := []map[string]map[string]string{}
			for _, item := range DataView2MetadataSchema {
				if item.SchemaSid == "" {
					continue
				}
				addItem := map[string]map[string]string{
					"start":     {"metadataschemaid": item.SchemaSid, "_start_entity": "metadataschema"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				}
				sideInfo7 = append(sideInfo7, addItem)

				searchCfg, err := c.adProxy.GetSearchConfig("metadataschema", "metadataschemaid", item.SchemaSid)
				if err != nil {
					continue
				}
				entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
				if len(entityInfo.Res.Nodes) == 0 {
					DataSourceAndMetadataSchema, err := c.dbRepo.GetDataSourceAndMetadataSchemaByMetadataSchema(ctx, item.SchemaSid)
					if err != nil {
						continue
					}
					if DataSourceAndMetadataSchema == nil {
						errors.Wrap(err, "can not find metadata "+item.SchemaSid)
						continue
					}
					metadataSchemaData := []map[string]any{
						{
							"metadataschemaid":   DataSourceAndMetadataSchema.SchemaSid,
							"metadataschemaname": DataSourceAndMetadataSchema.SchemaName,
							"prefixname":         "库",
						},
					}
					_, err = c.adProxy.InsertEntity(ctx, "entity", metadataSchemaData, graphIdInt, "metadataschema")
					if err != nil {
						return err
					}

					//// 数据源，顺便创建
					//dataSourceData := []map[string]any{
					//	{
					//		"source_type_name":      DataSourceAndMetadataSchema.SourceTypeName,
					//		"source_type_code":      DataSourceAndMetadataSchema.SourceTypeCode,
					//		"data_source_type_name": DataSourceAndMetadataSchema.DataSourceTypeName,
					//		"prefixname":            DataSourceAndMetadataSchema.PrefixName,
					//		"datasourcename":        DataSourceAndMetadataSchema.DataSourceName,
					//		"datasourceid":          DataSourceAndMetadataSchema.DataSourceUuid,
					//	},
					//}
					//_, err = c.adProxy.InsertEntity(ctx, "entity", dataSourceData, graphIdInt, "datasource")
					//if err != nil {
					//	return err
					//}
					//
					//// 边数据
					dataSource2MetadataSchema := []map[string]map[string]string{
						{
							"start":     {"datasourceid": DataSourceAndMetadataSchema.DataSourceUuid, "_start_entity": "datasource"},
							"end":       {"metadataschemaid": item.SchemaSid, "_end_entity": "metadataschema"},
							"edge_pros": {},
						},
					}

					_, err = c.adProxy.InsertSide(ctx, "edge", dataSource2MetadataSchema, graphIdInt, "datasource_2_metadataschema")
					if err != nil {
						return err
					}

				}
			}
			if len(sideInfo7) > 0 {
				_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo7, graphIdInt, "metadataschema_2_resource")
				if err != nil {
					return err
				}
			}

		}
	}

	if entityType == "Service" {
		// response_field
		interface2ResponseField, err := c.dbRepo.GetInterface2ResponseField(ctx, entityId)
		if err != nil {
			return err
		}
		if len(interface2ResponseField) > 0 {
			sideInfo5 := []map[string]map[string]string{}
			for _, item := range interface2ResponseField {
				addItem := map[string]map[string]string{
					"start":     {"field_id": item.FieldSid, "_start_entity": "response_field"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				}
				sideInfo5 = append(sideInfo5, addItem)

				searchCfg, err := c.adProxy.GetSearchConfig("response_field", "field_id", item.FieldSid)
				if err != nil {
					continue
				}
				entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
				if len(entityInfo.Res.Nodes) == 0 {
					interfaceField, err := c.dbRepo.GetResponseField(ctx, item.FieldSid)
					if err != nil {
						continue
					}
					if interfaceField == nil {
						log.Infof("interfaceField %s can not found", item.FieldSid)
						continue
					}
					interfaceFieldData := []map[string]any{
						{
							"field_id": interfaceField.FieldSid,
							"en_name":  interfaceField.EnName,
							"cn_name":  interfaceField.CnName,
						},
					}
					_, err = c.adProxy.InsertEntity(ctx, "entity", interfaceFieldData, graphIdInt, "response_field")
					if err != nil {
						return err
					}

				}
			}
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo5, graphIdInt, "Response_field_2_resource")
			if err != nil {
				return err
			}
		}
	}

	if entityType == "Indicator" {
		// dimension_model
		dimensionModel2Indicator, err := c.dbRepo.GetDimensionModel2IndicatorByIndicator(ctx, entityId)
		if err != nil {
			return err
		}
		if len(dimensionModel2Indicator) > 0 {
			sideInfo8 := []map[string]map[string]string{}
			for _, item := range dimensionModel2Indicator {
				addItem := map[string]map[string]string{
					"start":     {"id": item.DimensionModelId, "_start_entity": "dimension_model"},
					"end":       {"resourceid": entityId, "_end_entity": "resource"},
					"edge_pros": {},
				}
				sideInfo8 = append(sideInfo8, addItem)

				searchCfg, err := c.adProxy.GetSearchConfig("dimension_model", "id", item.DimensionModelId)
				if err != nil {
					continue
				}
				entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
				if len(entityInfo.Res.Nodes) == 0 {
					dimensionModel, err := c.dbRepo.GetDimensionModel(ctx, item.DimensionModelId)
					if err != nil {
						return err
					}
					if dimensionModel == nil {
						errors.Wrap(err, "can not find data_view "+item.DimensionModelId)
						return err
					}
					dimensionModelData := []map[string]any{
						{
							"description": dimensionModel.Description,
							"name":        dimensionModel.Name,
							"id":          dimensionModel.Id,
						},
					}
					_, err = c.adProxy.InsertEntity(ctx, "entity", dimensionModelData, graphIdInt, "dimension_model")
					if err != nil {
						return err
					}
				}
			}
			if len(sideInfo8) > 0 {
				_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo8, graphIdInt, "dimension_model_2_resource")
				if err != nil {
					return err
				}
			}

		}

		// indicator_analysis_dimension
		indicatorInfo, err := c.dbRepo.GetIndicatorInfoV2(ctx, entityId)
		if err != nil {
			return err
		}
		analysisDimVal := DAnalysisDims{}
		err = json.Unmarshal([]byte(indicatorInfo.AnalysisDimension), &analysisDimVal.AnalysisDimList)
		if err != nil {
			return err
		}
		entityInfo9 := []map[string]any{}
		sideInfo9 := []map[string]map[string]string{}
		for _, analysisItem := range analysisDimVal.AnalysisDimList {
			indicatorAnalysisDimensionData := map[string]any{
				"field_data_type":      analysisItem.DataType,
				"field_technical_name": analysisItem.TechnicalName,
				"field_business_name":  analysisItem.BusinessName,
				"field_id":             analysisItem.FieldId,
				"formview_id":          analysisItem.TableId,
			}
			entityInfo9 = append(entityInfo9, indicatorAnalysisDimensionData)

			addItem := map[string]map[string]string{
				"start":     {"field_id": analysisItem.FieldId, "formview_id": analysisItem.TableId, "_start_entity": "indicator_analysis_dimension"},
				"end":       {"resourceid": entityId, "_end_entity": "resource"},
				"edge_pros": {},
			}
			sideInfo9 = append(sideInfo9, addItem)
		}

		if len(entityInfo9) > 0 {
			_, err = c.adProxy.InsertEntity(ctx, "entity", entityInfo9, graphIdInt, "indicator_analysis_dimension")
			if err != nil {
				return err
			}
		}

		if len(sideInfo9) > 0 {
			_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo9, graphIdInt, "indicator_analysis_dimension_2_resource")
			if err != nil {
				return err
			}
		}

		//indicatorAnalysisDimension2Indicator, err := c.dbRepo.GetIndicatorAnalysisDimension2IndicatorByIndicator(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//if len(indicatorAnalysisDimension2Indicator) > 0 {
		//	sideInfo9 := []map[string]map[string]string{}
		//	for _, item := range indicatorAnalysisDimension2Indicator {
		//		addItem := map[string]map[string]string{
		//			"start":     {"field_id": item.FieldId, "formview_id": item.FormviewId, "_start_entity": "indicator_analysis_dimension"},
		//			"end":       {"resourceid": entityId, "_end_entity": "resource"},
		//			"edge_pros": {},
		//		}
		//		sideInfo9 = append(sideInfo9, addItem)

		//searchCfg, err := c.adProxy.GetSearchConfig("indicator_analysis_dimension", "field_id", item.FieldId)
		//if err != nil {
		//	continue
		//}
		//entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
		//if len(entityInfo.Res.Nodes) == 0 {
		//indicatorAnalysisDimension, err := c.dbRepo.GetIndicatorInfo(ctx, entityId)
		//	if err != nil {
		//		return err
		//	}
		//	if indicatorAnalysisDimension == nil {
		//		errors.Wrap(err, "can not find data_view "+entityId)
		//		return err
		//	}
		//	indicatorAnalysisDimensionData := []map[string]any{
		//		{
		//			"field_data_type":      indicatorAnalysisDimension.FieldDataType,
		//			"field_technical_name": indicatorAnalysisDimension.FieldTechnicalName,
		//			"field_business_name":  indicatorAnalysisDimension.FieldBusinessName,
		//			"field_id":             indicatorAnalysisDimension.FieldId,
		//			"formview_id":          indicatorAnalysisDimension.FormViewId,
		//		},
		//	}
		//	_, err = c.adProxy.InsertEntity(ctx, "entity", indicatorAnalysisDimensionData, graphIdInt, "indicator_analysis_dimension")
		//	if err != nil {
		//		return err
		//	}
		//}
		//}
		//	if len(sideInfo9) > 0 {
		//		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo9, graphIdInt, "indicator_analysis_dimension_2_resource")
		//		if err != nil {
		//			return err
		//		}
		//	}
		//
		//}
	}

	return nil
}

func (c *consumer) updateSource(ctx context.Context, graphConfigName string, entityInfo []map[string]any, entityId string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	fmt.Println(settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetsGraphConfigId)
	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	fmt.Println(graphId)
	fmt.Println(len(entityInfo), entityInfo)

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	dataViewInfo, err := c.dbRepo.GetDataViewInfo(ctx, entityId)
	if err != nil {
		return err
	}
	if dataViewInfo == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"resourceid":         dataViewInfo.ID,
			"code":               dataViewInfo.Code,
			"technical_name":     dataViewInfo.TechnicalName,
			"resourcename":       dataViewInfo.Name,
			"description":        dataViewInfo.Description,
			"asset_type":         dataViewInfo.AssetType,
			"color":              dataViewInfo.Color,
			"published_at":       dataViewInfo.PublishedAt,
			"owner_id":           dataViewInfo.OwnerId,
			"owner_name":         dataViewInfo.OwnerName,
			"department_id":      dataViewInfo.DepartmentId,
			"department":         dataViewInfo.DepartmentName,
			"department_path_id": dataViewInfo.DepartmentPathId,
			"department_path":    dataViewInfo.DepartmentPath,
			"subject_id":         dataViewInfo.SubjectId,
			"subject_name":       dataViewInfo.SubjectName,
			"subject_path_id":    dataViewInfo.SubjectPathId,
			"subject_path":       dataViewInfo.SubjectPath,
		},
	}

	//graphData := []map[string]any{}
	//graphResourceId := map[string]any{}
	//graphResourceId["resourceid"] = entityId
	//graphData = append(graphData, graphResourceId)

	//graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "resource")
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) deleteSource(ctx context.Context, graphConfigName string, entityId string, entityType string) error {
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
		{"resourceid": entityId},
	}

	_, err = c.adProxy.DeleteEntity(ctx, graphData, "resource", graphIdInt)
	if err != nil {
		return err
	}

	if entityType == "FormView" {
		//dataView2Fileds, err := c.dbRepo.GetDataView2Filed(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//for _, item := range dataView2Fileds {
		//	itemGraphData := []map[string]string{
		//		{"column_id": item.ColumnId},
		//	}
		//	_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "field", graphIdInt)
		//}

	} else if entityType == "Service" {
		interface2ResponseFields, err := c.dbRepo.GetInterface2ResponseField(ctx, entityId)
		if err != nil {
			return err
		}
		for _, item := range interface2ResponseFields {
			itemGraphData := []map[string]string{
				{"field_id": item.FieldSid},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "response_field", graphIdInt)
		}

	} else if entityType == "Indicator" {
		//dimensionModel2Indicators, err := c.dbRepo.GetDimensionModel2IndicatorByIndicator(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//for _, item := range dimensionModel2Indicators {
		//	itemGraphData := []map[string]string{
		//		{"id": item.DimensionModelId},
		//	}
		//	_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "dimension_model", graphIdInt)
		//}
		//indicatorAnalysisDimension2Indicators, err := c.dbRepo.GetIndicatorAnalysisDimension2IndicatorByIndicator(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//for _, item := range indicatorAnalysisDimension2Indicators {
		//	itemGraphData := []map[string]string{
		//		{"field_id": item.FieldId,
		//			"formview_id": entityId},
		//	}
		//	_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "indicator_analysis_dimension", graphIdInt)
		//}
	}

	return nil
}

func (c *consumer) createSubDomain(ctx context.Context, graphConfigName string, entityId string) error {
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

	subDomain, err := c.dbRepo.GetSubDomainInfo(ctx, entityId)
	if err != nil {
		return err
	}
	if subDomain == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"subdomainid":   subDomain.Id,
			"subdomainname": subDomain.Name,
			"prefixname":    subDomain.PrefixName,
		},
	}

	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	// to resource
	//subDomain2DataView, err := c.dbRepo.GetSubDomain2DataView(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(subDomain2DataView) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range subDomain2DataView {
	//		addItem := map[string]map[string]string{
	//			"start":     {"subdomainid": item.SubjectId, "_start_entity": "subdomin"},
	//			"end":       {"resourceid": entityId, "_end_entity": "resource"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "subdomain_2_dataresource")
	//	if err != nil {
	//		return err
	//	}
	//}

	// to domain
	subDomain2Domain, err := c.dbRepo.GetSubDomain2Domain(ctx, entityId)
	if err != nil {
		return err
	}
	if len(subDomain2Domain) > 0 {
		sideInfo2 := []map[string]map[string]string{}
		for _, item := range subDomain2Domain {
			addItem := map[string]map[string]string{
				"start":     {"domainid": item.DomainId, "_start_entity": "domain"},
				"end":       {"subdomainid": entityId, "_end_entity": "subdomain"},
				"edge_pros": {},
			}
			sideInfo2 = append(sideInfo2, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo2, graphIdInt, "domain_2_subdomain")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) updateSubDomain(ctx context.Context, graphConfigName string, entityId string) error {
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

	subDomain, err := c.dbRepo.GetSubDomainInfo(ctx, entityId)
	if err != nil {
		return err
	}
	if subDomain == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"subdomainid":   subDomain.Id,
			"subdomainname": subDomain.Name,
			"prefixname":    subDomain.PrefixName,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	return nil
}

// 主题域
func (c *consumer) deleteSubDomain(ctx context.Context, graphConfigName string, entityId string) error {
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
		{"subdomainid": entityId},
	}

	_, err = c.adProxy.DeleteEntity(ctx, graphData, "subdomain", graphIdInt)
	if err != nil {
		return err
	}

	return nil
}

// 主题域分组
func (c *consumer) createDomain(ctx context.Context, graphConfigName string, entityId string) error {
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

	domain, err := c.dbRepo.GetDomainInfo(ctx, entityId)
	if err != nil {
		return err
	}
	if domain == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"domainid":   domain.Id,
			"domainname": domain.Name,
			"prefixname": domain.PrefixName,
		},
	}

	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "domain")
	if err != nil {
		return err
	}

	// to domain
	//domain2SubDomain, err := c.dbRepo.GetDomain2SubDomain(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(domain2SubDomain) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range domain2SubDomain {
	//		addItem := map[string]map[string]string{
	//			"start":     {"domainid": item.DomainId, "_start_entity": "domain"},
	//			"end":       {"subdomainid": entityId, "_end_entity": "subdomain"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "domain_2_subdomain")
	//	if err != nil {
	//		return err
	//	}
	//}

	return nil
}

func (c *consumer) updateDomain(ctx context.Context, graphConfigName string, entityId string) error {
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

	domain, err := c.dbRepo.GetDomainInfo(ctx, entityId)
	if err != nil {
		return err
	}
	if domain == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"domainid":   domain.Id,
			"domainname": domain.Name,
			"prefixname": domain.PrefixName,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) createMetadataSchema(ctx context.Context, graphConfigName string, entityId string) error {
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

	metadataSchema, err := c.dbRepo.GetMetadataSchema(ctx, entityId)
	if err != nil {
		return err
	}
	if metadataSchema == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"metadataschemaid":   metadataSchema.SchemaSid,
			"metadataschemaname": metadataSchema.SchemaName,
			"prefixname":         metadataSchema.PrefixName,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	// to resource
	metadataSchema2DataView, err := c.dbRepo.GetMetadataSchema2DataView(ctx, entityId)
	if err != nil {
		return err
	}
	if len(metadataSchema2DataView) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range metadataSchema2DataView {
			addItem := map[string]map[string]string{
				"start":     {"metadataschemaid": entityId, "_start_entity": "metadataschema"},
				"end":       {"resourceid": item.FormViewUuid, "_end_entity": "resource"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "metadataschema_2_resource")
		if err != nil {
			return err
		}
	}

	// to data source
	metadataSchema2DataSource, err := c.dbRepo.GetMetadataSchema2DataSource(ctx, entityId)
	if err != nil {
		return err
	}
	if len(metadataSchema2DataSource) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range metadataSchema2DataSource {
			addItem := map[string]map[string]string{
				"start":     {"datasourceid": item.DataSourceUuid, "_start_entity": "datasource"},
				"end":       {"metadataschemaid": entityId, "_end_entity": "metadataschema"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "datasource_2_metadataschema")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) updateMetadataSchema(ctx context.Context, graphConfigName string, entityId string) error {
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

	metadataSchema, err := c.dbRepo.GetMetadataSchema(ctx, entityId)
	if err != nil {
		return err
	}
	if metadataSchema == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"metadataschemaid":   metadataSchema.SchemaSid,
			"metadataschemaname": metadataSchema.SchemaName,
			"prefixname":         metadataSchema.PrefixName,
		},
	}

	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) createDataSource(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataSource, err := c.dbRepo.GetDataSource(ctx, entityId)
	if err != nil {
		return err
	}
	if dataSource == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"source_type_name":      dataSource.SourceTypeName,
			"source_type_code":      dataSource.SourceTypeCode,
			"data_source_type_name": dataSource.DataSourceTypeName,
			"prefixname":            dataSource.PrefixName,
			"datasourcename":        dataSource.DataSourceName,
			"datasourceid":          dataSource.DataSourceUuid,
		},
	}
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "datasource")
	if err != nil {
		return err
	}

	// to metaschema
	dataSource2MetadataSchema, err := c.dbRepo.GetDataSource2MetadataSchema(ctx, entityId)
	if err != nil {
		return err
	}
	if len(dataSource2MetadataSchema) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range dataSource2MetadataSchema {
			addItem := map[string]map[string]string{
				"start":     {"datasourceid": entityId, "_start_entity": "datasource"},
				"end":       {"metadataschemaid": item.SchemaSid, "_end_entity": "metadataschema"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)

			dataSchema, err := c.dbRepo.GetMetadataSchema(ctx, item.SchemaSid)
			if err != nil {
				continue
			}
			if dataSchema == nil {
				continue
			}
			addInfo := []map[string]any{
				{
					"metadataschemaid":   dataSchema.SchemaSid,
					"metadataschemaname": dataSchema.SchemaName,
					"prefixname":         "库",
				},
			}
			_, err = c.adProxy.InsertEntity(ctx, "entity", addInfo, graphIdInt, "metadataschema")
			if err != nil {
				continue
			}
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "datasource_2_metadataschema")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) deleteDataSource(ctx context.Context, graphConfigName string, entityId string) error {
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

	mainSearchCfg, err := c.adProxy.GetSearchConfig("datasource", "datasourceid", entityId)
	mainEntityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", mainSearchCfg)

	if len(mainEntityInfo.Res.Nodes) == 0 {
		return nil
	}

	node := mainEntityInfo.Res.Nodes[0]

	edges, err := c.adProxy.NeighborSearchByEngineV2(ctx, node.Id, 1, graphId)
	if len(edges.Res.Nodes) > 0 {
		nNode := edges.Res.Nodes[0]
		metadataschemaid := ""
		if len(nNode.Properties) != 0 {
			for _, p := range nNode.Properties[0].Props {
				if p.Name == "metadataschemaid" {
					metadataschemaid = p.Value
				}
			}
			if metadataschemaid != "" {
				dItem := []map[string]string{
					{"metadataschemaid": metadataschemaid},
				}

				_, err = c.adProxy.DeleteEntity(ctx, dItem, "metadataschema", graphIdInt)
				if err != nil {
					return err
				}

			}
		}

	}

	graphData := []map[string]string{
		{"datasourceid": entityId},
	}
	entityName := "datasource"

	_, err = c.adProxy.DeleteEntity(ctx, graphData, entityName, graphIdInt)
	if err != nil {
		return err
	}
	// 删除库

	//dataSource2MetadataSchema, err := c.dbRepo.GetDataSource2MetadataSchema(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(dataSource2MetadataSchema) > 0 {
	//	for _, item := range dataSource2MetadataSchema {
	//		dItem := []map[string]string{
	//			{"metadataschemaid": item.SchemaSid},
	//		}
	//
	//		_, err = c.adProxy.DeleteEntity(ctx, dItem, "metadataschema", graphIdInt)
	//		if err != nil {
	//			return err
	//		}
	//	}
	//}

	return nil
}

func (c *consumer) createDataViewFields(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataView2Filed, err := c.dbRepo.GetDataViewFields(ctx, entityId)
	if err != nil {
		return err
	}
	if dataView2Filed == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"datatype":       dataView2Filed.DataType,
			"technical_name": dataView2Filed.TechnicalName,
			"formviewid":     dataView2Filed.FormviewUuid,
			"field_name":     dataView2Filed.FieldName,
			"column_id":      dataView2Filed.ColumnId,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "field")
	if err != nil {
		return err
	}

	// to resource
	if dataView2Filed != nil {
		sideInfo1 := []map[string]map[string]string{}
		addItem := map[string]map[string]string{
			"start":     {"column_id": entityId, "_start_entity": "field"},
			"end":       {"resourceid": dataView2Filed.FormviewUuid, "_end_entity": "resource"},
			"edge_pros": {},
		}
		sideInfo1 = append(sideInfo1, addItem)
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "field_2_resource")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) updateDataViewFields(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataView2Filed, err := c.dbRepo.GetDataViewFields(ctx, entityId)
	if err != nil {
		return err
	}
	if dataView2Filed == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"datatype":       dataView2Filed.DataType,
			"technical_name": dataView2Filed.TechnicalName,
			"formviewid":     dataView2Filed.FormviewUuid,
			"field_name":     dataView2Filed.FieldName,
			"column_id":      dataView2Filed.ColumnId,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "subdomain")
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) createResponseField(ctx context.Context, graphConfigName string, entityId string) error {
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

	responseField, err := c.dbRepo.GetResponseField(ctx, entityId)
	if err != nil {
		return err
	}
	if responseField == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"field_id": responseField.FieldSid,
			"en_name":  responseField.EnName,
			"cn_name":  responseField.CnName,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "response_field")
	if err != nil {
		return err
	}

	// to resource
	responseField2Interface, err := c.dbRepo.GetResponseField2Interface(ctx, entityId)
	if err != nil {
		return err
	}
	if len(responseField2Interface) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range responseField2Interface {
			addItem := map[string]map[string]string{
				"start":     {"field_id": entityId, "_start_entity": "response_field"},
				"end":       {"resourceid": item.Id, "_end_entity": "resource"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "Response_field_2_resource")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) createDataExploreReport(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataExploreReport, err := c.dbRepo.GetDataExploreReport(ctx, entityId)
	if err != nil {
		return err
	}
	if dataExploreReport == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"explore_result_value": dataExploreReport.ExploreResultValue,
			"explore_result":       dataExploreReport.ExploreResult,
			"column_name":          dataExploreReport.ColumnName,
			"explore_item":         dataExploreReport.ExploreItem,
			"column_id":            dataExploreReport.ColumnId,
		},
	}

	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "data_explore_report")
	if err != nil {
		return err
	}

	// to resource
	dataExploreReport2DataView, err := c.dbRepo.GetDataExploreReport2DataView(ctx, entityId)
	if err != nil {
		return err
	}
	if len(dataExploreReport2DataView) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range dataExploreReport2DataView {
			addItem := map[string]map[string]string{
				"start":     {"column_id": entityId, "_start_entity": "data_explore_report"},
				"end":       {"resourceid": item.FormviewUuid, "_end_entity": "resource"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "data_explore_report_2_resource")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) deleteDataExploreReport(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataExploreReport, err := c.dbRepo.GetDataExploreReport(ctx, entityId)
	if err != nil {
		return err
	}
	if dataExploreReport == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]string{
		{
			"explore_result": dataExploreReport.ExploreResult,
			"explore_item":   dataExploreReport.ExploreItem,
			"column_id":      dataExploreReport.ColumnId,
		},
	}

	_, err = c.adProxy.DeleteEntity(ctx, graphData, "data_explore_report", graphIdInt)
	if err != nil {
		return err
	}

	return nil
}

func (c *consumer) createDataOwner(ctx context.Context, graphConfigName string, entityId string) error {
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

	dataOwner, err := c.dbRepo.GetDataOwner(ctx, entityId)
	if err != nil {
		return err
	}
	if dataOwner == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"dataownerid":   dataOwner.OwnerId,
			"dataownername": dataOwner.OwnerName,
		},
	}

	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "dataowner")
	if err != nil {
		return err
	}

	// to resource
	//dataOwner2DataView, err := c.dbRepo.GetDataOwner2DataView(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(dataOwner2DataView) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range dataOwner2DataView {
	//		addItem := map[string]map[string]string{
	//			"start":     {"dataownerid": entityId, "_start_entity": "dataowner"},
	//			"end":       {"resourceid": item.Id, "_end_entity": "resource"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "dataowner_2_datacatalog")
	//	if err != nil {
	//		return err
	//	}
	//}

	return nil
}

func (c *consumer) createDepartment(ctx context.Context, graphConfigName string, entityId string) error {
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

	department, err := c.dbRepo.GetDepartment(ctx, entityId)
	if err != nil {
		return err
	}
	if department == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"departmentname": department.Name,
			"departmentid":   department.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "department")
	if err != nil {
		return err
	}

	// to resource
	//department2DataView, err := c.dbRepo.GetDepartment2DataView(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(department2DataView) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range department2DataView {
	//		addItem := map[string]map[string]string{
	//			"start":     {"departmentid": entityId, "_start_entity": "department"},
	//			"end":       {"resourceid": item.Id, "_end_entity": "resource"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "department_2_datacatalog")
	//	if err != nil {
	//		return err
	//	}
	//}

	return nil
}

func (c *consumer) createDimensionModel(ctx context.Context, graphConfigName string, entityId string) error {
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

	dimensionModel, err := c.dbRepo.GetDimensionModel(ctx, entityId)
	if err != nil {
		return err
	}
	if dimensionModel == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"description": dimensionModel.Description,
			"name":        dimensionModel.Name,
			"id":          dimensionModel.Id,
		},
	}

	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "dimension_model")
	if err != nil {
		return err
	}

	// to resource
	//dimensionModel2Indicator, err := c.dbRepo.GetDimensionModel2IndicatorByDimension(ctx, entityId)
	//if err != nil {
	//	return err
	//}
	//if len(dimensionModel2Indicator) > 0 {
	//	sideInfo1 := []map[string]map[string]string{}
	//	for _, item := range dimensionModel2Indicator {
	//		addItem := map[string]map[string]string{
	//			"start":     {"id": entityId, "_start_entity": "dimension_model"},
	//			"end":       {"resourceid": item.Id, "_end_entity": "resource"},
	//			"edge_pros": {},
	//		}
	//		sideInfo1 = append(sideInfo1, addItem)
	//	}
	//	_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "dimension_model_2_resource")
	//	if err != nil {
	//		return err
	//	}
	//}

	return nil
}

func (c *consumer) createIndicatorAnalysisDimension(ctx context.Context, graphConfigName string, entityId string) error {
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

	indicatorAnalysisDimension, err := c.dbRepo.GetIndicatorAnalysisDimension(ctx, entityId)
	if err != nil {
		return err
	}
	if indicatorAnalysisDimension == nil {
		errors.Wrap(err, "can not find data_view "+entityId)
		return err
	}
	graphData := []map[string]any{
		{
			"field_data_type":      indicatorAnalysisDimension.FieldDataType,
			"field_technical_name": indicatorAnalysisDimension.FieldTechnicalName,
			"field_business_name":  indicatorAnalysisDimension.FieldBusinessName,
			"field_id":             indicatorAnalysisDimension.FieldId,
			"formview_id":          indicatorAnalysisDimension.FormViewId,
		},
	}

	graphIdInt = 750
	//fmt.Println(graphIdInt, graphData)
	_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "indicator_analysis_dimension")
	if err != nil {
		return err
	}

	// to resource
	indicatorAnalysisDimension2Indicator, err := c.dbRepo.GetIndicatorAnalysisDimension2IndicatorByIndicatorAnalysisDimension(ctx, entityId)
	if err != nil {
		return err
	}
	if len(indicatorAnalysisDimension2Indicator) > 0 {
		sideInfo1 := []map[string]map[string]string{}
		for _, item := range indicatorAnalysisDimension2Indicator {
			addItem := map[string]map[string]string{
				"start":     {"field_id": entityId, "_start_entity": "indicator_analysis_dimension"},
				"end":       {"resourceid": string(item.InticatorId), "_end_entity": "resource"},
				"edge_pros": {},
			}
			sideInfo1 = append(sideInfo1, addItem)
		}
		_, err = c.adProxy.InsertSide(ctx, "edge", sideInfo1, graphIdInt, "indicator_analysis_dimension_2_resource")
		if err != nil {
			return err
		}
	}

	return nil
}

func (c *consumer) upsertDepartmentResourceEntity(ctx context.Context, graphId string, departmentId string, departmentName string) error {
	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}
	searchCfg, err := c.adProxy.GetSearchConfig("department", "departmentid", departmentId)
	entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
	if len(entityInfo.Res.Nodes) == 0 {
		//department, err := c.dbRepo.GetDepartment(ctx, entityId)
		//if err != nil {
		//	return err
		//}
		//if department == nil {
		//	errors.Wrap(err, "can not find data_view "+entityId)
		//	return err
		//}
		departmentData := []map[string]any{
			{
				"departmentid":   departmentId,
				"departmentname": departmentName,
			},
		}
		_, err = c.adProxy.InsertEntity(ctx, "entity", departmentData, graphIdInt, "department")
		if err != nil {
			return err
		}

	}

	return nil
}

func (c *consumer) upsertDataOwnerResourceEntity(ctx context.Context, graphId string, ownerId string, ownerName string) error {
	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}
	searchCfg, err := c.adProxy.GetSearchConfig("dataowner", "dataownerid", ownerId)
	entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
	if len(entityInfo.Res.Nodes) == 0 {

		dataOwnerData := []map[string]any{
			{
				"dataownerid":   ownerId,
				"dataownername": ownerName,
			},
		}
		_, err = c.adProxy.InsertEntity(ctx, "entity", dataOwnerData, graphIdInt, "dataowner")
		if err != nil {
			return err
		}

	}

	return nil
}

func (c *consumer) upsertExploreReportResourceEntity(ctx context.Context, graphId string, entityId string) error {

	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}

	searchCfg, err := c.adProxy.GetSearchConfig("data_explore_report", "column_id", entityId)
	entityInfo, err := c.adProxy.FulltextSearchV2(ctx, graphId, "", searchCfg)
	if len(entityInfo.Res.Nodes) == 0 {
		dataExploreReport, err := c.dbRepo.GetDataExploreReport(ctx, entityId)
		if err != nil {
			return err
		}
		if dataExploreReport == nil {
			errors.Wrap(err, "can not find data_view "+entityId)
			return err
		}
		graphData := []map[string]any{
			{
				"explore_result_value": dataExploreReport.ExploreResultValue,
				"explore_result":       dataExploreReport.ExploreResult,
				"column_name":          dataExploreReport.ColumnName,
				"explore_item":         dataExploreReport.ExploreItem,
				"column_id":            dataExploreReport.ColumnId,
			},
		}
		//fmt.Println(graphIdInt, graphData)
		_, err = c.adProxy.InsertEntity(ctx, "entity", graphData, graphIdInt, "data_explore_report")
		if err != nil {
			return err
		}

	}

	return nil
}

func (c *consumer) deleteSubjectDomainTypeResource(ctx context.Context, graphConfigName string, entityName string, entityId string, entityIdPath string) error {
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
		{"domainid": entityId},
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
				{"subdomainid": item.Id},
			}
			_, err = c.adProxy.DeleteEntity(ctx, itemGraphData, "subdomain", graphIdInt)
		default:
			continue
		}

	}

	return nil
}
