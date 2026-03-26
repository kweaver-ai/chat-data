package data_change_mq

import (
	"context"
	"fmt"
	"strconv"

	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/configuration_center"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/es_subject_model"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/gorm/knowledge_datasource"
	ad_proxy "github.com/kweaver-ai/chat-data/sailor-service/adapter/driven/knowledge_network"
	"github.com/kweaver-ai/chat-data/sailor-service/common/form_validator"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"

	//domain "github.com/kweaver-ai/chat-data/sailor-service/domain/data_catalog"
	"encoding/json"

	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/mq/kafkax"

	"reflect"
	"time"

	"github.com/pkg/errors"
	"github.com/samber/lo"
)

const (
	indexTypeCreate = "create"
	indexTypeInsert = "insert"
	indexTypeUpdate = "update"
	indexTypeDelete = "delete"
	indexTypeIgnore = "ignore"
)

type Consumer interface {
	MqBuild(ctx context.Context, msg *kafkax.Message) bool
	MqBuildV2(ctx context.Context, msg *kafkax.Message) bool
	MqBuildV3(ctx context.Context, msg *kafkax.Message) bool
	UpdateTableRows(ctx context.Context, m *kafkax.Message) bool
}

type consumer struct {
	//uc string
	adProxy  ad_proxy.AD
	esClient es_subject_model.ESSubjectModel

	configCenter configuration_center.DrivenConfigurationCenter
	adCfgHelper  knowledge_build.Helper
	dbRepo       knowledge_datasource.Repo

	msgCache      int
	msgTime       time.Time
	kgBuilderTime int64
	msgUpdateTime int64
	kgInfo        map[string]CacheData
	userTypeCache int
	adVersion     string
}

func NewConsumer(adProxy ad_proxy.AD, adCfgHelper knowledge_build.Helper, dbRepo knowledge_datasource.Repo, configCenter configuration_center.DrivenConfigurationCenter, esClient es_subject_model.ESSubjectModel) Consumer {
	nKgInfo := make(map[string]CacheData)
	nKgInfo[settings.GetConfig().KnowledgeNetworkResourceMap.AFBusinessRelationsGraphConfigId] = CacheData{time.Now(), 0}
	nKgInfo[settings.GetConfig().KnowledgeNetworkResourceMap.LineageGraphConfigId] = CacheData{time.Now(), 0}
	nKgInfo[settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId] = CacheData{time.Now(), 0}
	nKgInfo[settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId] = CacheData{time.Now(), 0}
	nKgInfo[settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId] = CacheData{time.Now(), 0}

	return &consumer{
		adProxy:      adProxy,
		esClient:     esClient,
		adCfgHelper:  adCfgHelper,
		configCenter: configCenter,
		dbRepo:       dbRepo,
		kgInfo:       nKgInfo,
		adVersion:    settings.GetConfig().AnyDataConf.Version,
	}
}

type CacheData struct {
	MsgTime       time.Time
	kgBuilderTime int64
}

// 根据消息类型，增量构建
func (c *consumer) MqBuild(ctx context.Context, msg *kafkax.Message) bool {
	var err error
	ctx, span := trace.StartConsumerSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	kgConfigIdMap := map[string]int{
		settings.GetConfig().KnowledgeNetworkResourceMap.AFBusinessRelationsGraphConfigId:         1,
		settings.GetConfig().KnowledgeNetworkResourceMap.LineageGraphConfigId:                     1,
		settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId:         1,
		settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId:  1,
		settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId: 1,
	}

	req := IndexMsg{}
	if err = json.Unmarshal(msg.Value, &req); err == nil {
		err = req.validate()
	}
	if err != nil {
		log.WithContext(ctx).Errorf("failed to handle msq, msq format err, topic: %v, key: %s, value: %s, err: %v", msg.Topic, msg.Key, msg.Value, err)
		return true // 丢弃消息
	}
	if c.userTypeCache == 0 {
		afVersion, err := c.configCenter.DataUseType(ctx)
		if err == nil {
			c.userTypeCache = afVersion.Using
		}
	}
	//log.WithContext(ctx).Infof("mq info: %s", req)
	for {
		switch req.PayLoad.Type {
		case indexTypeCreate, indexTypeUpdate, indexTypeDelete:
			//fmt.Println(req, "mq info: da")
			log.WithContext(ctx).Infof("mq info: %s", req)
			//fmt.Println(req.toIndexParam(), "mq info")
			c.msgCache += 1

			filterKg := ""
			if err == nil {
				if c.userTypeCache == 1 {
					filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
				} else if c.userTypeCache == 2 {
					filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
				}
			}

			kgConfigId := req.PayLoad.Content.Type
			_, ok := kgConfigIdMap[kgConfigId]
			if ok {
				if kgConfigId == filterKg {
					log.WithContext(ctx).Infof("kg graph %s is filter, userType %d", kgConfigId, c.userTypeCache)
					return true
				}
				kgBuilderTime := c.kgInfo[kgConfigId].kgBuilderTime
				msgTime := msg.Timestamp.UnixNano() / 1e6
				if msgTime < kgBuilderTime {
					log.WithContext(ctx).Infof("kg graph %s is filter, msg time:%v, build time:%v", kgConfigId, msgTime, kgBuilderTime)
					return true
				}
				//msgTime := c.kgInfo[kgConfigId].MsgTime
				//nTime := time.Now()
				//cTime := nTime.Sub(msgTime)
				err = c.incrementBuildGraph(ctx, kgConfigId)
				if err != nil {
					fmt.Println(err)
				} else {
					log.WithContext(ctx).Infof("kg graph %s is building", kgConfigId)
				}

			} else {
				log.WithContext(ctx).Infof("config id %s not exits", kgConfigId)
				return true
			}

			// 添加增量规则
			//if c.msgCache >= 1 || cTime.Minutes() >= 10 {
			//	_, ok := kgConfigIdMap[req.PayLoad.Graph]
			//	if ok {
			//		log.WithContext(ctx).Infof("config id %s is build", req.PayLoad.Graph)
			//		err = c.incrementBuildGraph(ctx, req.PayLoad.Graph)
			//		if err != nil {
			//			fmt.Println(err)
			//		}
			//		c.msgCache = 0
			//		c.msgTime = nTime
			//	} else {
			//		log.WithContext(ctx).Infof("config id %s not exits", req.PayLoad.Graph)
			//	}
			//}

		default:
			log.WithContext(ctx).Warnf("unsupported type, type: %v", req.PayLoad.Type)
			return true
		}

		if err != nil {
			select {
			case <-ctx.Done():
				log.Error("context is done")
				return true
			default:
				log.WithContext(ctx).Errorf("failed to update graph, retry, err: %v", err)
				time.Sleep(10 * time.Second)
				continue
			}

		}
		return true
	}
}

