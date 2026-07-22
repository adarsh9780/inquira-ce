package terminal

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"unicode"
)

const (
	DataEventName = "terminal:pty-data"
	ExitEventName = "terminal:pty-exit"
	maxDimension  = 500
)

var ErrSessionNotFound = errors.New("terminal session not found")

type StartRequest struct {
	WorkspaceID string `json:"workspace_id"`
	SessionID   string `json:"session_id"`
	Cwd         string `json:"cwd"`
	Cols        int    `json:"cols"`
	Rows        int    `json:"rows"`
}

type StartResponse struct {
	SessionID string `json:"session_id"`
	Cwd       string `json:"cwd"`
	Shell     string `json:"shell"`
}

type StopResponse struct {
	SessionID string `json:"session_id"`
	Stopped   bool   `json:"stopped"`
}

type DataEvent struct {
	SessionID string `json:"session_id"`
	Data      string `json:"data"`
}

type ExitEvent struct {
	SessionID string `json:"session_id"`
}

type Process interface {
	io.Reader
	io.Writer
	Resize(cols, rows int) error
	Kill() error
	Wait() error
}

type Factory interface {
	Start(ctx context.Context, cwd string, cols, rows int) (Process, string, error)
}

type Emitter func(eventName string, payload any)

type Service struct {
	mu       sync.Mutex
	factory  Factory
	emit     Emitter
	sessions map[string]*session
	closed   bool
}

type session struct {
	id      string
	process Process
	service *Service
	once    sync.Once
}

func NewService(factory Factory, emitter Emitter) *Service {
	return &Service{factory: factory, emit: emitter, sessions: make(map[string]*session)}
}

func NewPlatformService(emitter Emitter) *Service {
	return NewService(platformFactory{}, emitter)
}

func (s *Service) Start(ctx context.Context, request StartRequest) (StartResponse, error) {
	id, err := normalizeSessionID(request.SessionID)
	if err != nil {
		return StartResponse{}, err
	}
	cwd, err := normalizeCwd(request.Cwd)
	if err != nil {
		return StartResponse{}, err
	}
	cols := normalizeDimension(request.Cols)
	rows := normalizeDimension(request.Rows)

	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return StartResponse{}, errors.New("terminal service is closed")
	}
	existing := s.sessions[id]
	if existing != nil {
		delete(s.sessions, id)
	}
	s.mu.Unlock()
	if existing != nil {
		existing.terminate()
	}

	process, shell, err := s.factory.Start(ctx, cwd, cols, rows)
	if err != nil {
		return StartResponse{}, fmt.Errorf("start terminal process: %w", err)
	}
	if process == nil {
		return StartResponse{}, errors.New("start terminal process: process is unavailable")
	}
	created := &session{id: id, process: process, service: s}
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		_ = process.Kill()
		return StartResponse{}, errors.New("terminal service is closed")
	}
	s.sessions[id] = created
	s.mu.Unlock()
	go created.readOutput()
	go created.wait()
	return StartResponse{SessionID: id, Cwd: cwd, Shell: shell}, nil
}

func (s *Service) Write(sessionID, data string) error {
	current, err := s.get(sessionID)
	if err != nil {
		return err
	}
	if _, err := current.process.Write([]byte(data)); err != nil {
		return fmt.Errorf("write terminal input: %w", err)
	}
	return nil
}

func (s *Service) Resize(sessionID string, cols, rows int) error {
	current, err := s.get(sessionID)
	if err != nil {
		return err
	}
	if err := current.process.Resize(normalizeDimension(cols), normalizeDimension(rows)); err != nil {
		return fmt.Errorf("resize terminal: %w", err)
	}
	return nil
}

func (s *Service) Stop(sessionID string) (bool, error) {
	id := strings.TrimSpace(sessionID)
	s.mu.Lock()
	current := s.sessions[id]
	if current != nil {
		delete(s.sessions, id)
	}
	s.mu.Unlock()
	if current == nil {
		return false, nil
	}
	return true, current.terminate()
}

func (s *Service) Close() error {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return nil
	}
	s.closed = true
	active := make([]*session, 0, len(s.sessions))
	for _, current := range s.sessions {
		active = append(active, current)
	}
	clear(s.sessions)
	s.mu.Unlock()
	var result error
	for _, current := range active {
		result = errors.Join(result, current.terminate())
	}
	return result
}

func (s *Service) get(sessionID string) (*session, error) {
	id := strings.TrimSpace(sessionID)
	s.mu.Lock()
	defer s.mu.Unlock()
	current := s.sessions[id]
	if current == nil {
		return nil, ErrSessionNotFound
	}
	return current, nil
}

func (current *session) readOutput() {
	buffer := make([]byte, 4096)
	for {
		count, err := current.process.Read(buffer)
		if count > 0 {
			current.service.emitEvent(DataEventName, DataEvent{SessionID: current.id, Data: string(buffer[:count])})
		}
		if err != nil {
			current.finish()
			return
		}
	}
}

func (current *session) wait() {
	_ = current.process.Wait()
	current.finish()
}

func (current *session) terminate() error {
	err := current.process.Kill()
	current.finish()
	return err
}

func (current *session) finish() {
	current.once.Do(func() {
		current.service.mu.Lock()
		if current.service.sessions[current.id] == current {
			delete(current.service.sessions, current.id)
		}
		current.service.mu.Unlock()
		current.service.emitEvent(ExitEventName, ExitEvent{SessionID: current.id})
	})
}

func (s *Service) emitEvent(name string, payload any) {
	if s.emit != nil {
		s.emit(name, payload)
	}
}

func normalizeSessionID(value string) (string, error) {
	id := strings.TrimSpace(value)
	if id == "" {
		return "", errors.New("terminal session identity is required")
	}
	if len(id) > 200 {
		return "", errors.New("terminal session identity is too long")
	}
	for _, char := range id {
		if unicode.IsControl(char) {
			return "", errors.New("terminal session identity is invalid")
		}
	}
	return id, nil
}

func normalizeCwd(value string) (string, error) {
	cwd := strings.TrimSpace(value)
	if cwd == "" {
		return "", errors.New("terminal working directory is required")
	}
	absolute, err := filepath.Abs(cwd)
	if err != nil {
		return "", fmt.Errorf("resolve terminal working directory: %w", err)
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return "", fmt.Errorf("read terminal working directory: %w", err)
	}
	if !info.IsDir() {
		return "", errors.New("terminal working directory is not a directory")
	}
	return filepath.Clean(absolute), nil
}

func normalizeDimension(value int) int {
	if value < 1 {
		return 1
	}
	if value > maxDimension {
		return maxDimension
	}
	return value
}
