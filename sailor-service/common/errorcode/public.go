package errorcode

import (
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
)

// Model Name
const (
	publicModelName = constant.ServiceName + ".Public."
)

const (
	PublicInternalError            = publicModelName + "InternalError"
	PublicInvalidParameter         = publicModelName + "InvalidParameter"
	PublicInvalidParameterJson     = publicModelName + "InvalidParameterJson"
	PublicDatabaseError            = publicModelName + "DatabaseError"
	PublicResourceNotExisted       = publicModelName + "ResourceNotExisted"
	PublicInvalidParameterValue    = publicModelName + "InvalidParameterValue"
	PublicVEngineRequestBad        = publicModelName + "VEngineRequestBad"
	PublicDatabaseParameterError   = publicModelName + "DatabaseParameterError"
	PublicDataNotFoundError        = publicModelName + "DataNotFoundError"
	PublicExploreError             = publicModelName + "ExploreError"
	PublicRequestParameterError    = publicModelName + "RequestParameterError"
	UserNotHavePermission          = publicModelName + "UserNotHavePermission"
	AccessTypeNotSupport           = publicModelName + "AccessTypeNotSupport"
	GetAccessPermissionError       = publicModelName + "GetAccessPermissionError"
	TokenAuditFailed               = publicModelName + "TokenAuditFailed"
	UserNotActive                  = publicModelName + "UserNotActive"
	GetUserInfoFailed              = publicModelName + "GetUserInfoFailed"
	GetUserInfoFailedInterior      = publicModelName + "GetUserInfoFailedInterior"
	GetTokenEmpty                  = publicModelName + "GetTokenEmpty"
	ADUrlError                     = publicModelName + "ADUrlError"
	ModelTaskCenterProjectNotFound = publicModelName + "TaskCenterProjectNotFoundError"
	ADDataError                    = publicModelName + "ADDataError"
	ReportJsonMarshalError         = publicModelName + "JsonMarshalError"
	CurrentEmptyDataError          = publicModelName + "CurrentEmptyDataError"
	PublicDatabaseException        = publicModelName + "DatabaseException"
	PublicBadRequestError          = publicModelName + "BadRequest"
	PublicServiceInternalError     = publicModelName + "ServiceInternalError"
	PublicLogicalEntityError       = "PublicLogicalEntityError"
	SessionIdNotExistsError        = publicModelName + "ChatSessionError"

	NotAuthentication                     = publicModelName + "NotAuthentication"
	HydraException                        = publicModelName + "HydraException"
	AuthServiceException                  = publicModelName + "AuthServiceException"
	AuthenticationFailure                 = publicModelName + "AuthenticationFailure"
	GetUserInfoFailure                    = publicModelName + "GetUserInfoFailure"
	GetAppInfoFailure                     = publicModelName + "GetAppInfoFailure"
	GetProtonAppInfoFailure               = publicModelName + "GetProtonAppInfoFailure"
	AuthorizationFailure                  = publicModelName + "AuthorizationFailure"
	PermissionCheckFailure                = publicModelName + "PermissionCheckFailure"
	AccessControlClientTokenMustHasUserId = publicModelName + "AccessControlClientTokenMustHasUserId"

	ContextNotHaveToken    = publicModelName + "ContextNotHaveToken"
	ContextNotHaveUserInfo = publicModelName + "ContextNotHaveUserInfo"
	CallAfSailorError      = publicModelName + "CallAfSailorError"

	PublicResourceNotFoundError = publicModelName + "ResourceNotFoundError"
)