func change2string(inputValue interface{}) string {

	switch v := inputValue.(type) {
	case string:
		return v
	case int64:
		// 处理数字
		return strconv.FormatInt(v, 10)
	case int:
		// 处理数字
		return strconv.FormatInt(int64(v), 10)
	case float64:
		// 处理数字
		return strconv.FormatInt(int64(v), 10)
	default:
		fmt.Println("Kind is:", reflect.TypeOf(inputValue).Kind())
		return ""
	}
}

func change2string2(inputValue NumberOrString) string {

	if val, ok := inputValue.Value.(int64); ok {
		return strconv.FormatInt(val, 10)
	} else {
		if str, ok := inputValue.Value.(string); ok {
			return str
		} else {
			return ""
		}
	}

	return ""
}

// 根据消息类型，更新图谱数据
func (c *consumer) MqBuildV2(ctx context.Context, msg *kafkax.Message) bool {
	var err error
	ctx, span := trace.StartConsumerSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	kgConfigIdMap := map[string]int{
		settings.GetConfig().KnowledgeNetworkResourceMap.AFBusinessRelationsGraphConfigId:         1,
		settings.GetConfig().KnowledgeNetworkResourceMap.LineageGraphConfigId:                     1,
		settings.GetConfig().KnowledgeNetworkResourceMap.SmartRecommendationGraphConfigId:         1,
		settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId:  1,
		settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId: 1,
	}

	req := IndexMsg{}
	if err = json.Unmarshal(msg.Value, &req); err == nil {
		err = req.validate()
	}
	if err != nil {
		log.WithContext(ctx).Errorf("failed to handle msq, msq format err, topic: %v, key: %s, value: %s, err: %v", msg.Topic, msg.Key, msg.Value, err)
		return true // 丢弃消息
	}

	if c.userTypeCache == 0 {
		afVersion, err := c.configCenter.DataUseType(ctx)
		if err == nil {
			c.userTypeCache = afVersion.Using
		}
	}

	for {
		kgConfigId := req.PayLoad.Type
		_, ok := kgConfigIdMap[kgConfigId]
		if !ok {
			log.WithContext(ctx).Infof("config id %s not exits", kgConfigId)
			return true
		}

		if kgConfigId == "lineage-graph" {
			return true
		}
		if kgConfigId == "business-relation-graph" {
			return true
		}
		filterKg := ""
		if err == nil {
			if c.userTypeCache == 1 {
				filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
			} else if c.userTypeCache == 2 {
				filterKg = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
			}
		}
		log.Infof("filter graph %s", filterKg)

		if kgConfigId == filterKg {
			log.WithContext(ctx).Infof("config id %s is filter, env type %d", kgConfigId, c.userTypeCache)
			return true
		}

		graphId, err := c.adCfgHelper.GetGraphId(ctx, kgConfigId)
		if err != nil {
			log.Infof("stage 0 fail get graph %s id", kgConfigId)
			return true
		}

		resp, err := c.adProxy.ListGraphBuildTask(ctx, graphId, &ad_proxy.ListGraphBuildTaskReq{
			GraphName:   "",
			Order:       "desc",
			Page:        1,
			Size:        1,
			Rule:        "start_time",
			Status:      "all",
			TaskType:    "all",
			TriggerType: "all",
		})
		if err != nil {
			err = errors.Wrap(err, "list knw graph build task failed from ad")
			log.Info("stage 0 fail get graph status")
			return true
		}

		log.Infof("graph %s status %s", kgConfigId, resp.Res.GraphStatus)

		if lo.Contains([]string{`running`, `waiting`}, resp.Res.GraphStatus) {
			// 该图谱已经在构建中了，不发起更新任务
			log.WithContext(ctx).Warnf("stage 0 knw graph already building, graph id: %v, name: %v", graphId, kgConfigId)
			time.Sleep(10 * time.Second)

			continue

		}

		log.Infof("stage 1 graph %s %s entity %s type %s", kgConfigId, graphId, req.PayLoad.Content.TableName, req.PayLoad.Content.Type)

		// 比较ad版本和3.0.0.6， 如果大于，那么使用插入点的方式更新
		versionCp := compareVersions(c.adVersion, "3.0.0.6")

		if versionCp <= 0 {

			kgBuilderTime := c.kgInfo[kgConfigId].kgBuilderTime
			msgTime := msg.Timestamp.UnixNano() / 1e6
			if msgTime < kgBuilderTime {
				log.WithContext(ctx).Infof("kg graph %s is filter, msg time:%v, build time:%v", kgConfigId, msgTime, kgBuilderTime)
				return true
			}
			err = c.incrementBuildGraph(ctx, kgConfigId)
			if err != nil {
				log.WithContext(ctx).Error(err.Error())
			} else {
				log.WithContext(ctx).Infof("kg graph %s is building", kgConfigId)
			}
			return true
		}

		switch req.PayLoad.Content.Type {
		case indexTypeInsert, indexTypeUpdate:

			switch kgConfigId {
			case "cognitive-search-data-catalog-graph":
				return true
				switch req.PayLoad.Content.TableName {
				case "t_data_catalog":
					// 跳过
					return true
					//msgStruct := TDataCatalogBody{}
					//err = json.Unmarshal(msg.Value, &msgStruct)
					//if err != nil {
					//	log.Infof("data catalog parse error %s", err.Error())
					//	return true
					//}
					//msgStruct2 := TDataCatalogBody2{}
					//err = json.Unmarshal(msg.Value, &msgStruct)
					//if err != nil {
					//	log.Infof("data catalog parse error %s", err.Error())
					//	return true
					//}
					//msgStructItem := msgStruct2.Payload.Content.Entities[0]
					//dataCatalogId := msgStructItem.Id
					//if msgStructItem.State == 5 {
					//	err = c.createDataCatalog(ctx, kgConfigId, dataCatalogId, msgStructItem.FlowId)
					//} else {
					//	err = c.deleteEntity(ctx, kgConfigId, dataCatalogId, "datacatalogid", "datacatalog")
					//}
					//}
					//else {
					//	msgStructItem := msgStruct.Payload.Content.Entities[0]
					//	//if msgStructItem.FlowId == "" {
					//	//	log.Infof("graph %s filter entity TDataCatalog id %s", kgConfigId, msgStructItem.Id)
					//	//	return true
					//	//}
					//	//dataCatalogId := change2string(msgStructItem.Id)
					//	//log.Infof("%s %g %f %s", msgStructItem.Id, msgStructItem.Id, msgStructItem.Id, change2string(msgStructItem.Id))
					//	dataCatalogId := strconv.FormatInt(msgStructItem.Id, 10)
					//	//log.Infof("data catalog oid %v, uid %s, state %d", msgStructItem.Id, dataCatalogId, msgStructItem.State)
					//	if msgStructItem.State == 5 {
					//		err = c.createDataCatalog(ctx, kgConfigId, dataCatalogId, msgStructItem.FlowId)
					//	} else {
					//		err = c.deleteEntity(ctx, kgConfigId, dataCatalogId, "datacatalogid", "datacatalog")
					//	}

					//msgStructItem := msgStruct.Payload.Content.Entities[0]
					//log.Infof("data catalog oid %v", msgStructItem.Id)
					//dataCatalogId := change2string2(msgStructItem.Id)
					////log.Infof("data catalog oid %v, uid %s, state %d", msgStructItem.Id, dataCatalogId, msgStructItem.State)
					//dState := 0
					//dState, err = c.createDataCatalog(ctx, kgConfigId, dataCatalogId, msgStructItem.FlowId)
					//if dState == 2 {
					//	err = c.deleteEntity(ctx, kgConfigId, dataCatalogId, "datacatalogid", "datacatalog")
					//}
					//if msgStructItem.State == 5 {
					//
					//} else {
					//	err = c.deleteEntity(ctx, kgConfigId, dataCatalogId, "datacatalogid", "datacatalog")
					//}

				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					//log.Infof("publish at %s %t", msgStructItem.PublishAt, msgStructItem.PublishAt == nil)
					if msgStructItem.PublishAt == nil {
						log.Infof("graph %s filter entity FormView id %s reason: publish at %s", kgConfigId, msgStructItem.Id, msgStructItem.PublishAt)
					}
					err = c.createFormViewV2(ctx, kgConfigId, msgStructItem.Id)
					if err != nil {
						return true
					}
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createFormViewFieldV2(ctx, kgConfigId, msgStructItem.Id)
				case "t_report":
					msgStruct := TReportBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createDataExploreReportV2(ctx, kgConfigId, msgStructItem.FCode)
				case "t_data_catalog_info":
					msgStruct := TDataCatalogInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createCatalogTag(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10))
				case "info_system":
					msgStruct := InfoSystemBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse info_system fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createInfoSystem(ctx, kgConfigId, msgStructItem.Id)
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse department fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createDepartmentV2(ctx, kgConfigId, msgStructItem.Id)
				case "datasource":
					msgStruct := DataSourceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse datasource fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createDataSourceV2(ctx, kgConfigId, msgStructItem.Id)
				case "user":
					msgStruct := UserBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data owner fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Status == 2 {
						err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "dataownerid", "dataowner")
					} else {
						err = c.createDataOwnerV2(ctx, kgConfigId, msgStructItem.Id)
					}

				default:
					log.Infof("graph %s can not recognize entity %s", kgConfigId, req.PayLoad.Content.TableName)
					return true
				}
				if err != nil {
					log.Infof("stage 2 update cognitive-search-data-catalog-graph entity %s fail", req.PayLoad.Content.TableName)
					return true
				}
				log.Infof("stage 2 update cognitive-search-data-catalog-graph entity %s success", req.PayLoad.Content.TableName)
				return true
			case "cognitive-search-data-resource-graph":
				switch req.PayLoad.Content.TableName {
				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse SubjectDomain fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					if msgStructItem.Type == 1 {
						err = c.createDomain(ctx, kgConfigId, msgStructItem.Id)
					} else if msgStructItem.Type == 2 {
						err = c.createSubDomain(ctx, kgConfigId, msgStructItem.Id)
					} else {
						return true
					}
					log.Infof("stage 2 success update graph cognitive-search-data-resource-graph domain %d", msgStructItem.Type)
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.PublishAt == nil {
						log.Infof("graph %s filter entity FormView id %s reason: publish at %s", kgConfigId, msgStructItem.Id, msgStructItem.PublishAt)
					}
					err = c.createSource(ctx, kgConfigId, msgStructItem.Id, "FormView")
					if err != nil {
						return true
					}
					return true
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Errorf("parse form view field fail %s", err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createDataViewFields(ctx, kgConfigId, msgStructItem.Id)
					if err != nil {
						return true
					}
					return true
				case "service":
					msgStruct := ServiceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == 0 {
						log.WithContext(ctx).Info("filter entity Service")
						return true
					}

					err = c.createSource(ctx, kgConfigId, msgStructItem.ServiceId, "Service")
					//if err != nil {
					//	return true
					//}
					//return true
				case "service_param":
					msgStruct := ServiceParamBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createResponseField(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10))
				case "t_technical_indicator":
					msgStruct := IndicatorBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Errorf("parse indicator err %s", err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createSource(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10), "Indicator")
					if err != nil {
						log.Error(err.Error())
						return true
					}
					//return true
				case "t_dimension_model":
					msgStruct := DimensionModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Infof("parse t_dimension_model fail error %s", err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					//if msgStructItem.Id == 0 {
					//	log.WithContext(ctx).Info("filter entity indicator")
					//	return true
					//}

					err = c.createDimensionModel(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10))
					//if err != nil {
					//	return true
					//}
					//return true
				case "t_report":
					msgStruct := TReportBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createDataExploreReport(ctx, kgConfigId, msgStructItem.FCode)
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.createDepartment(ctx, kgConfigId, msgStructItem.Id)
				case "datasource":
					msgStruct := DataSourceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse datasource fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createDataSource(ctx, kgConfigId, msgStructItem.Id)
				case "user":
					msgStruct := UserBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data owner fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Status == 2 {
						err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "dataownerid", "dataowner")
					} else {
						err = c.createDataOwner(ctx, kgConfigId, msgStructItem.Id)
					}
				default:
					log.WithContext(ctx).Infof("kg config id %s  entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
					return true
				}
			case "smart-recommendation-graph":
				log.Infof("stage 1 success update smart-recommendation-graph")
				switch req.PayLoad.Content.TableName {
				case "domain":
					msgStruct := DomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					//if msgStruct.Payload.Model.Id == "" {
					//	return true
					//}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					log.Infof("domain id %s start", msgStructEntity.Id)
					if msgStructEntity.Type == 1 {
						err = c.createEntityDomainGroup(ctx, kgConfigId, msgStructEntity.Id)
					} else if msgStructEntity.Type == 2 {
						err = c.createEntityDomain(ctx, kgConfigId, msgStructEntity.Id)
					} else if msgStructEntity.Type == 3 {
						err = c.createEntityDomainFlow(ctx, kgConfigId, msgStructEntity.Id)
					} else {
						return true
					}
					log.Infof("stage 2 success update smart-recommendation-graph domain %s", msgStructEntity.Id)
					if err != nil {
						return true
					}
				case "business_model":
					msgStruct := BusinessModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityBusinessModel(ctx, kgConfigId, msgStructEntity.BusinessModelId)
					if err != nil {
						return true
					}
				case "business_flowchart":
					msgStruct := BusinessFlowchartBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityFlowchart(ctx, kgConfigId, msgStructEntity.FlowchartId)
				case "business_flowchart_component":
					msgStruct := BusinessFlowchartComponentBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					if msgStructEntity.Type != 1 && msgStructEntity.Type != 5 {
						log.Infof("stage 2 graph %s entity %s type %d filter", kgConfigId, "business_flowchart_component", msgStructEntity.Type)
						return true
					}
					err = c.createEntityFlowchartNode(ctx, kgConfigId, msgStructEntity.ComponentId)
					//if err != nil {
					//	return true
					//}
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					err = c.createEntityFormView(ctx, kgConfigId, msgStructItem.Id)
					if err != nil {
						return true
					}
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormViewField id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					err = c.createEntityFormViewField(ctx, kgConfigId, msgStructItem.Id)
					if err != nil {
						return true
					}
				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse SubjectDomain fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					if msgStructItem.Type == 1 {
						err = c.createEntitySubjectGroup(ctx, kgConfigId, msgStructItem.Id)
					} else if msgStructItem.Type == 2 {
						err = c.createEntitySubjectDomain(ctx, kgConfigId, msgStructItem.Id)
					} else if msgStructItem.Type == 3 {
						err = c.createEntitySubjectObject(ctx, kgConfigId, msgStructItem.Id)
					} else if msgStructItem.Type == 5 {
						err = c.createEntitySubjectEntity(ctx, kgConfigId, msgStructItem.Id)
					} else if msgStructItem.Type == 6 {
						err = c.createEntitySubjectProperty(ctx, kgConfigId, msgStructItem.Id)
					} else {
						return true
					}
					if err != nil {
						return true
					}
				case "business_form_standard":
					msgStruct := BusinessFormStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityForm(ctx, kgConfigId, msgStructEntity.BusinessFormId)
					//if err != nil {
					//	return true
					//}
				case "business_form_field_standard":
					msgStruct := BusinessFormFieldStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityField(ctx, kgConfigId, msgStructEntity.FieldId)
					if err != nil {
						return true
					}
				case "StandardInfo":
					msgStruct := StandardInfoBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					err = c.createEntityDataElement(ctx, kgConfigId, strconv.FormatInt(msgStruct.Payload.Model.Id, 10))
				case "info_system":
					msgStruct := InfoSystemBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse info_system fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityInfomationSystem(ctx, kgConfigId, msgStructItem.Id)
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse department fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityDepartment(ctx, kgConfigId, msgStructItem.Id)
				case "t_data_element_info":
					msgStruct := TDataElementInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityDataElement(ctx, kgConfigId, msgStructItem.Id)
				case "t_label":
					msgStruct := TLabel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse t_label fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					labelId := strconv.FormatInt(msgStructItem.Id, 10)
					err = c.createEntityLabel(ctx, kgConfigId, labelId)
				case "t_label_category":
					if req.PayLoad.Content.Type == indexTypeInsert {
						return true
					}

					msgStruct := TLabelCategory{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse t_label_category fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					log.Infof("entity label f_state %d", msgStructItem.FState)
					if msgStructItem.FState == nil || *(msgStructItem.FState) == 1 {
						labelId := strconv.FormatInt(msgStructItem.Id, 10)
						err = c.createEntityLabelByCategory(ctx, kgConfigId, labelId)
					} else {
						labelId := strconv.FormatInt(msgStructItem.Id, 10)
						err = c.deleteEntityLabelByCategory(ctx, kgConfigId, labelId)
					}
					return true
					//
				case "business_indicator":
					msgStruct := TBusinessIndicator{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse business_indicator fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityBusinessIndicator(ctx, kgConfigId, msgStructItem.IndicatorId)
				case "t_rule":
					msgStruct := TRule{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse business_indicator fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)

					ruleState := msgStructItem.State
					if ruleState != nil && *ruleState == "disable" {
						log.WithContext(ctx).Infof("kg config id %s  entity %s state %s delete", kgConfigId, req.PayLoad.Content.TableName, *ruleState)
						err = c.deleteEntity(ctx, kgConfigId, idStr, "id", "entity_rule")
					} else {
						err = c.createEntityRule(ctx, kgConfigId, idStr)
					}
				case "t_model_label_rec_rel":
					msgStruct := TModelLabelRecRel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.updateEntitySubjectModelLabel(ctx, strconv.FormatInt(msgStructItem.Id, 10), msgStructItem.Name, msgStructItem.RelatedModelIds)
					if err != nil {
						return true
					}
				case "t_graph_model":
					msgStruct := TGraphModel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.upsertEntitySubjectModel(ctx, msgStructItem.Id)
					if err != nil {
						return true
					}

				default:
					log.WithContext(ctx).Infof("kg config id %s  entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
					return true

				}

				if err != nil {
					log.WithContext(ctx).Infof("stage 2 fail update graph %s entity %s error %s", kgConfigId, req.PayLoad.Content.TableName, err.Error())
				} else {
					log.WithContext(ctx).Infof("stage 2 kg config id %s  entity %s udpate success", kgConfigId, req.PayLoad.Content.TableName)
				}

				return true
			case "business-relation-graph":
				log.Infof("stage 1 start update business-relation-graph")
				switch req.PayLoad.Content.TableName {
				case "business_model":
					msgStruct := BusinessModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createBRGEntityBusinessModel(ctx, kgConfigId, strconv.FormatInt(msgStructEntity.Id, 10))
					if err != nil {
						return true
					}
					log.Infof("stage 2 update business-relation-graph success")
				case "business_flowchart":
					msgStruct := BusinessFlowchartBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createBRGEntityFlowchart(ctx, kgConfigId, msgStructEntity.FlowchartId)

				case "business_flowchart_component":
					msgStruct := BusinessFlowchartComponentBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createBRGEntityFlowchartNode(ctx, kgConfigId, msgStructEntity.FlowchartId+msgStructEntity.MxcellId)
					if err != nil {
						return true
					}

				}
			default:
				log.WithContext(ctx).Infof("kg config id %s not exits", kgConfigId)
				return true
			}

			if err != nil {
				log.WithContext(ctx).Infof("stage 2 fail update graph %s entity %s error %s", kgConfigId, req.PayLoad.Content.TableName, err.Error())
			}

			log.WithContext(ctx).Infof("stage 2 success update graph %s entity %s", kgConfigId, req.PayLoad.Content.TableName)

			return true

		case indexTypeDelete:
			switch kgConfigId {
			case "cognitive-search-data-catalog-graph":
				switch req.PayLoad.Content.TableName {
				case "t_data_catalog":
					msgStruct := TDataCatalogBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					dataCatalogId := change2string(msgStructEntity.Id)

					err = c.deleteEntity(ctx, kgConfigId, dataCatalogId, "datacatalogid", "datacatalog")
					if err != nil {
						log.Errorf("graph %s entity %s delete fail", kgConfigId, req.PayLoad.Content.ClassName)
						return true
					}
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}

					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "formview_uuid", "form_view")
					//if err != nil {
					//	log.Errorf("graph %s entity %s delete fail", kgConfigId, req.PayLoad.Content.ClassName)
					//	return true
					//}
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "column_id", "form_view_field")
				case "t_data_catalog_info":
					msgStruct := TDataCatalogInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10), "catalogtagid", "catalogtag")
				case "info_system":
					msgStruct := InfoSystemBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "infosystemid", "info_system")
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "departmentid", "department")
				case "datasource":
					msgStruct := DataSourceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse datasource fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteDataSourceV2(ctx, kgConfigId, msgStructItem.Id)
					//err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "datasourceid", "datasource")
				case "user":
					msgStruct := UserBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data owner fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "dataownerid", "dataowner")
				case "t_report":
					msgStruct := TReportBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.deleteDataExploreReportV2(ctx, kgConfigId, msgStructItem.FCode)
				default:
					log.WithContext(ctx).Infof("kg %s entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
					return true
				}
			case "cognitive-search-data-resource-graph":
				switch req.PayLoad.Content.TableName {
				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					entityIdKey := ""
					entityName := ""

					if msgStructItem.Type == 1 {
						entityIdKey = "domainid"
						entityName = "domain"
						err = c.deleteSubjectDomainTypeResource(ctx, kgConfigId, entityName, msgStructItem.Id, msgStructItem.PathId)
					} else if msgStructItem.Type == 2 {
						entityIdKey = "subdomainid"
						entityName = "subdomain"
						err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
					} else {
						return true
					}

					if err != nil {
						return true
					}
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}

					err = c.deleteSource(ctx, kgConfigId, msgStructItem.Id, "FormView")
					if err != nil {
						return true
					}
					return true
				case "t_dimension_model":
					msgStruct := DimensionModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "dimension_model"

					err = c.deleteEntity(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10), entityIdKey, entityName)
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "column_id"
					entityName := "field"

					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
				case "service":
					msgStruct := ServiceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.deleteSource(ctx, kgConfigId, msgStructItem.ServiceId, "Service")
				case "service_param":
					msgStruct := ServiceParamBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					entityIdKey := "field_id"
					entityName := "response_field"
					err = c.deleteEntity(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10), entityIdKey, entityName)
				case "t_technical_indicator":
					msgStruct := IndicatorBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.deleteSource(ctx, kgConfigId, strconv.FormatInt(msgStructItem.Id, 10), "Indicator")
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "departmentid", "department")
				case "datasource":
					msgStruct := DataSourceBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse datasource fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteDataSource(ctx, kgConfigId, msgStructItem.Id)
				case "user":
					msgStruct := UserBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data owner fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "dataownerid", "dataowner")
				case "t_report":
					msgStruct := TReportBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.deleteDataExploreReport(ctx, kgConfigId, msgStructItem.FCode)
				default:
					log.WithContext(ctx).Infof("kg %s entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
					return true
				}
			case "smart-recommendation-graph":
				switch req.PayLoad.Content.TableName {
				case "domain":
					log.Info("stage 2 start delete smart-recommendation-graph domain")
					msgStruct := DomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					if msgStructEntity.Id == "" {
						log.Infof("stage 2 delete smart-recommendation-graph domain id %s fail", msgStructEntity.Id)
						return true
					}
					log.Infof("stage 2 continue delete smart-recommendation-graph domain %d", msgStructEntity.Type)
					entityIdKey := ""
					entityName := ""
					if msgStructEntity.Type == 3 {
						entityIdKey = "id"
						entityName = "entity_domain_flow"
					} else if msgStructEntity.Type == 2 {
						entityIdKey = "id"
						entityName = "entity_domain"
					} else if msgStructEntity.Type == 1 {
						entityIdKey = "id"
						entityName = "entity_domain_group"
					} else {
						return true
					}

					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.Id, entityIdKey, entityName)

					log.Infof("stage 2 delete smart-recommendation-graph domain id %s success", msgStructEntity.Id)
				case "business_model":
					msgStruct := BusinessModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "entity_business_model"

					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.BusinessModelId, entityIdKey, entityName)
					if err != nil {
						return true
					}
				case "business_flowchart":
					msgStruct := BusinessFlowchartBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}

					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "entity_flowchart"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.FlowchartId, entityIdKey, entityName)
					if err != nil {
						return true
					}
				case "business_flowchart_component":
					msgStruct := BusinessFlowchartComponentBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					if msgStructEntity.Type != 1 && msgStructEntity.Type != 5 {
						log.Infof("stage 2 graph %s entity %s type %d filter", kgConfigId, "business_flowchart_component", msgStructEntity.Type)
						return true
					}
					entityIdKey := "id"
					entityName := "entity_flowchart_node"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.ComponentId, entityIdKey, entityName)
					//if err != nil {
					//	return true
					//}
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					entityIdKey := "id"
					entityName := "entity_form_view"
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
					if err != nil {
						return true
					}
				case "form_view_field":
					msgStruct := FormViewFieldBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "entity_form_view_field"

					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
					if err != nil {
						return true
					}
					return true
				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					entityIdKey := ""
					entityName := ""
					if msgStructItem.Type == 1 {
						entityIdKey = "id"
						entityName = "entity_subject_group"
						err = c.deleteEntitySubjectDomainType(ctx, kgConfigId, entityName, msgStructItem.Id, msgStructItem.PathId)
					} else if msgStructItem.Type == 2 {
						entityIdKey = "id"
						entityName = "entity_subject_domain"
						err = c.deleteEntitySubjectDomainType(ctx, kgConfigId, entityName, msgStructItem.Id, msgStructItem.PathId)
					} else if msgStructItem.Type == 3 {
						entityIdKey = "id"
						entityName = "entity_subject_object"
						err = c.deleteEntitySubjectDomainType(ctx, kgConfigId, entityName, msgStructItem.Id, msgStructItem.PathId)
					} else if msgStructItem.Type == 5 {
						entityIdKey = "id"
						entityName = "entity_subject_entity"
						err = c.deleteEntitySubjectDomainType(ctx, kgConfigId, entityName, msgStructItem.Id, msgStructItem.PathId)
					} else if msgStructItem.Type == 6 {
						entityIdKey = "id"
						entityName = "entity_subject_property"
						err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
					} else {
						return true
					}

					if err != nil {
						return true
					}
				case "business_form_standard":
					msgStruct := BusinessFormStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Errorf("parse business_form_standard error %s", err.Error())
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "entity_form"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.BusinessFormId, entityIdKey, entityName)
					//if err != nil {
					//	return true
					//}
				case "business_form_field_standard":
					msgStruct := BusinessFormFieldStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "id"
					entityName := "entity_field"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.FieldId, entityIdKey, entityName)
					//if err != nil {
					//	return true
					//}
				case "info_system":
					msgStruct := InfoSystemBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "id", "entity_infomation_system")
				case "object":
					msgStruct := ObjectBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "id", "entity_department")
				case "t_data_element_info":
					msgStruct := TDataElementInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, "id", "entity_data_element")
				case "t_label":
					msgStruct := TLabelCategory{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}

					msgStructItem := msgStruct.Payload.Content.Entities[0]
					labelId := strconv.FormatInt(msgStructItem.Id, 10)
					err = c.deleteEntity(ctx, kgConfigId, labelId, "id", "entity_label")
				case "business_indicator":
					msgStruct := TBusinessIndicator{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntity(ctx, kgConfigId, msgStructItem.IndicatorId, "id", "entity_business_indicator")
				case "t_rule":
					msgStruct := TRule{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)
					err = c.deleteEntity(ctx, kgConfigId, idStr, "id", "entity_rule")
				case "t_model_label_rec_rel":
					msgStruct := TModelLabelRecRel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)
					err = c.deleteEntitySubjectModelLabel(ctx, idStr)
				case "t_graph_model":
					msgStruct := TGraphModel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntitySubjectModel(ctx, msgStructItem.Id)
				default:
					log.WithContext(ctx).Infof("kg %s entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
				}
			case "business-relation-graph":
				switch req.PayLoad.Content.TableName {
				case "business_model":
					msgStruct := BusinessModelBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "business_model_id"
					entityName := "entity_business_model"

					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.BusinessModelId, entityIdKey, entityName)
					if err != nil {
						return true
					}

				case "business_flowchart":
					msgStruct := BusinessFlowchartBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}

					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					entityIdKey := "flowchart_id"
					entityName := "entity_flowchart"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.FlowchartId, entityIdKey, entityName)
					if err != nil {
						return true
					}
				case "business_flowchart_component":
					msgStruct := BusinessFlowchartComponentBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					if msgStructEntity.Type != 1 && msgStructEntity.Type != 5 {
						log.Infof("stage 2 graph %s entity %s type %d filter", kgConfigId, "business_flowchart_component", msgStructEntity.Type)
						return true
					}
					entityIdKey := "node_id"
					entityName := "entity_flowchart_node"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.FlowchartId+msgStructEntity.MxcellId, entityIdKey, entityName)
				case "business_indicator":
					msgStruct := BusinessIndicatorBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]

					entityIdKey := "business_indicator_id"
					entityName := "entity_business_indicator"
					err = c.deleteEntity(ctx, kgConfigId, msgStructEntity.IndicatorId, entityIdKey, entityName)
				default:

					log.WithContext(ctx).Infof("entity type %s not exits", req.PayLoad.Content.TableName)
					return true
				}

			default:

				log.WithContext(ctx).Infof("config id %s not exits", kgConfigId)
				return true
			}

			if err != nil {
				log.Infof("stage 2 delete %s entity %s fail", kgConfigId, req.PayLoad.Content.TableName)
				return true
			}
			log.Infof("stage 2 delete %s entity %s success", kgConfigId, req.PayLoad.Content.TableName)
			return true

		default:
			log.WithContext(ctx).Warnf("unsupported type, type: %v", req.PayLoad.Type)
			return true
		}

		//if err != nil {
		//	log.WithContext(ctx).Errorf("failed to update graph, retry, err: %v", err)
		//	time.Sleep(10 * time.Second)
		//	continue
		//}
		//return true
	}
}

