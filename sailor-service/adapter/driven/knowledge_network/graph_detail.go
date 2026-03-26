package knowledge_network

import (
	"context"
	"fmt"
	"net/url"

	"github.com/jinzhu/copier"
	"github.com/kweaver-ai/chat-data/sailor-service/common/errorcode"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/samber/lo"
)

type PropertyMap map[string]string

type GraphDetailRes struct {
	Res GraphDetail `json:"res"`
}

type GraphDetail struct {
	Id              int               `json:"id"`
	CreateUser      string            `json:"create_user"`
	CreateTime      string            `json:"create_time"`
	UpdateUser      string            `json:"update_user"`
	UpdateTime      string            `json:"update_time"`
	GraphName       string            `json:"graph_name"`
	RabbitmqDs      int               `json:"rabbitmq_ds"`
	StepNum         int               `json:"step_num"`
	IsUpload        int               `json:"is_upload"`
	KDBName         string            `json:"KDB_name"`
	KDBNameTemp     string            `json:"KDB_name_temp"`
	KgDataVolume    int               `json:"kg_data_volume"`
	Status          string            `json:"status"`
	GraphUpdateTime interface{}       `json:"graph_update_time"`
	KnwId           int               `json:"knw_id"`
	QuantizedFlag   int               `json:"quantized_flag"`
	GraphBaseInfo   GraphBaseInfo     `json:"graph_baseInfo"`
	GraphDs         []GraphDatasource `json:"graph_ds"`
	GraphUsedDs     []GraphDatasource `json:"graph_used_ds"`
	GraphOtlSlice   []GraphOtl        `json:"graph_otl"`
	GraphKMap       *GraphKMap        `json:"graph_kmap"`
}
type GraphBaseInfo struct {
	GraphName      string `json:"graph_Name"`
	GraphDes       string `json:"graph_des"`
	GraphDBAddress string `json:"graphDBAddress"`
	GraphMongoName string `json:"graph_mongo_Name"`
	GraphDBName    string `json:"graph_DBName"`
}

type GraphDatasource struct {
	CreateUserName string      `json:"create_user_name"`
	UpdateUserName string      `json:"update_user_name"`
	Id             int         `json:"id"`
	CreateUser     string      `json:"create_user"`
	CreateTime     string      `json:"create_time"`
	UpdateUser     string      `json:"update_user"`
	UpdateTime     string      `json:"update_time"`
	Dsname         string      `json:"dsname"`
	DataType       string      `json:"dataType"`
	DataSource     string      `json:"data_source"`
	DsUser         interface{} `json:"ds_user"`
	DsPassword     interface{} `json:"ds_password"`
	DsAddress      string      `json:"ds_address"`
	DsPort         int         `json:"ds_port"`
	DsPath         string      `json:"ds_path"`
	ExtractType    string      `json:"extract_type"`
	DsAuth         string      `json:"ds_auth"`
	Vhost          string      `json:"vhost"`
	Queue          string      `json:"queue"`
	JsonSchema     string      `json:"json_schema"`
	ConnectType    string      `json:"connect_type"`
}

type GraphOtl struct {
	Id           int           `json:"id"`
	CreateUser   string        `json:"create_user"`
	CreateTime   string        `json:"create_time"`
	UpdateUser   string        `json:"update_user"`
	UpdateTime   string        `json:"update_time"`
	OntologyName string        `json:"ontology_name"`
	OntologyDes  string        `json:"ontology_des"`
	OtlStatus    string        `json:"otl_status"`
	Entity       []GraphEntity `json:"entity"`
	Edge         []GraphEdge   `json:"edge"`
	UsedTask     []int         `json:"used_task"`
	AllTask      []int         `json:"all_task"`
	IdentifyId   interface{}   `json:"identify_id"`
	KnwId        int           `json:"knw_id"`
	Domain       string        `json:"domain"`
	OtlTemp      string        `json:"otl_temp"`
	Canvas       struct{}      `json:"canvas"`
}

type GraphEdge struct {
	EdgeId             string   `json:"edge_id"`
	Name               string   `json:"name"`
	Description        string   `json:"description"`
	Alias              string   `json:"alias"`
	PropertiesIndex    []string `json:"properties_index"`
	PrimaryKey         []string `json:"primary_key"`
	DefaultTag         string   `json:"default_tag"`
	Properties         []any    `json:"properties"`
	Relations          []string `json:"relations"`
	Colour             string   `json:"colour"`
	Shape              string   `json:"shape"`
	Width              string   `json:"width"`
	SourceType         string   `json:"source_type"`
	IndexDefaultSwitch bool     `json:"index_default_switch"`
	Model              string   `json:"model"`
}

type GraphEntity struct {
	EntityId           string           `json:"entity_id"`
	EntityType         string           `json:"-"`
	Name               string           `json:"name"`
	Description        string           `json:"description"`
	Alias              string           `json:"alias"`
	Synonym            []interface{}    `json:"synonym"`
	DefaultTag         string           `json:"default_tag"`
	PropertiesIndex    []string         `json:"properties_index"` //索引
	SearchProp         string           `json:"search_prop"`
	PrimaryKey         []string         `json:"primary_key"` //融合属性
	VectorGeneration   []string         `json:"vector_generation"`
	Properties         []EntityProperty `json:"properties"`
	X                  float64          `json:"x"`
	Y                  float64          `json:"y"`
	Icon               string           `json:"icon"`
	Shape              string           `json:"shape"`
	Size               string           `json:"size"`
	FillColor          string           `json:"fill_color"`
	StrokeColor        string           `json:"stroke_color"`
	TextColor          string           `json:"text_color"`
	TextPosition       string           `json:"text_position"`
	TextWidth          int              `json:"text_width"`
	IndexDefaultSwitch bool             `json:"index_default_switch"`
	TextType           string           `json:"text_type"`
	SourceType         string           `json:"source_type"`
	Model              string           `json:"model"`
	TaskId             string           `json:"task_id"`
	IconColor          string           `json:"icon_color"`
}

type EntityProperty struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Alias       string `json:"alias"`
	DataType    string `json:"data_type"`
}

func (g *GraphDetail) GenNoCheckWithDeleteInfo() *GraphNoCheck {
	//复制详情的数据
	graphNoCheck := &GraphNoCheck{
		GraphBaseInfo: g.GraphBaseInfo,
		GraphDs: lo.Times(len(g.GraphDs), func(index int) int {
			return g.GraphDs[index].Id
		}),
		GraphOtl:  &GraphNoCheckOtl{},
		GraphKMap: &GraphKMap{},
	}
	graphNoCheck.GraphId = g.Id
	if len(g.GraphOtlSlice) > 0 {
		copier.Copy(graphNoCheck.GraphOtl, g.GraphOtlSlice[0])
	}
	copier.Copy(graphNoCheck.GraphKMap, g.GraphKMap)
	return graphNoCheck
}

func (a *ad) GraphDetail(ctx context.Context, knwId int) (detail *GraphDetail, err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rawURL := a.baseUrl + fmt.Sprintf(`/api/builder/v1/graph/%v`, knwId)
	realURL, _ := url.Parse(rawURL)

	detailRes, err := httpGetDoV2[GraphDetailRes](ctx, realURL, a)
	if err != nil {
		if errorcode.Contains(err, NetworkNotExistsMsg) {
			return nil, err
		}
		log.Error(err.Error())
		return nil, err
	}
	return &detailRes.Res, nil
}
