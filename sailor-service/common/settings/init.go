package settings

import (
	"context"

	"github.com/kweaver-ai/chat-data/sailor-service/common/form_validator"
	conf "github.com/kweaver-ai/idrm-go-frame/core/config"
	"github.com/kweaver-ai/idrm-go-frame/core/logx/zapx"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
)

type MainArgs struct {
	Name       string //服务名称
	Version    string //系统版本
	ConfigPath string //配置文件地址
	Addr       string //监听地址
}

func InitApp(configPath string) {
	//加载配置文件
	conf.InitSources(configPath)

	//init application controller
	globalConfig := conf.Scan[Config]()
	ResetConfig(&globalConfig)
	//初始化全局静态变量
	Init()

	//初始化日志
	options := conf.Scan[zapx.LogConfigs]()
	tc := GetConfig().Telemetry
	log.InitLogger(options.Logs, &tc)

	// 初始化trace
	if tc.TraceEnabled {
		tracerProvider := trace.InitTracer(&tc, "")
		defer func() {
			if err := tracerProvider.Shutdown(context.Background()); err != nil {
				panic(err)
			}
		}()
	}

	//初始化验证器
	form_validator.SetupValidator()
}