// 根据消息类型，更新图谱数据, 20251218
func (c *consumer) MqBuildV3(ctx context.Context, msg *kafkax.Message) bool {
	var err error
	ctx, span := trace.StartConsumerSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	req := IndexMsg{}
	if err = json.Unmarshal(msg.Value, &req); err == nil {
		err = req.validate()
	}
	if err != nil {
		log.WithContext(ctx).Errorf("failed to handle msq, msq format err, topic: %v, key: %s, value: %s, err: %v", msg.Topic, msg.Key, msg.Value, err)
		return true // 丢弃消息
	}

	for {
		kgConfigId := req.PayLoad.Type

		switch req.PayLoad.Content.Type {
		case indexTypeInsert, indexTypeUpdate:

			switch kgConfigId {
			case "smart-recommendation-graph":
				log.Infof("stage 1 success update smart-recommendation-graph")
				switch req.PayLoad.Content.TableName {

				//case "business_flowchart":
				//	msgStruct := BusinessFlowchartBody{}
				//	err = json.Unmarshal(msg.Value, &msgStruct)
				//	if err != nil {
				//		return true
				//	}
				//	msgStructEntity := msgStruct.Payload.Content.Entities[0]
				//	err = c.createEntityFlowchartV2(ctx, msgStructEntity.FlowchartId, msgStructEntity.Name, msgStructEntity.Description, msgStructEntity.Path, msgStructEntity.PathId)

				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					err = c.createEntityFormViewV2(ctx, msgStructItem.Id)
					if err != nil {
						return true
					}

				case "business_form_standard":
					msgStruct := BusinessFormStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityFormV2(ctx, msgStructEntity.BusinessFormId, msgStructEntity.Name, msgStructEntity.BusinessModelId, msgStructEntity.Description)
					//if err != nil {
					//	return true
					//}
				case "business_form_field_standard":
					msgStruct := BusinessFormFieldStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityFieldV2(ctx, msgStructEntity.FieldId, msgStructEntity.Name, msgStructEntity.BusinessFormId, msgStructEntity.BusinessFormName, msgStructEntity.NameEn, msgStructEntity.StandardId)
					if err != nil {
						return true
					}
				case "StandardInfo":
					msgStruct := StandardInfoBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					err = c.createEntityDataElementV2(ctx, strconv.FormatInt(msgStruct.Payload.Model.Id, 10))
				case "t_data_element_info":
					msgStruct := TDataElementInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.createEntityDataElementV2(ctx, msgStructItem.Id)
				//case "t_label":
				//	msgStruct := TLabel{}
				//	err = json.Unmarshal(msg.Value, &msgStruct)
				//	if err != nil {
				//		log.Info("parse t_label fail")
				//		return true
				//	}
				//	msgStructItem := msgStruct.Payload.Content.Entities[0]
				//	labelId := strconv.FormatInt(msgStructItem.Id, 10)
				//	err = c.createEntityLabelV2(ctx, labelId)
				//case "business_indicator":
				//	msgStruct := TBusinessIndicator{}
				//	err = json.Unmarshal(msg.Value, &msgStruct)
				//	if err != nil {
				//		log.Info("parse business_indicator fail")
				//		return true
				//	}
				//	msgStructItem := msgStruct.Payload.Content.Entities[0]
				//	err = c.createEntityBusinessIndicatorV2(ctx, msgStructItem.IndicatorId)
				case "t_rule":
					msgStruct := TRule{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse business_indicator fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)

					ruleState := msgStructItem.State
					if ruleState != nil && *ruleState == "disable" {
						indexName := "af_sailor_entity_data_element_idx"
						log.WithContext(ctx).Infof("kg config id %s  entity %s state %s delete", kgConfigId, req.PayLoad.Content.TableName, *ruleState)
						err = c.deleteEntityIndex(ctx, idStr, indexName)
					} else {
						err = c.createEntityRuleV2(ctx, idStr)
					}
				case "t_model_label_rec_rel":
					msgStruct := TModelLabelRecRel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.updateEntitySubjectModelLabel(ctx, strconv.FormatInt(msgStructItem.Id, 10), msgStructItem.Name, msgStructItem.RelatedModelIds)
					if err != nil {
						return true
					}
				case "t_graph_model":
					msgStruct := TGraphModel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					err = c.upsertEntitySubjectModel(ctx, msgStructItem.Id)
					if err != nil {
						return true
					}
				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse SubjectDomain fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					if msgStructItem.Type == 6 {
						err = c.createEntitySubjectPropertyV2(ctx, msgStructItem.Id)
					} else {
						return true
					}
					if err != nil {
						return true
					}

				default:
					log.WithContext(ctx).Infof("kg config id %s  entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
					return true

				}

				if err != nil {
					log.WithContext(ctx).Infof("stage 2 fail update graph %s entity %s error %s", kgConfigId, req.PayLoad.Content.TableName, err.Error())
				} else {
					log.WithContext(ctx).Infof("stage 2 kg config id %s  entity %s udpate success", kgConfigId, req.PayLoad.Content.TableName)
				}

				return true
			default:
				log.WithContext(ctx).Infof("kg config id %s not exits", kgConfigId)
				return true
			}

			if err != nil {
				log.WithContext(ctx).Infof("stage 2 fail update graph %s entity %s error %s", kgConfigId, req.PayLoad.Content.TableName, err.Error())
			}

			log.WithContext(ctx).Infof("stage 2 success update graph %s entity %s", kgConfigId, req.PayLoad.Content.TableName)

			return true

		case indexTypeDelete:
			switch kgConfigId {
			case "smart-recommendation-graph":
				switch req.PayLoad.Content.TableName {
				case "form_view":
					msgStruct := FormViewBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					if msgStructItem.Id == "" {
						log.Infof("graph %s filter entity FormView id %s", kgConfigId, msgStructItem.Id)
						return true
					}
					indexName := "af_sailor_entity_form_view_idx"
					err = c.deleteEntityIndex(ctx, msgStructItem.Id, indexName)
					if err != nil {
						return true
					}
				//case "form_view_field":
				//	msgStruct := FormViewFieldBody{}
				//	err = json.Unmarshal(msg.Value, &msgStruct)
				//	if err != nil {
				//		return true
				//	}
				//	msgStructItem := msgStruct.Payload.Content.Entities[0]
				//	entityIdKey := "id"
				//	entityName := "entity_form_view_field"
				//
				//	err = c.deleteEntity(ctx, kgConfigId, msgStructItem.Id, entityIdKey, entityName)
				//	if err != nil {
				//		return true
				//	}
				//	return true

				case "business_form_standard":
					msgStruct := BusinessFormStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Errorf("parse business_form_standard error %s", err.Error())
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]
					indexName := "af_sailor_entity_form_idx"
					err = c.deleteEntityIndex(ctx, msgStructEntity.BusinessFormId, indexName)
					//if err != nil {
					//	return true
					//}
				case "business_form_field_standard":
					msgStruct := BusinessFormFieldStandardBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Error(err.Error())
						return true
					}
					msgStructEntity := msgStruct.Payload.Content.Entities[0]

					indexName := "af_sailor_entity_field_idx"
					err = c.deleteEntityIndex(ctx, msgStructEntity.FieldId, indexName)
					//if err != nil {
					//	return true
					//}
				case "t_data_element_info":
					msgStruct := TDataElementInfo{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					indexName := "af_sailor_entity_data_element_idx"
					err = c.deleteEntityIndex(ctx, msgStructItem.Id, indexName)
				case "t_rule":
					msgStruct := TRule{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)
					indexName := "af_sailor_entity_rule_idx"
					err = c.deleteEntityIndex(ctx, idStr, indexName)
				case "t_model_label_rec_rel":
					msgStruct := TModelLabelRecRel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					idStr := strconv.FormatInt(msgStructItem.Id, 10)
					err = c.deleteEntitySubjectModelLabel(ctx, idStr)
				case "t_graph_model":
					msgStruct := TGraphModel{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						log.Info("parse data_element fail")
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]
					err = c.deleteEntitySubjectModel(ctx, msgStructItem.Id)

				case "subject_domain":
					msgStruct := SubjectDomainBody{}
					err = json.Unmarshal(msg.Value, &msgStruct)
					if err != nil {
						return true
					}
					msgStructItem := msgStruct.Payload.Content.Entities[0]

					if msgStructItem.Type == 6 {
						indexName := "af_sailor_entity_subject_property_idx"
						err = c.deleteEntityIndex(ctx, msgStructItem.Id, indexName)
					} else {
						return true
					}

					if err != nil {
						return true
					}
				default:
					log.WithContext(ctx).Infof("kg %s entity %s not exits", kgConfigId, req.PayLoad.Content.TableName)
				}

			default:

				log.WithContext(ctx).Infof("config id %s not exits", kgConfigId)
				return true
			}

			if err != nil {
				log.Infof("stage 2 delete %s entity %s fail", kgConfigId, req.PayLoad.Content.TableName)
				return true
			}
			log.Infof("stage 2 delete %s entity %s success", kgConfigId, req.PayLoad.Content.TableName)
			return true

		default:
			log.WithContext(ctx).Warnf("unsupported type, type: %v", req.PayLoad.Type)
			return true
		}

	}
}

