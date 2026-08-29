package netclient

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// Config controls outbound provider traffic. Empty proxy and CA values use the
// operating system and standard HTTP(S)_PROXY/NO_PROXY environment variables.
type Config struct {
	Timeout               time.Duration
	ProxyURL              string
	NoProxy               string
	CABundlePath          string
	ClientCertificatePath string
	ClientKeyPath         string
	DisableProxy          bool
}

func New(config Config) (*http.Client, error) {
	transport, ok := http.DefaultTransport.(*http.Transport)
	if !ok {
		return nil, fmt.Errorf("default HTTP transport has unexpected type")
	}
	cloned := transport.Clone()
	cloned.Proxy = http.ProxyFromEnvironment
	if config.DisableProxy {
		cloned.Proxy = nil
	}

	if config.ProxyURL != "" {
		parsed, err := url.Parse(config.ProxyURL)
		if err != nil || parsed.Scheme == "" || parsed.Host == "" {
			return nil, fmt.Errorf("invalid proxy URL")
		}
		cloned.Proxy = proxyWithBypass(parsed, config.NoProxy)
	}

	if config.ClientCertificatePath != "" || config.ClientKeyPath != "" {
		if config.ClientCertificatePath == "" || config.ClientKeyPath == "" {
			return nil, fmt.Errorf("client certificate and private key must be configured together")
		}
		certificate, err := tls.LoadX509KeyPair(config.ClientCertificatePath, config.ClientKeyPath)
		if err != nil {
			return nil, fmt.Errorf("load client certificate: %w", err)
		}
		if cloned.TLSClientConfig == nil {
			cloned.TLSClientConfig = &tls.Config{MinVersion: tls.VersionTLS12}
		} else {
			cloned.TLSClientConfig = cloned.TLSClientConfig.Clone()
		}
		cloned.TLSClientConfig.Certificates = []tls.Certificate{certificate}
	}

	if config.CABundlePath != "" {
		pem, err := os.ReadFile(config.CABundlePath)
		if err != nil {
			return nil, fmt.Errorf("read CA bundle: %w", err)
		}
		pool, err := x509.SystemCertPool()
		if err != nil || pool == nil {
			pool = x509.NewCertPool()
		}
		if !pool.AppendCertsFromPEM(pem) {
			return nil, fmt.Errorf("CA bundle contains no valid certificates")
		}
		if cloned.TLSClientConfig == nil {
			cloned.TLSClientConfig = &tls.Config{MinVersion: tls.VersionTLS12}
		} else {
			cloned.TLSClientConfig = cloned.TLSClientConfig.Clone()
		}
		cloned.TLSClientConfig.RootCAs = pool
	}

	timeout := config.Timeout
	if timeout <= 0 {
		timeout = 20 * time.Second
	}
	return &http.Client{Transport: cloned, Timeout: timeout}, nil
}

func proxyWithBypass(proxyURL *url.URL, noProxy string) func(*http.Request) (*url.URL, error) {
	patterns := strings.Split(noProxy, ",")
	return func(request *http.Request) (*url.URL, error) {
		host := request.URL.Hostname()
		for _, rawPattern := range patterns {
			pattern := strings.TrimSpace(strings.ToLower(rawPattern))
			if pattern == "" {
				continue
			}
			if pattern == "*" || hostMatchesNoProxy(strings.ToLower(host), pattern) {
				return nil, nil
			}
		}
		return proxyURL, nil
	}
}

func hostMatchesNoProxy(host, pattern string) bool {
	if _, network, err := net.ParseCIDR(pattern); err == nil {
		return network.Contains(net.ParseIP(host))
	}
	if patternHost, _, err := net.SplitHostPort(pattern); err == nil {
		pattern = patternHost
	}
	pattern = strings.TrimPrefix(pattern, "*.")
	pattern = strings.TrimPrefix(pattern, ".")
	return host == pattern || strings.HasSuffix(host, "."+pattern)
}
