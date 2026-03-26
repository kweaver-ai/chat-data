package copilot

import (
	"bufio"
	"bytes"
	"compress/gzip"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
	"github.com/samber/lo"
)

// 获取session_id

type ChatGetSessionReq struct {
	ChatGetSessionReqBody `param_type:"query"`
}

type ChatGetSessionReqBody struct {
	SessionType string `json:"session_type" binding:"omitempty"`
}

type ChatGetSessionResp struct {
	Res struct {
		SessionId string `json:"session_id"`
	} `json:"res"`
}

func (u *useCase) ChatGetSession(ctx context.Context, req *ChatGetSessionReq) (*ChatGetSessionResp, error) {
	userInfo := GetUserInfo(ctx)
	args := make(map[string]any)
	args["user_id"] = userInfo.ID
	//请求
	adResp, err := u.afSailorAgent.SailorGetSessionEngine(ctx, args)
	if err != nil {
		return nil, err
	}
	if req.SessionType != "data_application" {
		err = u.qaRepo.InsertChatHistory(ctx, userInfo.ID, adResp.Res)
		if err != nil {
			return nil, err
		}
	}

	chatSession := ChatGetSessionResp{}

	chatSession.Res.SessionId = adResp.Res

	return &chatSession, nil
}

// 多轮对话
type SailorChatReq struct {
	//SSEReqBody `param_type:"body"`
	SailorChatReqBody `param_type:"query"`
}

type SailorChatReqBody struct {
	Query          string `json:"query" form:"query" binding:"required"`
	AssetType      string `json:"asset_type" form:"asset_type"`
	DataVersion    string `json:"data_version" form:"data_version" binding:"required"`
	SessionId      string `json:"session_id" form:"session_id" binding:"required"`
	ChatType       string `json:"chat_type" form:"chat_type" binding:"omitempty,oneof=chat data_market_qa"`
	Resource       string `json:"resource" form:"resource"`
	IfDisplayGraph bool   `json:"if_display_graph" form:"if_display_graph"`
}

type ResourceItem struct {
	Id   string `json:"id"`
	Type string `json:"type"`
	Name string `json:"name"`
}

type SailorAnswerItem struct {
	Cites []struct {
		Id                string `json:"id"`
		Code              string `json:"code"`
		Type              string `json:"type"`
		Title             string `json:"title"`
		Description       string `json:"description"`
		ConnectedSubgraph struct {
			Nodes []any `json:"nodes"`
			Edges []any `json:"edges"`
		} `json:"connected_subgraph"`

		Sql struct {
			Sql string `json:"sql"`
		} `json:"sql,omitempty"`
	} `json:"cites"`
	Table []any    `json:"table"`
	Text  []string `json:"text"`
	Chart []any    `json:"chart"`

	Explain []struct {
		Method string `json:"method"`
		Url    string `json:"url"`
		Params string `json:"params"`
		Title  string `json:"title"`
		Sql    string `json:"sql"`
	} `json:"explain"`
}

type SailorAnswer struct {
	Result struct {
		Status string           `json:"status"`
		Res    SailorAnswerItem `json:"res"`

		Logs SailorAnswerLog `json:"logs,omitempty"`
	} `json:"result"`
}
type SailorAnswerLog []struct {
	Thought   string `json:"thought"`
	ToolName  string `json:"tool_name"`
	ToolInput struct {
		Question              string `json:"question"`
		ExtraneousInformation string `json:"extraneous_information"`
	} `json:"tool_input"`
	Result map[string]any `json:"result"`
	Time   string         `json:"time"`
	Tokens string         `json:"tokens"`
}

type SailorAnswerStruct struct {
	Answer []SailorAnswerItem `json:"answer"`
	Logs   SailorAnswerLog    `json:"logs,omitempty"`
}