func (c *consumer) incrementBuildGraph(ctx context.Context, graphConfigName string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	//fmt.Println(settings.GetConfig().KnowledgeNetworkResourceMap.DataAssetsGraphConfigId)
	graphId, err := c.adCfgHelper.GetGraphId(ctx, graphConfigName)
	if err != nil {
		return err
	}

	err = c.buildGraph(ctx, graphId, graphConfigName)

	if err != nil {
		return err
	}

	return nil
}

func (g *consumer) buildGraph(ctx context.Context, graphId string, configID string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	resp, err := g.adProxy.ListGraphBuildTask(ctx, graphId, &ad_proxy.ListGraphBuildTaskReq{
		GraphName:   "",
		Order:       "desc",
		Page:        1,
		Size:        1,
		Rule:        "start_time",
		Status:      "all",
		TaskType:    "all",
		TriggerType: "all",
	})
	if err != nil {
		return errors.Wrap(err, "list knw graph build task failed from ad")
	}

	if lo.Contains([]string{`running`, `waiting`}, resp.Res.GraphStatus) {
		// 该图谱已经在构建中了，不发起构建任务
		log.WithContext(ctx).Warnf("knw graph already building, graph id: %v, name: %v", graphId, "资产")
		//time.Sleep(5 * time.Second)
		return errors.Wrap(err, "knw graph already building")
	}

	var curGraphBuildTaskType string
	for _, graphCfg := range settings.GetConfig().KnowledgeNetworkBuild.Graph {
		if graphCfg.ID == configID {
			//curGraphBuildTaskType = "full"
			curGraphBuildTaskType = "full"
			break
		}
	}

	if len(curGraphBuildTaskType) < 1 {
		return errors.New(fmt.Sprintf("graph build task type is empty, graph id: %v, config id: %v, name: %v", graphId, configID, "资产"))
	}

	if _, err := g.adProxy.StartGraphBuildTask(ctx, graphId, &ad_proxy.ExecGraphBuildTaskReq{
		TaskType: curGraphBuildTaskType,
	}); err != nil {
		return errors.Wrap(err, "start graph build task failed")
	}
	//g.kgInfo[configID].kgBuilderTime += time.Now().UnixNano() / 1e6
	kgBuilderTime := time.Now().UnixNano() / 1e6
	g.kgInfo[configID] = CacheData{g.kgInfo[configID].MsgTime, kgBuilderTime}

	return nil
}

