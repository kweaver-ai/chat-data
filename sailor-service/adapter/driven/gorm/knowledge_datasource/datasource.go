package knowledge_datasource

import (
	"context"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/kweaver-ai/idrm-go-frame/core/store/gormx"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type Repo interface {
	GetDataViewInfo(ctx context.Context, dataViewId string) (*model.EntityDataResource, error)
	GetInterfaceServiceInfo(ctx context.Context, serviceId string) (*model.EntityDataResource, error)
	GetIndicatorInfo(ctx context.Context, entityId string) (*model.EntityDataResource, error)
	GetIndicatorInfoV2(ctx context.Context, entityId string) (*model.EntityIndicator, error)
	GetEmptyEntityDataResource() (*model.EntityDataResource, error)
	GetDataView2DataExploreReport(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2DataExploreReport, error)
	GetInterface2ResponseField(ctx context.Context, interfaceId string) ([]*model.EdgeInterface2ResponseField, error)
	GetDataView2Filed(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2Filed, error)
	GetDataView2MetadataSchema(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2MetadataSchema, error)
	GetDataView2MetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeDataView2MetadataSchema, error)
	GetDimensionModel2IndicatorByIndicator(ctx context.Context, entityId string) ([]*model.EdgeDimensionModel2Resource, error)
	GetIndicatorAnalysisDimension2IndicatorByIndicator(ctx context.Context, entityId string) ([]*model.EdgeIndicatorAnalysisDimension2Resource, error)
	GetDimensionModel(ctx context.Context, entityId string) (*model.EntityDimensionModel, error)
	GetDimensionModel2IndicatorByDimension(ctx context.Context, entityId string) ([]*model.EdgeDimensionModel2Resource, error)
	GetIndicatorAnalysisDimension(ctx context.Context, entityId string) (*model.EntityIndicatorAnalysisDimension, error)
	GetIndicatorAnalysisDimension2IndicatorByIndicatorAnalysisDimension(ctx context.Context, entityId string) ([]*model.EdgeIndicatorAnalysisDimension2Resource, error)
	GetSubDomainInfo(ctx context.Context, subDomainId string) (*model.EntitySubdomain, error)
	GetSubDomain2DataView(ctx context.Context, subDomainId string) ([]*model.EdgeSubdomain2DataView, error)
	GetSubDomain2Domain(ctx context.Context, subDomainId string) ([]*model.EdgeSubdomain2Domain, error)
	GetDomainInfo(ctx context.Context, domainId string) (*model.EntityDomain, error)
	GetDomain2SubDomain(ctx context.Context, domainId string) ([]*model.EdgeDomain2Subdomain, error)
	GetMetadataSchema(ctx context.Context, metadataSchemaId string) (*model.EntityMetadataSchema, error)
	GetMetadataSchema2DataView(ctx context.Context, metadataSchemaId string) ([]*model.EdgeMetadataSchema2DataView, error)
	GetMetadataSchema2DataSource(ctx context.Context, metadataSchemaId string) ([]*model.EdgeMetadataSchema2DataSource, error)
	GetDataSource(ctx context.Context, dataSourceId string) (*model.EntityDataSource, error)
	GetDataSource2MetadataSchema(ctx context.Context, dataSourceId string) ([]*model.EdgeDataSource2MetadataSchema, error)
	GetDataSourceAndMetadataSchemaByMetadataSchema(ctx context.Context, metadataSchemaId string) (*model.EdgeDataSourceAndMetadataSchemaByMetadataSchema, error)
	GetDataViewFields(ctx context.Context, dataViewFieldId string) (*model.EntityDataViewFields, error)
	//GetDataViewFields2DataView(ctx context.Context, dataViewFieldId string) ([]*model.EdgeDataViewFields2DataView, error)
	GetResponseField(ctx context.Context, filedId string) (*model.EntityResponseField, error)
	GetResponseField2Interface(ctx context.Context, filedId string) ([]*model.EdgeResponseField2Interface, error)
	GetDataExploreReport(ctx context.Context, filedId string) (*model.EntityDataExploreReport, error)
	GetDataExploreReport2DataView(ctx context.Context, columnId string) ([]*model.EdgeDataExploreReport2DataView, error)
	GetDataOwner(ctx context.Context, filedId string) (*model.EntityDataOwner, error)
	GetDataOwner2DataView(ctx context.Context, ownerId string) ([]*model.EdgeDataOwner2DataView, error)
	GetDepartment(ctx context.Context, filedId string) (*model.EntityDepartment, error)
	GetDepartment2DataView(ctx context.Context, departmentId string) ([]*model.EdgeDepartment2DataView, error)
	//GetEntityDomainGroup(ctx context.Context, entityId string)

	GetDataCatalog(ctx context.Context, entityId string) (*model.EntityDataCatalog, error)
	GetDataCatalogByFlowId(ctx context.Context, entityId string) (*model.EntityDataCatalog, error)
	GetEmptyDataCatalog() (*model.EntityDataCatalog, error)
	GetCatalogTag2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeCatalogTag2DataCatalog, error)
	GetInfoSystem2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeInfoSystem2DataCatalog, error)
	GetDepartment2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeDepartment2DataCatalog, error)
	GetDataOwner2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeDataOwner2DataCatalog, error)
	GetFormView2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeFormView2DataCatalog, error)
	GetCatalogTag(ctx context.Context, entityId string) (*model.EntityCatalogTag, error)
	GetCatalogTag2DataCatalogByCatalogTag(ctx context.Context, entityId string) ([]*model.EdgeCatalogTag2DataCatalog, error)
	GetInfoSystem(ctx context.Context, entityId string) (*model.EntityInfoSystem, error)
	GetInfoSystem2DataCatalogByInfoSystem(ctx context.Context, entityId string) ([]*model.EdgeInfoSystem2DataCatalog, error)
	GetDepartmentV2(ctx context.Context, entityId string) (*model.EntityDepartmentV2, error)
	GetDepartment2DataCatalogByDepartment(ctx context.Context, entityId string) ([]*model.EdgeDepartment2DataCatalog, error)
	GetDataOwnerV2(ctx context.Context, entityId string) (*model.EntityDataOwnerV2, error)
	GetDataOwner2DataCatalogByDataOwner(ctx context.Context, entityId string) ([]*model.EdgeDataOwner2DataCatalog, error)
	GetFormViewV2(ctx context.Context, entityId string) (*model.EntityFormViewV2, error)
	GetFormView2DataCatalogByFormView(ctx context.Context, entityId string) ([]*model.EdgeFormView2DataCatalog, error)
	GetDataExploreReport2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeDataExploreReport2MetadataTable, error)
	GetMetadataTableField2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeMetadataTableField2MetadataTable, error)
	GetMetadataSchema2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeMetadataSchema2MetadataTable, error)
	GetMetadataSchemaV2(ctx context.Context, entityId string) (*model.EntityMetadataSchemaV2, error)
	GetMetadataSchema2MetadataTableByMetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeMetadataSchema2MetadataTable, error)
	GetDatasource2MetaDataSchemaByMetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeDatasource2MetaDataSchema, error)
	GetDataSourceV2(ctx context.Context, entityId string) (*model.EntityDataSourceV2, error)
	GetDatasource2MetaDataSchemaByDataSourceV2(ctx context.Context, entityId string) ([]*model.EdgeDatasource2MetaDataSchema, error)
	GetDataExploreReportV2(ctx context.Context, entityId string) (*model.EntityDataExploreReportV2, error)
	GetDataExploreReport2MetadataTableByDataExploreReportV2(ctx context.Context, entityId string) ([]*model.EdgeDataExploreReport2MetadataTable, error)
	GetFormViewFieldV2(ctx context.Context, entityId string) (*model.EntityFormViewFieldV2, error)
	GetMetadataTableField2MetadataTableByFormViewFieldV2(ctx context.Context, entityId string) ([]*model.EdgeMetadataTableField2MetadataTable, error)

	GetEntityDomainGroup(ctx context.Context, entityId string) (*model.EntityEntityDomainGroup, error)
	GetRelationDomainGroup2DomainByDomainGroup(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainGroup2Domain, error)
	GetEntityDomain(ctx context.Context, entityId string) (*model.EntityEntityDomain, error)
	GetRelationDomainGroup2DomainByDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainGroup2Domain, error)
	GetRelationDomain2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2Self, error)
	GetRelationDomain2DomainFlowByDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2DomainFlow, error)
	GetEntityDomainFlow(ctx context.Context, entityId string) (*model.EntityEntityDomainFlow, error)
	GetRelationDomain2DomainFlowByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2DomainFlow, error)
	GetRelationDomainFlow2InfomationSystemByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainFlow2InfomationSystem, error)
	GetRelationBusinessModel2DepartmentByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Department, error)
	GetRelationBusinessModel2DomainFlowByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2DomainFlow, error)
	GetEntityInfomationSystem(ctx context.Context, entityId string) (*model.EntityEntityInfomationSystem, error)
	GetRelationDomainFlow2InfomationSystemByInfomationSystem(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainFlow2InfomationSystem, error)
	GetEntityDepartment(ctx context.Context, entityId string) (*model.EntityEntityDepartment, error)
	GetRelationBusinessModel2DepartmentByDepartment(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Department, error)
	GetRelationDepartment2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationDepartment2Self, error)
	GetEntityBusinessModel(ctx context.Context, entityId string) (*model.EntityEntityBusinessModel, error)
	GetRelationBusinessModel2DomainFlowByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2DomainFlow, error)
	GetRelationBusinessModel2FormByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Form, error)
	GetRelationBusinessModel2FlowchartByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Flowchart, error)
	GetEntityFlowchart(ctx context.Context, entityId string) (*model.EntityEntityFlowchart, error)
	GetRelationBusinessModel2FlowchartByFlowchart(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Flowchart, error)
	GetRelationFlowchart2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2Self, error)
	GetRelationFlowchart2FlowchartNodeByFlowchart(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2FlowchartNode, error)
	GetEntityFlowchartNode(ctx context.Context, entityId string) (*model.EntityEntityFlowchartNode, error)
	GetRelationFlowchartNode2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchartNode2Self, error)
	GetRelationFlowchart2FlowchartNodeByFlowchartNode(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2FlowchartNode, error)
	GetEntityForm(ctx context.Context, entityId string) (*model.EntityEntityForm, error)
	GetEntityFormList(ctx context.Context) ([]*model.EntityEntityForm, error)
	GetRelationForm2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Self, error)
	GetRelationBusinessModel2FormByForm(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Form, error)
	GetRelationForm2FieldByForm(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Field, error)
	GetEntityField(ctx context.Context, entityId string) (*model.EntityEntityField, error)
	GetRelationForm2FieldByField(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Field, error)
	GetRelationDataElement2FieldByField(ctx context.Context, entityId string) ([]*model.EdgeRelationDataElement2Field, error)
	GetEntityDataElement(ctx context.Context, entityId string) (*model.EntityEntityDataElement, error)
	GetEntityDataElementList(ctx context.Context) ([]*model.EntityEntityDataElement, error)
	GetEntityLabel(ctx context.Context, entityId string) (*model.EntityEntityLabel, error)
	GetEntityLabelsByCategory(ctx context.Context, entityId string) ([]*model.EntityEntityLabel, error)
	GetEntityLabelsByCategoryIgnoreFState(ctx context.Context, entityId string) ([]*model.EntityEntityLabel, error)
	GetEntityBusinessIndicator(ctx context.Context, entityId string) (*model.EntityEntityBusinessIndicator, error)
	GetEntityRule(ctx context.Context, entityId string) (*model.EntityEntityRule, error)
	GetEntityRuleList(ctx context.Context) ([]*model.EntityEntityRule, error)
	GetRelationDataElement2FieldByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationDataElement2Field, error)
	GetRelationViewField2DataElementByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationViewField2DataElement, error)
	GetRelationSubjectProperty2EntityDataElementByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectProperty2EntityDataElement, error)
	GetEntityFormViewField(ctx context.Context, entityId string) (*model.EntityEntityFormViewField, error)
	GetRelationViewField2DataElementByViewField(ctx context.Context, entityId string) ([]*model.EdgeRelationViewField2DataElement, error)
	GetRelationFormView2FieldByViewField(ctx context.Context, entityId string) ([]*model.EdgeRelationFormView2Field, error)
	GetEntityFormView(ctx context.Context, entityId string) (*model.EntityEntityFormView, error)
	GetEntityFormViewList(ctx context.Context) ([]*model.EntityEntityFormView, error)
	GetRelationFormView2FieldByFormView(ctx context.Context, entityId string) ([]*model.EdgeRelationFormView2Field, error)
	GetEntitySubjectProperty(ctx context.Context, entityId string) (*model.EntityEntitySubjectProperty, error)
	GetEntitySubjectPropertyList(ctx context.Context) ([]*model.EntityEntitySubjectProperty, error)
	GetRelationSubjectProperty2EntityDataElementBySubjectProperty(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectProperty2EntityDataElement, error)
	GetRelationSubjectEntity2SubjectPropBySubjectProperty(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectEntity2SubjectProp, error)
	GetEntitySubjectEntity(ctx context.Context, entityId string) (*model.EntityEntitySubjectEntity, error)
	GetRelationSubjectEntity2SubjectPropBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectEntity2SubjectProp, error)
	GetRelationSubjectObject2SubjectEntityBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2SubjectEntity, error)
	GetEntitySubjectObject(ctx context.Context, entityId string) (*model.EntityEntitySubjectObject, error)
	GetRelationSubjectObject2SubjectEntityBySubjectObject(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2SubjectEntity, error)
	GetRelationSubjectObject2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2Self, error)
	GetRelationSubjectDomain2SubjectObjectBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectDomain2SubjectObject, error)
	GetEntitySubjectDomain(ctx context.Context, entityId string) (*model.EntityEntitySubjectDomain, error)
	GetRelationSubjectDomain2SubjectObjectBySubjectDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectDomain2SubjectObject, error)
	GetRelationSubjectGroup2SubjectDomainsBySubjectDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectGroup2SubjectDomains, error)
	GetEntitySubjectGroup(ctx context.Context, entityId string) (*model.EntityEntitySubjectGroup, error)
	GetRelationSubjectGroup2SubjectDomainsBySubjectGroup(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectGroup2SubjectDomains, error)

	GetTableSubjectDomainByPathId(ctx context.Context, pathId string) ([]*model.TableSubjectDomain, error)
	GetEntitySubjectModel(ctx context.Context, entityId string) (*model.EntityEntitySubjectModel, error)
	GetEntitySubjectModelList(ctx context.Context) ([]*model.EntityEntitySubjectModel, error)
	GetEntitySubjectModelLabelList(ctx context.Context) ([]*model.EntityEntitySubjectModelLabel, error)

	// 业务架构图谱

	GetBRGEntityBusinessDomain(ctx context.Context, entityId string) (*model.BRGEntityBusinessDomain, error)
	GetBRGEntityThemeDomain(ctx context.Context, entityId string) (*model.BRGEntityThemeDomain, error)
	GetBRGEntityBusinessObject(ctx context.Context, entityId string) (*model.BRGEntityBusinessObject, error)
	GetBRGEntityDataCatalog(ctx context.Context, entityId string) (*model.BRGEntityDataCatalog, error)
	GetBRGEntityInfoSystem(ctx context.Context, entityId string) (*model.BRGEntityInfoSystem, error)
	GetBRGEntityBusinessScene(ctx context.Context, entityId string) (*model.BRGEntityBusinessScene, error)
	GetBRGEntityDataCatalogColumn(ctx context.Context, entityId string) (*model.BRGEntityDataCatalogColumn, error)
	GetBRGEntitySourceTable(ctx context.Context, entityId string) (*model.BRGEntitySourceTable, error)
	GetBRGEntityDepartment(ctx context.Context, entityId string) (*model.BRGEntityDepartment, error)
	GetBRGEntityStandardTable(ctx context.Context, entityId string) (*model.BRGEntityStandardTable, error)
	GetBRGEntityBusinessFormStandard(ctx context.Context, entityId string) (*model.BRGEntityBusinessFormStandard, error)
	GetBRGEntityField(ctx context.Context, entityId string) (*model.BRGEntityField, error)
	GetBRGEntityBusinessModel(ctx context.Context, entityId string) (*model.BRGEntityBusinessModel, error)
	GetBRGEntityBusinessIndicator(ctx context.Context, entityId string) (*model.BRGEntityBusinessIndicator, error)
	GetBRGEntityFlowchart(ctx context.Context, entityId string) (*model.BRGEntityFlowchart, error)
	GetBRGEntityFlowchartNode(ctx context.Context, entityId string) (*model.BRGEntityFlowchartNode, error)
	GetBRGEdgeEntityBusinessDomain2EntityThemeDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessDomain2EntityThemeDomain, error)
	GetBRGEdgeEntityThemeDomain2EntityBusinessDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityThemeDomain2EntityBusinessDomain, error)
	GetBRGEdgeEntityThemeDomain2EntityBusinessObject(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityThemeDomain2EntityBusinessObject, error)
	GetBRGEdgeEntityBusinessObject2EntityThemeDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityThemeDomain, error)
	GetBRGEdgeEntityBusinessObject2EntityBusinessForm(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityBusinessForm, error)
	GetBRGEdgeEntityBusinessObject2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityDataCatalog, error)
	GetBRGEdgeEntityDataCatalog2EntityInfoSystem(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityDataCatalog2EntityInfoSystem, error)
	GetBRGEdgeEntityCatalog2EntityBusinessSceneSource(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityCatalog2EntityBusinessSceneSource, error)
	GetBRGEdgeEntityCatalog2EntityBusinessSceneRelated(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityCatalog2EntityBusinessSceneRelated, error)
	GetBRGEdgeEntityDataCatalog2EntityDataCatalogColumn(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityDataCatalog2EntityDataCatalogColumn, error)
	GetBRGEdgeEntitySourceTable2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntitySourceTable2EntityDataCatalog, error)
	GetBRGEdgeEntityStandardTable2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityStandardTable2EntityDataCatalog, error)
	GetBRGEdgeEntityBusinessForm2EntityBusinessObject(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityBusinessObject, error)
	GetBRGEdgeEntityBusinessFormStandard2Self(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessFormStandard2Self, error)
	GetBRGEdgeEntityBusinessForm2EntityStandardTable(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityStandardTable, error)
	GetBRGEdgeEntityBusinessForm2EntityBusinessModel(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityBusinessModel, error)
	GetBRGEdgeEntityBusinessFormStandard2EntityField(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessFormStandard2EntityField, error)
	GetBRGEdgeEntityField2EntityBusinessIndicator(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityField2EntityBusinessIndicator, error)
	GetBRGEdgeEntityBusinessModel2EntityBusinessForm(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityBusinessForm, error)
	GetBRGEdgeEntityBusinessModel2EntityDepartment(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityDepartment, error)
	GetBRGEdgeEntityBusinessModel2EntityFlowchart(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityFlowchart, error)
	GetBRGEdgeEntityBusinessModel2EntityBusinessIndicator(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityBusinessIndicator, error)
	GetBRGEdgeEntityBusinessIndicator2EntityBusinessModel(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessIndicator2EntityBusinessModel, error)
	GetBRGEdgeEntityFlowchart2EntityFlowchart(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchart2EntityFlowchart, error)
	GetBRGEdgeEntityFlowchart2EntityFlowchartNode(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchart2EntityFlowchartNode, error)
	GetBRGEdgeEntityFlowchartNode2EntityFlowchartNode(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchartNode2EntityFlowchartNode, error)
}