func (u *useCase) SailorChat(c *gin.Context, req *SailorChatReq) (err error) {
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()
	answerId, err := uuid.NewRandom()
	if err != nil {
		fmt.Printf("%v\n", err)
	}
	//log.WithContext(c).Infof()
	inputQuery := strings.TrimSpace(req.Query)

	if len(inputQuery) == 0 {
		errors.Wrap(err, "input query can not be empty string")
		return err
	}

	sessionId := req.SessionId
	chatInfo, err := u.qaRepo.GetChatHistoryBySession(c, sessionId)
	if err != nil {
		return err
	}
	if chatInfo == nil {
		return errorcode.Detail(errorcode.SessionIdNotExistsError, err)
	}

	dataVersion := req.DataVersion

	//traceId := "helloworld"
	//AddChannel(traceId)
	//fmt.Println(req, "========")
	//log.WithContext(c).Infof("CopilotQa-Input:" + req.Query)

	w := c.Writer
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	answer := ""
	answerStruct := SailorAnswerStruct{}
	flusher, ok := w.(http.Flusher)
	if !ok {
		log.Panic("server not support")
		return errorcode.Detail(errorcode.PublicInternalError, err)
	}

	log.WithContext(c).Infof("chat input: answer_id:%s query:%s", answerId, req.Query)

	startDataInfo := map[string]any{}
	result := map[string]string{}
	result["qa_id"] = answerId.String()
	result["status"] = "search"
	result["source"] = "af-sailor-service"
	startDataInfo["result"] = result
	startDataInfoStr, er := json.Marshal(startDataInfo)
	if er != nil {
		return er
	}
	fmt.Fprintf(w, "data: %s\n\n", startDataInfoStr)
	flusher.Flush()

	args := make(map[string]any)
	//args["check_af_query"] = adReq

	args["query"] = req.Query
	args["limit"] = 100
	args["session_id"] = req.SessionId
	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}

	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	myFilter["data_kind"] = "0"
	myFilter["update_cycle"] = []int{-1}
	myFilter["shared_type"] = []int{-1}
	myFilter["department_id"] = []int{-1}
	myFilter["info_system_id"] = []int{-1}
	myFilter["owner_id"] = []int{-1}
	myFilter["subject_id"] = []int{-1}
	myFilter["publish_status_category"] = []int{-1}
	myFilter["online_status"] = []int{-1}
	myFilter["start_time"] = "1600122122"
	myFilter["end_time"] = "1800122122"
	if req.AssetType == "all" {
		myFilter["asset_type"] = []int{-1}
	} else if req.AssetType == "data_catalog" {
		myFilter["asset_type"] = []int{1}
	} else if req.AssetType == "interface_svc" {
		myFilter["asset_type"] = []int{2}
	} else if req.AssetType == "data_view" {
		myFilter["asset_type"] = []int{3}
	} else if req.AssetType == "indicator" {
		myFilter["asset_type"] = []int{4}
	} else {
		myFilter["asset_type"] = []int{-1}
	}

	myFilter["stop_entity_infos"] = []StopEntityInfo{}

	//sEntityInfo := StopEntityInfo{}
	//
	//myFilter.StopEntityInfos

	args["filter"] = myFilter

	ifDisplayGraph := req.IfDisplayGraph
	ifDisplayGraph = true

	// 获取graphId
	kgConfigId := ""
	if dataVersion == constant.DataCatalogVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	} else if dataVersion == constant.DataResourceVersion {
		ifDisplayGraph = false
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	} else {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	}

	args["if_display_graph"] = ifDisplayGraph

	// 获取appid
	appid, err := u.adProxy.GetAppId(c)
	if err != nil {
		return err
	}

	args["ad_appid"] = appid

	resourceEncoder := req.Resource
	resourceDecodedStr := ""
	var resourceReq []map[string]string
	if len(resourceEncoder) > 0 {
		resourceDecodedBytes, err := base64.StdEncoding.DecodeString(resourceEncoder)
		if err != nil {
			log.WithContext(c).Infof("Error decoding:%s", err)
			return err
		}

		// 将解码后的字节切片转换为字符串
		resourceDecodedStr = string(resourceDecodedBytes)
		log.WithContext(c).Infof("Decoded String:%s", resourceDecodedStr)

		var resourceArray []*ResourceItem
		err = json.Unmarshal([]byte(resourceDecodedStr), &resourceArray)
		if err != nil {
			fmt.Println("unjson 失败")
			return err
		}

		for _, item := range resourceArray {
			itType := "0"
			switch item.Type {
			case "data_catalog":
				itType = "1"
			case "interface_svc":
				itType = "2"
			case "data_view":
				itType = "3"
			case "indicator":
				itType = "4"
			default:
				continue
			}
			resourceReq = append(resourceReq, map[string]string{"id": item.Id, "type": itType, "name": item.Name})
		}
		args["resources"] = resourceReq

	}

	if len(resourceReq) == 0 {
		graphId, err := u.getGraphId(c, kgConfigId)
		if err != nil {
			return err
		}
		graphIdInt, err := strconv.Atoi(graphId)
		if err != nil {
			return err
		}
		args["kg_id"] = graphIdInt
	} else {
		args["kg_id"] = -1
	}

	args["entity2service"] = map[string]string{}

	// 这里暂时写死
	required_resource := make(map[string]any)
	if len(resourceReq) == 0 {
		lexicon_actrieId, err := u.getAdLexiconId(c, "cognitive_search_synonyms")
		if err != nil {
			return err
		}
		required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

		// 这里暂时写死
		stopwordsId, err := u.getAdLexiconId(c, "cognitive_search_stopwords")
		if err != nil {
			return err
		}
		required_resource["stopwords"] = lexiconInfo{stopwordsId}
	}

	args["required_resource"] = required_resource
	args["stream"] = true
	uInfo := GetUserInfo(c)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"

	if dataVersion == constant.DataCatalogVersion {
		args["af_editions"] = "catalog"
	} else {
		args["af_editions"] = "resource"
	}

	userRoles, err := u.configCenter.GetUserRoles(c)
	if err != nil {
		return err
	}
	rolesList := []string{}
	for _, item := range userRoles {

		rolesList = append(rolesList, item.Icon)
	}

	args["roles"] = rolesList

	//log.Infof("=======, %s", resourceEncoder)

	// 数据服务超市内部配置
	faker_req := GetDataMarketConfigReq{}
	configs, err := u.GetDataMarketConfig(c, &faker_req)
	if err != nil {
		args["configs"] = map[string]any{}
	} else {
		args["configs"] = configs.Res.Configs
	}

	log.WithContext(c).Infof("\nreq vo:\n%s\n", lo.T2(json.Marshal(args)).A)

	var body = bytes.NewReader(lo.T2(json.Marshal(args)).A)

	reqsse, _ := http.NewRequest("POST", settings.GetConfig().AfSailorAgentConf.URL+"/api/af-sailor-agent/v1/assistant/chat", body)
	reqsse.Header.Set("Accept", "text/event-stream")
	authorization := c.GetHeader("Authorization")
	//fmt.Println("Authorization:" + authorization)
	reqsse.Header.Set("Authorization", authorization)
	client := &http.Client{}

	res, err := client.Do(reqsse)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	reader := bufio.NewReader(res.Body)
	//closeNotify := c.Request.Context().Done()
	//go func() {
	//	<-closeNotify
	//	delete(channelsMap, traceId)
	//	log.Infof("SSE close for trace id = " + traceId)
	//	//fmt.Println("SSE close for trace id = " + traceId)
	//	return
	//}()
	//ctx := c.Request.Context()
	notify := w.(http.CloseNotifier).CloseNotify()
	//w.CloseNotify()
	//go func() {
	//	<-notify
	//	fmt.Println("SSE client connection closed")
	//	// 在这里，你可以执行清理操作或通知其他goroutine
	//}()
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	// 连续空字符串字数
	emptyStringTime := 0

	for {

		line, _ := reader.ReadString('\n')
		if line == "\n" || line == "\r\n" || line == "" {
			// 一个完整的事件读取完成
			emptyStringTime += 1
			if emptyStringTime < 2 {
				continue
			} else {
				log.Infof("emptyStringTime %d out limit %d, stop chat", emptyStringTime, 2)
				break
			}

		}
		emptyStringTime = 0

		fields := strings.SplitN(line, ":", 2)
		if len(fields) < 2 {
			continue
		}
		log.WithContext(c).Infof("\nsailor-agent output: qa_id:%s answer:%s", answerId, line)
		state := 0
		select {
		//case <-ticker.C:

		case <-notify:
			log.WithContext(c).Infof("receive chat %s client close notify", answerId)
			state = 1
			break

		default:
			log.Info("chat send info")

		}
		if state == 1 {
			log.WithContext(c).Infof("chat %s server close", answerId)
			break
		}

		switch fields[0] {
		case "event":
			fmt.Fprintf(w, "event: %s\n", fields[1])
		case "data":

			dataInfo := make(map[string]map[string]any)

			err := json.Unmarshal([]byte(fields[1]), &dataInfo)
			if err != nil {
				fmt.Println("unjson 失败ing")
				log.WithContext(c).Infof(err.Error())
				continue
			}
			answer += fields[1]

			if dataInfo["result"]["status"] == "answer" {
				answerItem := SailorAnswer{}
				err := json.Unmarshal([]byte(fields[1]), &answerItem)
				if err == nil {
					//fmt.Println("unjson 失败")
					answerStruct.Answer = append(answerStruct.Answer, answerItem.Result.Res)
					answerStruct.Logs = answerItem.Result.Logs
				} else {
					log.WithContext(c).Infof(err.Error())
				}

			}
			_, errr := w.Write([]byte("data: " + fields[1] + "\n"))
			if errr != nil {
				log.WithContext(c).Errorf("chat %s close, can not write", answerId)
				break
			}

		case "id":
			fmt.Fprintf(w, "id: %s\n", fields[1])
		case "retry":
			fmt.Fprintf(w, "retry: %s\n", fields[1])
		}

		flusher.Flush()
		time.Sleep(200 * time.Millisecond)

	}

	log.WithContext(c).Infof("chat %s end", answerId)
	if len(answerStruct.Answer) == 0 {
		log.WithContext(c).Infof("chat %s answer num zero /(ㄒoㄒ)/~~", answerId)
		return nil
		//return errorcode.Detail(errorcode.PublicInternalError, err)
	}
	chatType := req.ChatType
	if chatType == "" {
		chatType = constant.ChatGoing
	}
	//fmt.Println(chatType)
	if chatInfo.Status == constant.ChatReady {
		err = u.qaRepo.UpdateChatHistoryTitle(c, sessionId, chatType, req.Query)
		if err != nil {
			return err
		}
	}
	answerStruct.Answer = answerStruct.Answer[len(answerStruct.Answer)-1:]

	answerStr, _ := json.Marshal(&answerStruct)
	saveData := string(answerStr)
	saveStatus := ""
	if len(answerStr) > 7000 {
		log.Infof("before Compressed data length: %d", len(answerStr))
		compressedData, _ := gzipString(string(answerStr))
		log.Infof("Compressed data length: %d", len(compressedData))
		saveData = base64.StdEncoding.EncodeToString(compressedData)
		log.Infof("base64Data data length: %d", len(saveData))
		saveStatus = "gzip_data"
	}

	err = u.qaRepo.InsertChatHistoryDetail(c, sessionId, answerId.String(), inputQuery, saveData, resourceDecodedStr, saveStatus)
	if err != nil {
		return err
	}
	return nil
}