// UpdateTableRows 更新ES中的数据量和数据更新时间
func (c *consumer) UpdateTableRows(ctx context.Context, m *kafkax.Message) bool {
	req := UpdateTableRowsMsq{}
	err := json.Unmarshal(m.Value, &req)
	//if err == nil {
	//	err = req.validate()
	//}
	if err != nil {
		log.WithContext(ctx).Errorf("failed to handle msq, msq format err, topic: %v, key: %s, value: %s, err: %v", m.Topic, m.Key, m.Value, err)
		return true // 丢弃消息
	}

	//if err = c.uc.UpdateTableRowsAndUpdatedAt(ctx, req.toParam()); err != nil {
	//	log.Errorf("failed to update table row to es, err: %v", err)
	//	return false
	//}
	log.WithContext(ctx).Infof("recv msg, but data-catalog no need to update, topic: %v, key: %s, value: %s", m.Topic, m.Key, m.Value)

	return true
}

type IndexMsg struct {
	Header  MsgHeader    `json:"header"`
	PayLoad IndexMsqBody `json:"payload" binding:"required"`
}

type MsgHeader struct {
}

type IndexMsqBody struct {
	Type    string `json:"type"`
	Content struct {
		Type      string `json:"type"`
		ClassName string `json:"class_name"`
		TableName string `json:"table_name"`
	} `json:"content"`
}

