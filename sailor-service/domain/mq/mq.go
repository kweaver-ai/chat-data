package mq

import (
	//"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/data_catalog"
	"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/data_change_mq"
	//"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/data_view"
	//"github.com/kweaver-ai/chat-data/sailor-service/adapter/driver/interface_svc"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"

	"github.com/kweaver-ai/TelemetrySDK-Go/exporter/v2/ar_trace"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/mq/kafkax"
)

const (
	topicDataCatalogIndex = "af.data-catalog.es-index"
	//topicMetadataManageIndexUpdate = "af.metadata-manage.es-index.update"

	topicInterfaceSvcIndex = "af.interface-svc.es-index"
	topicDataViewIndex     = "data-view.es-index"
	topicDataChange        = "af.business-grooming.entity_change"
)

type MQConsumerService struct {
	kafkax.Consumer
	dataChangeConsumer data_change_mq.Consumer
}

func NewMQConsumeService(dataChangeConsumer data_change_mq.Consumer) *MQConsumerService {
	m := &MQConsumerService{
		Consumer: kafkax.NewConsumerService(&kafkax.ConsumerConfig{
			Version:   settings.GetConfig().KafkaConf.Version,
			Addr:      settings.GetConfig().KafkaConf.URI,
			ClientID:  settings.GetConfig().KafkaConf.ClientId,
			UserName:  settings.GetConfig().KafkaConf.Username,
			Password:  settings.GetConfig().KafkaConf.Password,
			GroupID:   settings.GetConfig().KafkaConf.GroupId,
			Mechanism: "PLAIN",
			Trace:     ar_trace.Tracer,
		}),
		dataChangeConsumer: dataChangeConsumer,
	}
	m.RegisterHandles()
	return m
}

//func (h *MQConsumerService) GetHandles() []kafkax.MessageHandleDef {
//	return []kafkax.MessageHandleDef{
//		{
//			Topic:  []string{topicDataChange},
//			Handle: h.dataChangeConsumer.MqBuildV2,
//			Options: []kafkax.Option{
//				kafkax.WithErrHandle(func(err error) {
//					log.Errorf("failed to consume kafka msg, err: %v", err)
//				}),
//				kafkax.WithAutoCommit(false),
//			},
//		},
//	}
//}

func (h *MQConsumerService) RegisterHandles() {
	h.Consumer.RegisterHandles(h.dataChangeConsumer.MqBuildV3, topicDataChange)

}
