package modelconfig

import (
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

const (
	NetworkModeInherit = "inherit"
	NetworkModeSystem  = "system"
	NetworkModeCustom  = "custom"
	NetworkModeDirect  = "direct"
)

// NetworkSettings controls proxy and trust configuration. Provider settings
// may inherit the application-wide configuration or override it.
type NetworkSettings struct {
	Mode                  string `json:"mode"`
	ProxyURL              string `json:"proxy_url,omitempty"`
	NoProxy               string `json:"no_proxy,omitempty"`
	CABundlePath          string `json:"ca_bundle_path,omitempty"`
	ClientCertificatePath string `json:"client_certificate_path,omitempty"`
	ClientKeyPath         string `json:"client_key_path,omitempty"`
}

type ProviderSettings struct {
	BaseURL      string          `json:"base_url,omitempty"`
	APIKeyHeader string          `json:"api_key_header,omitempty"`
	APIKeyPrefix string          `json:"api_key_prefix,omitempty"`
	APIVersion   string          `json:"api_version,omitempty"`
	Organization string          `json:"organization,omitempty"`
	Project      string          `json:"project,omitempty"`
	Network      NetworkSettings `json:"network"`
}

type NetworkPreferencesResponse struct {
	Global NetworkSettings `json:"global"`
}

type HTTPClientFactory func(NetworkSettings) (HTTPDoer, error)

func defaultNetworkSettings() NetworkSettings {
	return NetworkSettings{Mode: NetworkModeSystem}
}

func defaultProviderSettings() map[string]ProviderSettings {
	return map[string]ProviderSettings{
		"openrouter":        {BaseURL: "https://openrouter.ai/api/v1", APIKeyHeader: "Authorization", APIKeyPrefix: "Bearer", Network: NetworkSettings{Mode: NetworkModeInherit}},
		"openai":            {BaseURL: "https://api.openai.com/v1", APIKeyHeader: "Authorization", APIKeyPrefix: "Bearer", Network: NetworkSettings{Mode: NetworkModeInherit}},
		"anthropic":         {BaseURL: "https://api.anthropic.com/v1", APIKeyHeader: "x-api-key", Network: NetworkSettings{Mode: NetworkModeInherit}},
		"ollama":            {BaseURL: "http://localhost:11434", Network: NetworkSettings{Mode: NetworkModeInherit}},
		"openai-compatible": {APIKeyHeader: "Authorization", APIKeyPrefix: "Bearer", Network: NetworkSettings{Mode: NetworkModeInherit}},
	}
}

func mergeProviderSettings(saved map[string]ProviderSettings) map[string]ProviderSettings {
	merged := defaultProviderSettings()
	for provider, settings := range saved {
		provider = normalizeProvider(provider)
		defaults := merged[provider]
		if strings.TrimSpace(settings.BaseURL) == "" {
			settings.BaseURL = defaults.BaseURL
		}
		if strings.TrimSpace(settings.APIKeyHeader) == "" {
			settings.APIKeyHeader = defaults.APIKeyHeader
		}
		if strings.TrimSpace(settings.Network.Mode) == "" {
			settings.Network.Mode = NetworkModeInherit
		}
		merged[provider] = settings
	}
	return merged
}

func normalizeNetworkSettings(settings NetworkSettings, allowInherit bool) NetworkSettings {
	settings.Mode = strings.ToLower(strings.TrimSpace(settings.Mode))
	valid := settings.Mode == NetworkModeSystem || settings.Mode == NetworkModeCustom || settings.Mode == NetworkModeDirect
	if allowInherit && settings.Mode == NetworkModeInherit {
		valid = true
	}
	if !valid {
		if allowInherit {
			settings.Mode = NetworkModeInherit
		} else {
			settings.Mode = NetworkModeSystem
		}
	}
	settings.ProxyURL = strings.TrimSpace(settings.ProxyURL)
	settings.NoProxy = strings.TrimSpace(settings.NoProxy)
	settings.CABundlePath = strings.TrimSpace(settings.CABundlePath)
	settings.ClientCertificatePath = strings.TrimSpace(settings.ClientCertificatePath)
	settings.ClientKeyPath = strings.TrimSpace(settings.ClientKeyPath)
	return settings
}

func validateNetworkSettings(settings NetworkSettings, allowInherit bool) error {
	settings = normalizeNetworkSettings(settings, allowInherit)
	if settings.Mode == NetworkModeCustom {
		parsed, err := url.Parse(settings.ProxyURL)
		if err != nil || parsed.Host == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") {
			return fmt.Errorf("proxy URL must be a valid HTTP or HTTPS URL")
		}
	}
	if strings.ContainsAny(settings.NoProxy, "\r\n") {
		return fmt.Errorf("proxy bypass list may not contain line breaks")
	}
	for label, path := range map[string]string{
		"CA certificate bundle": settings.CABundlePath,
		"client certificate":    settings.ClientCertificatePath,
		"client private key":    settings.ClientKeyPath,
	} {
		if err := validateReadableFile(label, path); err != nil {
			return err
		}
	}
	if (settings.ClientCertificatePath == "") != (settings.ClientKeyPath == "") {
		return fmt.Errorf("client certificate and private key must be selected together")
	}
	return nil
}

func validateReadableFile(label, value string) error {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	if !filepath.IsAbs(value) {
		return fmt.Errorf("%s must be an absolute path", label)
	}
	info, err := os.Stat(value)
	if err != nil {
		return fmt.Errorf("%s is not accessible: %w", label, err)
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("%s must be a regular file", label)
	}
	return nil
}

func validateProviderSettings(provider string, settings ProviderSettings) error {
	provider = normalizeProvider(provider)
	settings.Network = normalizeNetworkSettings(settings.Network, true)
	if err := validateNetworkSettings(settings.Network, true); err != nil {
		return err
	}
	if provider == "openai-compatible" {
		if !isValidBaseURL(strings.TrimRight(strings.TrimSpace(settings.BaseURL), "/")) {
			return fmt.Errorf("base URL must be a valid HTTP or HTTPS URL")
		}
		if !validHeaderName(settings.APIKeyHeader) {
			return fmt.Errorf("API key header must be a valid HTTP header name")
		}
	}
	if strings.ContainsAny(settings.APIVersion, "\r\n") {
		return fmt.Errorf("API version may not contain line breaks")
	}
	return nil
}

func validHeaderName(value string) bool {
	value = strings.TrimSpace(value)
	if value == "" {
		return false
	}
	const separators = "()<>@,;:\\\"/[]?={} \t"
	for _, character := range value {
		if character < 33 || character > 126 || strings.ContainsRune(separators, character) {
			return false
		}
	}
	return true
}

func resolvedNetworkSettings(preferences Preferences, provider string) NetworkSettings {
	global := normalizeNetworkSettings(preferences.GlobalNetwork, false)
	providerNetwork := normalizeNetworkSettings(preferences.ProviderSettings[normalizeProvider(provider)].Network, true)
	if providerNetwork.Mode == NetworkModeInherit {
		return global
	}
	return providerNetwork
}