type InterfaceServiceBody struct {
	Id                 int64       `json:"id"`
	ServiceName        string      `json:"service_name"`
	ServiceId          string      `json:"service_id"`
	ServiceCode        string      `json:"service_code"`
	ServicePath        string      `json:"service_path"`
	Status             string      `json:"status"`
	AuditType          string      `json:"audit_type"`
	AuditStatus        string      `json:"audit_status"`
	ApplyId            string      `json:"apply_id"`
	ProcDefKey         string      `json:"proc_def_key"`
	AuditAdvice        string      `json:"audit_advice"`
	BackendServiceHost string      `json:"backend_service_host"`
	BackendServicePath string      `json:"backend_service_path"`
	DepartmentId       string      `json:"department_id"`
	DepartmentName     string      `json:"department_name"`
	OwnerId            string      `json:"owner_id"`
	OwnerName          string      `json:"owner_name"`
	SubjectDomainId    string      `json:"subject_domain_id"`
	SubjectDomainName  string      `json:"subject_domain_name"`
	CreateModel        string      `json:"create_model"`
	HttpMethod         string      `json:"http_method"`
	ReturnType         string      `json:"return_type"`
	Protocol           string      `json:"protocol"`
	FileId             string      `json:"file_id"`
	Description        string      `json:"description"`
	DeveloperId        string      `json:"developer_id"`
	DeveloperName      string      `json:"developer_name"`
	RateLimiting       int         `json:"rate_limiting"`
	Timeout            int         `json:"timeout"`
	ServiceType        string      `json:"service_type"`
	FlowId             string      `json:"flow_id"`
	FlowName           string      `json:"flow_name"`
	FlowNodeId         string      `json:"flow_node_id"`
	FlowNodeName       string      `json:"flow_node_name"`
	OnlineTime         interface{} `json:"online_time"`
	CreateTime         time.Time   `json:"create_time"`
	UpdateTime         time.Time   `json:"update_time"`
	DeleteTime         int         `json:"delete_time"`
}

