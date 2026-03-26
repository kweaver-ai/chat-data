package impl

import (
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/collection"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension/impl/concepts"
)

const (
	OpenAPIProcess = "openapi"
	ADProcess      = "ad"
	EngineProcess  = "engine"
	LogicTools     = "tools"
)
const (
	ColumnInfoCacheKeys    = "id,name_cn,column_info"
	ColumnCommentCacheKeys = "id,column_name,column_comment"
	CatalogCacheKeys       = "id,title,catalog_infos"
)

var 目录查询所属部门 = comprehension.Process{
	Desc: "目录查询所属部门",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.Catalog2DepartmentInfo,
	},
	Format: `{"department_info":{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"部门名称"}}`,
}

var 目录查询来源业务场景 = comprehension.Process{
	Desc: "目录查询关联业务场景",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.Catalog2SourceBusinessScene,
	},
	Format: `{"source_business_scene_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务场景名称"}]}`,
}

var 目录查询关联业务场景 = comprehension.Process{
	Desc: "目录查询关联业务场景",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.Catalog2RelatedBusinessScene,
	},
	Format: `{"related_business_scene_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务场景名称"}]}`,
}

var 目录查询业务对象信息 = comprehension.Process{
	Desc: "目录查询业务对象信息",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.Catalog2BusinessObjects,
	},
	Format: `{"business_object_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务对象名称"}]}`,
}

var 查询目录信息 = comprehension.Process{
	Desc: "查询目录信息",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.CatalogInfo,
	},
	Format: `{"catalog_info":{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","code":"目录编码",` +
		`"title":"目录名称","description":"资源目录描述","theme_name":"主题分类名称","group_name":"数据资源目录分类名称"}}`,
}

var 查询目录信息项 = comprehension.Process{
	Desc: "查询目录信息项",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.CatalogFields,
	},
	Format: `{"column_info_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name_cn":"创建日期",` +
		`"column_name":"CreatedDate","data_format":"char"}]}`,
}

var 查询目录标准表 = comprehension.Process{
	Desc: "查询目录标准表",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.Catalog2StandardTable,
	},
	Format: `{"standard_table_info":{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"标准标名称",` +
		`"description":"表描述","metadata_table_id":"对应元数据平台的table_id","schema_id":"schema唯一标识",` +
		`"schema_name":"schema名称","data_source_id":"数据源唯一标识","data_source_name":"数据源名称",` +
		`"ve_catalog_id":"数据源在虚拟化引擎的资源ID","table_rows":"表数据量"}}`,
}

var 时间字段过滤 = comprehension.Process{
	Desc: "时间字段过滤",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id",
		Question: `请严格按照json报文回复：从表字段中返回所有表示时间的字段，不要返回不相关的字段，没有就返回空数组，` +
			`表字段是：${column_info_slice},答案放在time_column_slice字段里面, 报文格式为：${format}`,
	},
	Format: `{"time_column_slice":[{"name_cn":"创建日期","column_name":"CreatedDate","data_format":"char"}]}`,
}

var 时间字段数据范围获取 = comprehension.Process{
	Desc: "时间字段数据范围获取",
	Way:  EngineProcess,
	Config: comprehension.VirtualEngineConfig{
		SQL: concepts.SearchTimeRange,
	},
	Format: `{"time_range_slice": [{"start":"${min_time}","end":"${max_time}"}]}`,
}

var 时间字段最大数据范围 = comprehension.Process{
	Desc: "时间字段最大数据范围获取",
	Way:  LogicTools,
	Config: comprehension.LogicHelperConfig{
		FuncStr: collection.MaxTimeRangeStr,
	},
	Format: `{"time_range_result":[{"start":"min_time","end":"max_time"}]}`,
}

var 标准表字段查询指标 = comprehension.Process{
	Desc: "标准表字段查询指标",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.StandardTable2Indicators,
	},
	Format: `{"indicator_slice":[{"name":"指标名称","description":"指标描述"}]}`,
}

var 标准表被引用字段查询指标 = comprehension.Process{
	Desc: "标准表字段查询指标",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.BusinessRefId2Indicators,
	},
	Format: `{"business_indicator_slice":[{"name":"指标名称","description":"指标描述"}]}`,
}