var publicErrorMap = errorCode{
	ReportJsonMarshalError: {
		description: "json.Marshal转化失败",
		cause:       "",
		solution:    "检查文件内容",
	},
	ADDataError: {
		description: "AnyData返回的数据有误",
		solution:    "请重试",
	},
	ModelTaskCenterProjectNotFound: {
		description: "该项目不存在",
		solution:    "请检查参数：project_id ",
	},
	PublicInternalError: {
		description: "内部错误",
		cause:       "",
		solution:    "",
	},
	CurrentEmptyDataError: {
		description: "暂未获取到数据",
		cause:       "",
		solution:    "请稍后重试",
	},
	PublicResourceNotExisted: {
		description: "资源不存在",
		cause:       "",
		solution:    "请检查资源是否已被删除",
	},
	PublicInvalidParameter: {
		description: "参数值校验不通过",
		cause:       "",
		solution:    "请使用请求参数构造规范化的请求字符串。详细信息参见产品 API 文档",
	},
	PublicInvalidParameterJson: {
		description: "参数值校验不通过：json格式错误",
		solution:    "请使用请求参数构造规范化的请求字符串，详细信息参见产品 API 文档",
	},
	PublicDatabaseError: {
		description: "数据库异常",
		cause:       "",
		solution:    "请检查数据库状态",
	},
	PublicRequestParameterError: {
		description: "请求参数格式错误",
		cause:       "输入请求参数格式或内容有问题",
		solution:    "请输入正确格式的请求参数",
	},
	UserNotHavePermission: {
		description: "暂无权限，您可联系系统管理员配置",
		cause:       "",
		solution:    "请重试",
	},
	AccessTypeNotSupport: {
		description: "暂不支持的访问类型",
		cause:       "",
		solution:    "请重试",
	},
	GetAccessPermissionError: {
		description: "获取访问权限失败",
		cause:       "",
		solution:    "请重试",
	},
	TokenAuditFailed: {
		description: "用户信息验证失败",
		cause:       "",
		solution:    "请重试",
	},
	UserNotActive: {
		description: "用户登录已过期",
		cause:       "",
		solution:    "请重新登陆",
	},
	GetUserInfoFailed: {
		description: "获取用户信息失败",
		cause:       "",
		solution:    "请重试",
	},
	GetUserInfoFailedInterior: {
		description: "获取用户信息失败",
		cause:       "",
		solution:    "请联系系统维护者",
	},
	GetTokenEmpty: {
		description: "获取用户信息失败",
		cause:       "",
		solution:    "请联系系统维护者",
	},
	NotAuthentication: {
		description: "无用户登录信息",
		cause:       "",
		solution:    "",
	},
	ADUrlError: {
		description: "AnyData服务异常，或url地址有误",
		solution:    "请检查AnyData服务，检查ip和端口后重试",
	},
	PublicDatabaseException: {
		description: "连接AnyFabric 数据库异常，请检AnyFabric 数据库是否可正常连接",
		solution:    "请检AnyFabric 数据库是否可正常连接",
	},
	PublicBadRequestError: {
		description: "输入参数异常，请求失败",
		solution:    "请检查参数、ip和端口后重试",
	},
	PublicServiceInternalError: {
		description: "服务异常，请求失败",
		solution:    "请检查服务后后重试",
	},
	PublicLogicalEntityError: {
		description: "logical entity id 不存在",
		solution:    "请输入正确的logical entity id",
	},
	SessionIdNotExistsError: {
		description: "session id 不存在",
		solution:    "请输入正确的session id",
	},
	PublicExploreError: {
		description: "数据探查失败",
		solution:    "请联系系统管理员，获取错误日志排查问题",
	},
	PublicDatabaseParameterError: {
		description: "数据库连接参数错误",
		solution:    "请检查提交数据库连接参数是否正确",
	},
	PublicVEngineRequestBad: {
		description: "虚拟化引擎请求失败",
		solution:    "请检查提交数据库连接参数或SQL是否正确",
	},
	PublicDataNotFoundError: {
		description: "数据未找到",
		solution:    "请检查请求参数",
	},
	HydraException: {
		description: "授权服务异常",
		cause:       "",
		solution:    "",
	},
	AuthServiceException: {
		description: "授权服务异常",
	},
	AuthenticationFailure: {
		description: "用户登录已过期",
		cause:       "",
		solution:    "",
	},
	GetUserInfoFailure: {
		description: "获取用户信息失败",
		cause:       "",
		solution:    "",
	},
	GetAppInfoFailure: {
		description: "获取应用信息失败",
		cause:       "",
		solution:    "",
	},
	GetProtonAppInfoFailure: {
		description: "获取部署控制台应用信息失败",
		cause:       "",
		solution:    "",
	},
	AuthorizationFailure: {
		description: "暂无权限，您可联系系统管理员配置",
		cause:       "",
		solution:    "",
	},
	PermissionCheckFailure: {
		description: "暂无[permission_name]权限，您可联系管理员配置",
		cause:       "",
		solution:    "请重试",
	},
	AccessControlClientTokenMustHasUserId: {
		description: "客户端token必须携带userId",
		cause:       "",
		solution:    "请重试",
	},
	ContextNotHaveToken: {
		description: "上下文中没有令牌",
		cause:       "",
		solution:    "请重试",
	},
	ContextNotHaveUserInfo: {
		description: "上下文中没有用户信息",
		cause:       "",
		solution:    "请重试",
	},
	CallAfSailorError: {
		description: "请求认知助手服务失败",
		cause:       "",
		solution:    "请检查配置及服务",
	},
	PublicResourceNotFoundError: {
		description: "资源不存在",
		solution:    "请检查参数和数据",
	},
}