func gzipString(s string) ([]byte, error) {
	var buf bytes.Buffer
	zw := gzip.NewWriter(&buf)
	_, err := zw.Write([]byte(s))
	if err != nil {
		return nil, err
	}
	err = zw.Close()
	if err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func ungzipString(data []byte) (string, error) {
	zr, err := gzip.NewReader(bytes.NewReader(data))
	if err != nil {
		return "", err
	}
	defer zr.Close()
	uncompressedData, err := ioutil.ReadAll(zr)
	if err != nil {
		return "", err
	}
	return string(uncompressedData), nil
}

// 多轮对话
type SailorChatPostReq struct {
	//SSEReqBody `param_type:"body"`
	SailorChatReqPostBody `param_type:"body"`
}

type SailorChatReqPostBody struct {
	Query       string `json:"query" binding:"required"`
	AssetType   string `json:"asset_type"`
	DataVersion string `json:"data_version" binding:"required"`
	SessionId   string `json:"session_id" binding:"required"`
	ChatType    string `json:"chat_type" binding:"omitempty,oneof=chat data_market_qa"`
	Resource    []struct {
		Id   string `json:"id"`
		Type string `json:"type"`
		Name string `json:"name"`
	} `json:"resource"`
}

func (u *useCase) SailorChatPost(c *gin.Context, req *SailorChatPostReq) (err error) {
	//ctx, span := trace.StartInternalSpan(ctx)
	//defer func() { trace.TelemetrySpanEnd(span, err) }()
	answerId, err := uuid.NewRandom()
	if err != nil {
		fmt.Printf("%v\n", err)
	}
	//log.WithContext(c).Infof()
	inputQuery := strings.TrimSpace(req.Query)

	if len(inputQuery) == 0 {
		errors.Wrap(err, "input query can not be empty string")
		return err
	}

	sessionId := req.SessionId
	chatInfo, err := u.qaRepo.GetChatHistoryBySession(c, sessionId)
	if err != nil {
		return err
	}
	if chatInfo == nil {
		return errorcode.Detail(errorcode.SessionIdNotExistsError, err)
	}

	dataVersion := req.DataVersion

	//traceId := "helloworld"
	//AddChannel(traceId)
	//fmt.Println(req, "========")
	//log.WithContext(c).Infof("CopilotQa-Input:" + req.Query)

	w := c.Writer
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	answer := ""
	answerStruct := SailorAnswerStruct{}
	flusher, ok := w.(http.Flusher)
	if !ok {
		log.Panic("server not support")
		return errorcode.Detail(errorcode.PublicInternalError, err)
	}

	log.WithContext(c).Infof("\nchat input: answer_id:%s query:%s", answerId, req.Query)
	startDataInfo := map[string]any{}
	result := map[string]string{}
	result["qa_id"] = answerId.String()
	result["status"] = "search"
	result["source"] = "af-sailor-service"
	startDataInfo["result"] = result
	startDataInfoStr, er := json.Marshal(startDataInfo)
	if er != nil {
		return er
	}
	fmt.Fprintf(w, "data: %s\n\n", startDataInfoStr)
	flusher.Flush()

	args := make(map[string]any)
	//args["check_af_query"] = adReq

	args["query"] = req.Query
	args["limit"] = 100
	args["session_id"] = req.SessionId
	args["stopwords"] = []string{}
	args["stop_entities"] = []string{}

	myFilter := make(map[string]any)
	//myFilter["data_kind"] = fmt.Sprintf("%d", req.DataKind[0])
	myFilter["data_kind"] = "0"
	myFilter["update_cycle"] = "[-1]"
	myFilter["shared_type"] = "[-1]"
	myFilter["department_id"] = "[-1]"
	myFilter["info_system_id"] = "[-1]"
	myFilter["owner_id"] = "[-1]"
	myFilter["subject_id"] = "[-1]"
	myFilter["start_time"] = "1600122122"
	myFilter["end_time"] = "1800122122"
	if req.AssetType == "all" {
		myFilter["asset_type"] = "[-1]"
	} else if req.AssetType == "data_catalog" {
		myFilter["asset_type"] = "[1]"
	} else if req.AssetType == "interface_svc" {
		myFilter["asset_type"] = "[2]"
	} else if req.AssetType == "data_view" {
		myFilter["asset_type"] = "[3]"
	} else if req.AssetType == "indicator" {
		myFilter["asset_type"] = "[4]"
	} else {
		myFilter["asset_type"] = "[-1]"
	}

	myFilter["stop_entity_infos"] = []StopEntityInfo{}

	args["filter"] = myFilter

	// 获取graphId
	kgConfigId := ""
	if dataVersion == constant.DataCatalogVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataCatalogGraphConfigId
	} else if dataVersion == constant.DataResourceVersion {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	} else {
		kgConfigId = settings.GetConfig().KnowledgeNetworkResourceMap.CognitiveSearchDataResourceGraphConfigId
	}

	graphId, err := u.getGraphId(c, kgConfigId)
	if err != nil {
		return err
	}
	// 获取appid
	appid, err := u.adProxy.GetAppId(c)
	if err != nil {
		return err
	}

	args["ad_appid"] = appid
	graphIdInt, err := strconv.Atoi(graphId)
	if err != nil {
		return err
	}
	args["kg_id"] = graphIdInt
	//args["entity2service"] = make(map[string]any)
	//entity2service, err := u.GetCognitiveSearchConfig(c, dataVersion)
	//if err != nil {
	//	return err
	//}
	args["entity2service"] = map[string]string{}

	// 这里暂时写死
	required_resource := make(map[string]any)
	lexicon_actrieId, err := u.getAdLexiconId(c, "cognitive_search_synonyms")
	if err != nil {
		return err
	}
	required_resource["lexicon_actrie"] = lexiconInfo{lexicon_actrieId}

	// 这里暂时写死
	stopwordsId, err := u.getAdLexiconId(c, "cognitive_search_stopwords")
	if err != nil {
		return err
	}
	required_resource["stopwords"] = lexiconInfo{stopwordsId}

	args["required_resource"] = required_resource
	args["stream"] = true
	uInfo := GetUserInfo(c)
	args["subject_id"] = uInfo.ID
	args["subject_type"] = "user"
	args["resource"] = req.Resource

	if dataVersion == constant.DataCatalogVersion {
		args["af_editions"] = "catalog"
	} else {
		args["af_editions"] = "resource"
	}

	log.WithContext(c).Infof("\nreq vo:\n%s\n", lo.T2(json.Marshal(args)).A)

	//var bodyStr string
	var body = bytes.NewReader(lo.T2(json.Marshal(args)).A)

	reqsse, _ := http.NewRequest("POST", settings.GetConfig().AfSailorAgentConf.URL+"/api/af-sailor-agent/v1/assistant/chat", body)
	reqsse.Header.Set("Accept", "text/event-stream")
	authorization := c.GetHeader("Authorization")
	//fmt.Println("Authorization:" + authorization)
	reqsse.Header.Set("Authorization", authorization)
	client := &http.Client{}

	res, err := client.Do(reqsse)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	reader := bufio.NewReader(res.Body)
	//closeNotify := c.Request.Context().Done()
	//go func() {
	//	<-closeNotify
	//	delete(channelsMap, traceId)
	//	log.Infof("SSE close for trace id = " + traceId)
	//	//fmt.Println("SSE close for trace id = " + traceId)
	//	return
	//}()
	//ctx := c.Request.Context()
	notify := w.(http.CloseNotifier).CloseNotify()
	//w.CloseNotify()
	//go func() {
	//	<-notify
	//	fmt.Println("SSE client connection closed")
	//	// 在这里，你可以执行清理操作或通知其他goroutine
	//}()
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {

		line, _ := reader.ReadString('\n')
		if line == "\n" || line == "\r\n" || line == "" {
			// 一个完整的事件读取完成
			break
		}

		fields := strings.SplitN(line, ":", 2)
		if len(fields) < 2 {
			continue
		}
		log.WithContext(c).Infof("\nsailor-agent output: qa_id:%s answer:%s", answerId, line)
		state := 0
		select {
		//case <-ticker.C:

		case <-notify:
			log.WithContext(c).Infof("receive chat %s client close notify", answerId)
			state = 1
			break

		default:
			log.Info("chat send info")

		}
		if state == 1 {
			log.WithContext(c).Infof("chat %s server close", answerId)
			break
		}

		switch fields[0] {
		case "event":
			fmt.Fprintf(w, "event: %s\n", fields[1])
		case "data":

			dataInfo := make(map[string]map[string]any)

			err := json.Unmarshal([]byte(fields[1]), &dataInfo)
			if err != nil {
				fmt.Println("unjson 失败")
				log.WithContext(c).Infof(err.Error())
				continue
			}
			answer += fields[1]

			if dataInfo["result"]["status"] == "answer" {
				answerItem := SailorAnswer{}
				err := json.Unmarshal([]byte(fields[1]), &answerItem)
				if err == nil {
					//fmt.Println("unjson 失败")
					answerStruct.Answer = append(answerStruct.Answer, answerItem.Result.Res)
					answerStruct.Logs = answerItem.Result.Logs
				} else {
					log.WithContext(c).Infof(err.Error())
				}

			}
			_, errr := w.Write([]byte("data: " + fields[1] + "\n"))
			if errr != nil {
				log.WithContext(c).Errorf("chat %s close, can not write", answerId)
				break
			}

			//_, errr := fmt.Fprintf(w, "data: "+fields[1]+"\n")

		case "id":
			fmt.Fprintf(w, "id: %s\n", fields[1])
		case "retry":
			fmt.Fprintf(w, "retry: %s\n", fields[1])
		}

		flusher.Flush()
		time.Sleep(1 * time.Second)

	}

	log.WithContext(c).Infof("chat %s end", answerId)
	if len(answerStruct.Answer) == 0 {
		log.WithContext(c).Infof("chat %s answer num zero /(ㄒoㄒ)/~~", answerId)
		return nil
		//return errorcode.Detail(errorcode.PublicInternalError, err)
	}
	chatType := req.ChatType
	if chatType == "" {
		chatType = constant.ChatGoing
	}
	//fmt.Println(chatType)
	if chatInfo.Status == constant.ChatReady {
		err = u.qaRepo.UpdateChatHistoryTitle(c, sessionId, chatType, req.Query)
		if err != nil {
			return err
		}
	}
	answerStr, _ := json.Marshal(&answerStruct)
	err = u.qaRepo.InsertChatHistoryDetail(c, sessionId, answerId.String(), inputQuery, string(answerStr), "", "")
	if err != nil {
		return err
	}
	return nil
}

