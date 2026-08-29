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

func TestExplicitProxyHonorsBypassList(t *testing.T) {
	client, err := New(Config{
		ProxyURL: "http://proxy.example:8080",
		NoProxy:  "localhost,.company.internal,10.0.0.0/8",
	})
	if err != nil {
		t.Fatal(err)
	}
	transport := client.Transport.(*http.Transport)
	for _, target := range []string{"https://api.company.internal/v1", "http://10.2.3.4/status"} {
		proxy, err := transport.Proxy(&http.Request{URL: mustURL(t, target)})
		if err != nil {
			t.Fatal(err)
		}
		if proxy != nil {
			t.Fatalf("proxy for %s = %v, want direct connection", target, proxy)
		}
	}
	proxy, err := transport.Proxy(&http.Request{URL: mustURL(t, "https://api.openai.com/v1/models")})
	if err != nil || proxy == nil || proxy.String() != "http://proxy.example:8080" {
		t.Fatalf("external proxy = %v, %v", proxy, err)
	}
}

func TestDirectModeDisablesEnvironmentProxy(t *testing.T) {
	t.Setenv("HTTPS_PROXY", "http://proxy.example:8080")
	client, err := New(Config{DisableProxy: true})
	if err != nil {
		t.Fatal(err)
	}
	if client.Transport.(*http.Transport).Proxy != nil {
		t.Fatal("direct mode retained a proxy resolver")
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
