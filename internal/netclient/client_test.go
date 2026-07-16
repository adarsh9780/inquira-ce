package netclient

import (
	"net/http"
	"net/url"
	"testing"
	"time"
)

func TestNewUsesExplicitProxyAndTimeout(t *testing.T) {
	client, err := New(Config{ProxyURL: "http://proxy.example:8080", Timeout: 3 * time.Second})
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	if client.Timeout != 3*time.Second {
		t.Fatalf("timeout = %v", client.Timeout)
	}
	transport := client.Transport.(*http.Transport)
	proxy, err := transport.Proxy(&http.Request{URL: mustURL(t, "https://api.openai.com/v1/models")})
	if err != nil {
		t.Fatalf("Proxy() error = %v", err)
	}
	if got := proxy.String(); got != "http://proxy.example:8080" {
		t.Fatalf("proxy = %q", got)
	}
}

func TestNewRejectsInvalidProxy(t *testing.T) {
	if _, err := New(Config{ProxyURL: "://bad"}); err == nil {
		t.Fatal("expected invalid proxy error")
	}
}

func mustURL(t *testing.T, raw string) *url.URL {
	t.Helper()
	parsed, err := url.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	return parsed
}
