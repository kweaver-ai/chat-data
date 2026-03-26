package impl

import (
	"github.com/kweaver-ai/chat-data/sailor-service/domain/comprehension"
)

const (
	ParentFail    = "parent.fail"
	ParentSuccess = "parent.success"
)

type ServiceItem struct {
	Name string `json:"name"`
	Id   int    `json:"id"`
}

var ServiceDomain = []ServiceItem{
	{Id: 1, Name: "信用信息"}, {Id: 2, Name: "金融信息"}, {Id: 3, Name: "医疗健康"}, {Id: 4, Name: "城市交通"},
	{Id: 5, Name: "文化旅游"}, {Id: 6, Name: "行政执法"}, {Id: 7, Name: "党的建设"},
}

var ThinkingMap = make(map[string]comprehension.ThinkingConfig)

func init() {
	for _, think := range ts {
		for _, t := range think.Thinking {
			t.Update(think)
		}
		ThinkingMap[think.Tag] = think
	}
}

func SetGlobalADGraphSQLSearchID(id string) {
	//config := settings.GetConfig()
	//config.AnyDataConf.SearchServiceID = id
}

func Configs() []comprehension.ThinkingConfig {
	return ts
}

var ts = []comprehension.ThinkingConfig{
	{
		Tag:       "时间范围",
		ResultKey: "${time_range_result}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      时间字段过滤,
			},
			{
				BreakThrough: true,
				LoopDataKey:  "time_column_slice",
				Inputs: []string{
					"${standard_table_info.ve_catalog_id}",
					"${standard_table_info.schema_name}",
					"${standard_table_info.name}",
					"${time_column.column_name}",
				},
				Process: 时间字段数据范围获取,
			},
			{
				BreakThrough: true,
				Inputs: []string{
					"${time_range_slice}",
				},
				Process: 时间字段最大数据范围,
			},
		},
	},
	{
		Tag:           "时间字段理解",
		CacheThinking: "查询目录信息项,单纯时间字段理解,时间字段加指标理解",
		CacheKey:      ColumnInfoCacheKeys,
		ResultKey:     "${column_comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      时间字段过滤,
			},
			{
				BreakThrough: false,
				LoopDataKey:  "${time_column_slice}",
				Inputs: []string{
					"${standard_table_info.id}",
					"${time_column.column_name}",
				},
				Process: 标准表字段查询指标,
				Child: []*comprehension.Thinking{
					{
						Condition:    ParentFail,
						BreakThrough: false,
						Inputs: []string{
							"${catalog_info.title}",
							"${time_column}",
						},
						Process: 单纯时间字段理解,
					},
					{
						Condition:    ParentSuccess,
						BreakThrough: false,
						Inputs: []string{
							"${catalog_info.title}",
							"${time_column}",
							"${indicator_slice}",
						},
						Process: 时间字段加指标理解,
					},
				},
			},
		},
	},
	{
		Tag:       "空间范围",
		ResultKey: "${space_range_result}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      空间字段过滤,
			},
			{
				BreakThrough: true,
				LoopDataKey:  "${space_column_slice}",
				Inputs: []string{
					"${standard_table_info.ve_catalog_id}",
					"${standard_table_info.schema_name}",
					"${standard_table_info.name}",
					"${space_column.column_name}",
				},
				Process: 空间字段数据范围获取,
			},
			{
				BreakThrough: true,
				Process:      空间字段最大数据范围获取,
			},
		},
	},
	{
		Tag:           "空间字段理解",
		CacheThinking: "查询目录信息项,空间字段加指标理解,单纯空间字段理解",
		CacheKey:      ColumnInfoCacheKeys,
		ResultKey:     "${column_comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      空间字段过滤,
			},
			{
				BreakThrough: false,
				LoopDataKey:  "${space_column_slice}",
				Inputs: []string{
					"${standard_table_info.id}",
					"${space_column.column_name}",
				},
				Process: 标准表字段查询指标,
				Child: []*comprehension.Thinking{
					{
						Condition:    ParentFail,
						BreakThrough: false,
						Inputs: []string{
							"${catalog_info.title}",
							"${space_column}",
						},
						Process: 单纯空间字段理解,
					},
					{
						Condition:    ParentSuccess,
						BreakThrough: false,
						Inputs: []string{
							"${catalog_info.title}",
							"${space_column}",
							"${indicator_slice}",
						},
						Process: 空间字段加指标理解,
					},
				},
			},
		},
	},
	{
		Tag:           "业务维度",
		CacheThinking: "查询目录信息项,重要字段加指标理解",
		CacheKey:      ColumnInfoCacheKeys,
		ResultKey:     "${column_comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				LoopDataKey:  "${column_info_slice}",
				Process:      标准表字段查询指标,
				Inputs: []string{
					"${standard_table_info.id}",
					"${column_info.column_name}",
				},
				Child: []*comprehension.Thinking{
					{
						Condition:    ParentSuccess,
						BreakThrough: false,
						Inputs: []string{
							"${catalog_info.title}",
							"${column_info}",
							"${indicator_slice}",
						},
						Process: 重要字段加指标理解,
					},
				},
			},
		},
	},
	{
		Tag:           "复合表达",
		CacheThinking: "AD引用业务表查询数据资源编目,AD查询到共同的指标_根据关联编目给出复合表达,AD没有查询到共同的指标_根据关联编目给出复合表达",
		CacheKey:      CatalogCacheKeys,
		ResultKey:     "${comprehension_results}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      AD数据资源目录查询引用业务表,
			},
			{
				BreakThrough: true,
				Process:      AD引用业务表查询数据资源编目,
				Inputs: []string{
					"${business_form_standard_slice.id}|form_ids",
				},
			},
			{
				BreakThrough: false,
				Process:      AD数资源目录查询业务指标,
			},
			{
				BreakThrough: false,
				Process:      AD关联数据资源目录的指定指标,
				Inputs: []string{
					"${data_catalog_slice.id}|catalog_ids",
					"${business_indicator1_slice.indicator_id}|indicator_ids",
				},
				Child: []*comprehension.Thinking{
					{
						Condition:    ParentSuccess,
						BreakThrough: false,
						LoopDataKey:  "${business_indicator2_slice}",
						Inputs: []string{
							"${business_indicator2.indicator_id}|indicator_id",
							"${data_catalog_slice.id}|catalog_ids",
							"${catalog_id}",
						},
						Process: AD查询到共同的指标_反查数据编目,
						Child: []*comprehension.Thinking{
							{
								BreakThrough: true,
								Process:      AD查询到共同的指标_根据关联编目给出复合表达,
								Inputs: []string{
									"${catalog_info.title}",
									"${data_catalog2_slice}",
									"${business_indicator2}",
								},
							},
						},
					},
					{
						BreakThrough:   true,
						UseLastResult:  true,
						LoopDataKey:    "${data_catalog_slice}",
						FilterPrevious: "${data_catalog2_slice.id}",
						Inputs: []string{
							"${catalog_info.title}",
							"${data_catalog}",
						},
						Process: AD没有查询到共同的指标_根据关联编目给出复合表达,
					},
				},
			},
		},
	},
	{
		Tag:       "服务领域",
		ResultKey: "${choices}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: false,
				Process:      目录查询业务对象信息,
			},
			{
				BreakThrough: false,
				Process:      目录查询来源业务场景,
			},
			{
				BreakThrough: false,
				Process:      目录查询关联业务场景,
			},
			{
				BreakThrough: false,
				Process:      服务领域识别,
				Inputs: []string{
					"${catalog_info.title}",
					"${business_object_slice.name}|business_object_name_slice",
					"${related_business_scene_slice}",
					"${source_business_scene_slice}",
					"${service_domain}",
					"${column_info_slice}",
				},
			},
		},
	},
	{
		Tag:       "服务范围",
		ResultKey: "${comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: false,
				Process:      目录查询业务对象信息,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      目录查询所属部门,
			},
			{
				BreakThrough: false,
				Inputs: []string{
					"${catalog_info.title}",
					"${department_info}",
					"${business_object_slice.name}|business_object_name_slice",
				},
				Process: 部门服务范围,
			},
			{
				BreakThrough: true,
				Process:      空间字段过滤,
			},
			{
				BreakThrough: true,
				LoopDataKey:  "${space_column_slice}",
				Inputs: []string{
					"${standard_table_info.ve_catalog_id}",
					"${standard_table_info.schema_name}",
					"${standard_table_info.name}",
					"${space_column.column_name}",
				},
				Process: 空间字段数据范围获取,
			},
			{
				BreakThrough: true,
				Process:      空间字段最大数据范围获取,
				Child: []*comprehension.Thinking{
					{
						Condition:    ParentSuccess,
						BreakThrough: false,
						Process:      识别空间字段服务范围,
						Inputs: []string{
							"${catalog_info.title}",
							"${space_range_result}",
						},
					},
				},
			},
		},
	},
	{
		Tag:       "正面支撑",
		ResultKey: "${comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      正面表达字段过滤,
			},
			{
				BreakThrough: false,
				LoopDataKey:  "${positive_column_info_slice}",
				Process:      AD标准表字段查询业务表字段,
				Inputs: []string{
					"${positive_column_info.column_name}",
					"${standard_table_info.id}|table_id",
				},
				Child: []*comprehension.Thinking{
					{
						BreakThrough: false,
						Process:      标准表字段查询指标,
						Inputs: []string{
							"${standard_table_info.id}",
							"${business_form_field.name_en}|column_name",
						},
					},
					{
						BreakThrough: false,
						Process:      AD业务表字段查询主干业务,
						Inputs: []string{
							"${business_form_field.business_form_id}|id",
						},
					},
					{
						BreakThrough: false,
						Process:      AD业务表字段查询业务流程,
						Inputs: []string{
							"${business_form_field.business_form_id}|id",
						},
					},
					{
						BreakThrough: true,
						Process:      根据数据识别正面表达,
						Inputs: []string{
							"${catalog_info.title}",
							"${business_form_field}",
							"${business_indicator_slice}",
							"${business_flowchart_slice}",
							"${business_model_slice}",
						},
					},
				},
			},
		},
	},
	{
		Tag:       "负面支撑",
		ResultKey: "${comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      负面表达字段过滤,
			},
			{
				BreakThrough: false,
				LoopDataKey:  "${negative_column_info_slice}",
				Process:      AD标准表字段查询业务表字段,
				Inputs: []string{
					"${negative_column_info.column_name}",
					"${standard_table_info.id}|table_id",
				},
				Child: []*comprehension.Thinking{
					{
						BreakThrough: false,
						Process:      标准表字段查询指标,
						Inputs: []string{
							"${standard_table_info.id}",
							"${business_form_field.name_en}|column_name",
						},
					},
					{
						BreakThrough: false,
						Process:      AD业务表字段查询主干业务,
						Inputs: []string{
							"${business_form_field.business_form_id}|id",
						},
					},
					{
						BreakThrough: false,
						Process:      AD业务表字段查询业务流程,
						Inputs: []string{
							"${business_form_field.business_form_id}|id",
						},
					},
					{
						BreakThrough: true,
						Process:      根据数据得出负面支撑,
						Inputs: []string{
							"${catalog_info.title}",
							"${business_form_field}",
							"${indicator_slice}",
							"${business_flowchart_slice}",
							"${business_model_slice}",
						},
					},
				},
			},
		},
	},
	{
		Tag:       "保护控制",
		ResultKey: "${comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      目录查询业务对象信息,
			},
			{
				BreakThrough: true,
				Process:      负面表达字段过滤,
			},
			{
				BreakThrough: true,
				Process:      AD多个标准表字段查询业务表字段,
				Inputs: []string{
					"${negative_column_info_slice.column_name} | column_name_slice",
					"${standard_table_info.id}|table_id",
				},
				Child: []*comprehension.Thinking{
					{
						BreakThrough: true,
						LoopDataKey:  "${business_form_field_slice}",
						Process:      AD业务表字段查询业务表_无业务对象关系,
						Inputs: []string{
							"${business_form_field.field_id}|ref_id",
							"${business_object_slice.name}|business_object_name_slice",
						},
						Child: []*comprehension.Thinking{
							{
								BreakThrough: false,
								LoopDataKey:  "${business_form_standard_slice}",
								Process:      标准表被引用字段查询指标,
								Inputs: []string{
									"${business_form_field.field_id}",
									"${business_form_standard.id}|business_form_id",
								},
							},
							{
								BreakThrough: false,
								LoopDataKey:  "${business_form_standard_slice}",
								Process:      AD业务表字段查询主干业务,
								Inputs: []string{
									"${business_form_standard.id}",
								},
							},
							{
								BreakThrough: false,
								LoopDataKey:  "${business_form_standard_slice}",
								Process:      AD业务表字段查询业务流程,
								Inputs: []string{
									"${business_form_standard.id}|id",
								},
							},
							{
								BreakThrough: true,
								Process:      根据数据识别保护限制,
								Inputs: []string{
									"${catalog_info.title}",
									"${business_form_field}",
									"${business_object_slice.name} | business_object_name_slice",
									"${business_indicator_slice}",
									"${business_flowchart_slice}",
									"${business_model_slice}",
								},
							},
						},
					},
				},
			},
		},
	},
	{
		Tag:       "促进推动",
		ResultKey: "${comprehension}",
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录信息,
			},
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Process:      目录查询业务对象信息,
			},
			{
				BreakThrough: true,
				Process:      正面表达字段过滤,
			},
			{
				BreakThrough: true,
				Process:      AD多个标准表字段查询业务表字段,
				Inputs: []string{
					"${positive_column_info_slice.column_name} | column_name_slice",
					"${standard_table_info.id}|table_id",
				},
			},
			{
				BreakThrough: true,
				LoopDataKey:  "${business_form_field_slice}",
				Process:      AD业务表字段查询业务表_无业务对象关系,
				Inputs: []string{
					"${business_form_field.field_id}|ref_id",
					"${business_object_slice.name} | business_object_name_slice",
				},
				Child: []*comprehension.Thinking{
					{
						BreakThrough: false,
						LoopDataKey:  "${business_form_standard_slice}",
						Process:      标准表被引用字段查询指标,
						Inputs: []string{
							"${business_form_field.field_id}",
							"${business_form_standard.id}|business_form_id",
						},
					},
					{
						BreakThrough: false,
						LoopDataKey:  "${business_form_standard_slice}",
						Process:      AD业务表字段查询主干业务,
						Inputs: []string{
							"${business_form_standard.id}",
						},
					},
					{
						BreakThrough: false,
						LoopDataKey:  "${business_form_standard_slice}",
						Process:      AD业务表字段查询业务流程,
						Inputs: []string{
							"${business_form_standard.id}",
						},
					},
					{
						BreakThrough: true,
						Process:      根据数据识别促进推动,
						Inputs: []string{
							"${catalog_info.title}",
							"${business_form_field}",
							"${business_object_slice.name} | business_object_name_slice",
							"${business_indicator_slice}",
							"${business_flowchart_slice}",
							"${business_model_slice}",
						},
					},
				},
			},
		},
	},
	{
		Tag:           "字段注释",
		ResultKey:     "${column_comment}",
		CacheThinking: "查询目录信息项,标准表字段加注释",
		CacheKey:      ColumnCommentCacheKeys,
		Thinking: []*comprehension.Thinking{
			{
				BreakThrough: true,
				Process:      查询目录标准表,
			},
			{
				BreakThrough: true,
				Process:      查询目录信息项,
			},
			{
				BreakThrough: true,
				Inputs: []string{
					"${column_info_slice}",
					"${standard_table_info.name}|table_name",
				},
				Process: 标准表字段加注释,
			},
		},
	},
}
