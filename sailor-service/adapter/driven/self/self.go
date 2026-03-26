// Package self 自己调用自己
package self

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/log"
	"github.com/kweaver-ai/idrm-go-frame/core/telemetry/trace"
	"github.com/pkg/errors"
)

type Proxy interface {
	ResetADInit(ctx context.Context, masterIP string) error
}

type proxy struct {
	httpCli *http.Client
}

func NewProxy(httpCli *http.Client) Proxy {
	return &proxy{httpCli: httpCli}
}

func (p *proxy) ResetADInit(ctx context.Context, masterIP string) error {
	var err error
	ctx, span := trace.StartInternalSpan(ctx)
	defer func() { trace.TelemetrySpanEnd(span, err) }()

	addr := settings.GetConfig().ServerConf.HttpConf.Addr
	port := addr[strings.LastIndexByte(addr, ':')+1:]

	uri := fmt.Sprintf("http://%s:%s/api/internal/af-sailor-service/v1/knowledge-build/reset", masterIP, port)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, uri, nil)
	if err != nil {
		return errors.Wrap(err, "failed to create http req")
	}

	log.WithContext(ctx).Infof("self proxy request uri: %s", uri)
	resp, err := p.httpCli.Do(req)
	if err != nil {
		return errors.Wrap(err, "req self failed")
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	respData, err := io.ReadAll(resp.Body)
	if err != nil {
		return errors.Wrap(err, "failed to read self resp data")
	}

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return nil
	}

	log.WithContext(ctx).Warnf("failed to request self, uri: %s, data: %s", uri, respData)
	if len(respData) > 1 {
		return errors.New(string(respData))
	}

	return errors.New("request self failed")
}