var 单纯时间字段理解 = comprehension.Process{
	Desc: "单纯时间字段理解",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文格式回复：给出数据库表时间字段的功能， 数据库表名称是：${title},` +
			`数据库表时间字段是:${time_column}, 答案放在column_comprehension字段里面, 报文格式为:${format}`,
	},
	Format: `{"column_comprehension":[{"column_info": {"name_cn": "字段中文名称","data_format": "number"},"comprehension": "时间字段功能描述"}]}`,
}
var 时间字段加指标理解 = comprehension.Process{
	Desc: "时间字段加指标理解",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文格式回复：结合指标理解数据库表时间字段的功能，指标是：${indicator_slice}, 数据库表名称是：${title},` +
			` 数据库表时间字段是：${time_column},  答案放在column_comprehension字段里面, 报文格式为：${format}`,
	},
	Format: `{"column_comprehension":[{"column_info": {"name_cn": "字段中文名称","data_format": "number"},"comprehension": "时间字段功能描述"}]}`,
}
var 空间字段过滤 = comprehension.Process{
	Desc: "空间字段过滤",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		MaxTokenSize:   1500,
		OmitemptyField: "id",
		Question: `请严格按照json报文回复：现在有表字段${column_info_slice},其中可能含有表示空间或者地域的字段，如果有，找出并返回，没有就返回空数组，` +
			`答案放在space_column_slice字段里面, 报文格式为：${format}`,
	},
	Format: `{"space_column_slice":[{"name_cn":"字段中文名","column_name":"字段英文名","data_format":"char"}]}`,
}

var 空间字段数据范围获取 = comprehension.Process{
	Desc: "空间字段数据范围获取",
	Way:  EngineProcess,
	Config: comprehension.VirtualEngineConfig{
		SQL: concepts.SearchDomainRange,
	},
	Format: `{"space_range_slice":[{"space":"${space_col}"}]}`,
}

var 空间字段最大数据范围获取 = comprehension.Process{
	Desc: "空间字段最大数据范围获取",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		Question: `请严格按照json报文回复：case1: 空间值:【广州市，汕头市】，得出最大空间范围值是广东各省市；` +
			`case2:空间值:【广东广州市，安徽合肥市】，得出最大空间范围值是全国各个城市；` +
			`case3:空间值:【上海市浦东新区，上海市黄浦区】得出最大空间范围值是：上海市各市区；根据上面描述回答下面问题。` +
			`查询结果列表中每条查询结果都可能包含了空间范围值，识别表示空间、地域的值，` +
			`匹配其中的某一种case，回答最大空间范围值，结果只有一个值。` +
			`查询结果是：${space_range_slice},  将答案替换报文格式中的space_range返回, 报文格式为：${format}`,
	},
	Format: `{"space_range_result":["space_range"]}`,
}

var 单纯空间字段理解 = comprehension.Process{
	Desc: "单纯空间字段理解",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文格式回复：理解数据库表字段的含义， 数据库表名称是：${title}, 数据库表字段是:${space_column}, ` +
			` 答案放在column_comprehension字段里面, 报文格式为:${format}`,
	},
	Format: `{"column_comprehension":[{"column_info": {"name_cn": "字段中文名称","data_type": "char"},"comprehension": "这是一个名字"}]}`,
}

var 空间字段加指标理解 = comprehension.Process{
	Desc: "空间字段加指标理解",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文格式回复：结合指标理解数据库表字段的含义，指标是：${indicator_slice}, ` +
			`数据库表名称是：${title}, 数据库表字段是：${space_column},  答案放在column_comprehension字段里面, 报文格式为：${format}`,
	},
	Format: `{"column_comprehension":[{"column_info": {"name_cn": "字段中文名称","data_type": "char"},"comprehension": "这是一个名字"}]}`,
}

