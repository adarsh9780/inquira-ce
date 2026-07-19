package conversation

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type HeapObject struct {
	RelativePath string
	ByteSize     int64
	SHA256       string
}

type HeapReconciliation struct {
	OrphansRemoved int
	MissingPaths   []string
}

type heap interface {
	CreateConversation(workspaceID, conversationID string) error
	RemoveConversation(workspaceID, conversationID string) error
	Put(workspaceID, conversationID, storageClass, objectID, format string, source io.Reader) (HeapObject, error)
	RemoveObject(workspaceID, relativePath string) error
	Resolve(workspaceID, relativePath string) (string, error)
	ReconcileWorkspace(workspaceID string, referenced map[string]map[string]struct{}) (HeapReconciliation, error)
}

type FileHeap struct {
	root string
}

func NewFileHeap(root string) *FileHeap {
	return &FileHeap{root: filepath.Clean(root)}
}

func (h *FileHeap) CreateConversation(workspaceID, conversationID string) error {
	if !safePathComponent(workspaceID) || !safePathComponent(conversationID) {
		return fmt.Errorf("invalid conversation heap identity")
	}
	if _, err := h.ensureDirectories(workspaceID, "conversations", conversationID); err != nil {
		return err
	}
	for _, storageClass := range []string{StorageClassArtifacts, StorageClassAttachments} {
		if _, err := h.ensureDirectories(workspaceID, "conversations", conversationID, storageClass); err != nil {
			return fmt.Errorf("create conversation %s directory: %w", storageClass, err)
		}
	}
	return nil
}

func (h *FileHeap) RemoveConversation(workspaceID, conversationID string) error {
	directory, err := h.conversationDirectory(workspaceID, conversationID)
	if err != nil {
		return err
	}
	if _, err := h.ensureDirectories(workspaceID, "conversations"); err != nil {
		return err
	}
	if err := os.RemoveAll(directory); err != nil {
		return fmt.Errorf("remove conversation heap: %w", err)
	}
	return nil
}

func (h *FileHeap) Put(workspaceID, conversationID, storageClass, objectID, format string, source io.Reader) (HeapObject, error) {
	if source == nil {
		return HeapObject{}, fmt.Errorf("artifact payload reader is nil")
	}
	conversationDirectory, err := h.conversationDirectory(workspaceID, conversationID)
	if err != nil {
		return HeapObject{}, err
	}
	if !validStorageClass(storageClass) || !safePathComponent(objectID) || !safeToken(format) {
		return HeapObject{}, fmt.Errorf("invalid heap object identity")
	}
	directory := filepath.Join(conversationDirectory, storageClass)
	if err := h.CreateConversation(workspaceID, conversationID); err != nil {
		return HeapObject{}, err
	}
	temporary, err := os.CreateTemp(directory, ".tmp-*")
	if err != nil {
		return HeapObject{}, fmt.Errorf("create temporary artifact: %w", err)
	}
	temporaryPath := temporary.Name()
	closed := false
	defer func() {
		if !closed {
			_ = temporary.Close()
		}
		_ = os.Remove(temporaryPath)
	}()
	if err := temporary.Chmod(0o600); err != nil {
		return HeapObject{}, fmt.Errorf("secure temporary artifact: %w", err)
	}
	digest := sha256.New()
	byteSize, err := io.Copy(io.MultiWriter(temporary, digest), source)
	if err != nil {
		return HeapObject{}, fmt.Errorf("write temporary artifact: %w", err)
	}
	if err := temporary.Sync(); err != nil {
		return HeapObject{}, fmt.Errorf("sync temporary artifact: %w", err)
	}
	if err := temporary.Close(); err != nil {
		return HeapObject{}, fmt.Errorf("close temporary artifact: %w", err)
	}
	closed = true
	target := filepath.Join(directory, objectID+"."+format)
	if _, err := os.Lstat(target); err == nil {
		return HeapObject{}, fmt.Errorf("artifact target already exists")
	} else if !os.IsNotExist(err) {
		return HeapObject{}, fmt.Errorf("inspect artifact target: %w", err)
	}
	if err := os.Rename(temporaryPath, target); err != nil {
		return HeapObject{}, fmt.Errorf("publish artifact: %w", err)
	}
	relative, err := filepath.Rel(filepath.Join(h.root, workspaceID), target)
	if err != nil {
		_ = os.Remove(target)
		return HeapObject{}, fmt.Errorf("identify artifact path: %w", err)
	}
	return HeapObject{
		RelativePath: filepath.ToSlash(relative),
		ByteSize:     byteSize,
		SHA256:       "sha256:" + hex.EncodeToString(digest.Sum(nil)),
	}, nil
}

func (h *FileHeap) RemoveObject(workspaceID, relativePath string) error {
	path, err := h.Resolve(workspaceID, relativePath)
	if err != nil {
		return err
	}
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove heap object: %w", err)
	}
	return nil
}

func (h *FileHeap) Resolve(workspaceID, relativePath string) (string, error) {
	if !safePathComponent(workspaceID) || filepath.IsAbs(relativePath) || relativePath == "" {
		return "", fmt.Errorf("invalid relative heap path")
	}
	workspaceDirectory := filepath.Join(h.root, workspaceID)
	resolved := filepath.Join(workspaceDirectory, filepath.FromSlash(relativePath))
	relative, err := filepath.Rel(workspaceDirectory, resolved)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) {
		return "", fmt.Errorf("heap path escapes workspace")
	}
	if err := h.validateDirectoryPath(filepath.Dir(resolved)); err != nil {
		return "", err
	}
	return resolved, nil
}