type repo struct {
	data *db.Data
}

func NewRepo(data *db.Data) Repo {
	return &repo{data: data}
}

func (r *repo) do(ctx context.Context) *gorm.DB {
	return r.data.DB.WithContext(ctx)
}

func (r *repo) GetDataViewInfo(ctx context.Context, dataViewId string) (*model.EntityDataResource, error) {
	var ms []*model.EntityDataResource

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select fv.`id`    as `id`, fv.`uniform_catalog_code`  as `code`,  fv.`technical_name`   as `technical_name`,   fv.`business_name`  as `name`,  fv.`description`           as `description`,  3      as `asset_type`, 'rgba(89,163,255,1)'   as `color`,  \n        round((fv.`publish_at` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400)  as `published_at`, \n        round((fv.`online_time` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400)        as `online_at`,\n       case when fv.`publish_at` >= 0 then 'published'\n            else   'unpublished'\n           end as `publish_status`, fv.`online_status`    as  `online_status` ,\n       case when fv.`publish_at` >= 0 then 'published_category'\n            else   'unpublished_category' end as publish_status_category,\n       fv.`owner_id`    as `owner_id`,   usr.`name`   as `owner_name`,   fv.`department_id`   as `department_id`,   dpt.`name`  as `department_name`,   dpt.`path_id`  as `department_path_id`,  dpt.`path`   as `department_path`,   fv.`subject_id`  as `subject_id`,    sbj.`name`     as `subject_name`,   sbj.`path_id`     as `subject_path_id`,   sbj.`path`   as `subject_path`\nfrom af_main.form_view fv  left join af_configuration.`user` usr  on fv.owner_id = usr.id\n         left join (SELECT `id`,   name,  path_id, `path` FROM af_configuration.`object` where type in (1, 2) and deleted_at = 0) dpt  on fv.department_id = dpt.id\n         left join (SELECT id,  name, description,  owners,  'L1' as `prefix_name`,  path_id,   `path`  FROM af_main.subject_domain g  where g.`type` in (1, 2)  and deleted_at = 0) sbj  on fv.subject_id  = sbj.id\nwhere (fv.deleted_at is null or fv.deleted_at = 0) and fv.`id`= ?",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select fv.`id`                    as `id`,                   -- char(36)数据资源id 逻辑视图uuid\n       fv.`uniform_catalog_code`  as `code`,                 -- 数据资源编码code'逻辑视图编码'\n       fv.`technical_name`        as `technical_name`,       -- '技术名称'\n       fv.`business_name`         as `name`,                 -- '数据资源名称'\n       fv.`description`           as `description`,          -- 数据资源描述'逻辑视图描述'\n       3                                                    as `asset_type`,         -- 资产类型 2 接口服务 3 逻辑视图 4 指标\n       'rgba(89,163,255,1)'                                 as `color`,                -- 颜色\n       round(UNIX_TIMESTAMP(fv.`publish_at`))               as `published_at`,       -- datetime'发布时间',UNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳\n       round(UNIX_TIMESTAMP(fv.`online_time`))             as `online_at`,\n       -- datetimeUNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳上线时间2.0.0.5版本新增了上线时间\n       case when fv.`publish_at` >= 0 then 'published'\n           else   'unpublished'\n           end as `publish_status`,\n       fv.`online_status`                                    as  `online_status` ,\n       -- 2.0.0.5版新增 上线状态默认：未上线 notline  全部状态枚举：未上线 notline、已上线 online、已下线offline、上线审核中up-auditing、下线审核中down-auditing、上线审核未通过up-reject、下线审核未通过down-reject\n       -- 以下三种状态属于已上线：已上线 online、下线审核中down-auditing、下线审核未通过down-reject\n       -- 搜索列表增加筛选项：需要支持以接口服务发布状态去筛选包括全部、未发布、已发布；未发布包含未发布、发布审核中、发布审核未通过已发布包含已发布、变更审核中、变更审核未通过\n       case when fv.`publish_at` >= 0 then 'published_category'\n           else   'unpublished_category' end as publish_status_category,\n       fv.`owner_id`              as `owner_id`,             -- '数据Ownerid'\n       usr.`name`                   as `owner_name`,         -- 数据owner姓名\n       fv.`department_id`         as `department_id`,        -- 部门id\n       dpt.`name`                   as `department_name`,      -- 部门名称\n       dpt.`path_id`                as `department_path_id`, -- 部门层级路径id\n       dpt.`path`                 as `department_path`,    -- 部门层级路径\n       fv.`subject_id`              as `subject_id`,           -- '主题id',包括L1和L2\n       sbj.`name`                                             as `subject_name`,         -- 主题名称\n       sbj.`path_id`                                          as `subject_path_id`,      -- 主题层级路径id\n       sbj.`path`                                           as `subject_path`          -- 主题层级路径\nfrom af_main.form_view fv\n         left join af_configuration.`user` usr\n                   on fv.owner_id = usr.id\n         left join (SELECT `id`,\n                           name,\n                           path_id,\n                           `path`\n                    FROM af_configuration.`object`\n                    where type in (1, 2)\n                      and deleted_at = 0) dpt\n                   on fv.department_id = dpt.id\n         left join (SELECT id,\n                           name,\n                           description,\n                           owners,\n                           'L1' as `prefix_name`,\n                           path_id,\n                           `path`\n                    FROM af_main.subject_domain g\n                    where g.`type` in (1, 2)\n                      and deleted_at = 0) sbj\n                   on fv.subject_id  = sbj.id\nwhere (fv.deleted_at is null or fv.deleted_at = 0) and fv.`id`= ?",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetInterfaceServiceInfo(ctx context.Context, serviceId string) (*model.EntityDataResource, error) {
	var ms []*model.EntityDataResource
	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select svc.`service_id`    as `id`,  svc.`service_code`   as `code`, ''   as `technical_name`, svc.`service_name`  as `name`,  svc.`description`        as `description`,  2 as `asset_type`, \n       'rgba(255,186,48,1)' as `color`,  round((svc.`publish_time` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400)  as `published_at`,  round((svc.`online_time` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400)    as `online_at`, \n       svc.publish_status   as `publish_status` ,  svc.status  as `online_status`,\n       case when svc.`publish_status` in ('unpublished','pub-auditing','pub-reject') then 'unpublished_category'\n            when svc.`publish_status` in ('published','change-auditing','change-reject') then 'published_category'\n               else  null end as publish_status_category,\n       svc.`owner_id`             as `owner_id`,   svc.`owner_name`         as `owner_name`,    svc.`department_id`      as `department_id`,   svc.`department_name`    as `department_name`,  dpt.`path_id`              as `department_path_id`,   dpt.`path`               as `department_path`,    svc.`subject_domain_id`    as `subject_id`,    svc.`subject_domain_name`  as `subject_name`,   sbj.`path_id`    as `subject_path_id`,   sbj.`path`   as `subject_path`  \nFROM data_application_service.service svc  left join (SELECT `id`, name,  path_id,  `path`  FROM af_configuration.`object`  where type in (1, 2)  and deleted_at = 0) dpt  on svc.department_id = dpt.`id` \n         left join (SELECT `id`,  name,  description,  owners,  'L1' as `prefix_name`,  path_id,  `path`  FROM af_main.subject_domain sd  where sd.`type` in (1, 2)  and deleted_at = 0) sbj  on svc.subject_domain_id  = sbj.`id` -- \nwhere (svc.delete_time is null or svc.delete_time = 0) and  svc.`service_id`=?",
			serviceId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select svc.`service_id`         as `id`,                   -- varchar(255)数据资源id接口服务uuid\n       svc.`service_code`       as `code`,               -- 数据资源编码code接口服务编码\n       ''                                                 as `technical_name`,     -- 技术名称\n       svc.`service_name`         as `name`,                 -- '数据资源名称' \n       svc.`description`        as `description`,          -- '数据资源描述'\n       2                                                  as `asset_type`,         -- 资产类型 2 接口服务 3 逻辑视图 4 指标\n       'rgba(255,186,48,1)'                               as `color`,                -- 颜色\n       -- 以下这个字段用于临时调试2.0.0.5版本之前 online——time是发布时间的意思有了2004环境后打开后续三个字段的注释\n       -- round(UNIX_TIMESTAMP(svc.`online_time`))           as `published_at`,\n       round(UNIX_TIMESTAMP(svc.`publish_time`))                as `published_at`,       -- datetime发布时间UNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳\n       round(UNIX_TIMESTAMP(svc.`online_time`))                 as `online_at`,          -- datetimeUNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳上线时间.0.0.4版本新增了上线时间\n       svc.publish_status                                 as `publish_status` ,\n       -- 2.0.0.5 版新增 发布状态默认：未发布unpublished全部状态枚举：未发布unpublished 、发布审核中pub-auditing、已发布published、发布审核未通过pub-reject、变更审核中change-auditing、变更审核未通过change-reject\n       svc.status                                         as `online_status`,\n       -- 2.0.0.5 版新增 上线状态默认：未上线 notline  全部状态枚举：未上线 notline、已上线 online、已下线offline、上线审核中up-auditing、下线审核中down-auditing、上线审核未通过up-reject、下线审核未通过down-reject\n       #聚合过的svc.publish_status ,只有已发布和未发布两种高级状态\n              -- 搜索列表增加筛选项：需要支持以接口服务发布状态去筛选包括全部、未发布、已发布；未发布包含未发布、发布审核中、发布审核未通过已发布包含已发布、变更审核中、变更审核未通过\n       case when svc.`publish_status` in ('unpublished','pub-auditing','pub-reject') then 'unpublished_category'\n            when svc.`publish_status` in ('published','change-auditing','change-reject') then 'published_category'\n               else  null end as publish_status_category,\n       svc.`owner_id`             as `owner_id`,             -- 数据Ownerid\n       svc.`owner_name`         as `owner_name`,           -- 数据owner姓名\n       svc.`department_id`      as `department_id`,        -- 部门id\n       svc.`department_name`    as `department_name`,      --  部门名称\n       dpt.`path_id`              as `department_path_id`, -- 部门层级路径id\n       dpt.`path`               as `department_path`,    -- 部门层级路径\n       svc.`subject_domain_id`    as `subject_id`,         -- '主题id',包括L2\n       svc.`subject_domain_name`  as `subject_name`,         -- 主题名称\n       sbj.`path_id`                                        as `subject_path_id`,      -- 主题层级路径id\n       sbj.`path`                                         as `subject_path`          -- 主题层级路径\nFROM data_application_service.service svc\n         left join (SELECT `id`,\n                           name,\n                           path_id,\n                           `path`\n                    FROM af_configuration.`object`\n                    where type in (1, 2)\n                      and deleted_at = 0) dpt\n                   on svc.department_id = dpt.`id` -- COLLATION 都是 \n         left join (SELECT `id`,\n                           name,\n                           description,\n                           owners,\n                           'L1' as `prefix_name`,\n                           path_id,\n                           `path`\n                    FROM af_main.subject_domain sd\n                    where sd.`type` in (1, 2)\n                      and deleted_at = 0) sbj\n                   on svc.subject_domain_id  = sbj.`id` -- \nwhere (svc.delete_time is null or svc.delete_time = 0) and  svc.`service_id`=?",
			serviceId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetIndicatorInfo(ctx context.Context, entityId string) (*model.EntityDataResource, error) {
	var ms []*model.EntityDataResource

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select ti.`id`  as id, ti.`code`  as code,  ti.`name`   as `technical_name`,     ti.`name`     as `name`,    ti.`description`   as `description`,   4       as `asset_type`,   'rgba(89,163,255,1)'   as `color`,round((ti.`updated_at` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400) as `published_at`,round((ti.`updated_at` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400) as `online_at`,\n       'published' as `publish_status` , 'online' as  `online_status`,  'published_category' as publish_status_category,\n       ti.`owner_uid`    as `owner_id`,       ti.`owner_name`    as `owner_name`,     ti.`mgnt_dep_id`   as `department_id`,    \n       ti.`mgnt_dep_name`   as `department_name`,    dpt.`path_id`     as `department_path_id`,    dpt.`path`   as `department_path`,     ti.`subject_domain_id`    as `subject_id`,   \n       sbj.`name`      as `subject_name`,     sbj.`path_id`     as `subject_path_id`,   sbj.`path`    as `subject_path`     \nfrom af_data_model.t_technical_indicator ti  left join (SELECT `id`,  name,  path_id,  `path`   FROM af_configuration.`object`   where type in (1, 2)  and deleted_at = 0) dpt   on ti.mgnt_dep_id = dpt.`id`\n         left join (SELECT `id`,  name,  description,  owners,  'L1' as `prefix_name`,  path_id,  `path`  FROM af_main.subject_domain g   where g.`type` in (1, 2)  and deleted_at = 0) sbj   on ti.subject_domain_id = sbj.`id`\nwhere (ti.deleted_at is null or  ti.deleted_at=0) and   ti.`updated_at` is not null and ti.`updated_at`>= 0 and ti.`id`=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select ti.`id`                                as id,                   -- bigint(20) unsigned 数据资源id '指标只有雪花id'\n       ti.`code`                              as code,                 -- 数据资源编码code'指标编码'\n       ti.`name`                                as `technical_name`,     -- '技术名称指标只有一个名称'\n       ti.`name`                                as `name`,                 -- '数据资源名称指标只有一个名称'\n       ti.`description`                       as `description`,          -- 数据资源描述'逻辑视图描述'\n       4                                      as `asset_type`,         -- 资产类型 2 接口服务 3 逻辑视图 4 指标\n       'rgba(89,163,255,1)'                   as `color`,-- 颜色\n       -- 以下四个时间字段和状态字段是为了和逻辑视图、接口服务的数据字段保持一致便于进行统一搜索\n       round(UNIX_TIMESTAMP(ti.`updated_at`)) as `published_at`,\n       -- datetimeUNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳'发布时间'指标有创建时间、更新时间、删除时间三个时间字段目前创建时间和更新时间相同\n       round(UNIX_TIMESTAMP(ti.`updated_at`)) as `online_at`,\n       -- datetimeUNIX_TIMESTAMP（）转为bigint型单位为秒的时间戳上线时间指标有创建时间、更新时间、删除时间三个时间字段目前创建时间和更新时间相同\n       'published' as `publish_status` ,\n       -- 2.0.0.4版新增 发布状态因为指标要基于已发布、已上线的逻辑视图所以一定是已发布 published\n       'online' as  `online_status`,\n       -- 2.0.0.4版新增 上线状态因为指标要基于已发布、已上线的逻辑视图所以一定是已上线 online\n       'published_category' as publish_status_category,\n       ti.`owner_uid`                           as `owner_id`,           -- '数据Ownerid'\n       ti.`owner_name`                        as `owner_name`,         -- 数据owner姓名\n       ti.`mgnt_dep_id`                         as `department_id`,      -- 部门id\n       ti.`mgnt_dep_name`                       as `department_name`,    -- 部门名称\n       dpt.`path_id`                            as `department_path_id`, -- 部门层级路径id\n       dpt.`path`                             as `department_path`,    -- 部门层级路径\n       ti.`subject_domain_id`                   as `subject_id`,         -- '主题id',包括L1和L2\n       sbj.`name`                               as `subject_name`,       -- 主题名称\n       sbj.`path_id`                            as `subject_path_id`,    -- 主题层级路径id\n       sbj.`path`                             as `subject_path`        -- 主题层级路径\nfrom af_data_model.t_technical_indicator ti\n         left join (SELECT `id`,\n                           name,\n                           path_id,\n                           `path`\n                    FROM af_configuration.`object`\n                    where type in (1, 2)\n                      and deleted_at = 0) dpt\n                   on ti.mgnt_dep_id = dpt.`id` \n         left join (SELECT `id`,\n                           name,\n                           description,\n                           owners,\n                           'L1' as `prefix_name`,\n                           path_id,\n                           `path`\n                    FROM af_main.subject_domain g\n                    where g.`type` in (1, 2)\n                      and deleted_at = 0) sbj\n                   on ti.subject_domain_id = sbj.`id`\nwhere (ti.deleted_at is null or  ti.deleted_at=0)\nand   ti.`updated_at` is not null and ti.`updated_at`>= 0 and ti.`id`=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetIndicatorInfoV2(ctx context.Context, entityId string) (*model.EntityIndicator, error) {
	var ms []*model.EntityIndicator
	if err := r.do(ctx).Raw(
		"select id, analysis_dimension from af_data_model.t_technical_indicator where id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetEmptyEntityDataResource() (*model.EntityDataResource, error) {
	item := model.EntityDataResource{}
	return &item, nil
}

func (r *repo) GetDataView2DataExploreReport(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2DataExploreReport, error) {
	var ms []*model.EdgeDataView2DataExploreReport
	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"SELECT \n  fvf.form_view_id,\n\tfvf.id AS `column_id`, -- 字段uuid\n\ttri.f_project as `explore_item`, -- 探查项目\n\t(case when tri.f_project in ('group','date_distribute_year','date_distribute_month')\n\t      then replace(JSON_VALUE(tri.f_result,concat('$[',numbers.`index`,'].key')),'\\\"','')\n\telse  replace(JSON_VALUE(tri.f_result , '$[0].result'),'\\\"','') end ) as explore_result -- 探查结果\nFROM \n\t( SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 2000) numbers join af_data_exploration.t_report_item tri on LENGTH(tri.f_result) - LENGTH(REPLACE(tri.f_result, '{', '')) >= numbers.`index`\n\tjoin af_data_exploration.t_report tet on tri.f_code=tet.f_code\n\tJOIN af_main.form_view_field fvf ON \n\tfvf.form_view_id = tet.f_table_id  AND \n\tfvf.technical_name = tri.f_column  \nwhere tri.f_project in ('date_distribute_year','date_distribute_month','dict','group','max','min')\nand tet.f_table_id is not null             \nand tri.f_result is not null \nand tet.f_latest=1\nAND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0) and fvf.form_view_id=?\nhaving explore_result is not null and explore_result!=\"\" and explore_result!='null'",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"SELECT \n  fvf.form_view_id,\n\tfvf.id AS `column_id`, -- 字段uuid\n\ttri.f_project as `explore_item`, -- 探查项目\n\t(case when tri.f_project in ('group','date_distribute_year','date_distribute_month')\n\t      then replace(JSON_EXTRACT(tri.f_result,concat('$[',numbers.`index`,'].key')),'\\\"','')\n\telse  replace(JSON_EXTRACT(tri.f_result , '$[0].result'),'\\\"','') end ) as explore_result -- 探查结果\nFROM \n\t(select @row_number:=@row_number + 1 as `index` from af_main.form_view_field fvf,\n\t(SELECT @row_number:=0) AS t where @row_number<2000) numbers\n\tjoin af_data_exploration.t_report_item tri on\n\tCHAR_LENGTH(tri.f_result) - CHAR_LENGTH(REPLACE(tri.f_result, '{', '')) >= numbers.`index`\n\tjoin af_data_exploration.t_report tet on tri.f_code=tet.f_code\n\tJOIN af_main.form_view_field fvf ON \n\tfvf.form_view_id = tet.f_table_id  AND \n\tfvf.technical_name = tri.f_column  \nwhere tri.f_project in ('date_distribute_year','date_distribute_month','dict','group','max','min')\nand tet.f_table_id is not null             \nand tri.f_result is not null \nand tet.f_latest=1\nAND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0) and fvf.form_view_id=?\nhaving explore_result is not null and explore_result!=\"\" and explore_result!='null'",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	return ms, nil
}

func (r *repo) GetInterface2ResponseField(ctx context.Context, interfaceId string) ([]*model.EdgeInterface2ResponseField, error) {
	var ms []*model.EdgeInterface2ResponseField
	if err := r.do(ctx).Raw(
		"select \nid as field_sid --  出参字段雪花id\n, `service_id`  as id -- 接口服务uuid\n-- , `service_code`  -- 数据资源编码code,接口服务code\nfrom data_application_service.service_param where `service_id`= ?",
		interfaceId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetDataView2Filed(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2Filed, error) {
	var ms []*model.EdgeDataView2Filed
	if err := r.do(ctx).Raw(
		"select\n    fvf.`id` as column_id -- '字段uuid'\n    ,fvf.`form_view_id` as formview_uuid -- 数据资源id\nfrom  af_main.form_view_field fvf\ninner join af_main.form_view fv\non fv.id=fvf.form_view_id\nwhere (fvf.deleted_at is null or fvf.deleted_at=0)\n-- and fv.publish_at>0\nand  (fv.deleted_at is null or fv.deleted_at=0) and fvf.`form_view_id`=?",
		dataViewId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetDataView2MetadataSchema(ctx context.Context, dataViewId string) ([]*model.EdgeDataView2MetadataSchema, error) {
	var ms []*model.EdgeDataView2MetadataSchema
	if err := r.do(ctx).Raw(
		"select fv.id  as formview_uuid ,-- 数据资源id逻辑视图uuid\n\ttt.f_schema_id as schema_sid -- 库雪花id\nfrom af_main.form_view fv\njoin `af_metadata`.`t_table` tt\n\ton fv.metadata_form_id = tt.f_id where fv.id=?",
		dataViewId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetDataView2MetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeDataView2MetadataSchema, error) {
	var ms []*model.EdgeDataView2MetadataSchema
	if err := r.do(ctx).Raw(
		"SELECT\n\tfv.id as formview_uuid,\n\tts.f_id AS schema_sid\nFROM\n\taf_main.form_view fv\nJOIN af_configuration.datasource ds ON fv.datasource_id = ds.id\nJOIN af_metadata.t_schema ts ON ds.data_source_id = ts.f_data_source_id where fv.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetDimensionModel2IndicatorByIndicator(ctx context.Context, entityId string) ([]*model.EdgeDimensionModel2Resource, error) {
	var ms []*model.EdgeDimensionModel2Resource
	if err := r.do(ctx).Raw(
		"select ti.dimension_model_id, -- 维度模型 雪花id没有uuid\n       ti.id                  -- 指标雪花id没有uuid\nfrom af_data_model.t_technical_indicator ti\nwhere (ti.deleted_at is null or ti.deleted_at=0) and ti.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetIndicatorAnalysisDimension2IndicatorByIndicator(ctx context.Context, entityId string) ([]*model.EdgeIndicatorAnalysisDimension2Resource, error) {
	var ms []*model.EdgeIndicatorAnalysisDimension2Resource
	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select inticator_id, table_id as formview_id  ,field_id from (SELECT  ti.id as inticator_id,  replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id, replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '') as field_id\n      FROM (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 100) numbers\n               join af_data_model.t_technical_indicator ti  on\n                  LENGTH(ti.analysis_dimension) - LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=\n                                numbers.`index`\n      where (ti.deleted_at is null\n          or ti.deleted_at = 0) and ti.id=?) tif\ngroup by inticator_id,table_id,field_id",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select inticator_id,  -- 指标雪花id\n       table_id as formview_id -- 逻辑视图 uuid\n     ,field_id  -- 分析维度字段 uuid\nfrom (SELECT\n        ti.id as inticator_id,   -- 指标雪花id\n        replace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id,\n        replace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '') as field_id\n        FROM (select @row_number := @row_number + 1 as `index`\n            from af_main.form_view_field fvf,\n                 (SELECT @row_number := 0) AS t\n            where @row_number < 100) numbers\n               join af_data_model.t_technical_indicator ti\n                    on\n                        CHAR_LENGTH(ti.analysis_dimension) - CHAR_LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=\n                        numbers.`index`\n        where (ti.deleted_at is null\n        or ti.deleted_at = 0) and ti.id=?) tif\ngroup by inticator_id,table_id,field_id",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}

	return ms, nil
}
func (r *repo) GetDimensionModel(ctx context.Context, entityId string) (*model.EntityDimensionModel, error) {
	var ms []*model.EntityDimensionModel
	if err := r.do(ctx).Raw(
		"select tdm.id,         -- 维度模型雪花id\n       tdm.name,       -- 维度模型名称\n       tdm.description -- 维度模型描述\nfrom af_data_model.t_dimension_model tdm\nwhere (tdm.deleted_at is null or tdm.deleted_at=0) and tdm.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetDimensionModel2IndicatorByDimension(ctx context.Context, entityId string) ([]*model.EdgeDimensionModel2Resource, error) {
	var ms []*model.EdgeDimensionModel2Resource
	if err := r.do(ctx).Raw(
		"select ti.dimension_model_id, -- 维度模型 雪花id没有uuid\n       ti.id                  -- 指标雪花id没有uuid\nfrom af_data_model.t_technical_indicator ti\nwhere (ti.deleted_at is null or ti.deleted_at=0) and ti.dimension_model_id =?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetIndicatorAnalysisDimension(ctx context.Context, entityId string) (*model.EntityIndicatorAnalysisDimension, error) {
	var ms []*model.EntityIndicatorAnalysisDimension
	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select table_id as formview_id  ,field_id  ,business_name field_business_name ,technical_name as field_technical_name  ,data_type as field_data_type \nfrom (SELECT  replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id,\n              replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '')     as field_id,\n          replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].business_name')), '\\\"','')     as business_name,\n          replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].technical_name')), '\\\"', '')    as technical_name,\n          replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].data_type')), '\\\"',  '')      as data_type\n      FROM (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 100) numbers\n               join af_data_model.t_technical_indicator ti  on  LENGTH(ti.analysis_dimension) - LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=  numbers.`index`\n      where (ti.deleted_at is null   or ti.deleted_at = 0) and field_id=?) tif \ngroup by table_id,field_id,business_name,technical_name,data_type",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select table_id as formview_id  -- 逻辑视图 uuid\n     ,field_id  -- 分析维度字段 uuid\n     ,business_name field_business_name -- 分析维度字段名称\n     ,technical_name as field_technical_name  -- 分析维度字段技术名称\n     ,data_type as field_data_type -- 分析维度字段数据类型\nfrom (SELECT\nreplace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id,\n\nreplace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"',\n        '')                                                                                             as field_id,\nreplace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].business_name')), '\\\"',\n        '')                                                                                             as business_name,\nreplace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].technical_name')), '\\\"',\n        '')                                                                                             as technical_name,\nreplace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].data_type')), '\\\"',\n        '')                                                                                             as data_type\n      FROM (select @row_number := @row_number + 1 as `index`\n            from af_main.form_view_field fvf,\n                 (SELECT @row_number := 0) AS t\n            where @row_number < 100) numbers\n               join af_data_model.t_technical_indicator ti\n                    on\n                        CHAR_LENGTH(ti.analysis_dimension) - CHAR_LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=\n                        numbers.`index`\n      where (ti.deleted_at is null\n         or ti.deleted_at = 0) and field_id=?) tif\ngroup by table_id,field_id,business_name,technical_name,data_type",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetIndicatorAnalysisDimension2IndicatorByIndicatorAnalysisDimension(ctx context.Context, entityId string) ([]*model.EdgeIndicatorAnalysisDimension2Resource, error) {
	var ms []*model.EdgeIndicatorAnalysisDimension2Resource

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select inticator_id, table_id as formview_id,field_id  from (SELECT  ti.id as inticator_id, \n          replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id,\n          replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '') as field_id\n      FROM (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 100) numbers\n               join af_data_model.t_technical_indicator ti  on  LENGTH(ti.analysis_dimension) - LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=  numbers.`index`\n      where (ti.deleted_at is null  or ti.deleted_at = 0) and replace(JSON_VALUE(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '')=?) tif \ngroup by inticator_id,table_id,field_id",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select inticator_id,  -- 指标雪花id\n       table_id as formview_id -- 逻辑视图 uuid\n     ,field_id  -- 分析维度字段 uuid\nfrom (SELECT\n        ti.id as inticator_id,   -- 指标雪花id\n        replace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].table_id')), '\\\"', '') as table_id,\n        replace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '') as field_id\n        FROM (select @row_number := @row_number + 1 as `index`\n            from af_main.form_view_field fvf,\n                 (SELECT @row_number := 0) AS t\n            where @row_number < 100) numbers\n               join af_data_model.t_technical_indicator ti\n                    on\n                        CHAR_LENGTH(ti.analysis_dimension) - CHAR_LENGTH(REPLACE(ti.analysis_dimension, '{', '')) >=\n                        numbers.`index`\n        where (ti.deleted_at is null\n        or ti.deleted_at = 0) and replace(JSON_EXTRACT(ti.analysis_dimension, concat('$[', numbers.`index` - 1, '].field_id')), '\\\"', '')=?) tif\ngroup by inticator_id,table_id,field_id",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	return ms, nil
}

func (r *repo) GetInterfaceSvcInfo(ctx context.Context, dataViewId string) (*model.EntityDataResource, error) {
	var ms []*model.EntityDataResource

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"select svc.`service_id` as id,   svc.`service_code`  as `code` ,   \"\"   as `technical_name` , svc.service_name  as name  ,   svc.`description`  as description  ,   2  as \"asset_type\"  , 'rgba(255,186,48,1)'  as color ,  round((svc.`online_time` - TO_DATE('1970-01-01', 'YYYY-MM-DD')) * 86400)  as `published_at` , svc.owner_id  as owner_id  ,  svc.`owner_name`  as owner_name  ,  svc.`department_id`  as department_id , svc.`department_name`  as department_name, dpt.path_id as `department_path_id` , dpt.`path` as `department_path` ,  svc.subject_domain_id  as `subject_id` ,  svc.subject_domain_name  as subject_name , sbj.path_id as subject_path_id, sbj.`path` as subject_path\nFROM data_application_service.service svc\n         left join (SELECT `id`, name,  path_id,  `path`  FROM af_configuration.`object`  where type in (1,2) and deleted_at=0) dpt  on svc.department_id = dpt.id\n         left join (SELECT id, name, description, owners, 'L1' as `prefix_name` ,  path_id,`path`  FROM af_main.subject_domain  g  where g.`type` in (1,2) and deleted_at=0) sbj\n                   on svc.subject_domain_id = sbj.id where svc.delete_time  = 0  and svc.status=\"publish\" and svc.`service_id`=?",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select  \n\tsvc.`service_id` as id, -- 数据资源id接口服务uuid\n\tsvc.`service_code`  as `code` ,   -- 数据资源编码code接口服务编码\n\t\"\"   as `technical_name` ,-- 技术名称\n\tsvc.service_name  as name  ,-- '数据资源名称'\n\tsvc.`description`  as description  ,-- '数据资源描述'\n\t2  as \"asset_type\"  ,-- 资产类型 2 接口服务 3 逻辑视图\n\t'rgba(255,186,48,1)'  as color ,-- 颜色\n\t UNIX_TIMESTAMP(svc.`online_time`)  as `published_at` ,-- 上线发布时间\n\tsvc.owner_id  as owner_id  ,-- 数据Ownerid\n\tsvc.`owner_name`  as owner_name  ,-- 数据owner姓名\n\tsvc.`department_id`  as department_id ,-- 部门id\n\tsvc.`department_name`  as department_name,  --  部门名称\n\tdpt.path_id as `department_path_id` , -- 部门层级路径id\n\tdpt.`path` as `department_path` , -- 部门层级路径\n\tsvc.subject_domain_id  as `subject_id` ,-- '主题id',包括L2\n\tsvc.subject_domain_name  as subject_name , -- 主题名称\n\tsbj.path_id as subject_path_id, -- 主题层级路径id\n\tsbj.`path` as subject_path -- 主题层级路径\nFROM data_application_service.service svc\nleft join (SELECT `id`,\n\t\t\t\tname, \n\t\t\t\tpath_id,\n\t\t\t\t`path`\n\t\t\tFROM af_configuration.`object`  \n\t\t\twhere type in (1,2) and deleted_at=0 \n\t\t\t) dpt\non svc.department_id = dpt.id\nleft join (SELECT id, name, description, owners, 'L1' as `prefix_name` ,\n\t\t\t\tpath_id,`path`\n\t\t\t\tFROM af_main.subject_domain  g\n\t\t\t\twhere g.`type` in (1,2) and deleted_at=0\n\t\t\t) sbj\non svc.subject_domain_id = sbj.id \nwhere svc.delete_time  = 0 \nand svc.status=\"publish\" and svc.`service_id`=?",
			dataViewId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetSubDomainInfo(ctx context.Context, subDomainId string) (*model.EntitySubdomain, error) {
	var ms []*model.EntitySubdomain
	if err := r.do(ctx).Raw(
		"SELECT id,  -- 主题域uuidL2\nname, \n'L2' as `prefix_name`  \nFROM af_main.subject_domain g\nwhere g.`type`=2 and deleted_at=0 and id=?",
		subDomainId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetSubDomain2DataView(ctx context.Context, subDomainId string) ([]*model.EdgeSubdomain2DataView, error) {
	var ms []*model.EdgeSubdomain2DataView
	if err := r.do(ctx).Raw(
		"select \n\tfv.`id`, -- 数据资源id逻辑视图uuid\n\t-- fv.`uniform_catalog_code` as code, -- 数据资源编码code'逻辑视图编码'\n\tsdo.`id` as `subject_id` -- '主题id',包括L1和L2\nfrom af_main.form_view fv\ninner join (select id  as id, name  as name from  af_main.subject_domain sd \n\twhere sd.`type`in (1,2) and id <>\"\") sdo\n\ton sdo.id = fv.subject_id \nwhere  fv.`publish_at`>=0 and (fv.deleted_at is null or fv.deleted_at=0) and sdo.`id` = ?",
		subDomainId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	//if len(ms) > 0 {
	//	return ms[0], nil
	//}
	return ms, nil
}

func (r *repo) GetSubDomain2Domain(ctx context.Context, subDomainId string) ([]*model.EdgeSubdomain2Domain, error) {
	var ms []*model.EdgeSubdomain2Domain
	if err := r.do(ctx).Raw(
		"select d.id as domain_id, -- 主体域分组uuidL1\n\tdt.id as theme_id  -- 主题域uuidL2\nfrom af_main.subject_domain dt \njoin af_main.subject_domain d \n\ton d.id=IF(dt.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(dt.path_id, '/', -2), '/', 1), '')\nwhere d.`type`=1 and d.deleted_at=0 and dt.`type`=2 and dt.deleted_at=0 and dt.id=?",
		subDomainId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDomainInfo(ctx context.Context, domainId string) (*model.EntityDomain, error) {
	var ms []*model.EntityDomain
	if err := r.do(ctx).Raw(
		"SELECT id, -- 主体域分组uuidL1\n\tname,  \n\t'L1' as `prefix_name`  \nFROM af_main.subject_domain  g\nwhere g.`type`=1 and deleted_at=0 and id=?",
		domainId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDomain2SubDomain(ctx context.Context, domainId string) ([]*model.EdgeDomain2Subdomain, error) {
	var ms []*model.EdgeDomain2Subdomain
	if err := r.do(ctx).Raw(
		"select d.id as domain_id, -- 主体域分组uuidL1\n\tdt.id as theme_id  -- 主题域uuidL2\nfrom af_main.subject_domain dt \njoin af_main.subject_domain d \n\ton d.id=IF(dt.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(dt.path_id, '/', -2), '/', 1), '')\nwhere d.`type`=1 and d.deleted_at=0 and dt.`type`=2 and dt.deleted_at=0 and d.id=?",
		domainId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetMetadataSchema(ctx context.Context, metadataSchemaId string) (*model.EntityMetadataSchema, error) {
	var ms []*model.EntityMetadataSchema
	if err := r.do(ctx).Raw(
		"Select `f_id` as `schema_sid`,  -- 库名称雪花id该表没有uuid字段\n\t`f_name` as `schema_name`,  -- 库名称\n\t'库' as `prefix_name` \nfrom `af_metadata`.`t_schema` where `f_id`=?",
		metadataSchemaId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetMetadataSchema2DataView(ctx context.Context, metadataSchemaId string) ([]*model.EdgeMetadataSchema2DataView, error) {
	var ms []*model.EdgeMetadataSchema2DataView
	if err := r.do(ctx).Raw(
		"select fv.id  as formview_uuid ,-- 数据资源id逻辑视图uuid\n\ttt.f_schema_id as schema_sid -- 库雪花id\nfrom af_main.form_view fv\njoin `af_metadata`.`t_table` tt\n\ton fv.metadata_form_id = tt.f_id where tt.f_schema_id=?",
		metadataSchemaId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetMetadataSchema2DataSource(ctx context.Context, metadataSchemaId string) ([]*model.EdgeMetadataSchema2DataSource, error) {
	var ms []*model.EdgeMetadataSchema2DataSource
	if err := r.do(ctx).Raw(
		"Select \n-- \t`f_data_source_id` as `data_source_sid`,   -- 数据源雪花id\n\tds.`id` as `data_source_uuid`, -- 数据源uuid字段\n\t`f_id` as `schema_sid`   -- 库名称雪花id\nfrom `af_metadata`.`t_schema` scm\njoin af_configuration.datasource ds \non scm.f_data_source_id = ds.data_source_id  where `f_id`=?",
		metadataSchemaId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataSource(ctx context.Context, dataSourceId string) (*model.EntityDataSource, error) {
	var ms []*model.EntityDataSource
	if err := r.do(ctx).Raw(
		"Select \n-- \tdata_source_sid,  -- 数据源雪花id\n\t`id` as `data_source_uuid`,  -- 数据源uuid字段\n\t`name` as `data_source_name`,  -- 数据源名称\n\t`type_name` as `data_source_type_name`, -- 数据源类型名称类型名称mysqlhive-jdbc等值\n\tsource_type as source_type_code,  -- 数据源类型编码1 记录型、2 分析型\n\tcase when source_type=1 then '记录型'\n\t\twhen source_type=2 then '分析型'\n\t\telse null\n\t\tend as source_type_name , -- 数据源类型名称记录型、分析型\n\t'数据源' as `prefix_name` \nfrom af_configuration.datasource where `id`=?",
		dataSourceId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDataSource2MetadataSchema(ctx context.Context, dataSourceId string) ([]*model.EdgeDataSource2MetadataSchema, error) {
	var ms []*model.EdgeDataSource2MetadataSchema
	if err := r.do(ctx).Raw(
		"Select\n-- \t`f_data_source_id` as `data_source_sid`,   -- 数据源雪花id\n\tds.`id` as `data_source_uuid`, -- 数据源uuid字段,因为`af_metadata`.`t_schema`表只有数据源雪花id所以需要关联af_configuration.datasource拿到uuid\n\t`f_id` as `schema_sid`   -- 库名称雪花id\nfrom `af_metadata`.`t_schema` scm\njoin af_configuration.datasource ds\non scm.f_data_source_id = ds.data_source_id and ds.`id`=?",
		dataSourceId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataSourceAndMetadataSchemaByMetadataSchema(ctx context.Context, metadataSchemaId string) (*model.EdgeDataSourceAndMetadataSchemaByMetadataSchema, error) {
	var ms []*model.EdgeDataSourceAndMetadataSchemaByMetadataSchema
	if err := r.do(ctx).Raw(
		"Select\n\tds.`id` as `data_source_uuid`,\n\tscm.`f_id` as `schema_sid`,\n  scm.`f_name` as `schema_name`,\n ds.`name` as `data_source_name`, \n ds.`type_name` as `data_source_type_name`,\n ds.source_type as source_type_code,\n case when ds.source_type=1 then '记录型'\n\t\twhen ds.source_type=2 then '分析型'\n\t\telse null\n\t\tend as source_type_name , -- 数据源类型名称记录型、分析型\n\t'数据源' as `prefix_name`  \nfrom `af_metadata`.`t_schema` scm\njoin af_configuration.datasource ds\non scm.f_data_source_id = ds.data_source_id where scm.`f_id`=?",
		metadataSchemaId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDataViewFields(ctx context.Context, dataViewFieldId string) (*model.EntityDataViewFields, error) {
	var ms []*model.EntityDataViewFields
	if err := r.do(ctx).Raw(
		"select\n--  fvf.`id` as field_id -- '字段uuid'\n    fvf.`id` as column_id -- '字段uuid'\n    ,fvf.`form_view_id`  as formview_uuid -- 数据资源id\n    ,fvf.`technical_name` -- '字段技术名称'\n    ,fvf. `business_name` as field_name  -- '字段业务名称'\n    ,fvf.`data_type` -- '数据类型'\nfrom  af_main.form_view_field fvf\ninner join af_main.form_view fv\non fv.id=fvf.form_view_id\nwhere (fvf.deleted_at is null or fvf.deleted_at=0)\n-- and fv.publish_at>0\nand  (fv.deleted_at is null or fv.deleted_at=0) and fvf.`id`=?",
		dataViewFieldId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetResponseField(ctx context.Context, filedId string) (*model.EntityResponseField, error) {
	var ms []*model.EntityResponseField
	if err := r.do(ctx).Raw(
		"SELECT `id` as field_sid , -- 出参字段雪花id\n-- , `service_code` , -- 数据资源编码code,接口服务code\n `cn_name` , -- 中文名称\n `en_name`  -- 英文名称\nFROM data_application_service.service_param\nwhere delete_time =0 and `id`=?",
		filedId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetResponseField2Interface(ctx context.Context, filedId string) ([]*model.EdgeResponseField2Interface, error) {
	var ms []*model.EdgeResponseField2Interface
	if err := r.do(ctx).Raw(
		"select \nid as field_sid --  出参字段雪花id\n, `service_id`  as id -- 接口服务uuid\n-- , `service_code`  -- 数据资源编码code,接口服务code\nfrom data_application_service.service_param where id=?",
		filedId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataExploreReport(ctx context.Context, filedId string) (*model.EntityDataExploreReport, error) {
	var ms []*model.EntityDataExploreReport

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"SELECT fvf.`id`    AS `column_id`,    tri.f_project    as `explore_item`,  tri.f_column    as `column_name`, \n       replace(JSON_VALUE(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"',  '')   as explore_result, \n       case\n           when tri.f_params is not null and tri.f_params <> '' then\n               JSON_VALUE(tri.f_params, CONCAT('$.', replace(JSON_VALUE(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"', '')))\n           else replace(JSON_VALUE(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"','')\n           end   AS explore_result_value \nFROM (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 2000) numbers\n         join af_data_exploration.t_report_item tri on  LENGTH(tri.f_result) - LENGTH(REPLACE(tri.f_result, '[', '')) - 1 >= numbers.`index`\n         join af_data_exploration.t_report tet on tri.f_code = tet.f_code\n         JOIN af_main.form_view_field fvf ON\n            fvf.form_view_id = tet.f_table_id  AND\n            fvf.technical_name = tri.f_column\nwhere tri.f_project in ('Group', 'Month', 'Year')  and tet.f_table_id is not null and tri.f_result is not null  and tet.f_latest = 1  AND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0) \nhaving explore_result is not null  and explore_result != ''  and explore_result != 'null' and fvf.`id`=?",
			filedId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"SELECT fvf.`id`                                                                                 AS `column_id`,    -- 字段uuid\n             tri.f_project                                                                            as `explore_item`, -- 探查项目\n             tri.f_column                                                                             as `column_name`,  -- 字段名称\n             replace(JSON_EXTRACT(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"',\n                     '')                                                                              as explore_result, -- 探查结果\n             case\n                 when tri.f_params is not null and tri.f_params <> '' then\n                     JSON_UNQUOTE(JSON_EXTRACT(tri.f_params, CONCAT('$.', replace(\n                             JSON_EXTRACT(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"', ''))))\n                 else replace(JSON_EXTRACT(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"','')\n                 end   AS explore_result_value -- 探查结果关联码表的码值 否则为null\n      FROM (select @row_number := @row_number + 1 as `index`\n            from af_main.form_view_field fvf,\n                 (SELECT @row_number := 0) AS t\n            where @row_number < 2000) numbers\n               join af_data_exploration.t_report_item tri on\n          CHAR_LENGTH(tri.f_result) - CHAR_LENGTH(REPLACE(tri.f_result, '[', '')) - 1 >= numbers.`index`\n               join af_data_exploration.t_report tet on tri.f_code = tet.f_code\n               JOIN af_main.form_view_field fvf ON\n          fvf.form_view_id = tet.f_table_id  AND\n          fvf.technical_name = tri.f_column \n      where tri.f_project in ('Group', 'Month', 'Year')\n        and tet.f_table_id is not null\n        and tri.f_result is not null\n        and tet.f_latest = 1\n        AND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0)\n      having explore_result is not null\n         and explore_result != ''\n         and explore_result != 'null' and fvf.`id`=?",
			filedId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDataExploreReport2DataView(ctx context.Context, columnId string) ([]*model.EdgeDataExploreReport2DataView, error) {
	var ms []*model.EdgeDataExploreReport2DataView
	if err := r.do(ctx).Raw(
		"select \n\tfvf.form_view_id as formview_uuid -- 数据资源id\n\t,fvf.`id` as column_id -- 字段ID\nfrom af_main.form_view_field fvf\nwhere (fvf.deleted_at is null or fvf.deleted_at=0) and fvf.`id`=?",
		columnId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataOwner(ctx context.Context, filedId string) (*model.EntityDataOwner, error) {
	var ms []*model.EntityDataOwner
	if err := r.do(ctx).Raw(
		"select id as `owner_id`, name as `owner_name` from af_configuration.`user` where id=?",
		filedId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDataOwner2DataView(ctx context.Context, ownerId string) ([]*model.EdgeDataOwner2DataView, error) {
	var ms []*model.EdgeDataOwner2DataView
	if err := r.do(ctx).Raw(
		"select fv.`id`  -- 数据资源id逻辑视图uuid\n\t,fv.`owner_id`  -- '数据Owner uuid'\nfrom af_main.form_view fv\nwhere  fv.`publish_at`>=0 and (fv.deleted_at is null or fv.deleted_at=0) and fv.`owner_id` is not null and fv.`id`=?",
		ownerId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDepartment(ctx context.Context, filedId string) (*model.EntityDepartment, error) {
	var ms []*model.EntityDepartment
	if err := r.do(ctx).Raw(
		"SELECT `id`,  -- 部门uuid\nname  -- 部门名称\nFROM af_configuration.`object`  \nwhere type in (1,2) -- 类型：1：组织2：部门3：信息系统4：业务事项5：主干业务6：业务表单\n\tand deleted_at=0 and `id`=?",
		filedId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDepartment2DataView(ctx context.Context, departmentId string) ([]*model.EdgeDepartment2DataView, error) {
	var ms []*model.EdgeDepartment2DataView
	if err := r.do(ctx).Raw(
		"select fv.`id`  -- 数据资源id逻辑视图uuid\n\t,fv.`department_id` -- 部门uuid\nfrom af_main.form_view fv\nwhere  fv.`publish_at`>=0 and (fv.deleted_at is null or fv.deleted_at=0) and  fv.`department_id`=?",
		departmentId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataCatalog(ctx context.Context, entityId string) (*model.EntityDataCatalog, error) {
	var ms []*model.EntityDataCatalog
	if err := r.do(ctx).Raw(
		"SELECT  tdc.`id` as sid, -- 数据资源目录雪花id\n\ttdc.`code` , -- 数据资源目录编码code, 因为历史遗留问题要用code字段后续会改为uuid\n\ttdc.`title`  as name, -- 数据资源目录名称\n\ttdc.`description` , -- 数据资源目录描述\n\t1 as `asset_type`, -- 资产类型 数据资源目录值为1\n\t'rgba(89,163,255,1)' as color , -- 资产的颜色\n\ttdc.`data_kind` , -- 基础信息分类\n\ttdc.`shared_type` , -- 共享类型\n\tround(UNIX_TIMESTAMP(tdc.`published_at`)) as `published_at` ,  -- 上线发布时间\n\ttdc.`update_cycle` , -- 更新周期\n\ttdc.`owner_id`  , -- 数据owner id\n\ttdc.`owner_name` ,  -- 数据owner 姓名\n\ttdc. `orgcode` as `department_id` , -- 部门id\n\ttdc. `orgname` as `department` ,-- 部门名称\n\tdpt.path_id as `department_path_id` , -- 部门层级路径id\n\tdpt.`path` as `department_path` , -- 部门层级路径\n\ttt.f_data_source_name  as `datasource`, -- 数据源\n\tds.catalog_name  as  ves_catalog_name, -- 数据源在虚拟化引擎(virtual engine service)中的技术名称用于调用参数\n\ttt.f_schema_name as `metadata_schema`,  -- 库名称\n-- \t,tdci.id as info_system_id  -- 信息系统雪花id left join 该值可能为null\n\ttdci.info_key as info_system_id , -- 信息系统uuid\n\ttdci.info_value as info_system_name-- 信息系统名称\tleft join 该值可能为null\nFROM af_data_catalog.t_data_catalog tdc  -- 数据资源目录主表\ninner join af_data_catalog.t_data_catalog_resource_mount tdcrm -- 数据资源目录挂接资源表\n  \ton tdc.code=tdcrm.code\ninner join af_metadata.t_table tt -- 数据目录对应的表 包含库名称\n  \ton tt.f_id=tdcrm.res_id\nleft join  (select * from `af_data_catalog`.`t_data_catalog_info` where info_type =4) tdci -- 包含信息系统信息的表\n\ton tdc.id=tdci.catalog_id\nleft join (SELECT `id`,\n\t\t\tname, \n\t\t\tpath_id,\n\t\t\t`path`\n\t\t\tFROM af_configuration.`object`  \n\t\t\twhere type in (1,2) and deleted_at=0 \n\t\t\t) dpt\n\ton tdc. `orgcode` = dpt.id\nleft join af_configuration.datasource ds \n\ton tt.f_data_source_id = ds.data_source_id \nwhere   (tdc.deleted_at is null or tdc.deleted_at=0) \n\tand tdc.state=5 and tdc.`id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetDataCatalogByFlowId(ctx context.Context, entityId string) (*model.EntityDataCatalog, error) {
	var ms []*model.EntityDataCatalog
	if err := r.do(ctx).Raw(
		"SELECT  tdc.`id` as sid, -- 数据资源目录雪花id\n\ttdc.`code` , -- 数据资源目录编码code, 因为历史遗留问题要用code字段后续会改为uuid\n\ttdc.`title`  as name, -- 数据资源目录名称\n\ttdc.`description` , -- 数据资源目录描述\n\t1 as `asset_type`, -- 资产类型 数据资源目录值为1\n\t'rgba(89,163,255,1)' as color , -- 资产的颜色\n\ttdc.`data_kind` , -- 基础信息分类\n\ttdc.`shared_type` , -- 共享类型\n\tround(UNIX_TIMESTAMP(tdc.`published_at`)) as `published_at` ,  -- 上线发布时间\n\ttdc.`update_cycle` , -- 更新周期\n\ttdc.`owner_id`  , -- 数据owner id\n\ttdc.`owner_name` ,  -- 数据owner 姓名\n\ttdc. `orgcode` as `department_id` , -- 部门id\n\ttdc. `orgname` as `department` ,-- 部门名称\n\tdpt.path_id as `department_path_id` , -- 部门层级路径id\n\tdpt.`path` as `department_path` , -- 部门层级路径\n\ttt.f_data_source_name  as `datasource`, -- 数据源\n\tds.catalog_name  as  ves_catalog_name, -- 数据源在虚拟化引擎(virtual engine service)中的技术名称用于调用参数\n\ttt.f_schema_name as `metadata_schema`,  -- 库名称\n-- \t,tdci.id as info_system_id  -- 信息系统雪花id left join 该值可能为null\n\ttdci.info_key as info_system_id , -- 信息系统uuid\n\ttdci.info_value as info_system_name-- 信息系统名称\tleft join 该值可能为null\nFROM af_data_catalog.t_data_catalog tdc  -- 数据资源目录主表\ninner join af_data_catalog.t_data_catalog_resource_mount tdcrm -- 数据资源目录挂接资源表\n  \ton tdc.code=tdcrm.code\ninner join af_metadata.t_table tt -- 数据目录对应的表 包含库名称\n  \ton tt.f_id=tdcrm.res_id\nleft join  (select * from `af_data_catalog`.`t_data_catalog_info` where info_type =4) tdci -- 包含信息系统信息的表\n\ton tdc.id=tdci.catalog_id\nleft join (SELECT `id`,\n\t\t\tname, \n\t\t\tpath_id,\n\t\t\t`path`\n\t\t\tFROM af_configuration.`object`  \n\t\t\twhere type in (1,2) and deleted_at=0 \n\t\t\t) dpt\n\ton tdc. `orgcode` = dpt.id\nleft join af_configuration.datasource ds \n\ton tt.f_data_source_id = ds.data_source_id \nwhere   (tdc.deleted_at is null or tdc.deleted_at=0) \n\tand tdc.state=5 and tdc.flow_id = ?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetEmptyDataCatalog() (*model.EntityDataCatalog, error) {
	item := model.EntityDataCatalog{}
	return &item, nil
}

func (r *repo) GetCatalogTag2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeCatalogTag2DataCatalog, error) {
	var ms []*model.EdgeCatalogTag2DataCatalog
	if err := r.do(ctx).Raw(
		"Select tdci.`id` as `tag_sid`,  -- 资产标签的雪花id\n\ttdci.`catalog_id` as `data_catalog_sid`  -- 数据资源目录的雪花id\nfrom `af_data_catalog`.`t_data_catalog_info` tdci\ninner join af_data_catalog.t_data_catalog tdc\non tdci.catalog_id = tdc.id\nwhere tdci.`info_type` = 1\nand  (tdc.deleted_at is null or tdc.deleted_at=0)\nand tdc.state=5 and tdci.`catalog_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetInfoSystem2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeInfoSystem2DataCatalog, error) {
	var ms []*model.EdgeInfoSystem2DataCatalog
	if err := r.do(ctx).Raw(
		"Select\n\ttdci.`info_key` as `sys_sid`, -- 信息系统的雪花id\n\ttdci.`catalog_id` as `data_catalog_sid` -- 数据资源目录的雪花id\nfrom `af_data_catalog`.`t_data_catalog_info` tdci\ninner join af_data_catalog.t_data_catalog tdc\non tdci.catalog_id = tdc.id\nwhere `info_type` = 4\nand  (tdc.deleted_at is null or tdc.deleted_at=0)\nand tdc.state=5 and tdci.`catalog_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDepartment2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeDepartment2DataCatalog, error) {
	var ms []*model.EdgeDepartment2DataCatalog
	if err := r.do(ctx).Raw(
		"select  tdc.id as `data_catalog_sid`,   -- 数据资源目录的雪花id\n\ttdc.orgcode as department_id  -- 部门的uuid\nfrom af_data_catalog.t_data_catalog tdc \nwhere  (tdc.deleted_at=0 \n\tor tdc.deleted_at is null) and tdc.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDataOwner2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeDataOwner2DataCatalog, error) {
	var ms []*model.EdgeDataOwner2DataCatalog
	if err := r.do(ctx).Raw(
		"Select \n\t`id` as `sys_sid`, -- 信息系统的雪花id\n\t`catalog_id` as `data_catalog_sid` -- 数据资源目录的雪花id\nfrom `af_data_catalog`.`t_data_catalog_info`\nwhere `info_type` = 4 and `catalog_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetFormView2DataCatalogByDataCatalog(ctx context.Context, entityId string) ([]*model.EdgeFormView2DataCatalog, error) {
	var ms []*model.EdgeFormView2DataCatalog
	if err := r.do(ctx).Raw(
		"select tdc.`code`  as datacatalog_code-- 数据资源目录编码code\n\t,tdcrm.s_res_id  as formview_uuid-- 逻辑视图uuid\nfrom af_data_catalog.t_data_catalog tdc \njoin af_data_catalog.t_data_catalog_resource_mount tdcrm\non tdc.code=tdcrm.code \nwhere tdcrm.res_type =1 and s_res_id is not null and tdc.`code`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetCatalogTag(ctx context.Context, entityId string) (*model.EntityCatalogTag, error) {
	var ms []*model.EntityCatalogTag
	if err := r.do(ctx).Raw(
		"Select `id` as `tag_sid`,  -- 资产标签的雪花id\n \t\t`info_key` as `tag_code`,  -- 资产标签的code\n \t\t`info_value` as `tag_name`  -- 资产标签名称\n from `af_data_catalog`.`t_data_catalog_info` \n where `info_type` = 1 and `id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetCatalogTag2DataCatalogByCatalogTag(ctx context.Context, entityId string) ([]*model.EdgeCatalogTag2DataCatalog, error) {
	var ms []*model.EdgeCatalogTag2DataCatalog
	if err := r.do(ctx).Raw(
		"Select `id` as `tag_sid`,  -- 资产标签的雪花id\n\t`catalog_id` as `data_catalog_sid`  -- 数据资源目录的雪花id\nfrom `af_data_catalog`.`t_data_catalog_info` \nwhere `info_type` = 1 and `id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetInfoSystem(ctx context.Context, entityId string) (*model.EntityInfoSystem, error) {
	var ms []*model.EntityInfoSystem
	if err := r.do(ctx).Raw(
		"select si.info_ststem_id as `sys_sid`,   -- 信息系统的雪花id\n\t`id` as `info_system_uuid`,  -- 信息系统的uuid\n    name as `info_system_name` , -- 信息系统的名称\n    description as `info_system_description` -- 信息系统的描述\nfrom af_configuration.info_system si\nwhere (si.deleted_at is null or si.deleted_at=0) and `id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetInfoSystem2DataCatalogByInfoSystem(ctx context.Context, entityId string) ([]*model.EdgeInfoSystem2DataCatalog, error) {
	var ms []*model.EdgeInfoSystem2DataCatalog
	if err := r.do(ctx).Raw(
		"Select\n\ttdci.`info_key` as `sys_sid`, -- 信息系统的雪花id\n\ttdci.`catalog_id` as `data_catalog_sid` -- 数据资源目录的雪花id\nfrom `af_data_catalog`.`t_data_catalog_info` tdci\ninner join af_data_catalog.t_data_catalog tdc\non tdci.catalog_id = tdc.id\nwhere `info_type` = 4\nand  (tdc.deleted_at is null or tdc.deleted_at=0)\nand tdc.state=5 and tdci.`info_key`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDepartmentV2(ctx context.Context, entityId string) (*model.EntityDepartmentV2, error) {
	var ms []*model.EntityDepartmentV2
	if err := r.do(ctx).Raw(
		"SELECT `id`,  -- 部门的uuid\n\tname   -- 部门的名称\nFROM af_configuration.`object`  \nwhere type in (1,2)   -- 类型：1：组织2：部门3：信息系统4：业务事项5：主干业务6：业务表单\n\tand deleted_at=0 and `id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetDepartment2DataCatalogByDepartment(ctx context.Context, entityId string) ([]*model.EdgeDepartment2DataCatalog, error) {
	var ms []*model.EdgeDepartment2DataCatalog
	if err := r.do(ctx).Raw(
		"select  tdc.id as `data_catalog_sid`,   -- 数据资源目录的雪花id\n\ttdc.orgcode as department_id  -- 部门的uuid\nfrom af_data_catalog.t_data_catalog tdc \nwhere  tdc.deleted_at=0 \n\tor tdc.deleted_at is null and tdc.orgcode=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDataOwnerV2(ctx context.Context, entityId string) (*model.EntityDataOwnerV2, error) {
	var ms []*model.EntityDataOwnerV2
	if err := r.do(ctx).Raw(
		"select id as `owner_id`, name as `owner_name` from af_configuration.`user` where id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetDataOwner2DataCatalogByDataOwner(ctx context.Context, entityId string) ([]*model.EdgeDataOwner2DataCatalog, error) {
	var ms []*model.EdgeDataOwner2DataCatalog
	if err := r.do(ctx).Raw(
		"Select `id` as `data_catalog_sid`,  -- 数据资源目录的雪花id\n\t`owner_id` as `owner_id`   -- 数据owner的uuid\nfrom `af_data_catalog`.`t_data_catalog` \nwhere `owner_id`!='' and `owner_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetFormViewV2(ctx context.Context, entityId string) (*model.EntityFormViewV2, error) {
	var ms []*model.EntityFormViewV2
	if err := r.do(ctx).Raw(
		"select\nfv.`id`   as formview_uuid -- 逻辑视图uuid\n,fv.`uniform_catalog_code`   as formview_code -- '逻辑视图编码code'\n,fv.`technical_name`  as `technical_name` -- '技术名称'\n,fv.`business_name`   as `business_name` -- '业务名称'\n,fv.`type`  -- '逻辑视图来源 1：元数据视图、2：自定义视图、3：逻辑实体视图' 认知搜索目前只处理 1\n,fv.`description`   as `description` -- '逻辑视图描述'\n,fv.`datasource_id`   as `datasource_id`  -- '数据源id'\n,fv.`publish_at` -- '发布时间'\n,fv.`owner_id`              as `owner_id`,             -- '数据Ownerid'\nusr.`name`                   as `owner_name`,         -- 数据owner姓名\nfv.`department_id`         as `department_id`,        -- 部门id\ndpt.`name`                   as `department_name`,      -- 部门名称\ndpt.`path_id`                as `department_path_id`, -- 部门层级路径id\ndpt.`path`                 as `department_path`,    -- 部门层级路径\nfv.`subject_id`              as `subject_id`,           -- '主题id',包括L1和L2,'主题域id',如果是元数据视图和自定义视图这个字段有值就是主题域id如果逻辑实体视图这个字段必填是逻辑实体id\nsbj.`name`                                             as `subject_name`,         -- 主题名称\nsbj.`path_id`                                          as `subject_path_id`,      -- 主题层级路径id\nsbj.`path`                                           as `subject_path`          -- 主题层级路径\nfrom af_main.form_view fv\n         left join af_configuration.`user` usr\n                   on fv.owner_id = usr.id\n         left join (SELECT `id`,\n                           name,\n                           path_id,\n                           `path`\n                    FROM af_configuration.`object`\n                    where type in (1, 2)\n                      and deleted_at = 0) dpt\n                   on fv.department_id = dpt.id\n         left join (SELECT id,\n                           name,\n                           description,\n                           owners,\n                           'L1' as `prefix_name`,\n                           path_id,\n                           `path`\n                    FROM af_main.subject_domain g\n                    where g.`type` in (1, 2)\n                      and deleted_at = 0) sbj\n                   on fv.subject_id  = sbj.id\nwhere  fv.`publish_at`>=0\nand (fv.deleted_at is null or fv.deleted_at=0) and fv.`id`=?;",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetFormView2DataCatalogByFormView(ctx context.Context, entityId string) ([]*model.EdgeFormView2DataCatalog, error) {
	var ms []*model.EdgeFormView2DataCatalog
	if err := r.do(ctx).Raw(
		"select tdc.`code`  as datacatalog_code -- 数据资源目录编码code\n\t,tdcrm.s_res_id  as formview_uuid-- 逻辑视图uuid\nfrom af_data_catalog.t_data_catalog tdc \njoin af_data_catalog.t_data_catalog_resource_mount tdcrm\non tdc.code=tdcrm.code \nwhere tdcrm.res_type =1 and s_res_id is not null  and tdcrm.s_res_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetDataExploreReport2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeDataExploreReport2MetadataTable, error) {
	var ms []*model.EdgeDataExploreReport2MetadataTable

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"SELECT fvf.`id`      AS `column_id`, fvf.`form_view_id`  As `form_view_id`,  tri.f_project   as `explore_item`,\n       replace(JSON_VALUE(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"','')      as explore_result \nFROM (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 2000) numbers\n         join af_data_exploration.t_report_item tri on  LENGTH(tri.f_result) - LENGTH(REPLACE(tri.f_result, '[', '')) - 1 >= numbers.`index`\n         join af_data_exploration.t_report tet on tri.f_code = tet.f_code\n         JOIN af_main.form_view_field fvf ON fvf.form_view_id = tet.f_table_id  AND  fvf.technical_name = tri.f_column\nwhere tri.f_project in ('Group', 'Month', 'Year')  and tet.f_table_id is not null  and tri.f_result is not null  and tet.f_latest = 1  AND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0)\nhaving explore_result is not null  and explore_result != ''   and explore_result != 'null' and fvf.`form_view_id`=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"SELECT fvf.`id`                                                                                 AS `column_id`,    -- 字段uuid\n           fvf.`form_view_id`                                                                   As `form_view_id`,\n             tri.f_project                                                                            as `explore_item`, -- 探查项目\n             replace(JSON_EXTRACT(tri.f_result, concat('$[', numbers.`index` - 1, '][0]')), '\\\"',\n                     '')                                                                              as explore_result -- 探查结果\n      FROM (select @row_number := @row_number + 1 as `index`\n            from af_main.form_view_field fvf,\n                 (SELECT @row_number := 0) AS t\n            where @row_number < 2000) numbers\n               join af_data_exploration.t_report_item tri on\n          CHAR_LENGTH(tri.f_result) - CHAR_LENGTH(REPLACE(tri.f_result, '[', '')) - 1 >= numbers.`index`\n               join af_data_exploration.t_report tet on tri.f_code = tet.f_code\n               JOIN af_main.form_view_field fvf ON\n          fvf.form_view_id = tet.f_table_id  AND\n          fvf.technical_name = tri.f_column \n      where tri.f_project in ('Group', 'Month', 'Year')\n        and tet.f_table_id is not null\n        and tri.f_result is not null\n        and tet.f_latest = 1\n        AND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0)\n      having explore_result is not null\n         and explore_result != ''\n         and explore_result != 'null' and fvf.`form_view_id`=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	return ms, nil
}

func (r *repo) GetMetadataTableField2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeMetadataTableField2MetadataTable, error) {
	var ms []*model.EdgeMetadataTableField2MetadataTable
	if err := r.do(ctx).Raw(
		"select \n\tfvf.`id` as column_id -- '字段uuid'\n\t,fvf.`form_view_id` as formview_uuid -- 逻辑视图uuid\nfrom  af_main.form_view_field fvf\nwhere (fvf.deleted_at is null or fvf.deleted_at=0) and fvf.`form_view_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetMetadataSchema2MetadataTableByFormView(ctx context.Context, entityId string) ([]*model.EdgeMetadataSchema2MetadataTable, error) {
	var ms []*model.EdgeMetadataSchema2MetadataTable
	if err := r.do(ctx).Raw(
		"select fv.id  as formview_uuid -- 逻辑视图uuid\n,tt.f_schema_id as schema_sid-- 库雪花id\nfrom af_main.form_view fv\njoin `af_metadata`.`t_table` tt\non fv.metadata_form_id = tt.f_id and fv.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetMetadataSchemaV2(ctx context.Context, entityId string) (*model.EntityMetadataSchemaV2, error) {
	var ms []*model.EntityMetadataSchemaV2
	if err := r.do(ctx).Raw(
		"Select `f_id` as `schema_sid`,  -- 库名称雪花id该表没有uuid字段\n `f_name` as `schema_name`,   -- 库名称\n'库' as `prefix_name` \nfrom `af_metadata`.`t_schema` and `f_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetMetadataSchema2MetadataTableByMetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeMetadataSchema2MetadataTable, error) {
	var ms []*model.EdgeMetadataSchema2MetadataTable
	if err := r.do(ctx).Raw(
		"select fv.id  as formview_uuid -- 逻辑视图uuid\n,tt.f_schema_id as schema_sid-- 库雪花id\nfrom af_main.form_view fv\njoin `af_metadata`.`t_table` tt\non fv.metadata_form_id = tt.f_id and tt.f_schema_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDatasource2MetaDataSchemaByMetadataSchemaV2(ctx context.Context, entityId string) ([]*model.EdgeDatasource2MetaDataSchema, error) {
	var ms []*model.EdgeDatasource2MetaDataSchema
	if err := r.do(ctx).Raw(
		"Select \n\tds.`id` as data_source_uuid, -- 数据源uuid\n\t`f_id` as `schema_sid`  -- 库名称雪花id 没有uuid\nfrom `af_metadata`.`t_schema` ts\ninner join af_configuration.datasource ds \non ts.f_data_source_id = ds.data_source_id and `f_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDataSourceV2(ctx context.Context, entityId string) (*model.EntityDataSourceV2, error) {
	var ms []*model.EntityDataSourceV2
	if err := r.do(ctx).Raw(
		"Select \n\t`id` as `data_source_uuid`,  -- 数据源uuid字段\n\t`name` as `data_source_name`,  -- 数据源名称\n\t`type_name` as `data_source_type_name`, -- 数据源类型名称类型名称mysqlhive-jdbc等值\n\tsource_type as source_type_code,  -- 数据源类型编码1 记录型、2 分析型\n\tcase when source_type=1 then '记录型'\n\t\twhen source_type=2 then '分析型'\n\t\telse null\n\t\tend as source_type_name , -- 数据源类型名称记录型、分析型\n\t'数据源' as `prefix_name` \nfrom af_configuration.datasource where `id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetDatasource2MetaDataSchemaByDataSourceV2(ctx context.Context, entityId string) ([]*model.EdgeDatasource2MetaDataSchema, error) {
	var ms []*model.EdgeDatasource2MetaDataSchema
	if err := r.do(ctx).Raw(
		"Select \n\tds.`id` as data_source_uuid, -- 数据源uuid\n\t`f_id` as `schema_sid`  -- 库名称雪花id 没有uuid\nfrom `af_metadata`.`t_schema` ts\ninner join af_configuration.datasource ds \non ts.f_data_source_id = ds.data_source_id and ds.`id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetDataExploreReportV2(ctx context.Context, entityId string) (*model.EntityDataExploreReportV2, error) {
	var ms []*model.EntityDataExploreReportV2

	if strings.Contains(gormx.DriveDm, r.data.DB.Dialector.Name()) {
		if err := r.do(ctx).Raw(
			"SELECT   fvf.id AS `column_id`, tri.f_project as `explore_item`, tri.f_column as `column_name`,\n    (case when tri.f_project in ('group','date_distribute_year','date_distribute_month')\n              then replace(JSON_VALUE(tri.f_result,concat('$[',numbers.`index`,'].key')),'\\\"','')\n          else  replace(JSON_VALUE(tri.f_result , '$[0].result'),'\\\"','') end ) as explore_result\nFROM  (SELECT ROWNUM AS \"index\" FROM af_main.form_view_field fvf WHERE ROWNUM <= 2000) numbers\n        join af_data_exploration.t_report_item tri on\n                LENGTH(tri.f_result) - LENGTH(REPLACE(tri.f_result, '{', '')) >= numbers.`index`\n        join af_data_exploration.t_report tet on tri.f_code=tet.f_code\n        JOIN af_main.form_view_field fvf ON   fvf.form_view_id = tet.f_table_id  AND   fvf.technical_name = tri.f_column\nwhere tri.f_project in ('date_distribute_year','date_distribute_month','dict','group','max','min')  and tet.f_table_id is not null  and tri.f_result is not null  and tet.f_latest=1  AND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0) \nhaving explore_result is not null and explore_result!=\"\" and explore_result!='null' and fvf.id=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"SELECT \n\tfvf.id AS `column_id`, -- 字段uuid\n\ttri.f_project as `explore_item`, -- 探查项目\n\ttri.f_column as `column_name`, -- 字段名称\n\t(case when tri.f_project in ('group','date_distribute_year','date_distribute_month')\n\t      then replace(JSON_EXTRACT(tri.f_result,concat('$[',numbers.`index`,'].key')),'\\\"','')\n\telse  replace(JSON_EXTRACT(tri.f_result , '$[0].result'),'\\\"','') end ) as explore_result -- 探查结果\nFROM \n\t(select @row_number:=@row_number + 1 as `index` from af_main.form_view_field fvf,\n\t(SELECT @row_number:=0) AS t where @row_number<2000) numbers\n\tjoin af_data_exploration.t_report_item tri on\n\tCHAR_LENGTH(tri.f_result) - CHAR_LENGTH(REPLACE(tri.f_result, '{', '')) >= numbers.`index`\n\tjoin af_data_exploration.t_report tet on tri.f_code=tet.f_code\n\tJOIN af_main.form_view_field fvf ON \n\tfvf.form_view_id = tet.f_table_id  AND \n\tfvf.technical_name = tri.f_column  \nwhere tri.f_project in ('date_distribute_year','date_distribute_month','dict','group','max','min')\nand tet.f_table_id is not null             \nand tri.f_result is not null \nand tet.f_latest=1\nAND (fvf.deleted_at IS NULL OR fvf.deleted_at = 0)\nhaving explore_result is not null and explore_result!=\"\" and explore_result!='null' and fvf.id=?",
			entityId).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetDataExploreReport2MetadataTableByDataExploreReportV2(ctx context.Context, entityId string) ([]*model.EdgeDataExploreReport2MetadataTable, error) {
	var ms []*model.EdgeDataExploreReport2MetadataTable
	if err := r.do(ctx).Raw(
		"select \n\tfvf.form_view_id as formview_uuid -- 逻辑视图uuid\n\t,fvf.`id` as column_id -- 字段uuID\nfrom af_main.form_view_field fvf\nwhere (fvf.deleted_at is null or fvf.deleted_at=0) and fvf.`id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetFormViewFieldV2(ctx context.Context, entityId string) (*model.EntityFormViewFieldV2, error) {
	var ms []*model.EntityFormViewFieldV2
	if err := r.do(ctx).Raw(
		"select\n-- \tfvf.form_view_field_sid ,  -- 字段雪花id\n\tfvf.`id` as column_id -- '字段uuid'\n\t,fvf.`form_view_id`  as formview_uuid -- 逻辑视图uuid\n\t,fvf.`technical_name` -- '字段技术名称'\n\t,fvf. `business_name`  -- '字段业务名称'\n\t,fvf.`data_type` -- '数据类型'\nfrom  af_main.form_view_field fvf\ninner join af_main.form_view fv\non fv.id=fvf.form_view_id\nwhere (fvf.deleted_at is null or fvf.deleted_at=0)\nand fv.publish_at>0\nand  (fv.deleted_at is null or fv.deleted_at=0) and fvf.`id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetMetadataTableField2MetadataTableByFormViewFieldV2(ctx context.Context, entityId string) ([]*model.EdgeMetadataTableField2MetadataTable, error) {
	var ms []*model.EdgeMetadataTableField2MetadataTable
	if err := r.do(ctx).Raw(
		"select \n\tfvf.`id` as column_id -- '字段uuid'\n\t,fvf.`form_view_id` as formview_uuid -- 逻辑视图uuid\nfrom  af_main.form_view_field fvf\nwhere (fvf.deleted_at is null or fvf.deleted_at=0) and fvf.`id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

// 业务架构图谱——算法
func (r *repo) GetEntityDomainGroup(ctx context.Context, entityId string) (*model.EntityEntityDomainGroup, error) {
	var ms []*model.EntityEntityDomainGroup
	if err := r.do(ctx).Raw(
		"select id, name, description, path, path_id, department_id, business_system, model_id\nfrom af_business.domain\nwhere type=1 and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationDomainGroup2DomainByDomainGroup(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainGroup2Domain, error) {
	var ms []*model.EdgeRelationDomainGroup2Domain
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_business.domain a\nwhere deleted_at=0 and a.path_id like '%/%' and a.path not like '%/%/%' and a.type=2 and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityDomain(ctx context.Context, entityId string) (*model.EntityEntityDomain, error) {
	var ms []*model.EntityEntityDomain
	if err := r.do(ctx).Raw(
		"select id, name, description, path, path_id, department_id, business_system, model_id\nfrom af_business.domain\nwhere type=2 and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationDomainGroup2DomainByDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainGroup2Domain, error) {
	var ms []*model.EdgeRelationDomainGroup2Domain
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_business.domain a\nwhere deleted_at=0 and a.path_id like '%/%' and a.path not like '%/%/%' and a.type=2 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationDomain2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2Self, error) {
	var ms []*model.EdgeRelationDomain2Self
	if err := r.do(ctx).Raw(
		"select a.id, \"\" as parent_id\nfrom af_business.domain a\nwhere a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationDomain2DomainFlowByDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2DomainFlow, error) {
	var ms []*model.EdgeRelationDomain2DomainFlow
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_business.domain a\nwhere deleted_at=0 and a.path_id like '%/%/%' and a.type=2 and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityDomainFlow(ctx context.Context, entityId string) (*model.EntityEntityDomainFlow, error) {
	var ms []*model.EntityEntityDomainFlow
	if err := r.do(ctx).Raw(
		"select id, name, description, path, path_id, department_id, business_system, model_id\nfrom af_business.domain\nwhere type=3 and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationDomain2DomainFlowByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationDomain2DomainFlow, error) {
	var ms []*model.EdgeRelationDomain2DomainFlow
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_business.domain a\nwhere deleted_at=0 and a.path_id like '%/%/%' and a.type=2 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationDomainFlow2InfomationSystemByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainFlow2InfomationSystem, error) {
	var ms []*model.EdgeRelationDomainFlow2InfomationSystem
	if err := r.do(ctx).Raw(
		"select a.id as domain_flow_id, b.id as infomation_system_id\nfrom af_business.domain a, af_configuration.info_system b\nwhere instr(convert(a.business_system using utf8mb4), convert(b.id using utf8mb4)) > 0\n  and  a.deleted_at=0 and a.type=3 and a.business_system!='' and a.business_system is not null\n  and b.deleted_at=0 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationBusinessModel2DepartmentByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Department, error) {
	var ms []*model.EdgeRelationBusinessModel2Department
	if err := r.do(ctx).Raw(
		"select a.id as domain_flow_id, b.id as department_id\nfrom af_business.domain a, af_configuration.object b\nwhere a.deleted_at=0 and a.type=3 and convert(a.department_id using utf8mb4)=convert(b.id using utf8mb4) and domain_flow_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationBusinessModel2DomainFlowByDomainFlow(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2DomainFlow, error) {
	var ms []*model.EdgeRelationBusinessModel2DomainFlow
	if err := r.do(ctx).Raw(
		"select business_model_id, b.id as business_domain_id\nfrom af_business.business_model a, af_business.domain b\nwhere a.deleted_at=0 and b.deleted_at=0 and b.type=3 and a.business_domain_id = b.id and b.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityInfomationSystem(ctx context.Context, entityId string) (*model.EntityEntityInfomationSystem, error) {
	var ms []*model.EntityEntityInfomationSystem
	if err := r.do(ctx).Raw(
		"select id, name, description\nfrom af_configuration.info_system\nwhere deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationDomainFlow2InfomationSystemByInfomationSystem(ctx context.Context, entityId string) ([]*model.EdgeRelationDomainFlow2InfomationSystem, error) {
	var ms []*model.EdgeRelationDomainFlow2InfomationSystem
	if err := r.do(ctx).Raw(
		"select a.id as domain_flow_id, b.id as infomation_system_id\nfrom af_business.domain a, af_configuration.info_system b\nwhere instr(convert(a.business_system using utf8mb4), convert(b.id using utf8mb4)) > 0\n  and  a.deleted_at=0 and a.type=3 and a.business_system!='' and a.business_system is not null\n  and b.deleted_at=0 and b.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityDepartment(ctx context.Context, entityId string) (*model.EntityEntityDepartment, error) {
	var ms []*model.EntityEntityDepartment
	if err := r.do(ctx).Raw(
		"select id, name, path_id, path\nfrom af_configuration.object\nwhere deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationBusinessModel2DepartmentByDepartment(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Department, error) {
	var ms []*model.EdgeRelationBusinessModel2Department
	if err := r.do(ctx).Raw(
		"select a.id as domain_flow_id, b.id as department_id\nfrom af_business.domain a, af_configuration.object b\nwhere a.deleted_at=0 and a.type=3 and convert(a.department_id using utf8mb4)=convert(b.id using utf8mb4) and b.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationDepartment2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationDepartment2Self, error) {
	var ms []*model.EdgeRelationDepartment2Self
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_configuration.object a\nwhere deleted_at=0 and a.path_id like '%/%' and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityBusinessModel(ctx context.Context, entityId string) (*model.EntityEntityBusinessModel, error) {
	var ms []*model.EntityEntityBusinessModel
	if err := r.do(ctx).Raw(
		"select business_model_id as id,business_domain_id as domain_id,name,description\nfrom af_business.business_model\nwhere deleted_at=0 and business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationBusinessModel2DomainFlowByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2DomainFlow, error) {
	var ms []*model.EdgeRelationBusinessModel2DomainFlow
	if err := r.do(ctx).Raw(
		"select business_model_id, b.id as business_domain_id\nfrom af_business.business_model a, af_business.domain b\nwhere a.deleted_at=0 and b.deleted_at=0 and b.type=3 and a.business_domain_id = b.id and business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationBusinessModel2FormByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Form, error) {
	var ms []*model.EdgeRelationBusinessModel2Form
	if err := r.do(ctx).Raw(
		"select a.business_form_id as form_id, b.business_model_id\nfrom af_business.business_form_standard a, af_business.business_model b\nwhere a.deleted_at =0 and b.deleted_at =0 and a.business_model_id=b.business_model_id and b.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationBusinessModel2FlowchartByBusinessModel(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Flowchart, error) {
	var ms []*model.EdgeRelationBusinessModel2Flowchart
	if err := r.do(ctx).Raw(
		"select a.flowchart_id, b.business_model_id\nfrom af_business.business_flowchart a, af_business.business_model b\nwhere a.deleted_at =0 and b.deleted_at =0 and a.business_model_id=b.business_model_id and b.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityFlowchart(ctx context.Context, entityId string) (*model.EntityEntityFlowchart, error) {
	var ms []*model.EntityEntityFlowchart
	if err := r.do(ctx).Raw(
		"SELECT flowchart_id as id,name,description,business_model_id,path, path_id\nFROM af_business.business_flowchart\nwhere deleted_at=0 and flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationBusinessModel2FlowchartByFlowchart(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Flowchart, error) {
	var ms []*model.EdgeRelationBusinessModel2Flowchart
	if err := r.do(ctx).Raw(
		"select a.flowchart_id, b.business_model_id\nfrom af_business.business_flowchart a, af_business.business_model b\nwhere a.deleted_at =0 and b.deleted_at =0 and a.business_model_id=b.business_model_id and b.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationFlowchart2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2Self, error) {
	var ms []*model.EdgeRelationFlowchart2Self
	if err := r.do(ctx).Raw(
		"select a.flowchart_id from_flowchart_id, a.sub_flowchart_id  to_flowchart_id\nfrom af_business.business_flowchart_relationship a\nwhere a.flowchart_id is not null and a.sub_flowchart_id is not null and from_flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationFlowchart2FlowchartNodeByFlowchart(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2FlowchartNode, error) {
	var ms []*model.EdgeRelationFlowchart2FlowchartNode
	if err := r.do(ctx).Raw(
		"select a.flowchart_id, b.component_id as flowchart_node_id\nfrom af_business.business_flowchart a, af_business.business_flowchart_component b\nwhere a.deleted_at=0 and `type` in (1,5) and a.flowchart_id=b.flowchart_id and a.flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityFlowchartNode(ctx context.Context, entityId string) (*model.EntityEntityFlowchartNode, error) {
	var ms []*model.EntityEntityFlowchartNode
	if err := r.do(ctx).Raw(
		"SELECT component_id as id,mxcell_id,flowchart_id,name,description, source, target\nFROM af_business.business_flowchart_component\nwhere `type` in (1,5) and component_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationFlowchartNode2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchartNode2Self, error) {
	var ms []*model.EdgeRelationFlowchartNode2Self
	if err := r.do(ctx).Raw(
		"select a.component_id as from_flowchart_node_id, b.component_id as to_flowchart_node_id\nfrom af_business.business_flowchart_component a, af_business.business_flowchart_component b, af_business.business_flowchart_component c\nwhere c.type=11 and a.type in (1,5) and b.type in (1,5) and c.source=a.mxcell_id and c.target=b.mxcell_id and a.component_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationFlowchart2FlowchartNodeByFlowchartNode(ctx context.Context, entityId string) ([]*model.EdgeRelationFlowchart2FlowchartNode, error) {
	var ms []*model.EdgeRelationFlowchart2FlowchartNode
	if err := r.do(ctx).Raw(
		"select a.flowchart_id, b.component_id as flowchart_node_id\nfrom af_business.business_flowchart a, af_business.business_flowchart_component b\nwhere a.deleted_at=0 and `type` in (1,5) and a.flowchart_id=b.flowchart_id and b.component_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityForm(ctx context.Context, entityId string) (*model.EntityEntityForm, error) {
	var ms []*model.EntityEntityForm
	if err := r.do(ctx).Raw(
		"select business_form_id as id,name, description, business_model_id\nfrom af_business.business_form_standard\nwhere deleted_at=0 and business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntityFormList(ctx context.Context) ([]*model.EntityEntityForm, error) {
	var ms []*model.EntityEntityForm
	if err := r.do(ctx).Raw(
		"select business_form_id as id,name, description, business_model_id\nfrom af_business.business_form_standard\nwhere deleted_at=0").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetRelationForm2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Self, error) {
	var ms []*model.EdgeRelationForm2Self
	if err := r.do(ctx).Raw(
		"select a.business_form_id  as from_form_id, b.business_form_id as to_form_id\nfrom af_business.business_form_field_standard a\njoin af_business.business_form_field_standard b on a.field_id=b.ref_id\nwhere a.deleted_at=0 and b.deleted_at=0 and a.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationBusinessModel2FormByForm(ctx context.Context, entityId string) ([]*model.EdgeRelationBusinessModel2Form, error) {
	var ms []*model.EdgeRelationBusinessModel2Form
	if err := r.do(ctx).Raw(
		"select a.business_form_id as form_id, b.business_model_id\nfrom af_business.business_form_standard a, af_business.business_model b\nwhere a.deleted_at =0 and b.deleted_at =0 and a.business_model_id=b.business_model_id and a.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationForm2FieldByForm(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Field, error) {
	var ms []*model.EdgeRelationForm2Field
	if err := r.do(ctx).Raw(
		"select a.business_form_id as form_id, b.field_id\nfrom af_business.business_form_standard a, af_business.business_form_field_standard b\nwhere a.deleted_at=0 and b.deleted_at=0 and a.business_form_id=b.business_form_id and a.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityField(ctx context.Context, entityId string) (*model.EntityEntityField, error) {
	var ms []*model.EntityEntityField
	if err := r.do(ctx).Raw(
		"SELECT field_id as id,business_form_id,business_form_name,name,name_en, standard_id\nFROM af_business.business_form_field_standard\nwhere deleted_at=0 and field_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationForm2FieldByField(ctx context.Context, entityId string) ([]*model.EdgeRelationForm2Field, error) {
	var ms []*model.EdgeRelationForm2Field
	if err := r.do(ctx).Raw(
		"select a.business_form_id as form_id, b.field_id\nfrom af_business.business_form_standard a, af_business.business_form_field_standard b\nwhere a.deleted_at=0 and b.deleted_at=0 and a.business_form_id=b.business_form_id and b.field_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationDataElement2FieldByField(ctx context.Context, entityId string) ([]*model.EdgeRelationDataElement2Field, error) {
	var ms []*model.EdgeRelationDataElement2Field
	if err := r.do(ctx).Raw(
		"select a.field_id as field_id, b.f_de_code as standard_id\nfrom af_business.business_form_field_standard a, af_std.t_data_element_info b\nwhere a.standard_id != '' and a.standard_id=b.f_de_code and a.field_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityDataElement(ctx context.Context, entityId string) (*model.EntityEntityDataElement, error) {
	var ms []*model.EntityEntityDataElement
	if err := r.do(ctx).Raw(
		"select f_de_id as id,f_de_code as code,f_name_en as name_en,f_name_cn as name_cn,concat(f_de_code, '###', f_std_type) as std_type,\n       f_rule_id as rule_id, f_department_ids as department_ids\nfrom af_std.t_data_element_info where f_deleted=0 and f_de_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntityDataElementList(ctx context.Context) ([]*model.EntityEntityDataElement, error) {
	var ms []*model.EntityEntityDataElement
	if err := r.do(ctx).Raw(
		"select f_de_id as id,f_de_code as code,f_name_en as name_en,f_name_cn as name_cn,concat(f_de_code, '###', f_std_type) as std_type,\n       f_rule_id as rule_id, f_department_ids as department_ids\nfrom af_std.t_data_element_info where f_deleted=0").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetEntityLabel(ctx context.Context, entityId string) (*model.EntityEntityLabel, error) {
	var ms []*model.EntityEntityLabel
	if err := r.do(ctx).Raw(
		"select T1.id, T1.name, T1.category_id, T1.f_path, T1.f_sort, T2.name as category_name, T2.f_range_type_key as category_range_type, T2.f_description as category_description\nfrom af_main.t_label as T1\nleft join af_main.t_label_category as T2 on T1.category_id=T2.id\nwhere T1.deleted_at=0 and T2.deleted_at=0\n    and f_audit_status='published' and f_state=1 and T1.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetEntityLabelsByCategory(ctx context.Context, entityId string) ([]*model.EntityEntityLabel, error) {
	var ms []*model.EntityEntityLabel
	if err := r.do(ctx).Raw(
		"select T1.id, T1.name, T1.category_id, T1.f_path, T1.f_sort, T2.name as category_name, T2.f_range_type_key as category_range_type, T2.f_description as category_description\nfrom af_main.t_label as T1\nleft join af_main.t_label_category as T2 on T1.category_id=T2.id\nwhere T1.deleted_at=0 and T2.deleted_at=0\n    and f_audit_status='published' and f_state=1 and T2.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetEntityLabelsByCategoryIgnoreFState(ctx context.Context, entityId string) ([]*model.EntityEntityLabel, error) {
	var ms []*model.EntityEntityLabel
	if err := r.do(ctx).Raw(
		"select T1.id, T1.name, T1.category_id, T1.f_path, T1.f_sort, T2.name as category_name, T2.f_range_type_key as category_range_type, T2.f_description as category_description\nfrom af_main.t_label as T1\nleft join af_main.t_label_category as T2 on T1.category_id=T2.id\nwhere T1.deleted_at=0 and T2.deleted_at=0\n    and f_audit_status='published'  and T2.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetEntityBusinessIndicator(ctx context.Context, entityId string) (*model.EntityEntityBusinessIndicator, error) {
	var ms []*model.EntityEntityBusinessIndicator
	if err := r.do(ctx).Raw(
		"select business_model_id, indicator_id as id, name, description,\n       calculation_formula, unit, statistics_cycle, statistical_caliber\nfrom af_business.business_indicator\nwhere deleted_at=0 and indicator_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntityRule(ctx context.Context, entityId string) (*model.EntityEntityRule, error) {
	var ms []*model.EntityEntityRule
	if err := r.do(ctx).Raw(
		"select f_id as id, f_name as name, f_catalog_id as category_id, f_org_type as org_type,\n       f_description as description, f_rule_type as rule_type, f_expression as expression, f_department_ids as department_ids\nfrom af_std.t_rule\nwhere f_deleted=0 and f_id = ?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntityRuleList(ctx context.Context) ([]*model.EntityEntityRule, error) {
	var ms []*model.EntityEntityRule
	if err := r.do(ctx).Raw(
		"select f_id as id, f_name as name, f_catalog_id as category_id, f_org_type as org_type,\n       f_description as description, f_rule_type as rule_type, f_expression as expression, f_department_ids as department_ids\nfrom af_std.t_rule\nwhere f_deleted=0").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetRelationDataElement2FieldByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationDataElement2Field, error) {
	var ms []*model.EdgeRelationDataElement2Field
	if err := r.do(ctx).Raw(
		"select a.field_id as field_id, b.f_de_code as standard_id\nfrom af_business.business_form_field_standard a, af_std.t_data_element_info b\nwhere a.standard_id != '' and a.standard_id=b.f_de_code and b.f_de_code=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationViewField2DataElementByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationViewField2DataElement, error) {
	var ms []*model.EdgeRelationViewField2DataElement
	if err := r.do(ctx).Raw(
		"select a.id as view_field_id, b.f_de_code as standard_id\nfrom af_main.form_view_field a, af_std.t_data_element_info b\nwhere a.deleted_at=0 and a.standard_code=b.f_de_code and b.f_de_code=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectProperty2EntityDataElementByDataElement(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectProperty2EntityDataElement, error) {
	var ms []*model.EdgeRelationSubjectProperty2EntityDataElement
	if err := r.do(ctx).Raw(
		"select a.id as subject_prop_id, b.f_de_code as standard_id\nfrom af_main.subject_domain a, af_std.t_data_element_info b\nwhere a.deleted_at=0 and a.type=6 and a.standard_id=b.f_de_code and b.f_de_code=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityFormViewField(ctx context.Context, entityId string) (*model.EntityEntityFormViewField, error) {
	var ms []*model.EntityEntityFormViewField
	if err := r.do(ctx).Raw(
		"select id, form_view_id,technical_name,business_name as name, standard_code, standard,code_table_id\nfrom  af_main.form_view_field\nwhere deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationViewField2DataElementByViewField(ctx context.Context, entityId string) ([]*model.EdgeRelationViewField2DataElement, error) {
	var ms []*model.EdgeRelationViewField2DataElement
	if err := r.do(ctx).Raw(
		"select a.id as view_field_id, b.f_de_code as standard_id\nfrom af_main.form_view_field a, af_std.t_data_element_info b\nwhere a.deleted_at=0 and a.standard_code=b.f_de_code and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationFormView2FieldByViewField(ctx context.Context, entityId string) ([]*model.EdgeRelationFormView2Field, error) {
	var ms []*model.EdgeRelationFormView2Field
	if err := r.do(ctx).Raw(
		"select a.id as view_form_id, b.id as view_form_field_id\nfrom af_main.form_view a, af_main.form_view_field b\nwhere a.deleted_at=0 and b.deleted_at=0 and a.id=b.form_view_id and b.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntityFormView(ctx context.Context, entityId string) (*model.EntityEntityFormView, error) {
	var ms []*model.EntityEntityFormView
	if err := r.do(ctx).Raw(
		"select id,technical_name,business_name as name, type,datasource_id,subject_id,description\nfrom af_main.form_view\nwhere deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntityFormViewList(ctx context.Context) ([]*model.EntityEntityFormView, error) {
	var ms []*model.EntityEntityFormView
	if err := r.do(ctx).Raw(
		"select id,technical_name,business_name as name, type,datasource_id,subject_id,description\nfrom af_main.form_view\nwhere deleted_at=0").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}
func (r *repo) GetRelationFormView2FieldByFormView(ctx context.Context, entityId string) ([]*model.EdgeRelationFormView2Field, error) {
	var ms []*model.EdgeRelationFormView2Field
	if err := r.do(ctx).Raw(
		"select a.id as view_form_id, b.id as view_form_field_id\nfrom af_main.form_view a, af_main.form_view_field b\nwhere a.deleted_at=0 and b.deleted_at=0 and a.id=b.form_view_id and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntitySubjectProperty(ctx context.Context, entityId string) (*model.EntityEntitySubjectProperty, error) {
	var ms []*model.EntityEntitySubjectProperty
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path,standard_id\nfrom af_main.subject_domain\nwhere deleted_at=0 and type=6 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetEntitySubjectPropertyList(ctx context.Context) ([]*model.EntityEntitySubjectProperty, error) {
	var ms []*model.EntityEntitySubjectProperty
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path,standard_id\nfrom af_main.subject_domain\nwhere deleted_at=0 and type=6").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return ms, nil
}

func (r *repo) GetEntitySubjectModel(ctx context.Context, entityId string) (*model.EntityEntitySubjectModel, error) {
	var ms []*model.EntityEntitySubjectModel
	if err := r.do(ctx).Raw(
		"select id, business_name,technical_name,description,data_view_id from af_main.t_graph_model where deleted_at=0 and model_type=3 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetEntitySubjectModelList(ctx context.Context) ([]*model.EntityEntitySubjectModel, error) {
	var ms []*model.EntityEntitySubjectModel
	if err := r.do(ctx).Raw(
		"select id, business_name,technical_name,description,data_view_id from af_main.t_graph_model where deleted_at=0 and model_type=3").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetEntitySubjectModelLabelList(ctx context.Context) ([]*model.EntityEntitySubjectModelLabel, error) {
	var ms []*model.EntityEntitySubjectModelLabel
	if err := r.do(ctx).Raw(
		"select id, name, related_model_ids  from af_main.t_model_label_rec_rel where deleted_at=0").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetRelationSubjectProperty2EntityDataElementBySubjectProperty(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectProperty2EntityDataElement, error) {
	var ms []*model.EdgeRelationSubjectProperty2EntityDataElement
	if err := r.do(ctx).Raw(
		"select a.id as subject_prop_id, b.f_de_code as standard_id\nfrom af_main.subject_domain a, af_std.t_data_element_info b\nwhere a.deleted_at=0 and a.type=6 and a.standard_id=b.f_de_code and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectEntity2SubjectPropBySubjectProperty(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectEntity2SubjectProp, error) {
	var ms []*model.EdgeRelationSubjectEntity2SubjectProp
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%/%/%' and a.path not like '%/%/%/%/%/%' and a.type=6 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntitySubjectEntity(ctx context.Context, entityId string) (*model.EntityEntitySubjectEntity, error) {
	var ms []*model.EntityEntitySubjectEntity
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path\nfrom af_main.subject_domain\nwhere deleted_at=0 and type=5 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationSubjectEntity2SubjectPropBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectEntity2SubjectProp, error) {
	var ms []*model.EdgeRelationSubjectEntity2SubjectProp
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%/%/%' and a.path not like '%/%/%/%/%/%' and a.type=6 and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectObject2SubjectEntityBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2SubjectEntity, error) {
	var ms []*model.EdgeRelationSubjectObject2SubjectEntity
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%/%' and a.path not like '%/%/%/%/%' and a.type=5 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntitySubjectObject(ctx context.Context, entityId string) (*model.EntityEntitySubjectObject, error) {
	var ms []*model.EntityEntitySubjectObject
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path, ref_id\nfrom af_main.subject_domain\nwhere deleted_at=0 and type in (3,4) and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationSubjectObject2SubjectEntityBySubjectObject(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2SubjectEntity, error) {
	var ms []*model.EdgeRelationSubjectObject2SubjectEntity
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%/%' and a.path not like '%/%/%/%/%' and a.type=5 and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectObject2Self(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectObject2Self, error) {
	var ms []*model.EdgeRelationSubjectObject2Self
	if err := r.do(ctx).Raw(
		"select id, ref_id\nfrom af_main.subject_domain\nwhere deleted_at=0 and ref_id is not null and ref_id != '' and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectDomain2SubjectObjectBySubjectEntity(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectDomain2SubjectObject, error) {
	var ms []*model.EdgeRelationSubjectDomain2SubjectObject
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%' and a.path not like '%/%/%/%' and a.type in (3,4) and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntitySubjectDomain(ctx context.Context, entityId string) (*model.EntityEntitySubjectDomain, error) {
	var ms []*model.EntityEntitySubjectDomain
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path\nfrom af_main.subject_domain\nwhere deleted_at=0 and type=2 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationSubjectDomain2SubjectObjectBySubjectDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectDomain2SubjectObject, error) {
	var ms []*model.EdgeRelationSubjectDomain2SubjectObject
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%/%' and a.path not like '%/%/%/%' and a.type in (3,4) and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetRelationSubjectGroup2SubjectDomainsBySubjectDomain(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectGroup2SubjectDomains, error) {
	var ms []*model.EdgeRelationSubjectGroup2SubjectDomains
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%' and a.path not like '%/%/%' and a.type=2 and a.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetEntitySubjectGroup(ctx context.Context, entityId string) (*model.EntityEntitySubjectGroup, error) {
	var ms []*model.EntityEntitySubjectGroup
	if err := r.do(ctx).Raw(
		"select id, name,description,path_id,path\nfrom af_main.subject_domain\nwhere deleted_at=0 and type=1 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetRelationSubjectGroup2SubjectDomainsBySubjectGroup(ctx context.Context, entityId string) ([]*model.EdgeRelationSubjectGroup2SubjectDomains, error) {
	var ms []*model.EdgeRelationSubjectGroup2SubjectDomains
	if err := r.do(ctx).Raw(
		"select a.id, IF(a.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1), '') as parent_id\nfrom af_main.subject_domain a\nwhere deleted_at=0 and a.path_id like '%/%' and a.path not like '%/%/%' and a.type=2 and SUBSTRING_INDEX(SUBSTRING_INDEX(a.path_id, '/', -2), '/', 1)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetTableSubjectDomainByPathId(ctx context.Context, pathId string) ([]*model.TableSubjectDomain, error) {
	var ms []*model.TableSubjectDomain
	if err := r.do(ctx).Raw(
		"SELECT id, -- 主体域分组uuidL1\n\tname,  \n\ttype,\n\tdeleted_at\nFROM af_main.subject_domain  \nwhere deleted_at=0 and path_id like ?",
		pathId+"%").Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}

func (r *repo) GetBRGEntityBusinessDomain(ctx context.Context, entityId string) (*model.BRGEntityBusinessDomain, error) {
	var ms []*model.BRGEntityBusinessDomain
	if err := r.do(ctx).Raw(
		"SELECT id, name, description, owners  FROM af_main.subject_domain g  where g.`type`=1  and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityThemeDomain(ctx context.Context, entityId string) (*model.BRGEntityThemeDomain, error) {
	var ms []*model.BRGEntityThemeDomain
	if err := r.do(ctx).Raw(
		"SELECT id, name, description, owners  FROM af_main.subject_domain g  \twhere g.`type`=2  and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityBusinessObject(ctx context.Context, entityId string) (*model.BRGEntityBusinessObject, error) {
	var ms []*model.BRGEntityBusinessObject
	if err := r.do(ctx).Raw(
		"SELECT id, name, description, owners  FROM af_main.subject_domain g  \twhere g.`type` in (3, 4)  and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityDataCatalog(ctx context.Context, entityId string) (*model.BRGEntityDataCatalog, error) {
	var ms []*model.BRGEntityDataCatalog
	if err := r.do(ctx).Raw(
		"SELECT `id`,`code`,title,group_id,`group_name`,theme_id,`theme_name`,  `description`,data_range,update_cycle,data_kind,orgcode,orgname  FROM af_data_catalog.t_data_catalog  \twhere deleted_at is null or deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityInfoSystem(ctx context.Context, entityId string) (*model.BRGEntityInfoSystem, error) {
	var ms []*model.BRGEntityInfoSystem
	if err := r.do(ctx).Raw(
		"select `id`, `name`, `path`,`attribute` from af_configuration.object  where type=3 and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityBusinessScene(ctx context.Context, entityId string) (*model.BRGEntityBusinessScene, error) {
	var ms []*model.BRGEntityBusinessScene
	if err := r.do(ctx).Raw(
		"select `id`, `name`, `path`,`attribute` from af_configuration.object  where type=4 and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityDataCatalogColumn(ctx context.Context, entityId string) (*model.BRGEntityDataCatalogColumn, error) {
	var ms []*model.BRGEntityDataCatalogColumn
	if err := r.do(ctx).Raw(
		"select id,catalog_id,column_name,name_cn,description,\n(case when data_format=0 then \"number\"\n      when data_format=1 then \"char\"\n      when data_format=2 then \"date\"\n      when data_format=3 then \"datetime\"\n      when data_format=4 then \"timestamp\"\n      when data_format=5 then \"bool\"\n      when data_format=6 then \"binary\"\n      else \"\" end ) data_format,\ndata_length,datameta_id,datameta_name,ranges,codeset_id,codeset_name,timestamp_flag from af_data_catalog.t_data_catalog_column and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntitySourceTable(ctx context.Context, entityId string) (*model.BRGEntitySourceTable, error) {
	var ms []*model.BRGEntitySourceTable
	if err := r.do(ctx).Raw(
		"  select df.id, df.name, df.description,tt.f_id metadata_table_id, d.schema schema_name, d.catalog_name ve_catalog_id \n  from af_business.data_collecting_model dcm \n  join af_business.dw_form df on dcm.target_table_id= df.id \n  join af_configuration.datasource d  on d.id  =df.datasource_id \n  join af_metadata.t_table tt on tt.f_name  = df.name  \n  \tand d.data_source_id=tt.f_data_source_id \n  \tand d.`schema`   =tt.f_schema_name\n  where df.version=2 and df.deleted_at=0 and dcm.deleted_at=0 and df.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityDepartment(ctx context.Context, entityId string) (*model.BRGEntityDepartment, error) {
	var ms []*model.BRGEntityDepartment
	if err := r.do(ctx).Raw(
		"SELECT `id`,name FROM af_configuration.`object`  where type in (1,2) and deleted_at=0 and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityStandardTable(ctx context.Context, entityId string) (*model.BRGEntityStandardTable, error) {
	var ms []*model.BRGEntityStandardTable
	if err := r.do(ctx).Raw(
		"select df.id, df.name, df.description,tt.f_id metadata_table_id, d.schema schema_name, d.catalog_name ve_catalog_id \n  from af_business.data_processing_model dpm  \n  join af_business.dw_form df on dpm.target_table_id = df.id  \n  join af_configuration.datasource d  on d.id  =df.datasource_id \n  join af_metadata.t_table tt on tt.f_name   = df.name \n  \tand d.data_source_id =tt.f_data_source_id  \n  \tand d.`schema`  =tt.f_schema_name   \n  where df.version=2 and df.deleted_at=0 and dpm.deleted_at=0 and df.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityBusinessFormStandard(ctx context.Context, entityId string) (*model.BRGEntityBusinessFormStandard, error) {
	var ms []*model.BRGEntityBusinessFormStandard
	if err := r.do(ctx).Raw(
		"select business_form_id as id,business_model_id,name,description,guideline from af_business.business_form_standard where deleted_at=0 and business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityField(ctx context.Context, entityId string) (*model.BRGEntityField, error) {
	var ms []*model.BRGEntityField
	if err := r.do(ctx).Raw(
		"SELECT `field_id`,business_form_id,business_form_name,`name`,name_en,  `data_type`,`data_length`,value_range,field_relationship,ref_id,standard_id  FROM af_business.business_form_field_standard  g  \twhere deleted_at=0 and `field_id`=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityBusinessModel(ctx context.Context, entityId string) (*model.BRGEntityBusinessModel, error) {
	var ms []*model.BRGEntityBusinessModel
	if err := r.do(ctx).Raw(
		"select business_model_id,main_business_id,name,description from af_business.business_model where deleted_at=0 and main_business_id!=\"\" and business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityBusinessIndicator(ctx context.Context, entityId string) (*model.BRGEntityBusinessIndicator, error) {
	var ms []*model.BRGEntityBusinessIndicator
	if err := r.do(ctx).Raw(
		" select id,name,description, business_indicator_id, '' as business_model_id  from  af_data_model.t_technical_indicator tti and id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityFlowchart(ctx context.Context, entityId string) (*model.BRGEntityFlowchart, error) {
	var ms []*model.BRGEntityFlowchart
	if err := r.do(ctx).Raw(
		"SELECT `flowchart_id`,name,description,`business_model_id`,main_business_id   FROM af_business.business_flowchart where deleted_at=0 and flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}
func (r *repo) GetBRGEntityFlowchartNode(ctx context.Context, entityId string) (*model.BRGEntityFlowchartNode, error) {
	var ms []*model.BRGEntityFlowchartNode
	if err := r.do(ctx).Raw(
		"SELECT distinct concat(flowchart_id,mxcell_id) as node_id,flowchart_id,diagram_id,`diagram_name`,name,description,target,source  \t\tFROM af_business.business_flowchart_component  where `type` in (1,5) and concat(flowchart_id,mxcell_id)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) GetBRGEdgeEntityBusinessDomain2EntityThemeDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessDomain2EntityThemeDomain, error) {
	var ms []*model.BRGEdgeEntityBusinessDomain2EntityThemeDomain
	if err := r.do(ctx).Raw(
		"select d.id as domain_id, dt.id as theme_id  \nfrom\taf_main.subject_domain dt \n    join af_main.subject_domain d \n        on d.id=IF(dt.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(dt.path_id, '/', -2), '/', 1), '')\nwhere d.`type`=1 and d.deleted_at=0 and dt.`type`=2 and dt.deleted_at=0 and d.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityThemeDomain2EntityBusinessDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityThemeDomain2EntityBusinessDomain, error) {
	var ms []*model.BRGEdgeEntityThemeDomain2EntityBusinessDomain
	if err := r.do(ctx).Raw(
		"select d.id as domain_id, dt.id as theme_id  \nfrom\taf_main.subject_domain dt \n    join af_main.subject_domain d \n        on d.id=IF(dt.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(dt.path_id, '/', -2), '/', 1), '')\nwhere d.`type`=1 and d.deleted_at=0 and dt.`type`=2 and dt.deleted_at=0 and dt.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityThemeDomain2EntityBusinessObject(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityThemeDomain2EntityBusinessObject, error) {
	var ms []*model.BRGEdgeEntityThemeDomain2EntityBusinessObject
	if err := r.do(ctx).Raw(
		"select dt.id as theme_id, o.id as object_id\nfrom\taf_main.subject_domain dt join af_main.subject_domain o\n    on dt.id=IF(o.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(o.path_id, '/', -2), '/', 1), '')\nwhere dt.`type`=2  and dt.deleted_at=0 and o.`type`=3  and o.deleted_at=0 and dt.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessObject2EntityThemeDomain(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityThemeDomain, error) {
	var ms []*model.BRGEdgeEntityBusinessObject2EntityThemeDomain
	if err := r.do(ctx).Raw(
		"select dt.id as theme_id, o.id as object_id\nfrom\taf_main.subject_domain dt join af_main.subject_domain o\n    on dt.id=IF(o.path_id like '%/%', SUBSTRING_INDEX(SUBSTRING_INDEX(o.path_id, '/', -2), '/', 1), '')\nwhere dt.`type`=2  and dt.deleted_at=0 and o.`type`=3  and o.deleted_at=0 and o.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessObject2EntityBusinessForm(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityBusinessForm, error) {
	var ms []*model.BRGEdgeEntityBusinessObject2EntityBusinessForm
	if err := r.do(ctx).Raw(
		"select bfs.business_form_id as business_form_id, fbor.business_object_id as business_object_id  \n   \t\tfrom af_business.business_form_standard bfs\tjoin af_main.form_business_object_relation fbor \n   \t\t\ton  bfs.business_form_id   = fbor.form_id  \n   \twhere fbor.form_id !=\"\" and fbor.business_object_id !=\"\" and bfs.deleted_at=0 and fbor.business_object_id =?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessObject2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessObject2EntityDataCatalog, error) {
	var ms []*model.BRGEdgeEntityBusinessObject2EntityDataCatalog
	if err := r.do(ctx).Raw(
		"select tdci.info_key as object_id, tdci.catalog_id  from af_data_catalog.t_data_catalog_info tdci\n\twhere tdci.info_type=6 and tdci.info_key=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityDataCatalog2EntityInfoSystem(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityDataCatalog2EntityInfoSystem, error) {
	var ms []*model.BRGEdgeEntityDataCatalog2EntityInfoSystem
	if err := r.do(ctx).Raw(
		"select  tdc.id catalog_id, tdci.info_key info_system_id from af_data_catalog.t_data_catalog tdc\n    join af_data_catalog.t_data_catalog_info tdci on tdci.catalog_id=tdc.id\n    where  tdci.info_type=4 and (tdc.deleted_at=0 or tdc.deleted_at is null) and tdc.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityCatalog2EntityBusinessSceneSource(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityCatalog2EntityBusinessSceneSource, error) {
	var ms []*model.BRGEdgeEntityCatalog2EntityBusinessSceneSource
	if err := r.do(ctx).Raw(
		"select tdc.id catalog_id, tdci.info_key business_scene_id from af_data_catalog.t_data_catalog tdc\n    join af_data_catalog.t_data_catalog_info tdci on tdci.catalog_id=tdc.id\n    where tdci.info_type=3 and (tdc.deleted_at=0 or tdc.deleted_at is null) and tdc.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityCatalog2EntityBusinessSceneRelated(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityCatalog2EntityBusinessSceneRelated, error) {
	var ms []*model.BRGEdgeEntityCatalog2EntityBusinessSceneRelated
	if err := r.do(ctx).Raw(
		"select tdc.id catalog_id, tdci.info_key business_scene_id from af_data_catalog.t_data_catalog tdc\n    join af_data_catalog.t_data_catalog_info tdci on tdci.catalog_id=tdc.id\n    where tdci.info_type=3 and (tdc.deleted_at=0 or tdc.deleted_at is null) and tdc.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityDataCatalog2EntityDataCatalogColumn(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityDataCatalog2EntityDataCatalogColumn, error) {
	var ms []*model.BRGEdgeEntityDataCatalog2EntityDataCatalogColumn
	if err := r.do(ctx).Raw(
		"select tdc.id catalog_id, tdcc.id field_id from af_data_catalog.t_data_catalog tdc  join af_data_catalog.t_data_catalog_column tdcc  on tdc.id=tdcc.catalog_id  where tdc.deleted_at is null  or tdc.deleted_at=0 and tdc.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntitySourceTable2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntitySourceTable2EntityDataCatalog, error) {
	var ms []*model.BRGEdgeEntitySourceTable2EntityDataCatalog
	if err := r.do(ctx).Raw(
		"select df.id source_id,  tdcrm.code code from af_business.data_collecting_model dcm  \n  join af_business.dw_form df on dcm.target_table_id= df.id \n  join af_configuration.datasource d  on d.id =df.datasource_id  \n  join af_metadata.t_table tt on d.data_source_id=tt.f_data_source_id    \n  \tand tt.f_name = df.name\n  \tand d.schema =tt.f_schema_name \n  join af_data_catalog.t_data_catalog_resource_mount tdcrm on  tdcrm.res_id=tt.f_id \n  where df.version=2 and df.deleted_at=0 and dcm.deleted_at=0 and df.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityStandardTable2EntityDataCatalog(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityStandardTable2EntityDataCatalog, error) {
	var ms []*model.BRGEdgeEntityStandardTable2EntityDataCatalog
	if err := r.do(ctx).Raw(
		"select df.id as standard_id,  tdcrm.code as code  from af_business.data_processing_model dpm  \n  join af_business.dw_form df on dpm.target_table_id= df.id \n  join af_configuration.datasource d on d.id =df.datasource_id  \n  join af_metadata.t_table tt on d.data_source_id=tt.f_data_source_id  \n  \tand  tt.f_name = df.name\n  \tand d.schema  =tt.f_schema_name\n  join af_data_catalog.t_data_catalog_resource_mount tdcrm on tdcrm.res_id=tt.f_id \n  where df.version=2 and df.deleted_at=0 and dpm.deleted_at=0 and df.id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessForm2EntityBusinessObject(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityBusinessObject, error) {
	var ms []*model.BRGEdgeEntityBusinessForm2EntityBusinessObject
	if err := r.do(ctx).Raw(
		"select bfs.business_form_id as business_form_id, fbor.business_object_id as business_object_id  \n   \t\tfrom af_business.business_form_standard bfs\tjoin af_main.form_business_object_relation fbor \n   \t\t\ton  bfs.business_form_id   = fbor.form_id  \n   \twhere fbor.form_id !=\"\" and fbor.business_object_id !=\"\" and bfs.deleted_at=0 and bfs.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessFormStandard2Self(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessFormStandard2Self, error) {
	var ms []*model.BRGEdgeEntityBusinessFormStandard2Self
	if err := r.do(ctx).Raw(
		"select p.business_form_id  business_form_id_p, c.business_form_id  business_form_id_c\n\tfrom af_business.business_form_field_standard p\n\tjoin af_business.business_form_field_standard c on p.field_id=c.ref_id\n\twhere p.deleted_at=0 and c.deleted_at=0 and p.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessForm2EntityStandardTable(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityStandardTable, error) {
	var ms []*model.BRGEdgeEntityBusinessForm2EntityStandardTable
	if err := r.do(ctx).Raw(
		"select business_form_id, target_table_id as standard_id from af_business.data_processing_model where deleted_at=0 and business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessForm2EntityBusinessModel(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessForm2EntityBusinessModel, error) {
	var ms []*model.BRGEdgeEntityBusinessForm2EntityBusinessModel
	if err := r.do(ctx).Raw(
		"select bfs.business_form_id, bm.business_model_id  from af_business.business_model bm\t\tjoin af_business.business_form_standard bfs\t\t\ton bm.business_model_id = bfs.business_model_id\t\t\twhere bm.deleted_at =0 and bfs.deleted_at =0 and bm.main_business_id !=\"\" and bfs.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessFormStandard2EntityField(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessFormStandard2EntityField, error) {
	var ms []*model.BRGEdgeEntityBusinessFormStandard2EntityField
	if err := r.do(ctx).Raw(
		"select bfs.business_form_id, bffs.field_id  from af_business.business_form_standard bfs\t  join af_business.business_form_field_standard bffs\t \ton bfs.business_form_id =bffs.business_form_id\t \t  where bfs.deleted_at =0 and bffs.deleted_at=0 and bfs.business_form_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityField2EntityBusinessIndicator(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityField2EntityBusinessIndicator, error) {
	var ms []*model.BRGEdgeEntityField2EntityBusinessIndicator
	if err := r.do(ctx).Raw(
		"select tti.id as `indicator_id`, tts.field_id from af_data_model.t_technical_indicator tti\n \tjoin (select bffs.field_id, tdcc.id \n  from af_business.business_form_standard bfs  \n  join af_business.data_processing_model dpm on bfs.business_form_id=dpm.business_form_id  \n  join af_business.dw_form df on dpm.target_table_id = df.id  \n  join af_configuration.datasource d  on d.id =df.datasource_id \n  join af_metadata.t_table tt on  d.data_source_id=tt.f_data_source_id  \n  \tand  tt.f_name  =df.name\n  \tand d.`schema` =tt.f_schema_name\n  join af_data_catalog.t_data_catalog_resource_mount tdcrm on tdcrm.res_id=tt.f_id \n  join af_data_catalog.t_data_catalog tdc on tdc.code=tdcrm.code \n  join af_business.business_form_field_standard bffs on bffs.business_form_id=bfs.business_form_id \n  join af_data_catalog.t_data_catalog_column tdcc on  tdcc.catalog_id =tdc.id  \n  \t\tand tdcc.column_name=bffs.name_en  \n   where df.version=2 and df.deleted_at=0 and dpm.deleted_at=0 \n   \t\tand bfs.deleted_at=0 and bffs.deleted_at=0 ) tts on \n \ttti.expression  like concat('%',tts.id,'%') or  \n \ttti.time_restrict  like concat('%',tts.id,'%') or \n \ttti.modifier_restrict like concat('%',tts.id,'%') \n \twhere tti.deleted_at=0 or tti.deleted_at is null and tti.id = ?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessModel2EntityBusinessForm(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityBusinessForm, error) {
	var ms []*model.BRGEdgeEntityBusinessModel2EntityBusinessForm
	if err := r.do(ctx).Raw(
		"select bfs.business_form_id, bm.business_model_id  from af_business.business_model bm\t\tjoin af_business.business_form_standard bfs\t\t\ton bm.business_model_id = bfs.business_model_id\t\t\twhere bm.deleted_at =0 and bfs.deleted_at =0 and bm.main_business_id !=\"\" and bm.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessModel2EntityDepartment(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityDepartment, error) {
	var ms []*model.BRGEdgeEntityBusinessModel2EntityDepartment
	if err := r.do(ctx).Raw(
		"select bm.business_model_id, bm.department_id from af_business.business_model bm where bm.deleted_at=0 and department_id !=\"\" and bm.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessModel2EntityFlowchart(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityFlowchart, error) {
	var ms []*model.BRGEdgeEntityBusinessModel2EntityFlowchart
	if err := r.do(ctx).Raw(
		"select bm.business_model_id, bf.flowchart_id  from af_business.business_model bm\t\tjoin af_business.business_flowchart bf\t\ton bm.business_model_id = bf.business_model_id\t\t\twhere bm.deleted_at =0 and bf.deleted_at =0 and bm.main_business_id !=\"\"\tand bm.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessModel2EntityBusinessIndicator(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessModel2EntityBusinessIndicator, error) {
	var ms []*model.BRGEdgeEntityBusinessModel2EntityBusinessIndicator
	if err := r.do(ctx).Raw(
		"select bi.indicator_id, bi.business_model_id  from af_business.business_indicator bi where bi.deleted_at=0 and bi.business_model_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityBusinessIndicator2EntityBusinessModel(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityBusinessIndicator2EntityBusinessModel, error) {
	var ms []*model.BRGEdgeEntityBusinessIndicator2EntityBusinessModel
	if err := r.do(ctx).Raw(
		"select bi.indicator_id, bi.business_model_id  from af_business.business_indicator bi where bi.deleted_at=0 and bi.indicator_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityFlowchart2EntityFlowchart(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchart2EntityFlowchart, error) {
	var ms []*model.BRGEdgeEntityFlowchart2EntityFlowchart
	if err := r.do(ctx).Raw(
		"select bfr.flowchart_id flowchart_id_p, bfr.sub_flowchart_id  flowchart_id_c\n\tfrom af_business.business_flowchart_relationship bfr where bfr.flowchart_id is not null and bfr.sub_flowchart_id is not null and bfr.flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityFlowchart2EntityFlowchartNode(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchart2EntityFlowchartNode, error) {
	var ms []*model.BRGEdgeEntityFlowchart2EntityFlowchartNode
	if err := r.do(ctx).Raw(
		"select distinct bfr.flowchart_id, concat(bfr.flowchart_id, bfr.node_id)  node_id\tfrom  af_business.business_flowchart_relationship bfr  where bfr.node_id !=\"\" and bfr.flowchart_id=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
func (r *repo) GetBRGEdgeEntityFlowchartNode2EntityFlowchartNode(ctx context.Context, entityId string) ([]*model.BRGEdgeEntityFlowchartNode2EntityFlowchartNode, error) {
	var ms []*model.BRGEdgeEntityFlowchartNode2EntityFlowchartNode
	if err := r.do(ctx).Raw(
		"select concat(p.flowchart_id,p.mxcell_id) node_id_p, concat(c.flowchart_id,c.mxcell_id) node_id_c\n\t\tfrom af_business.business_flowchart_component p\n\t\tjoin af_business.business_flowchart_component l on p.mxcell_id=l.source\n\t\tjoin af_business.business_flowchart_component c on l.target=c.mxcell_id\n\t\twhere l.`type`=11 and p.`type` in (1,5) and c.`type` in (1,5) and concat(p.flowchart_id,p.mxcell_id)=?",
		entityId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return ms, nil
}