var 重要字段加指标理解 = comprehension.Process{
	Desc: "重要字段加指标理解",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文格式回复：结合一条或者多条指标理解数据库表字段的含义，` +
			`指标是：${indicator_slice}, 数据库表名称是：${title}, 数据库表字段是：${column_info}, ` +
			`答案放在column_comprehension字段里面, 报文格式为：${format}`,
	},
	Format: `{"column_comprehension":[{"column_info": {"name_cn": "字段中文名称","data_type": "char"},"comprehension": "这是一个名字"}]}`,
}

var AD数据资源目录查询引用业务表 = comprehension.Process{
	Desc: "AD数据资源目录查询引用业务表",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.DataCatalog2RelatedBusinessForm,
	},
	Format: `{"business_form_standard_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务表名称","description":"业务表描述"}]}`,
}

var AD引用业务表查询数据资源编目 = comprehension.Process{
	Desc: "AD引用业务表查询数据资源编目",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.BusinessForm2DataCatalog,
	},
	Format: `{"data_catalog_slice":[{"id":"469979324087293346","code":"aaa/111","title":"编目名称","description":"编目描述"}]}`,
}

var AD数资源目录查询业务指标 = comprehension.Process{
	Desc: "AD数资源目录查询业务指标",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.DataCatalog2Indicator,
	},
	Format: `{"business_indicator1_slice":[{"indicator_id":"46888e403f","name":"指标名称","description":"指标描述"}]}`,
}

var AD关联数据资源目录的指定指标 = comprehension.Process{
	Desc: "AD关联数据资源目录的指定指标",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.DataCatalog2SomeIndicator,
	},
	Format: `{"business_indicator2_slice":[{"indicator_id":"46888e403f","name":"指标名称","description":"指标描述"}]}`,
}

var AD查询到共同的指标_反查数据编目 = comprehension.Process{
	Desc: "AD查询到共同的指标，反查数据编目",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.CommonIndicator2DataCatalog,
	},
	Format: `{"data_catalog2_slice":[{"id":"469979324087293346","code":"aaa/111","title":"编目名称","description":"编目描述"}]}`,
}

var AD查询到共同的指标_根据关联编目给出复合表达 = comprehension.Process{
	Desc: "AD查询到共同的指标_根据关联编目给出复合表达",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文回复。指标是使用一个或者多个表的得出的统计数据。` +
			`假设有数据目录1:人口信息，关联的数据目录2是: 生育登记` +
			`两个目录共同支撑的指标就是：当地年度生育率。` +
			`那么数据目录1的复合表达就是：联合【生育登记】得出该地的生育率。` +
			`根据上述回答问题：现在有数据目录：${title},其关联的数据目录是：${data_catalog2_slice},` +
			`两者共同支撑的业务指标是：${business_indicator2}，` +
			`请给出对该数据目录的复合表达, 答案放在comprehension字段里面, ` +
			`关联的数据目录放在catalog_infos里面，不要输出现有的数据目录${title}的信息，报文格式为：${format}`,
	},
	Format: `{"comprehension_results":[{"comprehension":"复合表达","catalog_infos":[{"code":"aaa/111","title":"编目名称","description":"编目描述"}]}]}`,
}

var AD没有查询到共同的指标_根据关联编目给出复合表达 = comprehension.Process{
	Desc: "AD没有查询到共同的指标_根据关联编目给出复合表达",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `请严格按照json报文回复。` +
			`现在有数据目录：${title},其关联的数据目录是：${data_catalog},` +
			`请结合关联数据目录，给出对该数据目录的功能描述, 答案放在comprehension字段里面, ` +
			`关联的数据目录放在catalog_infos里面，不要输出现有的数据目录${title}的信息，报文格式为：${format}。`,
	},
	Format: `{"comprehension_results":[{"comprehension":"复合表达","catalog_infos":[{"code":"aaa/111","title":"编目名称","description":"编目描述"}]}]}`,
}

var 服务领域识别 = comprehension.Process{
	Desc: "服务领域识别",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,column_name",
		Question: `给定的服务领域有：${service_domain}，` +
			`您的任务是就给定的数据目录信息可能属于哪些给定的服务领悟给出建议，请严格按照json报文格式回复，` +
			`建议放在choices字段里面，报文格式为：：${format}。` +
			`给定的数据目录信息如下：` +
			`名称：${title}；` +
			`关联业务场景：${related_business_scene_slice}；` +
			`来源业务场景：${source_business_scene_slice}；` +
			`数据目录的信息项是:${column_info_slice}；` +
			`关联业务对象：${business_object_name_slice}；`,
	},
	Format: `{"choices":[[{"id":1,"name":"领域"}]]}`,
}

var 部门服务范围 = comprehension.Process{
	Desc: "部门服务范围",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,path",
		Question: `结合目录的名字、部门信息、业务对象理解该编目的服务范围；` +
			`使用："服务[部门信息]部门的[业务对象]",句式回答。` +
			`使用动词开头，回答要灵活，让人容易理解，不要包含双引号。` +
			`目录的名字是：${title}; 部门路径是:${department_info};业务对象是${business_object_name_slice},` +
			`如果业务对象是空，那就返回空，答案替换报文格式中的service_domain输出,请严格按照json报文格式回复, 报文格式为：${format}。`,
	},
	Format: `{"comprehension":["service_domain"]}`,
}