func (h *FileHeap) ReconcileWorkspace(workspaceID string, referenced map[string]map[string]struct{}) (HeapReconciliation, error) {
	if !safePathComponent(workspaceID) {
		return HeapReconciliation{}, fmt.Errorf("invalid workspace identity")
	}
	conversationsRoot, err := h.ensureDirectories(workspaceID, "conversations")
	if err != nil {
		return HeapReconciliation{}, fmt.Errorf("create conversations heap: %w", err)
	}
	result := HeapReconciliation{MissingPaths: make([]string, 0)}
	entries, err := os.ReadDir(conversationsRoot)
	if err != nil {
		return HeapReconciliation{}, fmt.Errorf("read conversations heap: %w", err)
	}
	for _, entry := range entries {
		references, exists := referenced[entry.Name()]
		path := filepath.Join(conversationsRoot, entry.Name())
		if !exists || !entry.IsDir() {
			if err := os.RemoveAll(path); err != nil {
				return HeapReconciliation{}, fmt.Errorf("remove orphan conversation object: %w", err)
			}
			result.OrphansRemoved++
			continue
		}
		removed, err := h.removeUnreferenced(path, references)
		if err != nil {
			return HeapReconciliation{}, err
		}
		result.OrphansRemoved += removed
		if err := h.CreateConversation(workspaceID, entry.Name()); err != nil {
			return HeapReconciliation{}, err
		}
	}
	for conversationID, references := range referenced {
		if err := h.CreateConversation(workspaceID, conversationID); err != nil {
			return HeapReconciliation{}, err
		}
		for relativePath := range references {
			path, err := h.Resolve(workspaceID, relativePath)
			if err != nil {
				return HeapReconciliation{}, err
			}
			info, statErr := os.Stat(path)
			if statErr != nil || !info.Mode().IsRegular() {
				result.MissingPaths = append(result.MissingPaths, relativePath)
			}
		}
	}
	return result, nil
}

func (h *FileHeap) removeUnreferenced(conversationDirectory string, referenced map[string]struct{}) (int, error) {
	removed := 0
	entries, err := os.ReadDir(conversationDirectory)
	if err != nil {
		return 0, err
	}
	for _, entry := range entries {
		if entry.Name() != StorageClassArtifacts && entry.Name() != StorageClassAttachments {
			if err := os.RemoveAll(filepath.Join(conversationDirectory, entry.Name())); err != nil {
				return 0, err
			}
			removed++
			continue
		}
		classDirectory := filepath.Join(conversationDirectory, entry.Name())
		if !entry.IsDir() {
			if err := os.Remove(classDirectory); err != nil {
				return 0, err
			}
			removed++
			continue
		}
		objects, err := os.ReadDir(classDirectory)
		if err != nil {
			return 0, err
		}
		for _, object := range objects {
			path := filepath.Join(classDirectory, object.Name())
			relative, err := filepath.Rel(filepath.Dir(filepath.Dir(conversationDirectory)), path)
			if err != nil {
				return 0, err
			}
			if _, exists := referenced[filepath.ToSlash(relative)]; exists && !object.IsDir() {
				continue
			}
			if err := os.RemoveAll(path); err != nil {
				return 0, err
			}
			removed++
		}
	}
	return removed, nil
}

func (h *FileHeap) conversationDirectory(workspaceID, conversationID string) (string, error) {
	if !safePathComponent(workspaceID) || !safePathComponent(conversationID) {
		return "", fmt.Errorf("invalid conversation heap identity")
	}
	return filepath.Join(h.root, workspaceID, "conversations", conversationID), nil
}

func (h *FileHeap) ensureDirectories(components ...string) (string, error) {
	if err := os.MkdirAll(h.root, 0o700); err != nil {
		return "", fmt.Errorf("create heap root: %w", err)
	}
	if err := requireRealDirectory(h.root); err != nil {
		return "", err
	}
	current := h.root
	for _, component := range components {
		if !safePathComponent(component) {
			return "", fmt.Errorf("invalid heap directory identity")
		}
		current = filepath.Join(current, component)
		if err := os.Mkdir(current, 0o700); err != nil && !os.IsExist(err) {
			return "", fmt.Errorf("create heap directory: %w", err)
		}
		if err := requireRealDirectory(current); err != nil {
			return "", err
		}
	}
	return current, nil
}

func (h *FileHeap) validateDirectoryPath(directory string) error {
	relative, err := filepath.Rel(h.root, directory)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) {
		return fmt.Errorf("heap directory escapes root")
	}
	if err := requireRealDirectory(h.root); err != nil {
		return err
	}
	current := h.root
	if relative == "." {
		return nil
	}
	for _, component := range strings.Split(relative, string(os.PathSeparator)) {
		current = filepath.Join(current, component)
		if err := requireRealDirectory(current); err != nil {
			return err
		}
	}
	return nil
}

func requireRealDirectory(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		return fmt.Errorf("inspect heap directory: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
		return fmt.Errorf("heap directory is not a real directory")
	}
	return nil
}

func safePathComponent(value string) bool {
	return value != "" && value != "." && value != ".." && filepath.Base(value) == value && !strings.ContainsAny(value, `/\\`)
}

func safeToken(value string) bool {
	if value == "" {
		return false
	}
	for _, current := range value {
		if (current < 'a' || current > 'z') && (current < '0' || current > '9') {
			return false
		}
	}
	return true
}

func validStorageClass(value string) bool {
	return value == StorageClassArtifacts || value == StorageClassAttachments
}