type MsgModel struct {
}

func (i *IndexMsg) validate() error {
	if _, err := form_validator.BindStructAndValid(i); err != nil {
		return err
	}

	return nil
}

//func (i *IndexMsg) toIndexParam() *IndexToESReqParam {
//
//	var infoSystemID, infoSystemName string
//	if i.Body.InfoSystems != nil && len(i.Body.InfoSystems) > 0 {
//		infoSystemID = i.Body.InfoSystems[0].ID
//		infoSystemName = i.Body.InfoSystems[0].Name
//	}
//	//fmt.Println()
//	return &IndexToESReqParam{
//		DocId:         i.Body.DocId,
//		Title:         *i.Body.Title,
//		Description:   lo.FromPtr(i.Body.Description),
//		ID:            *i.Body.ID,
//		Code:          *i.Body.Code,
//		DataKind:      i.Body.DataKind,
//		DataRange:     i.Body.DataRange,
//		UpdateCycle:   i.Body.UpdateCycle,
//		SharedType:    *i.Body.SharedType,
//		OrgCode:       *i.Body.Orgcode,
//		OrgName:       *i.Body.Orgname,
//		TableId:       lo.FromPtr(i.Body.TableId),
//		TableRows:     i.Body.TableRows,
//		DataUpdatedAt: i.Body.UpdatedAt,
//		PublishedAt:   *i.Body.PublishedAt,
//
//		BusinessObjects: i.Body.BusinessObjects,
//		OwnerName:       i.Body.OwnerName,
//		OwnerID:         i.Body.OwnerID,
//		DataSourceName:  i.Body.DataSourceName,
//		DataSourceID:    i.Body.DataSourceID,
//		SchemaName:      i.Body.SchemaName,
//		SchemaID:        i.Body.SchemaID,
//
//		InfoSystemID:   infoSystemID,
//		InfoSystemName: infoSystemName,
//	}
//}