var 识别空间字段服务范围 = comprehension.Process{
	Desc: "识别空间字段服务范围",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		Question: `结合目录的名字、编目数据的空间范围最大值，理解该目录的服务范围；` +
			`使用："包含[最大空间范围值]内[目录]数据",句式回答。` +
			`使用动词开头，回答要灵活，让人容易理解，不要包含双引号。` +
			`目录的名字是：${title};空间范围最大值是:${space_range_result};` +
			`请严格按照json报文格式回复,答案替换报文格式中的service_domain输出, 报文格式为：${format}。`,
	},
	Format: `{"comprehension":["service_domain"]}`,
}
var 正面表达字段过滤 = comprehension.Process{
	Desc: "正面表达字段过滤",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id",
		Question: `请严格按照json报文回复：从表字段中返回5个和正面或者中性表达的字段，没有就返回空数组，表字段是：${column_info_slice},` +
			` 答案放在positive_column_info_slice字段里面, 报文格式为：${format}`,
	},
	Format: `{"positive_column_info_slice":[{"name_cn":"创建日期","column_name":"CreatedDate","data_format":"char"}]}`,
}

var AD标准表字段查询业务表字段 = comprehension.Process{
	Desc: "AD标准表字段查询业务表字段",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.StandardField2BusinessFormField,
	},
	Format: `{"business_form_field":{"field_id":"业务表字段","name":"业务字段中文名称",` +
		`"business_form_id":"6ee4dce3-ad84-4cd2-9704-ba182412a952","name_en":"field_en_name","data_type":"数据类型"}}`,
}

var AD多个标准表字段查询业务表字段 = comprehension.Process{
	Desc: "AD多个标准表字段查询业务表字段",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.StandardFields2BusinessFormFields,
	},
	Format: `{"business_form_field_slice":[{"field_id":"业务表字段","name":"业务字段中文名称",` +
		`"business_form_id":"6ee4dce3-ad84-4cd2-9704-ba182412a952","name_en":"field_en_name","data_type":"数据类型"}]}`,
}

var AD业务表字段查询主干业务 = comprehension.Process{
	Desc: "AD业务表字段查询主干业务",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.BusinessForm2BusinessModel,
	},
	Format: `{"business_model_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"主干业务名称","description":"主干业务描述"}]}`,
}

var AD业务表字段查询业务流程 = comprehension.Process{
	Desc: "AD业务表字段查询业务流程",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.BusinessForm2BusinessFlowchart,
	},
	Format: `{"business_flowchart_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务流程名称","description":"业务流程描述"}]}`,
}

var 根据数据识别正面表达 = comprehension.Process{
	Desc: "根据数据识别正面表达",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,name_en",
		Question: `请严格按照json报文回复：根据表名和表字段，结合标准表关联指标，关联的主干业务，还有业务流程，给出该表的正面支撑，` +
			`比如，如果表是人口信息表，结合人口年龄字段得出：可以支持了解当地的人口年龄结构。` +
			`标准表名是${title}，表字段是：${business_form_field},关联的指标是${business_indicator_slice},` +
			`关联的主干业务是${business_model_slice}, 关联的业务流程是${business_flowchart_slice},` +
			`答案替换报文格式中的'正面支撑'返回, 报文格式为：${format}`,
	},
	Format: `{"comprehension":["正面支撑"]}`,
}

var 负面表达字段过滤 = comprehension.Process{
	Desc: "负面表达字段过滤",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id",
		Question: `请严格按照json报文回复：负面(negative，downside)，通常是指不好的，坏的, 消极的一面。` +
			`数据表有很多字段，结合表名称，每个字段都有一个或者多个功能，这些功能有负面的，有正面的。` +
			`根据上面描述回答：有一张数据表名称是：${title}, 表字段如下：${column_info_slice}` +
			`返回5个有负面功能的字段，答案放在column_info_slice字段里面, 没有就返回空， 报文格式为：${format}`,
	},
	Format: `{"negative_column_info_slice":[{"name_cn":"创建日期","column_name":"CreatedDate","data_format":"char"}]}`,
}

