package impl

import (
	"context"
	_ "embed"
	"errors"
	"net/http"

	es "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/opensearch"
	es_common_object "github.com/kweaver-ai/chat-data/sailor-service/common/es"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/olivere/elastic/v7"
)

const (
	mappingVersionV1                 = "af_sailor_subject_model_idx_v1"
	mappingVersionV2                 = "af_sailor_subject_model_idx_v2"
	labelMappingVersionV3            = "af_sailor_subject_model_label_idx_v1"
	EntityRuleVersionV1              = "af_sailor_entity_rule_idx_v1"
	EntityFormVersionV1              = "af_sailor_entity_form_idx_v1"
	EntityFlowchartVersionV1         = "af_sailor_entity_flow_chart_idx_v1"
	EntityDataElementVersionV1       = "af_sailor_entity_data_element_idx_v1"
	EntityFieldVersionV1             = "af_sailor_entity_field_idx_v1"
	EntityBusinessIndicatorVersionV1 = "af_sailor_entity_business_indicator_idx_v1"
	EntityFormViewVersionV1          = "af_sailor_entity_form_view_idx_v1"
	EntityLabelVersionV1             = "af_sailor_entity_label_idx_v1"
	EntitySubjectPropertyVersionV1   = "af_sailor_entity_subject_property_idx_v1"
)

var (
	//go:embed mapping_v1.json
	mappingV1 string
	//go:embed mapping_v2.json
	mappingV2 string
	//go:embed mapping_v3.json
	mappingV3 string
	//go:embed mapping_entity_rule_v1.json
	entityRuleMappingV1 string
	//go:embed mapping_entity_form_v1.json
	entityFormMappingV1 string
	//go:embed mapping_entity_data_element_v1.json
	entityDataElementMappingV1 string
	//go:embed mapping_entity_field_v1.json
	entityFieldMappingV1 string
	//go:embed mapping_entity_form_view_v1.json
	entityFormViewMappingV1 string
	//go:embed mapping_entity_subject_property_v1.json
	entitySubjectPropertyMappingV1 string
)

const (
	indicesAlias                      = "af_sailor_subject_model_idx"
	IndicesName                       = mappingVersionV2
	indicesLabelAlias                 = "af_sailor_subject_model_label_idx"
	IndicesLabelName                  = labelMappingVersionV3
	indicesEntityRuleAlias            = "af_sailor_entity_rule_idx"
	IndicesEntityRuleName             = EntityRuleVersionV1
	indicesEntityFormAlias            = "af_sailor_entity_form_idx"
	IndicesEntityFormName             = EntityFormVersionV1
	indicesEntityDataElementAlias     = "af_sailor_entity_data_element_idx"
	IndicesEntityDataElementName      = EntityDataElementVersionV1
	indicesEntityFieldAlias           = "af_sailor_entity_field_idx"
	IndicesEntityFieldName            = EntityFieldVersionV1
	indicesEntityFormViewAlias        = "af_sailor_entity_form_view_idx"
	IndicesEntityFormViewName         = EntityFormViewVersionV1
	indicesEntitySubjectPropertyAlias = "af_sailor_entity_subject_property_idx"
	IndicesEntitySubjectPropertyName  = EntitySubjectPropertyVersionV1
)

var (
	mappingVersionMap = map[string]string{
		mappingVersionV1:               mappingV1,
		mappingVersionV2:               mappingV2,
		labelMappingVersionV3:          mappingV3,
		EntityRuleVersionV1:            entityRuleMappingV1,
		EntityFormVersionV1:            entityFormMappingV1,
		EntityDataElementVersionV1:     entityDataElementMappingV1,
		EntityFieldVersionV1:           entityFieldMappingV1,
		EntityFormViewVersionV1:        entityFormViewMappingV1,
		EntitySubjectPropertyVersionV1: entitySubjectPropertyMappingV1,
	}

	mapping                      = mappingVersionMap[IndicesName]
	mappingLabel                 = mappingVersionMap[IndicesLabelName]
	mappingEntityRule            = mappingVersionMap[IndicesEntityRuleName]
	mappingEntityForm            = mappingVersionMap[IndicesEntityFormName]
	mappingEntityDataElement     = mappingVersionMap[IndicesEntityDataElementName]
	mappingEntityField           = mappingVersionMap[IndicesEntityFieldName]
	mappingEntityFormView        = mappingVersionMap[IndicesEntityFormViewName]
	mappingEntitySubjectProperty = mappingVersionMap[IndicesEntitySubjectPropertyName]
)

