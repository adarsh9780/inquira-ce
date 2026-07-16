package modelconfig

import (
	"errors"
	"fmt"
	"strings"

	keyring "github.com/zalando/go-keyring"
)

const keychainService = "com.inquira.desktop"

type SecretStore interface {
	Set(provider, secret string) error
	Get(provider string) (string, error)
	Delete(provider string) error
	Has(provider string) (bool, error)
}

type OSKeychain struct{}

func (OSKeychain) Set(provider, secret string) error {
	if err := keyring.Set(keychainService, keychainAccount(provider), strings.TrimSpace(secret)); err != nil {
		return fmt.Errorf("store API key in OS keychain: %w", err)
	}
	return nil
}

func (OSKeychain) Get(provider string) (string, error) {
	secret, err := keyring.Get(keychainService, keychainAccount(provider))
	if errors.Is(err, keyring.ErrNotFound) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read API key from OS keychain: %w", err)
	}
	return strings.TrimSpace(secret), nil
}

func (OSKeychain) Delete(provider string) error {
	err := keyring.Delete(keychainService, keychainAccount(provider))
	if errors.Is(err, keyring.ErrNotFound) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("delete API key from OS keychain: %w", err)
	}
	return nil
}

func (keychain OSKeychain) Has(provider string) (bool, error) {
	secret, err := keychain.Get(provider)
	return secret != "", err
}

func keychainAccount(provider string) string {
	return "llm-api-key:" + normalizeProvider(provider)
}
