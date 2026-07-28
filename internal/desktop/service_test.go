package desktop

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"slices"
	"strings"
	"testing"
)

type commandCall struct {
	name string
	args []string
}

type fakeStarter struct {
	calls []commandCall
	err   error
}

func (s *fakeStarter) Start(name string, args ...string) error {
	s.calls = append(s.calls, commandCall{name: name, args: append([]string(nil), args...)})
	return s.err
}

func TestExternalURLUsesPlatformLauncherAndRejectsUnsafeSchemes(t *testing.T) {
	for _, test := range []struct {
		platform string
		command  string
		args     []string
	}{
		{platform: "darwin", command: "open", args: []string{"https://example.com/docs?q=go"}},
		{platform: "linux", command: "xdg-open", args: []string{"https://example.com/docs?q=go"}},
		{platform: "windows", command: "rundll32", args: []string{"url.dll,FileProtocolHandler", "https://example.com/docs?q=go"}},
	} {
		t.Run(test.platform, func(t *testing.T) {
			starter := &fakeStarter{}
			service := NewService(Config{Platform: test.platform, Starter: starter})
			if err := service.OpenExternalURL(" https://example.com/docs?q=go "); err != nil {
				t.Fatal(err)
			}
			if len(starter.calls) != 1 || starter.calls[0].name != test.command || !slices.Equal(starter.calls[0].args, test.args) {
				t.Fatalf("launcher calls = %#v", starter.calls)
			}
		})
	}

	service := NewService(Config{Platform: "darwin", Starter: &fakeStarter{}})
	if err := service.OpenExternalURL("HTTPS://example.com/docs"); err != nil {
		t.Fatalf("uppercase HTTP scheme should be accepted: %v", err)
	}
	for _, value := range []string{
		"", "javascript:alert(1)", "file:///tmp/private", "http:///missing-host",
		"https://user:secret@example.com", "https://example.com\nmalicious",
	} {
		if err := service.OpenExternalURL(value); err == nil {
			t.Fatalf("unsafe URL %q unexpectedly succeeded", value)
		}
	}
}

func TestOpenDirectoryAndRestartOnlyLaunchValidatedTargets(t *testing.T) {
	starter := &fakeStarter{}
	executable := filepath.Join(t.TempDir(), "inquira-go")
	if err := os.WriteFile(executable, []byte("binary"), 0o700); err != nil {
		t.Fatal(err)
	}
	service := NewService(Config{
		Platform: "linux", Starter: starter,
		Executable: func() (string, error) { return executable, nil },
		Arguments:  []string{"--safe-mode"},
	})
	logs := t.TempDir()
	if err := service.OpenDirectory(logs); err != nil {
		t.Fatal(err)
	}
	if err := service.Restart(); err != nil {
		t.Fatal(err)
	}
	if len(starter.calls) != 2 || starter.calls[0].name != "xdg-open" || starter.calls[0].args[0] != logs ||
		starter.calls[1].name != executable || !slices.Equal(starter.calls[1].args, []string{"--safe-mode"}) {
		t.Fatalf("launcher calls = %#v", starter.calls)
	}
	if err := service.OpenDirectory(filepath.Join(logs, "missing")); err == nil {
		t.Fatal("missing diagnostics directory unexpectedly opened")
	}
	starter.err = errors.New("launch failed")
	if err := service.Restart(); err == nil || !strings.Contains(err.Error(), "launch failed") {
		t.Fatalf("restart error = %v", err)
	}
}

func TestAppendStartupLogCreatesPrivateSingleLineDiagnostics(t *testing.T) {
	directory := filepath.Join(t.TempDir(), "logs")
	path, err := AppendStartupLog(directory, "startup failed\nwith details")
	if err != nil {
		t.Fatal(err)
	}
	if path != filepath.Join(directory, StartupLogName) {
		t.Fatalf("log path = %q", path)
	}
	contents, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(contents), "startup failed with details") || strings.Count(strings.TrimSpace(string(contents)), "\n") != 0 {
		t.Fatalf("log contents = %q", contents)
	}
	info, err := os.Stat(path)
	if err != nil || (runtime.GOOS != "windows" && info.Mode().Perm()&0o077 != 0) {
		t.Fatalf("log permissions = %#o, %v", info.Mode().Perm(), err)
	}
}

func TestAppendStartupLogRotatesOversizedDiagnostics(t *testing.T) {
	directory := t.TempDir()
	path := filepath.Join(directory, StartupLogName)
	if err := os.WriteFile(path, []byte(strings.Repeat("x", maxStartupLog)), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := AppendStartupLog(directory, "fresh startup"); err != nil {
		t.Fatal(err)
	}
	contents, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(contents), strings.Repeat("x", 100)) || !strings.Contains(string(contents), "fresh startup") {
		t.Fatalf("rotated log contents = %q", contents)
	}
}
