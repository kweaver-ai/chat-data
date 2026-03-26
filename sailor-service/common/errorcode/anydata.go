package errorcode

import "github.com/kweaver-ai/chat-data/sailor-service/common/constant"

// Model Name
const (
	knowledgeNetworkModelName = constant.ServiceName + ".knowledge-network."
)

const (
	FullTextSearchEmptyError     = knowledgeNetworkModelName + "FullTextSearchEmptyError"
	AnyDataAppIDError            = knowledgeNetworkModelName + "AnyDataAppIDError"
	AnyDataServiceError          = knowledgeNetworkModelName + "AnyDataServiceError"
	AnyDataAuthError             = knowledgeNetworkModelName + "AnyDataAuthError"
	AnyDataConfigError           = knowledgeNetworkModelName + "AnyDataConfigError"
	AnyDataConnectionError       = knowledgeNetworkModelName + "AnyDataConnectionError"
	AFSailorConnectionError      = constant.ServiceName + ".AFSailorConnectionError"
	AFSailorAgentConnectionError = constant.ServiceName + ".AFSailorAgentConnectionError"
)

var knowledgeNetworkErrorMap = errorCode{
	FullTextSearchEmptyError: {
		description: "AnyDATA Framework 无数据，请登录AnyDATA Framework，重新构建数据资产图谱",
		cause:       "",
		solution:    "请检查后重试",
	},
	AnyDataAppIDError: {
		description: "获取AppID错误",
		cause:       "",
		solution:    "请检查后重试",
	},
	AnyDataServiceError: {
		description: "AnyDATA Framework 异常，请检查AnyDATA Framework",
		cause:       "",
		solution:    "请检查后重试",
	},
	AnyDataAuthError: {
		description: "AnyDATA Framework 用户名，密码 相关配置信息错误，请修改相关配置文件",
		cause:       "",
		solution:    "请修改相关配置文件",
	},
	AnyDataConfigError: {
		description: "AnyDATA Framework 配置信息错误，请修改相关配置文件",
		cause:       "",
		solution:    "请修改相关配置文件",
	},
	AnyDataConnectionError: {
		description: "AnyDATA Framework 无法连接",
		solution:    "请修改相关配置文件",
	},
	AFSailorConnectionError: {
		description: "AFSailor服务无法连接",
		solution:    "请修改查看相关服务状态",
	},
	AFSailorAgentConnectionError: {
		description: "AFSailorAgent服务无法连接",
		solution:    "请修改查看相关服务状态",
	},
}
