package desktop

import (
	"encoding/base64"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type ExportFilter struct {
	Name       string   `json:"name"`
	Extensions []string `json:"extensions"`
}

type ExportRequest struct {
	DefaultFileName string         `json:"default_file_name"`
	ContentBase64   string         `json:"content_base64"`
	Filters         []ExportFilter `json:"filters"`
}

type PreparedExport struct {
	DefaultFileName string
	Content         []byte
	Filters         []ExportFilter
}

func PrepareExport(request ExportRequest) (PreparedExport, error) {
	fileName := strings.TrimSpace(request.DefaultFileName)
	if fileName == "" || fileName == "." || fileName == ".." || strings.ContainsAny(fileName, "/\\\r\n\x00") {
		return PreparedExport{}, errors.New("a safe default export filename is required")
	}
	content, err := base64.StdEncoding.DecodeString(request.ContentBase64)
	if err != nil {
		return PreparedExport{}, fmt.Errorf("decode export content: %w", err)
	}
	filters := make([]ExportFilter, 0, len(request.Filters))
	for _, filter := range request.Filters {
		name := strings.TrimSpace(filter.Name)
		if strings.ContainsAny(name, "\r\n\x00") {
			return PreparedExport{}, errors.New("export filter name contains unsupported characters")
		}
		extensions := make([]string, 0, len(filter.Extensions))
		seen := make(map[string]struct{}, len(filter.Extensions))
		for _, rawExtension := range filter.Extensions {
			extension := strings.ToLower(strings.TrimSpace(rawExtension))
			if !validExportExtension(extension) {
				return PreparedExport{}, fmt.Errorf("unsupported export extension %q", rawExtension)
			}
			if _, exists := seen[extension]; exists {
				continue
			}
			seen[extension] = struct{}{}
			extensions = append(extensions, extension)
		}
		if len(extensions) == 0 {
			return PreparedExport{}, errors.New("export filters must include at least one extension")
		}
		if name == "" {
			name = strings.ToUpper(extensions[0]) + " file"
		}
		filters = append(filters, ExportFilter{Name: name, Extensions: extensions})
	}
	return PreparedExport{DefaultFileName: fileName, Content: content, Filters: filters}, nil
}

func validExportExtension(extension string) bool {
	if extension == "" {
		return false
	}
	for _, character := range extension {
		if (character < 'a' || character > 'z') && (character < '0' || character > '9') {
			return false
		}
	}
	return true
}

func WriteExport(target string, content []byte) error {
	if strings.TrimSpace(target) == "" {
		return errors.New("an export destination is required")
	}
	absolute, err := filepath.Abs(target)
	if err != nil {
		return fmt.Errorf("resolve export destination: %w", err)
	}
	directory := filepath.Dir(absolute)
	info, err := os.Stat(directory)
	if err != nil {
		return fmt.Errorf("read export destination directory: %w", err)
	}
	if !info.IsDir() {
		return errors.New("export destination parent is not a directory")
	}
	temporary, err := os.CreateTemp(directory, ".inquira-export-*.tmp")
	if err != nil {
		return fmt.Errorf("create staged export: %w", err)
	}
	temporaryPath := temporary.Name()
	committed := false
	defer func() {
		_ = temporary.Close()
		if !committed {
			_ = os.Remove(temporaryPath)
		}
	}()
	if err := temporary.Chmod(0o600); err != nil {
		return fmt.Errorf("secure staged export: %w", err)
	}
	if _, err := temporary.Write(content); err != nil {
		return fmt.Errorf("write staged export: %w", err)
	}
	if err := temporary.Sync(); err != nil {
		return fmt.Errorf("sync staged export: %w", err)
	}
	if err := temporary.Close(); err != nil {
		return fmt.Errorf("close staged export: %w", err)
	}
	if err := os.Rename(temporaryPath, absolute); err != nil {
		return fmt.Errorf("publish export: %w", err)
	}
	committed = true
	return nil
}
