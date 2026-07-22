//go:build windows

package terminal

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"

	"github.com/UserExistsError/conpty"
)

type platformFactory struct{}

type windowsProcess struct {
	terminal *conpty.ConPty
	waitCtx  context.Context
	cancel   context.CancelFunc
	close    sync.Once
	closeErr error
}

func (platformFactory) Start(ctx context.Context, cwd string, cols, rows int) (Process, string, error) {
	if !conpty.IsConPtyAvailable() {
		return nil, "", errors.New("Windows ConPTY is unavailable; Windows 10 version 1809 or newer is required")
	}
	shell, arguments := detectWindowsShell()
	commandLine := quoteWindowsCommand(shell)
	if len(arguments) > 0 {
		commandLine += " " + strings.Join(arguments, " ")
	}
	terminal, err := conpty.Start(
		commandLine,
		conpty.ConPtyDimensions(cols, rows),
		conpty.ConPtyWorkDir(cwd),
		conpty.ConPtyEnv(append(os.Environ(), "TERM=xterm-256color")),
	)
	if err != nil {
		return nil, "", err
	}
	waitCtx, cancel := context.WithCancel(ctx)
	return &windowsProcess{terminal: terminal, waitCtx: waitCtx, cancel: cancel}, shell, nil
}

func (p *windowsProcess) Read(target []byte) (int, error) { return p.terminal.Read(target) }
func (p *windowsProcess) Write(value []byte) (int, error) { return p.terminal.Write(value) }
func (p *windowsProcess) Resize(cols, rows int) error     { return p.terminal.Resize(cols, rows) }
func (p *windowsProcess) Kill() error {
	p.cancel()
	return p.closeTerminal()
}
func (p *windowsProcess) Wait() error {
	_, err := p.terminal.Wait(p.waitCtx)
	closeErr := p.closeTerminal()
	return errors.Join(err, closeErr)
}

func (p *windowsProcess) closeTerminal() error {
	p.close.Do(func() { p.closeErr = p.terminal.Close() })
	return p.closeErr
}

func detectWindowsShell() (string, []string) {
	if powershell, err := exec.LookPath("powershell.exe"); err == nil {
		return powershell, []string{"-NoLogo"}
	}
	if command := strings.TrimSpace(os.Getenv("COMSPEC")); command != "" && filepath.IsAbs(command) {
		return command, nil
	}
	return "cmd.exe", nil
}

func quoteWindowsCommand(value string) string {
	if !strings.ContainsAny(value, " \t\"") {
		return value
	}
	return `"` + strings.ReplaceAll(value, `"`, `\"`) + `"`
}
