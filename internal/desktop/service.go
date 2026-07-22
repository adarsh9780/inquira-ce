package desktop

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const (
	StartupLogName = "desktop-startup.log"
	maxStartupLog  = 1024 * 1024
)

type CommandStarter interface {
	Start(name string, args ...string) error
}

type Config struct {
	Platform   string
	Starter    CommandStarter
	Executable func() (string, error)
	Arguments  []string
}

type Service struct {
	platform   string
	starter    CommandStarter
	executable func() (string, error)
	arguments  []string
}

type processStarter struct{}

func (processStarter) Start(name string, args ...string) error {
	return exec.Command(name, args...).Start()
}

func New() *Service { return NewService(Config{}) }

func NewService(config Config) *Service {
	platform := strings.TrimSpace(config.Platform)
	if platform == "" {
		platform = runtime.GOOS
	}
	starter := config.Starter
	if starter == nil {
		starter = processStarter{}
	}
	executable := config.Executable
	if executable == nil {
		executable = os.Executable
	}
	arguments := config.Arguments
	if arguments == nil {
		arguments = os.Args[1:]
	}
	return &Service{
		platform: platform, starter: starter, executable: executable,
		arguments: append([]string(nil), arguments...),
	}
}

func (s *Service) OpenExternalURL(rawURL string) error {
	value := strings.TrimSpace(rawURL)
	if value == "" || strings.ContainsAny(value, "\r\n\x00") {
		return errors.New("a valid external URL is required")
	}
	parsed, err := url.Parse(value)
	scheme := ""
	if parsed != nil {
		scheme = strings.ToLower(parsed.Scheme)
	}
	if err != nil || (scheme != "http" && scheme != "https") || parsed.Hostname() == "" || parsed.User != nil {
		return errors.New("only credential-free HTTP or HTTPS links can be opened externally")
	}
	command, arguments, err := platformOpenCommand(s.platform, value, false)
	if err != nil {
		return err
	}
	if err := s.starter.Start(command, arguments...); err != nil {
		return fmt.Errorf("open external URL: %w", err)
	}
	return nil
}

func (s *Service) OpenDirectory(path string) error {
	absolute, err := filepath.Abs(strings.TrimSpace(path))
	if err != nil {
		return fmt.Errorf("resolve diagnostics directory: %w", err)
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return fmt.Errorf("read diagnostics directory: %w", err)
	}
	if !info.IsDir() {
		return errors.New("diagnostics path is not a directory")
	}
	command, arguments, err := platformOpenCommand(s.platform, absolute, true)
	if err != nil {
		return err
	}
	if err := s.starter.Start(command, arguments...); err != nil {
		return fmt.Errorf("open diagnostics directory: %w", err)
	}
	return nil
}

func (s *Service) Restart() error {
	executable, err := s.executable()
	if err != nil {
		return fmt.Errorf("resolve application executable: %w", err)
	}
	executable = strings.TrimSpace(executable)
	if executable == "" {
		return errors.New("application executable is unavailable")
	}
	if err := s.starter.Start(executable, s.arguments...); err != nil {
		return fmt.Errorf("restart desktop application: %w", err)
	}
	return nil
}

func platformOpenCommand(platform, target string, directory bool) (string, []string, error) {
	switch platform {
	case "darwin":
		return "open", []string{target}, nil
	case "linux":
		return "xdg-open", []string{target}, nil
	case "windows":
		if directory {
			return "explorer", []string{target}, nil
		}
		return "rundll32", []string{"url.dll,FileProtocolHandler", target}, nil
	default:
		return "", nil, fmt.Errorf("desktop launcher is unsupported on %s", platform)
	}
}

func AppendStartupLog(directory, message string) (string, error) {
	directory = filepath.Clean(strings.TrimSpace(directory))
	if directory == "." || directory == "" {
		return "", errors.New("startup log directory is required")
	}
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return "", fmt.Errorf("create startup log directory: %w", err)
	}
	path := filepath.Join(directory, StartupLogName)
	flags := os.O_CREATE | os.O_WRONLY | os.O_APPEND
	if info, err := os.Stat(path); err == nil && info.Size() >= maxStartupLog {
		flags = os.O_CREATE | os.O_WRONLY | os.O_TRUNC
	}
	file, err := os.OpenFile(path, flags, 0o600)
	if err != nil {
		return path, fmt.Errorf("open startup log: %w", err)
	}
	defer file.Close()
	if err := file.Chmod(0o600); err != nil {
		return path, fmt.Errorf("secure startup log: %w", err)
	}
	line := strings.Join(strings.Fields(message), " ")
	if line == "" {
		line = "Startup status unavailable."
	}
	if _, err := fmt.Fprintf(file, "%s %s\n", time.Now().UTC().Format(time.RFC3339Nano), line); err != nil {
		return path, fmt.Errorf("write startup log: %w", err)
	}
	return path, nil
}
