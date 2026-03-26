package db

import (
	"sync"
	"time"

	_ "github.com/golang-migrate/migrate/v4/database/mysql"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/redis/go-redis/v9"
	"github.com/uptrace/opentelemetry-go-extra/otelgorm"
	"gorm.io/gorm"

	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
)

var (
	once sync.Once
)

// Data .
type Data struct {
	DB       *gorm.DB
	RedisCli redis.UniversalClient
}

// NewData .
func NewData() (*Data, func(), error) {
	dbConfig := settings.GetConfig().DBOptions
	client, err := dbConfig.NewClient()
	if err != nil {
		log.Errorf("open mysql failed, err: %v", err)
		return nil, nil, err
	}
	if err = client.Use(otelgorm.NewPlugin()); err != nil {
		log.Errorf("init db otelgorm, err: %v\n", err.Error())
		return nil, nil, err
	}

	var redisCli redis.UniversalClient
	once.Do(func() {
		redisConf := settings.GetConfig().Redis
		redisCli = redis.NewUniversalClient(&redis.UniversalOptions{
			Addrs:            []string{redisConf.Addr},
			ClientName:       redisConf.ClientName,
			DB:               redisConf.DB,
			Protocol:         3,
			Password:         redisConf.Password,
			SentinelPassword: redisConf.SentinelPassword,
			MaxRetries:       redisConf.MaxRetries,
			MinRetryBackoff:  time.Duration(redisConf.MinRetryBackoff) * time.Millisecond,
			MaxRetryBackoff:  time.Duration(redisConf.MaxRetryBackoff) * time.Millisecond,
			DialTimeout:      time.Duration(redisConf.DialTimeout) * time.Millisecond,
			ReadTimeout:      time.Duration(redisConf.ReadTimeout) * time.Millisecond,
			WriteTimeout:     time.Duration(redisConf.WriteTimeout) * time.Millisecond,
			PoolSize:         redisConf.PoolSize,
			PoolTimeout:      time.Duration(redisConf.PoolTimeout) * time.Millisecond,
			MinIdleConns:     redisConf.MinIdleConns,
			MaxIdleConns:     redisConf.MaxIdleConns,
			ConnMaxIdleTime:  time.Duration(redisConf.ConnMaxIdleTime) * time.Minute,
			ConnMaxLifetime:  time.Duration(redisConf.ConnMaxLifetime) * time.Minute,
			MasterName:       redisConf.MasterName,
		})
	})

	globalData := &Data{
		DB:       client,
		RedisCli: redisCli,
	}
	return globalData, releaseFunc(redisCli), nil
}

func releaseFunc(redisCli redis.UniversalClient) func() {
	return func() {
		log.Info("closing the data resources")
		if err := redisCli.Close(); err != nil {
			log.Warnf("failed to close redis client, err: %v", err)
		}
	}
}