//func (i *IndexMsg) toDeleteParam() *DeleteFromESReqParam {
//	return &DeleteFromESReqParam{
//		ID: i.Body.DocId,
//	}
//}

type UpdateTableRowsMsq struct {
	TableId   string `json:"table_id" binding:"required,max=36"`
	TableRows *int64 `json:"table_rows,omitempty" binding:"required_without=UpdatedAt,omitempty,gte=0"`
	UpdatedAt *int64 `json:"updated_at,omitempty" binding:"required_without=TableRows,omitempty,gte=0"`
}

//func (m *UpdateTableRowsMsq) validate() error {
//	if err := form_validator.BindStructAndValid(m); err != nil {
//		return err
//	}
//
//	return nil
//}

func (m *UpdateTableRowsMsq) toParam() *UpdateTableRowsAndUpdatedAtReqParam {
	return &UpdateTableRowsAndUpdatedAtReqParam{
		TableId:       m.TableId,
		TableRows:     m.TableRows,
		DataUpdatedAt: m.UpdatedAt,
	}
}

func checkNil(values ...any) bool {
	for _, v := range values {
		value := reflect.ValueOf(v)
		if value.Kind() != reflect.Pointer {
			continue
		}

		if value.IsNil() {
			return true
		}
	}

	return false
}
