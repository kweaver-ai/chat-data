package knowledge_build

import (
	"context"
	"encoding/json"
	"errors"
	"math/rand"
	"net"
	"sync"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/bsm/redislock"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/chat-data/sailor-service/infrastructure/repository/db"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/redis/go-redis/v9"
	"github.com/samber/lo"
	"go.uber.org/atomic"
)

const (
	lockKey = "xxx.cn/anyfabric/af-sailor-service/graph-init/master-lock-key"

	lockKeyTTL = 24 * time.Hour // key过期时间默认一天
)

type Mutex struct {
	redisCli redis.UniversalClient
	locker   *redislock.Client
	localIP  string

	mtx sync.Mutex
	lck *redislock.Lock

	stop atomic.Bool

	lastPrintTime *time.Time
}

func NewMutex(db *db.Data) *Mutex {
	return &Mutex{
		redisCli: db.RedisCli,
		locker:   redislock.New(db.RedisCli),
		localIP:  settings.GetConfig().SysConf.SelfIP,
	}
}

func (m *Mutex) LoopLock(ctx context.Context) context.Context {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	rand.Seed(time.Now().UnixMilli())
	var ticker *time.Ticker
	defer func() {
		if ticker != nil {
			ticker.Stop()
		}
	}()
	for {
		if ticker == nil {
			ticker = time.NewTicker(time.Second * 10)
		} else {
			select {
			case <-ctx.Done():
				return ctx
			case <-ticker.C:
			}
		}

		m.mtx.Lock()
		err := m.obtainLocked(ctx)
		if err != nil || m.lck == nil {
			m.mtx.Unlock()
			continue
		}

		m.mtx.Unlock()
		break
	}

	ctx, cancel := context.WithCancel(ctx)
	// 异步定时更新ttl
	go func() {
		ticker := time.NewTicker(10 * time.Hour)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}

			if err := m.lck.Refresh(ctx, lockKeyTTL, nil); err != nil {
				log.WithContext(ctx).Warnf("redis.Locker.Refresh failed, err: %v", err)
			}
		}
	}()

	// 异步检测key是否存在
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
			}

			ttl, err := retry.DoWithData(func() (time.Duration, error) {
				ttl, err := m.lck.TTL(ctx)
				if err != nil {
					log.WithContext(ctx).Errorf("redis.Locker.TTL failed, err: %v", err)
					return 0, err
				}

				return ttl, nil
			},
				retry.Attempts(3),
				retry.DelayType(retry.CombineDelay(retry.FixedDelay, retry.RandomDelay)),
				retry.Delay(1*time.Second),
				retry.MaxJitter(1*time.Second),
				retry.Context(ctx),
			)

			// 有错误，认为已经失去锁，取消ctx以取消业务逻辑
			if err != nil {
				log.WithContext(ctx).Errorf("redis.Locker.TTL failed, ctx cancel, err: %v", err)
				cancel()
				break
			}

			if ttl > 0 {
				continue
			}

			// ttl没有值，已经失去锁，取消ctx以取消业务逻辑
			log.WithContext(ctx).Warnf("key ttl not exists, ctx cancel")
			cancel()
			break
		}
	}()

	return ctx
}

func (m *Mutex) obtainLocked(ctx context.Context) (err error) {
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	m.lck, err = m.locker.Obtain(ctx, lockKey, lockKeyTTL, &redislock.Options{
		RetryStrategy: redislock.LimitRetry(redislock.LinearBackoff(1*time.Second), 3),
		Token:         m.localIP,
	})
	if errors.Is(err, redislock.ErrNotObtained) {
		if m.lastPrintTime == nil || time.Now().Sub(*m.lastPrintTime) > 1*time.Hour {
			m.lastPrintTime = lo.ToPtr(time.Now())
			log.WithContext(ctx).Infof("redis.Locker.Obtain not obtained")
		}
		return nil
	} else if err != nil {
		log.WithContext(ctx).Errorf("redis.Locker.Obtain failed, err: %v", err)
		return err
	}

	log.WithContext(ctx).Infof("obtained distributed mutex")
	return nil
}

func (m *Mutex) Release(ctx context.Context) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	if m.lck != nil {
		if err := m.lck.Release(ctx); err != nil {
			log.WithContext(ctx).Errorf("redis.Locker.Release failed, err: %v", err)
			return err
		}
	}

	return nil
}

func (m *Mutex) GetMasterIP(ctx context.Context) (string, error) {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	ip := m.redisCli.Get(ctx, lockKey).Val()
	if len(ip) < 1 {
		log.WithContext(ctx).Errorf("key not exist, master ip not found")
		return "", errors.New("key not exist, master ip not found")
	}

	parseIP := net.ParseIP(ip)
	if parseIP == nil {
		log.WithContext(ctx).Errorf("master ip invalid, ip: %s", ip)
		return "", errors.New("master ip invalid")
	}

	return ip, nil
}

func (m *Mutex) DelLock(ctx context.Context) error {
	return m.redisCli.Del(ctx, lockKey).Err()
}

func (m *Mutex) Set(ctx context.Context, data any, key string, d time.Duration) error {
	bs, _ := json.Marshal(data)
	return m.redisCli.Set(ctx, key, string(bs), d).Err()
}

func (m *Mutex) Get(ctx context.Context, key string) (ds []byte, err error) {
	return m.redisCli.Get(ctx, key).Bytes()
}

func (m *Mutex) Del(ctx context.Context, key string) error {
	return m.redisCli.Del(ctx, key).Err()
}
