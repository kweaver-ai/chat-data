package assistant

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/kweaver-ai/chat-data/sailor-service/common/constant"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type Repo interface {
	GetQaWordHistory(ctx context.Context, userId string) (*model.QaWordHistory, error)
	UpdateQaWordHistory(ctx context.Context, userId string, qListStr string) error
	InsertQaWordHistory(ctx context.Context, userId string, qListStr string) error

	GetDetailByIds(ctx context.Context, orgcodes []string, ids ...uint64) ([]*model.TDataCatalog, error)
	GetByCatalogIDs(ctx context.Context, ids []uint64) ([]*model.TDataCatalogColumn, error)
	GetData(ctx context.Context, infoTypes []int8, catalogIDS []uint64) ([]*model.TDataCatalogInfo, error)
	//GetByCatalogIDs2(ctx context.Context, codes []string, resType int8) ([]*model.TDataCatalogResourceMount, error)
	GetByCodes(ctx context.Context, codes []string, uid string) ([]*model.TUserDataCatalogRel, error)
	GetByCodesV2(ctx context.Context, codes []string, uid string, state int) ([]*model.TDataCatalogDownloadApply, error)
	GetByCodesV3(ctx context.Context, codes []string, resType int8) ([]*model.TDataCatalogResourceMount, error)
	GetByCodesV4(ctx context.Context, catalogIDS []uint64) ([]*model.TDataResource, error)
	GetFieldByResourceIDs(ctx context.Context, ids []string) ([]*model.DataViewFields, error)
	GetSVCFieldByResourceIDs(ctx context.Context, ids []string) ([]*model.SVCFields, error)
	GetIndicatorByResourceIDs(ctx context.Context, ids []string) ([]*model.IndicatorFields, error)
	GetFormViewIdByCatalogIDs(ctx context.Context, id string) (*model.CatalogFormView, error)

	InsertChatHistory(ctx context.Context, userId string, sessionId string) error
	GetChatHistoryList(ctx context.Context, userId string) ([]*model.ChatHistory, error)
	GetChatHistoryBySession(ctx context.Context, sessionId string) (*model.ChatHistory, error)
	GetChatHistoryDetail(ctx context.Context, sessionId string) ([]*model.ChatHistoryDetail, error)
	UpdateChatHistory(ctx context.Context, sessionId string, status string) error
	UpdateChatHistoryTitle(ctx context.Context, sessionId string, status string, title string) error
	InsertChatHistoryDetail(ctx context.Context, sessionId string, qaId string, query string, answer string, resource string, status string) error
	GetChatFavoriteList(ctx context.Context, userId string) ([]*model.ChatFavorite, error)
	//GetChatFavoriteById(ctx context.Context, favoriteId string) ([]*model.ChatFavorite, error)
	GetChatFavoriteDetail(ctx context.Context, favoriteId string) ([]*model.ChatFavoriteDetail, error)
	GetChatDetailByFavorite(ctx context.Context, favoriteId string) ([]*model.ChatHistoryDetail, error)
	AddChatFavorite(ctx context.Context, sessionId string, favoriteId string) error
	DeleteChatFavorite(ctx context.Context, favoriteId string) error
	UpdateChatHistoryDetailFavorite(ctx context.Context, sessionId string, favoriteId string) error
	InsertChatFavoriteDetail(ctx context.Context, favoriteId string, qaId string, query string, answer string, like string) error
	UpdateChatStatus(ctx context.Context, qaId string, likeStatus string) error

	GetAssistantConfig(ctx context.Context) (*model.AssistantConfig, error)
	InsertAssistantConfig(ctx context.Context, userId string, cType string, config string) error
	UpdateAssistantConfig(ctx context.Context, cType string, config string) error

	GetAgentList(ctx context.Context) ([]*model.TAgent, error)
	InsertAgent(ctx context.Context, adpAgentKey string) (id string, err error)
	DeleteAgent(ctx context.Context, afAgentId string) error
}

type repo struct {
	data *db.Data
}

func NewRepo(data *db.Data) Repo {
	return &repo{data: data}
}

func (r *repo) do(ctx context.Context) *gorm.DB {
	return r.data.DB.WithContext(ctx)
}

