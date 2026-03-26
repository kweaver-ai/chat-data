package main

import (
	"github.com/kweaver-ai/chat-data/sailor-service/cmd/server"
	"github.com/kweaver-ai/chat-data/sailor-service/common/settings"
	"github.com/spf13/cobra"
)

var addr string

var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "start server",
	RunE:  run,
}

func init() {
	serverCmd.Flags().StringVarP(&addr, "addr", "a", ":80", "http server host, eg: -addr 0.0.0.0:80")
}

func run(_ *cobra.Command, _ []string) error {
	cfg := settings.MainArgs{
		Name:       Name,
		Version:    Version,
		ConfigPath: confPath,
		Addr:       addr,
	}
	return server.Run(cfg)
}