// 获取历史记录列表
type ChatGetHistoryListReq struct {
}

type ChatHistoryItem struct {
	SessionId string `json:"session_id"`
	Title     string `json:"title"`
	UpdatedAt *int64 `json:"updated_at"`
}

type ChatGetHistoryListResp struct {
	Res []ChatHistoryItem `json:"res"`
}

func (u *useCase) ChatHistoryList(ctx context.Context, req *ChatGetHistoryListReq) (*ChatGetHistoryListResp, error) {
	var err error
	userInfo := GetUserInfo(ctx)
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatGetHistoryListResp

	chatHistory, err := u.qaRepo.GetChatHistoryList(ctx, userInfo.ID)
	if chatHistory == nil {

		return &resp, nil
	}

	for _, item := range chatHistory {
		updateTime := item.UpdatedAt.Unix()
		resp.Res = append(resp.Res, ChatHistoryItem{item.SessionId, item.Title, &updateTime})
	}

	//data := `{"person_name":"xiaoming","person_age":18}`

	return &resp, nil
}

// 获取历史记录详情
type ChatGetHistoryDetailReq struct {
}

type ChatDetailItem struct {
	QaId     string           `json:"qa_id"`
	Query    string           `json:"query"`
	Answer   SailorAnswerItem `json:"answer"`
	Logs     SailorAnswerLog  `json:"logs,omitempty"`
	Like     string           `json:"like"`
	QaTime   int64            `json:"qa_time"`
	Resource []*ResourceItem  `json:"resource"`
}

