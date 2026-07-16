package main

import "testing"

func TestTargetDetails(t *testing.T) {
	tests := []struct {
		goos       string
		goarch     string
		target     string
		archive    string
		executable string
	}{
		{goos: "darwin", goarch: "arm64", target: "aarch64-apple-darwin", archive: "tar.gz", executable: "uv"},
		{goos: "linux", goarch: "amd64", target: "x86_64-unknown-linux-gnu", archive: "tar.gz", executable: "uv"},
		{goos: "windows", goarch: "amd64", target: "x86_64-pc-windows-msvc", archive: "zip", executable: "uv.exe"},
	}
	for _, test := range tests {
		t.Run(test.goos+"-"+test.goarch, func(t *testing.T) {
			target, archive, executable, err := targetDetails(test.goos, test.goarch)
			if err != nil {
				t.Fatal(err)
			}
			if target != test.target || archive != test.archive || executable != test.executable {
				t.Fatalf("got %q %q %q", target, archive, executable)
			}
		})
	}
}

func TestTargetDetailsRejectsUnsupportedTarget(t *testing.T) {
	if _, _, _, err := targetDetails("plan9", "amd64"); err == nil {
		t.Fatal("expected unsupported target to fail")
	}
}