var 根据数据得出负面支撑 = comprehension.Process{
	Desc: "根据数据得出负面支撑",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,name_en",
		Question: `请严格按照json报文回复：` +
			`负面(negative，downside)，通常是指不好的，坏的, 消极的一面。` +
			`数据表有很多字段，结合表名称，每个字段都有一个或者多个功能，这些功能有负面的，有正面的。` +
			`指标是某个数据表字段的统计指标，是表字段的实际应用，` +
			`业务流程是描述表在数据治理过程的流程，主干业务是指标，业务表，业务指标的集合。` +
			`负面支撑就是该表的有负面表达的功能。根据上面描述回答问题：` +
			`根据表名和负面表达的表字段，给出表的负面支撑，如果有标准表关联的指标，关联的主干业务，还有业务流程，` +
			`联合关联数据给出关于该表的负面支撑，如果关联数据有空的，忽略该关联数据。` +
			`标准表名是${title}，负面表达的表字段是：${business_form_field},关联的指标是${indicator_slice},` +
			`关联的主干业务是${business_model_slice}, 关联的业务流程是${business_flowchart_slice},` +
			`没有负面表达的的表字段就返回空，答案不要出现'负面支撑'关键字，答案替换报文格式中的'负面支撑'返回, 报文格式为：${format}`,
	},
	Format: `{"comprehension":["负面支撑"]}`,
}

var AD业务表字段查询业务表_无业务对象关系 = comprehension.Process{
	Desc: "AD业务表字段查询业务表_无业务对象关系",
	Way:  ADProcess,
	Config: comprehension.AnydataConfig{
		SQL: concepts.BusinessFormField2BusinessFormWithoutBusinessObject,
	},
	Format: `{"business_form_standard_slice":[{"id":"eb87ffdc-9e9f-492a-9eda-4fce012c6237","name":"业务表名称","description":"业务表描述"}]}`,
}

var 根据数据识别保护限制 = comprehension.Process{
	Desc: "根据数据识别保护限制",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,name_en",
		Question: `请严格按照json报文回复。存在一个标准表，` +
			`该标准表的部分字段被其他表引用，通过该引用表关联的指标，关联的主干业务，关联的业务流程` +
			`我们可以得出该标准表的信息可以对一些业务对象（业务活动）有保护控制功能。` +
			`比如人口信息表，被引用表是社保参保表，被引用的字段是年龄，业务对象是参保，` +
			`可以得出的保护控制是：限制参保人年龄。` +
			`标准表名是${title}，关联的指标是${business_indicator_slice},` +
			`业务对象是${business_object_name_slice},被引用的字段是${business_form_field}，` +
			`关联的主干业务是${business_model_slice}, 关联的业务流程是${business_flowchart_slice},` +
			`给出有关该标准表的保护控制能力,答案替换报文中的'保护控制'返回, 报文格式为：${format}`,
	},
	Format: `{"comprehension":["保护控制"]}`,
}

var 根据数据识别促进推动 = comprehension.Process{
	Desc: "根据数据识别促进推动",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id,name_en",
		Question: `请严格按照json报文回复。存在一个标准表，` +
			`该标准表的部分字段被其他表引用，通过该引用表关联的指标，关联的主干业务，关联的业务流程` +
			`我们可以得出该标准表的信息可以对一些业务对象（业务活动）有促进推动功能。` +
			`比如人口信息表，被引用表是社保参保表，被引用的字段是年龄，业务对象是参保，` +
			`可以得出的促进推动是：分析未参保人年龄段，推动更多符合条件的人参保。` +
			`标准表名是${title}，关联的指标是${business_indicator_slice},` +
			`业务对象是${business_object_name_slice},被引用的字段是${business_form_field}，` +
			`关联的主干业务是${business_model_slice}, 关联的业务流程是${business_flowchart_slice},` +
			`给出有关该标准表的促进推动能力,答案替换报文中的'促进推动'返回, 报文格式为：${format}`,
	},
	Format: `{"comprehension":["促进推动"]}`,
}

var 标准表字段加注释 = comprehension.Process{
	Desc: "标准表字段加注释",
	Way:  OpenAPIProcess,
	Config: comprehension.OpenapiConfig{
		OmitemptyField: "id",
		Question: `请严格按照json报文回复：结合表名称和字段，理解每个字段的意思，表名称是：${table_name}，` +
			`表字段是：${column_info_slice},答案放在ai_comment字段里面, 报文格式为：${format}。`,
	},
	Format: `{"column_comment":[{"column_name": "column_name","name_cn": "字段中文名称","data_type": "char","ai_comment": "这是一个名字"}]}`,
}
