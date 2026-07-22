//go:build !windows

package terminal

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/creack/pty"
)

type platformFactory struct{}

type unixProcess struct {
	command *exec.Cmd
	pty     *os.File
}

func (platformFactory) Start(ctx context.Context, cwd string, cols, rows int) (Process, string, error) {
	shell, err := detectUnixShell()
	if err != nil {
		return nil, "", err
	}
	command := exec.CommandContext(ctx, shell, "-l")
	command.Dir = cwd
	command.Env = append(os.Environ(), "TERM=xterm-256color", "COLORTERM=truecolor")
	terminal, err := pty.StartWithSize(command, &pty.Winsize{Cols: uint16(cols), Rows: uint16(rows)})
	if err != nil {
		return nil, "", err
	}
	return &unixProcess{command: command, pty: terminal}, shell, nil
}

func (p *unixProcess) Read(target []byte) (int, error) { return p.pty.Read(target) }
func (p *unixProcess) Write(value []byte) (int, error) { return p.pty.Write(value) }
func (p *unixProcess) Resize(cols, rows int) error {
	return pty.Setsize(p.pty, &pty.Winsize{Cols: uint16(cols), Rows: uint16(rows)})
}
func (p *unixProcess) Kill() error {
	var result error
	if p.command.Process != nil {
		result = p.command.Process.Kill()
	}
	if err := p.pty.Close(); result == nil {
		result = err
	}
	return result
}
func (p *unixProcess) Wait() error {
	err := p.command.Wait()
	_ = p.pty.Close()
	return err
}

func detectUnixShell() (string, error) {
	candidates := []string{strings.TrimSpace(os.Getenv("SHELL")), "/bin/zsh", "/bin/bash", "/bin/sh"}
	for _, candidate := range candidates {
		if candidate == "" || !filepath.IsAbs(candidate) {
			continue
		}
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() && info.Mode()&0o111 != 0 {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("no executable login shell is available")
}
