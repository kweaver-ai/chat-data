package server

import (
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/knowledge_build"
	"github.com/kweaver-ai/chat-data/sailor-service/domain/mq"
	goFrame "github.com/kweaver-ai/idrm-go-frame"
	"github.com/kweaver-ai/idrm-go-frame/core/transport"
	"github.com/kweaver-ai/idrm-go-frame/core/transport/rest"
)

var arg = settings.MainArgs{
	Name:    "af-sailor-service",
	Version: "1.0",
}

func newApp(ss []transport.Server) *goFrame.App {
	return goFrame.New(
		goFrame.Name(arg.Name),
		goFrame.Server(ss...),
	)
}

func toTransportServer(hs *rest.Server, knBuildServer *knowledge_build.Server, mqServer *mq.MQConsumerService) []transport.Server {
	return []transport.Server{hs, knBuildServer, mqServer}
}

func Run(runCfg settings.MainArgs) error {
	arg = runCfg

	settings.InitApp(arg.ConfigPath)

	httpConf := settings.HttpConf{Addr: arg.Addr}

	//region 读取数据库配置信息
	appRunner, cleanup, err := InitApp(httpConf)
	if err != nil {
		return err
	}
	defer cleanup()

	//start and wait for stop signal
	if err := appRunner.Run(); err != nil {
		return err
	}

	return nil
}
