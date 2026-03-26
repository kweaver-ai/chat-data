package copilot

import (
	"context"
	"encoding/json"

	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
)

type GetDataMarketConfigReq struct {
}

type DataMarketConfig struct {
	AgentToolsPrompt           *string `json:"agent_tools_prompt,omitempty"`
	BackgroundPrompt           *string `json:"background_prompt,omitempty"`
	SearchToolsPrompt          *string `json:"search_tools_prompt,omitempty"`
	Text2sqlPrompt             *string `json:"text2sql_prompt,omitempty"`
	Text2metricPrompt          *string `json:"text2metric_prompt,omitempty"`
	DatasourceFilterPrompt     *string `json:"datasource_filter_prompt,omitempty"`
	KnowledgeEnhancementFlag   bool    `json:"knowledge_enhancement_flag"`
	KnowledgeEnhancementConfig struct {
	} `json:"knowledge_enhancement_config" binding:"required"`
}

type GetDataMarketConfigResp struct {
	Res struct {
		Configs DataMarketConfig `json:"configs"`
	} `json:"res"`
}

func GetDefaultConfig() *DataMarketConfig {
	agentToolsPrompt := "- 不要捏造工具，不要使用模拟或假设的数据，不要捏造工具的返回结果，工具有返回结果时，不需要补充数据\n- 如果问题没有明确要求要画图，默认**不要** 调用 json2plot 来绘图，直接返回结果即可，如果用户需要表格，也不需要调用\n- 你需要使用 json2plot 工具，请确保 \"title\" 参数必须和 text2sql 工具或 text2metric 工具返回的数据 \"title\" 一致，否则显示时无法匹配，工具调用成功即认为绘图成功，不需要生成url 或图的 blob 数据\n- 请慎重选择工具，如果 text2metric 工具有相关的指标，**不要**使用 text2sql 工具，**必须**使用 text2metric 工具\n- 工具输出格式中不能出现双大括号，即 `{{` 或 `}}`，例如： {{'sql': '', 'explanation': {{'a': ''}},'title': 'xx'}} 是不合法的，会导致程序崩溃\n- 你在总结问题的时候，需要以标准的markdown格式输出"
	backgroundPrompt := "此外你需要注意以下的时间处理规则：\n- 当用户没有提到具体的时间约束，默认是今年\n如果让你重新回答，那么就重新思考问题，然后输出答案"
	searchToolsPrompt := "- 如果需要反问用户，请直接结束对话\n- 在上下文中没有缓存任何数据资源，不能直接反问用户，**必须**使用 search 工具查找数据资源\n- 回答问题前，最优先的是帮助用户找到数据资源，并引导用户问出正确的问题\n- 如果 search 工具没有返回结果，不要着急结束问答，不要着急反问用户，先使用 search 搜索数据资源，确认我们是否有相关的资源，并尽量给用户提供可用的数据资源\n- 反问用户前，记得先使用 search 搜索数据资源，确认我们是否有相关的资源，并尽量给用户提供可用的数据资源，别忘了把搜索结果告诉给用户\n- 如果 search 搜索后没有找打合适的资源，不需要调用工具进行查询\n- 如果用户的问题不明确或有歧义的，你要根据数据表的描述来反问用户引导用户补全条件，并根据描述信息提示用户可以根据哪些字段和维度进行提问\n- 当用户问题不明确或有歧义的时，不要调用 text2sql 工具或 text2metric 工具，根据规则反问用户，等待用户补充问题\n- 你可以进行多次反问，并且在任何阶段都可以反问用户\n- 如果你不能理解用户问题中的某些成分时，需要反问用户，该成分属于什么实体\n- 如果搜索工具返回的结果为空，你需要反问用户\n- 如果缓存的数据资源不能支持回答用户的问题，要重新搜索\n- 你需要判断当前拿到的数据资源能否支持回答用户的问题，如果不能回答则需要重新调用 search 工具，如果可以支持回答用户的问题，则使用已有的资源回答，不需要在调用 search 工具\n- 切记不能捏造数据进行反问，否则会误导用户并导致毁灭性灾难\n- 如果你发现缺少必要字段或视图结构问题，请停止当前Action，并反问用户，引导用户补充必要条件\n- 你在反问用户时，可以给用户体统一些案例，但是你反问用户的问题，必须根据数据资源的描述来生成，不能捏造数据来反问，例如，你是不是想问以下问题 1、去年公司简称为XXX公司的营业收入是多少  2、 公司简称为XXX的证券代码是多少  3、 今年一季度每个月的销量是多少"
	text2sqlPrompt := "where 条件中如果指定查询的值为中文，请使用单引号，例如 name='张三'"
	text2metricPrompt := ""
	datasourceFilterPrompt := ""
	config := DataMarketConfig{
		AgentToolsPrompt:         &agentToolsPrompt,
		BackgroundPrompt:         &backgroundPrompt,
		SearchToolsPrompt:        &searchToolsPrompt,
		Text2sqlPrompt:           &text2sqlPrompt,
		Text2metricPrompt:        &text2metricPrompt,
		DatasourceFilterPrompt:   &datasourceFilterPrompt,
		KnowledgeEnhancementFlag: false,
	}
	return &config
}

