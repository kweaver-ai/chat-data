package knowledge_network

import (
	"context"
	"time"

	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db/model"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type Repo interface {
	GetInfoByConfigId(ctx context.Context, configId string) (*model.KnowledgeNetworkInfo, error)
	SaveRes(ctx context.Context, mInfo *model.KnowledgeNetworkInfo, mDetail *model.KnowledgeNetworkInfoDetail) error
	DeleteResAll(ctx context.Context) error
	SelectResAll(ctx context.Context) ([]*model.KnowledgeNetworkInfoRecord, error)
	DeleteInfoById(ctx context.Context, id string) error
	ListInfoByType(ctx context.Context, types ...int32) ([]*model.KnowledgeNetworkInfo, error)
	GetInfoByTypeAndConfigId(ctx context.Context, tpe int32, cfgId string) (*model.KnowledgeNetworkInfo, error)
	GetInfosByTypeAndConfigId(ctx context.Context, tpe int32, cfgId string) ([]*model.KnowledgeNetworkInfo, error)
	ListInfoByConfigIds(ctx context.Context, config_ids ...string) ([]*model.KnowledgeNetworkInfo, error)
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

func (r *repo) GetInfoByConfigId(ctx context.Context, configId string) (*model.KnowledgeNetworkInfo, error) {
	var ms []*model.KnowledgeNetworkInfo
	if err := r.do(ctx).Raw(
		"select * from t_knowledge_network_info where f_config_id=? and f_deleted_at=0 limit 1",
		configId).Scan(&ms).Error; err != nil {
		return nil, errors.Wrap(err, "get info by id failed from db")
	}

	if len(ms) > 0 {
		return ms[0], nil
	}
	return nil, nil
}

func (r *repo) SaveRes(ctx context.Context, mInfo *model.KnowledgeNetworkInfo, mDetail *model.KnowledgeNetworkInfoDetail) error {
	if err := r.do(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(mInfo).Error; err != nil {
			return err
		}

		if err := tx.Create(mDetail).Error; err != nil {
			return err
		}

		return nil
	}); err != nil {
		return errors.Wrap(err, "save res info and detail failed in db")
	}

	return nil
}

func (r *repo) DeleteResAll(ctx context.Context) error {
	if err := r.do(ctx).Exec(
		"update t_knowledge_network_info set f_deleted_at=? where f_deleted_at=0",
		time.Now().UnixMilli()).Error; err != nil {
		return errors.Wrap(err, "delete res info failed in db")
	}

	return nil
}

func (r *repo) SelectResAll(ctx context.Context) (datas []*model.KnowledgeNetworkInfoRecord, err error) {
	if err = r.do(ctx).Raw(`select tkni.*, tknid.f_detail from t_knowledge_network_info tkni   
 				join af_cognitive_assistant.t_knowledge_network_info_detail tknid   
				 on tkni.f_id=tknid.f_id  where tkni.f_deleted_at=0`).Scan(&datas).Error; err != nil {
		return nil, errors.Wrap(err, "select record info failed in db")
	}
	return
}

func (r *repo) DeleteInfoById(ctx context.Context, id string) error {
	if err := r.do(ctx).Exec(
		"update t_knowledge_network_info set f_deleted_at=? where f_id=? and f_deleted_at=0",
		time.Now().UnixMilli(), id).Error; err != nil {
		return errors.Wrap(err, "delete res info failed in db")
	}

	return nil
}

func (r *repo) ListInfoByType(ctx context.Context, types ...int32) ([]*model.KnowledgeNetworkInfo, error) {
	if len(types) < 1 {
		return nil, nil
	}
	var ret []*model.KnowledgeNetworkInfo
	if err := r.do(ctx).Raw(
		`select * from t_knowledge_network_info where f_deleted_at=0 and f_type in ?`,
		types).Scan(&ret).Error; err != nil {
		return nil, errors.Wrap(err, "get knw info by type failed from db")
	}

	return ret, nil
}

func (r *repo) GetInfoByTypeAndConfigId(ctx context.Context, tpe int32, cfgId string) (*model.KnowledgeNetworkInfo, error) {
	var ret []*model.KnowledgeNetworkInfo
	if err := r.do(ctx).Raw(
		`select * from t_knowledge_network_info where f_deleted_at=0 and f_type=? and f_config_id=? limit 1`,
		tpe, cfgId).Scan(&ret).Error; err != nil {
		return nil, errors.Wrap(err, "get knw info by type and config id failed from db")
	}

	if len(ret) > 0 {
		return ret[0], nil
	}
	return nil, nil
}

func (r *repo) GetInfosByTypeAndConfigId(ctx context.Context, tpe int32, cfgId string) ([]*model.KnowledgeNetworkInfo, error) {
	var ret []*model.KnowledgeNetworkInfo
	if err := r.do(ctx).Raw(
		`select * from t_knowledge_network_info where f_deleted_at=0 and f_type=? and f_config_id=?`,
		tpe, cfgId).Scan(&ret).Error; err != nil {
		return nil, errors.Wrap(err, "get knw info by type and config id failed from db")
	}

	if len(ret) > 0 {
		return ret, nil
	}
	return nil, nil
}

func (r *repo) ListInfoByConfigIds(ctx context.Context, config_ids ...string) ([]*model.KnowledgeNetworkInfo, error) {
	if len(config_ids) < 1 {
		return nil, nil
	}
	var ret []*model.KnowledgeNetworkInfo
	if err := r.do(ctx).Raw(
		`select * from t_knowledge_network_info where f_deleted_at=0 and f_config_id in ?`,
		config_ids).Scan(&ret).Error; err != nil {
		return nil, errors.Wrap(err, "get knw info by type failed from db")
	}

	return ret, nil
}
