package netclient

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"time"
)

// Config controls outbound provider traffic. Empty proxy and CA values use the
// operating system and standard HTTP(S)_PROXY/NO_PROXY environment variables.
type Config struct {
	Timeout      time.Duration
	ProxyURL     string
	CABundlePath string
}

func New(config Config) (*http.Client, error) {
	transport, ok := http.DefaultTransport.(*http.Transport)
	if !ok {
		return nil, fmt.Errorf("default HTTP transport has unexpected type")
	}
	cloned := transport.Clone()
	cloned.Proxy = http.ProxyFromEnvironment

	if config.ProxyURL != "" {
		parsed, err := url.Parse(config.ProxyURL)
		if err != nil || parsed.Scheme == "" || parsed.Host == "" {
			return nil, fmt.Errorf("invalid proxy URL")
		}
		cloned.Proxy = http.ProxyURL(parsed)
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