type objSearch struct {
	esClient *opensearch.SearchClient
}

func NewObjSearch(esClient *opensearch.SearchClient) (es.ESSubjectModel, error) {
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesAlias,
		IndicesName,
		mapping,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesLabelAlias,
		IndicesLabelName,
		mappingLabel,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntityRuleAlias,
		IndicesEntityRuleName,
		mappingEntityRule,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntityFormAlias,
		IndicesEntityFormName,
		mappingEntityForm,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntityDataElementAlias,
		IndicesEntityDataElementName,
		mappingEntityDataElement,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntityFieldAlias,
		IndicesEntityFieldName,
		mappingEntityDataElement,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntityFormViewAlias,
		IndicesEntityFormViewName,
		mappingEntityDataElement,
		esClient,
	); err != nil {
		return nil, err
	}
	if err := es_common_object.InitIndices(
		context.Background(),
		indicesEntitySubjectPropertyAlias,
		IndicesEntitySubjectPropertyName,
		mappingEntityDataElement,
		esClient,
	); err != nil {
		return nil, err
	}
	return &objSearch{esClient: esClient}, nil
}

func (e objSearch) Index(ctx context.Context, doc *es.SubjectModelDoc) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

func (e objSearch) IndexLabel(ctx context.Context, doc *es.SubjectModelLabelDoc) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesLabelAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesLabelAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

func (e objSearch) IndexEntityRule(ctx context.Context, doc *es.EntityRuleDoc) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntityRuleAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntityRuleAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

func (e objSearch) IndexEntityFormDoc(ctx context.Context, doc *es.EntityFormDoc) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntityFormAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntityFormAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

//func (e objSearch) IndexEntityFlowchart(ctx context.Context, doc *es.EntityFlowchart) (err error) {
//	ctx, span := trace.StartInternalSpan(ctx)
//	defer func() { trace.TelemetrySpanEnd(span, err) }()
//
//	if doc == nil {
//		return nil
//	}
//	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesAlias, doc.DocID)
//
//	resp, err := e.esClient.WriteClient.
//		Index().
//		Index(indicesAlias).
//		Id(doc.DocID).
//		BodyJson(doc).
//		Do(ctx)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
//		return err
//	}
//
//	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
//	return nil
//}

func (e objSearch) IndexEntityDataElement(ctx context.Context, doc *es.EntityDataElement) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntityDataElementAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntityDataElementAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

func (e objSearch) IndexEntityField(ctx context.Context, doc *es.EntityField) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntityFieldAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntityFieldAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

//func (e objSearch) IndexEntityBusinessIndicator(ctx context.Context, doc *es.EntityBusinessIndicator) (err error) {
//	ctx, span := trace.StartInternalSpan(ctx)
//	defer func() { trace.TelemetrySpanEnd(span, err) }()
//
//	if doc == nil {
//		return nil
//	}
//	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesAlias, doc.DocID)
//
//	resp, err := e.esClient.WriteClient.
//		Index().
//		Index(indicesLabelAlias).
//		Id(doc.DocID).
//		BodyJson(doc).
//		Do(ctx)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
//		return err
//	}
//
//	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
//	return nil
//}