func (r *repo) GetQaWordHistory(ctx context.Context, userId string) (*model.QaWordHistory, error) {
	var ms []*model.QaWordHistory
	if err := r.do(ctx).Raw(
		"select * from t_qa_word_history where user_id=? limit 1", userId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) InsertQaWordHistory(ctx context.Context, userId string, qListStr string) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {

		now := time.Now()
		qWordHistory := model.QaWordHistory{
			UserId:    userId,
			QWordList: &qListStr,
			CreatedAt: &now,
			UpdatedAt: &now,
		}
		if err := tx.Create(qWordHistory).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) UpdateQaWordHistory(ctx context.Context, userId string, qListStr string) error {
	if err := r.do(ctx).Exec(
		"update t_qa_word_history set qword_list=?, updated_at=? where user_id=?",
		qListStr, time.Now(), userId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) GetDetailByIds(ctx context.Context, orgcodes []string, ids ...uint64) ([]*model.TDataCatalog, error) {
	ms := make([]*model.TDataCatalog, 0)
	if len(orgcodes) == 0 {
		if err := r.do(ctx).Raw(
			"select id, code, title, description, online_status,department_id,\"\" as department_name,published_at,owner_id,owner_name from af_data_catalog.t_data_catalog where id in (?)", ids).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select * from af_data_catalog.t_data_catalog where id in (?) and department_id in (?)", ids, orgcodes).Scan(&ms).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}

	if len(ms) > 0 {
		return ms, nil
	}
	return nil, nil
}

func (r *repo) GetByCatalogIDs(ctx context.Context, ids []uint64) ([]*model.TDataCatalogColumn, error) {

	var result []*model.TDataCatalogColumn

	if err := r.do(ctx).Raw(
		`Select catalog_id, technical_name,business_name From af_data_catalog.t_data_catalog_column Where catalog_id In (?);`, ids).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	return result, nil
}

func (r *repo) GetData(ctx context.Context, infoTypes []int8, catalogIDS []uint64) ([]*model.TDataCatalogInfo, error) {
	var result []*model.TDataCatalogInfo
	if len(catalogIDS) == 0 && len(infoTypes) == 0 {
		if err := r.do(ctx).Raw(
			`Select * From af_data_catalog.t_data_catalog_info  order by catalog_id ASC, info_type ASC, id ASC`).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else if len(catalogIDS) > 0 && len(infoTypes) == 0 {
		if err := r.do(ctx).Raw(
			`Select * From af_data_catalog.t_data_catalog_info Where catalog_id in (?) order by catalog_id ASC, info_type ASC, id ASC`, catalogIDS).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else if len(catalogIDS) == 0 && len(infoTypes) > 0 {
		if err := r.do(ctx).Raw(
			`Select * From af_data_catalog.t_data_catalog_info Where info_type in (?) order by catalog_id ASC, info_type ASC, id ASC`, infoTypes).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"Select * From af_data_catalog.t_data_catalog_info Where catalog_id in (?) and info_type in (?) order by catalog_id ASC, info_type ASC, id ASC", catalogIDS, infoTypes).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}
	//db := r.do(ctx).Model(&model.TDataCatalogInfo{})
	//if len(catalogIDS) > 0 {
	//	db = db.Where("catalog_id in ?", catalogIDS)
	//}
	//if len(infoTypes) > 0 {
	//	db = db.Where("info_type in ?", infoTypes)
	//}
	return result, nil
}

func (r *repo) GetByCatalogIDs2(ctx context.Context, codes []string, resType int8) ([]*model.TDataCatalogResourceMount, error) {
	var result []*model.TDataCatalogResourceMount
	if resType > 0 {
		if err := r.do(ctx).Raw(
			"select * from af_data_catalog.t_data_catalog_resource_mount where code in (?)", codes).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select * from af_data_catalog.t_data_catalog_resource_mount where code in (?) and res_type = ?", codes, resType).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}

	return result, nil
}

func (r *repo) GetByCodes(ctx context.Context, codes []string, uid string) ([]*model.TUserDataCatalogRel, error) {
	var result []*model.TUserDataCatalogRel
	db := r.do(ctx).Model(&model.TUserDataCatalogRel{})
	db.Raw(`
		Select 
			id, code, expired_at 
		From 
			af_data_catalog.t_user_data_catalog_rel 
		Where
			code in (?)
		And
			uid = ?
		And
			expired_flag = 1
		And 
			expired_at > now();
	`, codes, uid).Scan(&result)
	return result, db.Error
}

func (r *repo) GetByCodesV2(ctx context.Context, codes []string, uid string, state int) ([]*model.TDataCatalogDownloadApply, error) {
	// t_data_catalog_download_apply
	var result []*model.TDataCatalogDownloadApply
	db := r.do(ctx).Model(&model.TDataCatalogDownloadApply{})
	db.Raw(`
		Select 
			code
		From
			af_data_catalog.t_data_catalog_download_apply
		Where
			code in (?)
		And
			state = ?
		And
			uid = ?;
	`, codes, state, uid).Scan(&result)
	return result, db.Error
}

func (r *repo) GetByCodesV3(ctx context.Context, codes []string, resType int8) ([]*model.TDataCatalogResourceMount, error) {
	var result []*model.TDataCatalogResourceMount
	if resType > 0 {
		if err := r.do(ctx).Raw(
			"select * from af_data_catalog.t_data_catalog_resource_mount where code in (?)", codes).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	} else {
		if err := r.do(ctx).Raw(
			"select * from af_data_catalog.t_data_catalog_resource_mount where code in (?) and res_type = ?", codes, resType).Scan(&result).Error; err != nil {
			return nil, errors.Wrap(err, "get info by id failed from db")
		}
	}

	return result, nil
}

func (r *repo) GetByCodesV4(ctx context.Context, catalogIDS []uint64) ([]*model.TDataResource, error) {
	var result []*model.TDataResource
	if err := r.do(ctx).Raw(
		"select a.id, a.resource_id,b.technical_name,a.catalog_id from af_data_catalog.t_data_resource a LEFT JOIN af_main.form_view b on a.resource_id=b.id where b.technical_name is not null and catalog_id in (?)", catalogIDS).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetFieldByResourceIDs(ctx context.Context, ids []string) ([]*model.DataViewFields, error) {
	var result []*model.DataViewFields
	if err := r.do(ctx).Raw(
		"select form_view_id, technical_name, business_name from af_main.form_view_field where  deleted_at =0 and form_view_id in (?)", ids).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetSVCFieldByResourceIDs(ctx context.Context, ids []string) ([]*model.SVCFields, error) {
	var result []*model.SVCFields
	if err := r.do(ctx).Raw(
		"select service_id, cn_name, en_name from data_application_service.service_param where  delete_time =0 and service_id in (?)", ids).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetIndicatorByResourceIDs(ctx context.Context, ids []string) ([]*model.IndicatorFields, error) {
	var result []*model.IndicatorFields
	if err := r.do(ctx).Raw(
		"select id, analysis_dimension from af_data_model.t_technical_indicator where analysis_dimension is not null and id in (?)", ids).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetFormViewIdByCatalogIDs(ctx context.Context, id string) (*model.CatalogFormView, error) {
	var result []*model.CatalogFormView
	if err := r.do(ctx).Raw(
		"select `code`, s_res_id from af_data_catalog.t_data_catalog_resource_mount where `code`=?", id).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(result) > 0 {
		return result[0], nil
	}
	return nil, nil
}

func (r *repo) InsertChatHistory(ctx context.Context, userId string, sessionId string) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {

		now := time.Now()
		chatHistory := model.ChatHistory{
			UserId:    userId,
			SessionId: sessionId,
			Status:    constant.ChatReady,
			CreatedAt: &now,
			UpdatedAt: &now,
		}
		if err := tx.Create(chatHistory).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) GetChatHistoryList(ctx context.Context, userId string) ([]*model.ChatHistory, error) {
	var result []*model.ChatHistory
	if err := r.do(ctx).Raw(
		"select * from t_chat_history where user_id=? and status=? order by chat_at desc limit 50", userId, constant.ChatGoing).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetChatHistoryBySession(ctx context.Context, sessionId string) (*model.ChatHistory, error) {
	var result []*model.ChatHistory
	if err := r.do(ctx).Raw(
		"select * from t_chat_history where session_id = ?", sessionId).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(result) > 0 {
		return result[0], nil
	}
	return nil, nil
}

func (r *repo) InsertChatHistoryDetail(ctx context.Context, sessionId string, qaId string, query string, answer string, resource string, status string) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {

		now := time.Now()
		chatHistory := model.ChatHistoryDetail{
			SessionId:        sessionId,
			QaId:             qaId,
			Query:            query,
			Answer:           answer,
			Like:             "neutrality",
			CreatedAt:        &now,
			UpdatedAt:        &now,
			ResourceRequired: resource,
			Status:           status,
		}
		if err := tx.Create(chatHistory).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) GetChatHistoryDetail(ctx context.Context, sessionId string) ([]*model.ChatHistoryDetail, error) {
	var result []*model.ChatHistoryDetail
	if err := r.do(ctx).Raw(
		"select * from t_chat_history_detail where session_id = ?", sessionId).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) UpdateChatHistory(ctx context.Context, sessionId string, status string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history set status=?, updated_at=? where session_id=?",
		status, time.Now(), sessionId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) UpdateChatHistoryTitle(ctx context.Context, sessionId string, status string, title string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history set title=?, status=?, updated_at=?, chat_at=? where session_id=?",
		title, status, time.Now(), time.Now(), sessionId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) GetChatFavoriteList(ctx context.Context, userId string) ([]*model.ChatFavorite, error) {
	var result []*model.ChatFavorite
	if err := r.do(ctx).Raw(
		"select * from t_chat_history where favorite_id != '' and user_id = ? order by favorite_at desc", userId).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) AddChatFavorite(ctx context.Context, sessionId string, favoriteId string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history set favorite_id=?, favorite_at=?, updated_at=? where session_id=?",
		favoriteId, time.Now(), time.Now(), sessionId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) InsertChatFavoriteDetail(ctx context.Context, favoriteId string, qaId string, query string, answer string, like string) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {

		now := time.Now()
		chatFavorite := model.ChatFavoriteDetail{
			FavoriteId: favoriteId,
			QaId:       qaId,
			Query:      query,
			Answer:     answer,
			Like:       like,
			CreatedAt:  &now,
			UpdatedAt:  &now,
		}
		if err := tx.Create(chatFavorite).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) GetChatDetailByFavorite(ctx context.Context, favoriteId string) ([]*model.ChatHistoryDetail, error) {
	var result []*model.ChatHistoryDetail
	if err := r.do(ctx).Raw(
		"select * from t_chat_history_detail where favorite_id = ?", favoriteId).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) GetChatFavoriteDetail(ctx context.Context, favoriteId string) ([]*model.ChatFavoriteDetail, error) {
	var result []*model.ChatFavoriteDetail
	if err := r.do(ctx).Raw(
		"select * from t_chat_favorite_detail where favorite_id = ?", favoriteId).Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	return result, nil
}

func (r *repo) DeleteChatFavorite(ctx context.Context, favoriteId string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history set favorite_id=?, updated_at=? where favorite_id=?",
		"", time.Now(), favoriteId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) UpdateChatHistoryDetailFavorite(ctx context.Context, sessionId string, favoriteId string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history_detail set favorite_id=?, updated_at=? where session_id=?",
		favoriteId, time.Now(), sessionId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) UpdateChatStatus(ctx context.Context, qaId string, likeStatus string) error {
	if err := r.do(ctx).Exec(
		"update t_chat_history_detail set like_status=?, updated_at=? where qa_id=?",
		likeStatus, time.Now(), qaId).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) GetAssistantConfig(ctx context.Context) (*model.AssistantConfig, error) {
	var result []*model.AssistantConfig
	if err := r.do(ctx).Raw(
		"select `user_id`, `type`, `config` from t_assistant_config").Scan(&result).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}
	if len(result) > 0 {
		return result[0], nil
	}
	return nil, nil
}

func (r *repo) UpdateAssistantConfig(ctx context.Context, cType string, config string) error {
	if err := r.do(ctx).Exec(
		"update t_assistant_config set config=?, updated_at=? where type=?",
		config, time.Now(), cType).Error; err != nil {
		return errors.Wrap(err, "update res info failed in db")
	}

	return nil
}

func (r *repo) InsertAssistantConfig(ctx context.Context, userId string, cType string, config string) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {

		now := time.Now()
		chatFavorite := model.AssistantConfig{
			UserId:    userId,
			TType:     cType,
			Config:    config,
			CreatedAt: &now,
			UpdatedAt: &now,
		}
		if err := tx.Create(chatFavorite).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) GetAgentList(ctx context.Context) ([]*model.TAgent, error) {
	var db *gorm.DB
	db = r.data.DB.WithContext(ctx).Table(model.TableNameTAgent).Where("deleted_at=0")
	var results []*model.TAgent
	err := db.Find(&results).Error
	if err != nil {
		return nil, err
	}
	return results, err
}

func (r *repo) InsertAgent(ctx context.Context, adpAgentKey string) (id string, err error) {
	data := model.TAgent{
		ID:          uuid.New().String(),
		AdpAgentKey: adpAgentKey,
	}
	err = r.data.DB.WithContext(ctx).Create(&data).Error
	if err != nil {
		return "", err
	}
	return data.ID, nil
}

func (r *repo) DeleteAgent(ctx context.Context, afAgentId string) error {
	return r.data.DB.WithContext(ctx).
		Model(&model.TAgent{}).
		Where("id = ?", afAgentId).
		Where("deleted_at = 0").
		Update("deleted_at", time.Now().Unix()).
		Error
}