func (u *useCase) GetDataMarketConfig(ctx context.Context, req *GetDataMarketConfigReq) (*GetDataMarketConfigResp, error) {
	configInfo, err := u.qaRepo.GetAssistantConfig(ctx)
	if err != nil {
		return nil, err
	}

	if configInfo == nil {
		resp := GetDataMarketConfigResp{}
		resp.Res.Configs = *GetDefaultConfig()
		return &resp, nil
	}

	configStr := configInfo.Config

	var config *DataMarketConfig
	err = json.Unmarshal([]byte(configStr), &config)
	if err != nil {
		return nil, err
	}
	resp := GetDataMarketConfigResp{}
	resp.Res.Configs = *config

	return &resp, nil
}

type UpdateDataMarketConfigReq struct {
	UpdateDataMarketConfigReqBody `param_type:"body"`
}

type UpdateDataMarketConfigReqBody struct {
	Configs DataMarketConfig `json:"configs"`
}

type UpdateDataMarketConfigResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) UpdateDataMarketConfig(ctx context.Context, req *UpdateDataMarketConfigReq) (*UpdateDataMarketConfigResp, error) {
	userRoles, err := u.configCenter.GetUserRoles(ctx)
	if err != nil {
		return nil, err
	}
	isAdmin := false
	//rolesList := []string{}
	for _, item := range userRoles {

		if item.Icon == "tc-system-mgm" {
			isAdmin = true
			break
		}
	}

	if isAdmin == false {
		return nil, errorcode.Detail(errorcode.UserNotHavePermission, err)
	}

	configInfo, err := u.qaRepo.GetAssistantConfig(ctx)
	if err != nil {
		return nil, err
	}
	userInfo := GetUserInfo(ctx)
	config := req.Configs

	if configInfo == nil {
		defaultConfig := GetDefaultConfig()

		if config.AgentToolsPrompt == nil {
			config.AgentToolsPrompt = defaultConfig.AgentToolsPrompt
		}
		if config.BackgroundPrompt == nil {
			config.BackgroundPrompt = defaultConfig.BackgroundPrompt
		}
		if config.SearchToolsPrompt == nil {
			config.SearchToolsPrompt = defaultConfig.SearchToolsPrompt
		}
		if config.Text2sqlPrompt == nil {
			config.Text2sqlPrompt = defaultConfig.Text2sqlPrompt
		}
		if config.Text2metricPrompt == nil {
			config.Text2metricPrompt = defaultConfig.Text2metricPrompt
		}
		if config.DatasourceFilterPrompt == nil {
			config.DatasourceFilterPrompt = defaultConfig.DatasourceFilterPrompt
		}
		configStr, _ := json.Marshal(&config)
		err = u.qaRepo.InsertAssistantConfig(ctx, userInfo.ID, "data-market", string(configStr))
		if err != nil {
			return nil, err
		}
		resp := UpdateDataMarketConfigResp{}
		resp.Res.Status = "success"
		return &resp, nil
	} else {
		var dbConfig *DataMarketConfig
		err = json.Unmarshal([]byte(configInfo.Config), &dbConfig)
		if err != nil {
			return nil, err
		}
		if config.AgentToolsPrompt == nil {
			config.AgentToolsPrompt = dbConfig.AgentToolsPrompt
		}
		if config.BackgroundPrompt == nil {
			config.BackgroundPrompt = dbConfig.BackgroundPrompt
		}
		if config.SearchToolsPrompt == nil {
			config.SearchToolsPrompt = dbConfig.SearchToolsPrompt
		}
		if config.Text2sqlPrompt == nil {
			config.Text2sqlPrompt = dbConfig.Text2sqlPrompt
		}
		if config.Text2metricPrompt == nil {
			config.Text2metricPrompt = dbConfig.Text2metricPrompt
		}
		if config.DatasourceFilterPrompt == nil {
			config.DatasourceFilterPrompt = dbConfig.DatasourceFilterPrompt
		}
		configStr, _ := json.Marshal(&config)
		err = u.qaRepo.UpdateAssistantConfig(ctx, "data-market", string(configStr))
		if err != nil {
			return nil, err
		}
		resp := UpdateDataMarketConfigResp{}
		resp.Res.Status = "success"
		return &resp, nil
	}
}

type ResetDataMarketConfigReq struct {
}

type ResetDataMarketConfigResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ResetDataMarketConfig(ctx context.Context, req *ResetDataMarketConfigReq) (*ResetDataMarketConfigResp, error) {
	userRoles, err := u.configCenter.GetUserRoles(ctx)
	if err != nil {
		return nil, err
	}
	isAdmin := false
	//rolesList := []string{}
	for _, item := range userRoles {

		if item.Icon == "tc-system-mgm" {
			isAdmin = true
		}
	}

	if isAdmin == false {
		return nil, errorcode.Detail(errorcode.UserNotHavePermission, err)
	}

	configInfo, err := u.qaRepo.GetAssistantConfig(ctx)
	if err != nil {
		return nil, err
	}

	if configInfo == nil {
		resp := ResetDataMarketConfigResp{}
		resp.Res.Status = "success"
		return &resp, nil
	} else {
		config := GetDefaultConfig()

		configStr, _ := json.Marshal(&config)
		err = u.qaRepo.UpdateAssistantConfig(ctx, "data-market", string(configStr))
		if err != nil {
			return nil, err
		}
		resp := ResetDataMarketConfigResp{}
		resp.Res.Status = "success"
		return &resp, nil
	}
}