type ChatGetHistoryDetailResp struct {
	Res        []ChatDetailItem `json:"res"`
	SessionId  string           `json:"session_id"`
	FavoriteId string           `json:"favorite_id"`
}

func (u *useCase) ChatHistoryDetail(ctx context.Context, req *ChatGetHistoryDetailReq, sessionId string) (*ChatGetHistoryDetailResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatGetHistoryDetailResp

	chatInfo, err := u.qaRepo.GetChatHistoryBySession(ctx, sessionId)
	if err != nil {
		return nil, err
	}
	if chatInfo == nil {
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	chatDetail, err := u.qaRepo.GetChatHistoryDetail(ctx, sessionId)
	if chatDetail == nil {
		return nil, errorcode.Detail(errorcode.PublicInternalError, err)
	}

	resp.SessionId = sessionId
	resp.FavoriteId = chatInfo.FavoriteId
	if chatDetail == nil {
		resp.Res = []ChatDetailItem{}
		return &resp, err
	}

	for _, item := range chatDetail {
		answerItemStruct := SailorAnswerStruct{}
		if item.Status == "gzip_data" {
			retrievedBinaryData, _ := base64.StdEncoding.DecodeString(item.Answer)
			uncompressedString, _ := ungzipString(retrievedBinaryData)
			_ = json.Unmarshal([]byte(uncompressedString), &answerItemStruct)

		} else {
			_ = json.Unmarshal([]byte(item.Answer), &answerItemStruct)
		}

		qaTime := item.CreatedAt.Unix()

		resourceList := []*ResourceItem{}
		if len(item.ResourceRequired) > 0 {
			err = json.Unmarshal([]byte(item.ResourceRequired), &resourceList)
			if err != nil {
				log.WithContext(ctx).Error("parse ResourceItem fail")
				continue
			}
		}
		resp.Res = append(resp.Res, ChatDetailItem{item.QaId, item.Query, answerItemStruct.Answer[len(answerItemStruct.Answer)-1], answerItemStruct.Logs, item.Like, qaTime, resourceList})
	}

	return &resp, nil
}

type ChatDeleteHistoryReq struct {
}

type ChatDeleteHistoryResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatDeleteHistory(ctx context.Context, req *ChatDeleteHistoryReq, sessionId string) (*ChatDeleteHistoryResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatDeleteHistoryResp

	err = u.qaRepo.UpdateChatHistory(ctx, sessionId, constant.ChatDelete)
	if err != nil {
		return nil, err
	}

	resp.Res.Status = "success"

	return &resp, nil
}

type ChatFavoriteItem struct {
	FavoriteId string `json:"favorite_id"`
	Title      string `json:"title"`
	UpdatedAt  int64  `json:"updated_at"`
}

// 获取收藏记录列表
type ChatGetFavoriteListReq struct {
}

type ChatGetFavoriteListResp struct {
	Res []ChatFavoriteItem `json:"res"`
}

func (u *useCase) ChatFavoriteList(ctx context.Context, req *ChatGetFavoriteListReq) (*ChatGetFavoriteListResp, error) {
	var err error
	userInfo := GetUserInfo(ctx)
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatGetFavoriteListResp
	//resp.Res = []QaRecordOut{}

	chatFavoriteList, err := u.qaRepo.GetChatFavoriteList(ctx, userInfo.ID)
	if err != nil {
		return nil, err
	}
	if len(chatFavoriteList) == 0 {
		resp.Res = []ChatFavoriteItem{}
		return &resp, nil
	}
	for _, item := range chatFavoriteList {
		updateTime := item.FavoriteAt.Unix()
		resp.Res = append(resp.Res, ChatFavoriteItem{item.FavoriteId, item.Title, updateTime})
	}

	//data := `{"person_name":"xiaoming","person_age":18}`

	return &resp, nil
}

// 获取多轮问答收藏记录详情
type ChatGetFavoriteDetailReq struct {
}

type ChatGetFavoriteDetailResp struct {
	Res       []ChatDetailItem `json:"res"`
	SessionId string           `json:"session_id"`
}

func (u *useCase) ChatFavoriteDetail(ctx context.Context, req *ChatGetFavoriteDetailReq, favoriteId string) (*ChatGetFavoriteDetailResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatGetFavoriteDetailResp

	//chatInfo, err := u.qaRepo.GetChatHistoryBySession(ctx, sessionId)
	//	//if err != nil {
	//	//	return nil, err
	//	//}
	sessionId := ""

	chatFavorite, err := u.qaRepo.GetChatDetailByFavorite(ctx, favoriteId)
	if err != nil {

		return nil, err
	}

	for _, item := range chatFavorite {
		answerItemStruct := SailorAnswerStruct{}
		_ = json.Unmarshal([]byte(item.Answer), &answerItemStruct)
		qaTime := item.CreatedAt.Unix()
		sessionId = item.SessionId

		resourceList := []*ResourceItem{}
		if len(item.ResourceRequired) > 0 {
			err = json.Unmarshal([]byte(item.ResourceRequired), &resourceList)
			if err != nil {
				log.WithContext(ctx).Error("parse ResourceItem fail")
				continue
			}
		}

		resp.Res = append(resp.Res, ChatDetailItem{item.QaId, item.Query, answerItemStruct.Answer[len(answerItemStruct.Answer)-1], answerItemStruct.Logs, item.Like, qaTime, resourceList})
	}
	resp.SessionId = sessionId

	return &resp, nil
}

// 收藏问答记录
type ChatPostFavoriteReq struct {
	//SessionId string `json:"session_id"`
}

type ChatPostFavoriteResp struct {
	Res struct {
		Status     string `json:"status"`
		FavoriteId string `json:"favorite_id"`
	} `json:"res"`
}

func (u *useCase) ChatPostFavorite(ctx context.Context, req *ChatPostFavoriteReq, sessionId string) (*ChatPostFavoriteResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatPostFavoriteResp

	favoriteId, err := uuid.NewRandom()
	if err != nil {
		return &resp, err
	}

	err = u.qaRepo.AddChatFavorite(ctx, sessionId, favoriteId.String())
	if err != nil {
		return &resp, nil
	}

	err = u.qaRepo.UpdateChatHistoryDetailFavorite(ctx, sessionId, favoriteId.String())
	if err != nil {
		return &resp, nil
	}

	//// 插入问答记录
	//chatDetail, err := u.qaRepo.GetChatHistoryDetail(ctx, sessionId)
	//
	//for _, item := range chatDetail {
	//	_ = u.qaRepo.InsertChatFavoriteDetail(ctx, favoriteId.String(), item.QaId, item.Query, item.Answer, item.Like)
	//}

	resp.Res.Status = "success"
	resp.Res.FavoriteId = favoriteId.String()

	return &resp, nil
}

// 更新同步收藏问答
type ChatPutFavoriteReq struct {
	//SessionId string `json:"session_id"`
}

// 更新同步收藏问答
type ChatPutFavoriteResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatPutFavorite(ctx context.Context, req *ChatPutFavoriteReq, sessionId string) (*ChatPutFavoriteResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatPutFavoriteResp

	chatInfo, err := u.qaRepo.GetChatHistoryBySession(ctx, sessionId)
	if err != nil {
		return nil, err
	}

	err = u.qaRepo.UpdateChatHistoryDetailFavorite(ctx, sessionId, chatInfo.FavoriteId)
	if err != nil {
		return &resp, nil
	}

	resp.Res.Status = "success"

	return &resp, nil
}

// 删除收藏问答记录
type ChatDeleteFavoriteReq struct {
}

type ChatDeleteFavoriteResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatDeleteFavorite(ctx context.Context, req *ChatDeleteFavoriteReq, favoriteId string) (*ChatDeleteFavoriteResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatDeleteFavoriteResp

	err = u.qaRepo.DeleteChatFavorite(ctx, favoriteId)
	if err != nil {

		return &resp, nil
	}

	resp.Res.Status = "success"

	return &resp, nil
}

// 点赞 点踩
type ChatQaLikeReq struct {
	ChatQaLikeBody `param_type:"body"`
}
type ChatQaLikeBody struct {
	Action    string `json:"action" binding:"required"`
	SessionId string `json:"session_id"`
}

type ChatQaLikeResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatQaLike(ctx context.Context, req *ChatQaLikeReq, QAId string) (*ChatQaLikeResp, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()
	var resp ChatQaLikeResp
	if req.Action == "cancel" {
		req.Action = "neutrality"
	}
	err = u.qaRepo.UpdateChatStatus(ctx, QAId, req.Action)
	if err != nil {
		return nil, err
	}
	resp.Res.Status = "success"

	return &resp, nil
}

// 获取反馈结果
type ChatFeedbackReq struct {
	ChatFeedbackReqBody `param_type:"body"`
}

type ChatFeedbackReqBody struct {
	SessionId string `json:"session_id"`
	//QAId      string `json:"qa_id"`
	Option []string `json:"option"`
	Remark string   `json:"remark"`
	File   string   `json:"file"`
}

type ChatFeedbackResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatFeedback(ctx context.Context, req *ChatFeedbackReq, QAId string) (*ChatFeedbackResp, error) {

	uInfo := GetUserInfo(ctx)
	log.WithContext(ctx).Infof("\nuser_id:%s session_id:%s answer_id:%s feedback_option:%s remark:%s", uInfo.ID, req.SessionId, QAId, strings.Join(req.Option, ", "), req.Remark)
	var resp ChatFeedbackResp

	resp.Res.Status = "success"

	return &resp, nil
}

type ChatToChatReq struct {
	ChatToChatReqBody `param_type:"body"`
}

type ChatToChatReqBody struct {
	SessionId string `json:"session_id"`
}

type ChatToChatResp struct {
	Res struct {
		Status string `json:"status"`
	} `json:"res"`
}

func (u *useCase) ChatToChat(ctx context.Context, req *ChatToChatReq) (*ChatToChatResp, error) {

	sessionId := req.SessionId
	err := u.qaRepo.UpdateChatHistory(ctx, sessionId, constant.ChatGoing)
	if err != nil {
		return nil, err
	}
	var resp ChatToChatResp

	resp.Res.Status = "success"

	return &resp, nil
}