func (e objSearch) IndexEntityFormView(ctx context.Context, doc *es.EntityFormView) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntityFormViewAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntityFormViewAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

func (e objSearch) IndexEntitySubjectProperty(ctx context.Context, doc *es.EntitySubjectProperty) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if doc == nil {
		return nil
	}
	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesEntitySubjectPropertyAlias, doc.DocID)

	resp, err := e.esClient.WriteClient.
		Index().
		Index(indicesEntitySubjectPropertyAlias).
		Id(doc.DocID).
		BodyJson(doc).
		Do(ctx)
	if err != nil {
		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
		return err
	}

	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
	return nil
}

//func (e objSearch) IndexEntityLabel(ctx context.Context, doc *es.EntityLabel) (err error) {
//	ctx, span := trace.StartInternalSpan(ctx)
//	defer func() { trace.TelemetrySpanEnd(span, err) }()
//
//	if doc == nil {
//		return nil
//	}
//	log.WithContext(ctx).Infof("index doc to es,index: %v, doc id: %v", indicesAlias, doc.DocID)
//
//	resp, err := e.esClient.WriteClient.
//		Index().
//		Index(indicesEntityLabelAlias).
//		Id(doc.DocID).
//		BodyJson(doc).
//		Do(ctx)
//	if err != nil {
//		log.WithContext(ctx).Errorf("failed to index doc to es, err info: %v", err.Error())
//		return err
//	}
//
//	log.WithContext(ctx).Infof("es index doc resp: %v", *resp)
//	return nil
//}

func (e objSearch) Delete(ctx context.Context, id string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	log.WithContext(ctx).Infof("delete data-view  doc from es, doc id")
	if id == "" {
		return nil
	}
	resp, err := e.esClient.WriteClient.
		Delete().
		Index(indicesAlias).
		Id(id).
		Do(ctx)
	if err != nil {
		var esErr *elastic.Error
		if errors.As(err, &esErr) && esErr.Status == http.StatusNotFound {
			log.WithContext(ctx).Warnf("failed to delete doc from es, doc not found, docid: %v, err: %v", id, err)
			return nil
		}

		log.WithContext(ctx).Errorf("failed to delete doc from es, err: %v", err)
		return err
	}

	log.WithContext(ctx).Infof("es delete doc resp: %v", *resp)
	return nil
}

func (e objSearch) DeleteLabel(ctx context.Context, id string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	log.WithContext(ctx).Infof("delete data-view  doc from es, doc id")
	if id == "" {
		return nil
	}
	resp, err := e.esClient.WriteClient.
		Delete().
		Index(indicesLabelAlias).
		Id(id).
		Do(ctx)
	if err != nil {
		var esErr *elastic.Error
		if errors.As(err, &esErr) && esErr.Status == http.StatusNotFound {
			log.WithContext(ctx).Warnf("failed to delete doc from es, doc not found, docid: %v, err: %v", id, err)
			return nil
		}

		log.WithContext(ctx).Errorf("failed to delete doc from es, err: %v", err)
		return err
	}

	log.WithContext(ctx).Infof("es delete doc resp: %v", *resp)
	return nil
}

func (e objSearch) DeleteIndex(ctx context.Context, id string, indexAlias string) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	log.WithContext(ctx).Infof("delete data-view  doc from es, doc id")
	if id == "" {
		return nil
	}
	resp, err := e.esClient.WriteClient.
		Delete().
		Index(indexAlias).
		Id(id).
		Do(ctx)
	if err != nil {
		var esErr *elastic.Error
		if errors.As(err, &esErr) && esErr.Status == http.StatusNotFound {
			log.WithContext(ctx).Warnf("failed to delete doc from es, doc not found, docid: %v, err: %v", id, err)
			return nil
		}

		log.WithContext(ctx).Errorf("failed to delete doc from es, err: %v", err)
		return err
	}

	log.WithContext(ctx).Infof("es delete doc resp: %v", *resp)
	return nil
}
