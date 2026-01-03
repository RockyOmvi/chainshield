// Package chainshield provides the official Go SDK for ChainShield Risk Assessment API.
//
// Usage:
//
//	client := chainshield.New("cs_your_api_key")
//	result, err := client.Analyze("0x742d35Cc...")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	if result.IsHighRisk() {
//	    log.Println("High risk wallet!")
//	}
package chainshield

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	DefaultBaseURL = "https://api.chainshield.io"
	APIVersion     = "v1"
	SDKVersion     = "1.0.0"
)

// RiskLevel represents the risk category
type RiskLevel string

const (
	RiskLevelLow      RiskLevel = "LOW"
	RiskLevelMedium   RiskLevel = "MEDIUM"
	RiskLevelHigh     RiskLevel = "HIGH"
	RiskLevelCritical RiskLevel = "CRITICAL"
)

// Chain represents supported blockchain networks
type Chain string

const (
	ChainEthereum  Chain = "ethereum"
	ChainPolygon   Chain = "polygon"
	ChainArbitrum  Chain = "arbitrum"
	ChainBSC       Chain = "bsc"
	ChainOptimism  Chain = "optimism"
	ChainBase      Chain = "base"
	ChainAvalanche Chain = "avalanche"
	ChainFantom    Chain = "fantom"
	ChainZkSync    Chain = "zksync"
	ChainBitcoin   Chain = "bitcoin"
	ChainSolana    Chain = "solana"
)

// RiskAssessment is the result of analyzing a wallet
type RiskAssessment struct {
	Address   string    `json:"address"`
	Chain     Chain     `json:"chain"`
	RiskScore float64   `json:"risk_score"`
	RiskLevel RiskLevel `json:"risk_level"`
	Blocked   bool      `json:"blocked"`
	Factors   []string  `json:"factors"`
	Entity    *Entity   `json:"entity,omitempty"`
	Timestamp string    `json:"timestamp,omitempty"`
}

// Entity represents a known entity
type Entity struct {
	Name     string `json:"name"`
	Category string `json:"category"`
}

// IsHighRisk returns true if the wallet is high or critical risk
func (r *RiskAssessment) IsHighRisk() bool {
	return r.RiskLevel == RiskLevelHigh || r.RiskLevel == RiskLevelCritical
}

// IsSanctioned returns true if the wallet is blocked/sanctioned
func (r *RiskAssessment) IsSanctioned() bool {
	return r.Blocked
}

// IsSafe returns true if the wallet is considered safe
func (r *RiskAssessment) IsSafe() bool {
	return r.RiskLevel == RiskLevelLow && !r.Blocked
}

// Client is the ChainShield API client
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
}

// Option is a client configuration option
type Option func(*Client)

// WithBaseURL sets a custom base URL
func WithBaseURL(url string) Option {
	return func(c *Client) {
		c.baseURL = url
	}
}

// WithHTTPClient sets a custom HTTP client
func WithHTTPClient(client *http.Client) Option {
	return func(c *Client) {
		c.httpClient = client
	}
}

// WithTimeout sets the request timeout
func WithTimeout(timeout time.Duration) Option {
	return func(c *Client) {
		c.httpClient.Timeout = timeout
	}
}

// New creates a new ChainShield client
func New(apiKey string, opts ...Option) *Client {
	c := &Client{
		apiKey:  apiKey,
		baseURL: DefaultBaseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}

	for _, opt := range opts {
		opt(c)
	}

	return c
}

// Error represents an API error
type Error struct {
	StatusCode int
	Message    string
}

func (e *Error) Error() string {
	return fmt.Sprintf("chainshield: %s (status %d)", e.Message, e.StatusCode)
}

func (c *Client) doRequest(ctx context.Context, method, path string, body interface{}) ([]byte, error) {
	url := fmt.Sprintf("%s/api/%s%s", c.baseURL, APIVersion, path)

	var reqBody io.Reader
	if body != nil {
		jsonBytes, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewReader(jsonBytes)
	}

	req, err := http.NewRequestWithContext(ctx, method, url, reqBody)
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-API-Key", c.apiKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "ChainShield-Go-SDK/"+SDKVersion)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		return nil, &Error{
			StatusCode: resp.StatusCode,
			Message:    string(respBody),
		}
	}

	return respBody, nil
}

// AnalyzeRequest is the request for analyzing a wallet
type AnalyzeRequest struct {
	Address string `json:"address"`
	Chain   Chain  `json:"chain,omitempty"`
}

// Analyze analyzes a wallet address for risk
func (c *Client) Analyze(ctx context.Context, address string) (*RiskAssessment, error) {
	return c.AnalyzeWithChain(ctx, address, ChainEthereum)
}

// AnalyzeWithChain analyzes a wallet on a specific chain
func (c *Client) AnalyzeWithChain(ctx context.Context, address string, chain Chain) (*RiskAssessment, error) {
	body, err := c.doRequest(ctx, "POST", "/wallet/analyze", AnalyzeRequest{
		Address: address,
		Chain:   chain,
	})
	if err != nil {
		return nil, err
	}

	var result RiskAssessment
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	return &result, nil
}

// IsSanctioned quickly checks if an address is sanctioned
func (c *Client) IsSanctioned(ctx context.Context, address string) (bool, error) {
	result, err := c.Analyze(ctx, address)
	if err != nil {
		return false, err
	}
	return result.Blocked, nil
}

// IsHighRisk quickly checks if an address is high risk
func (c *Client) IsHighRisk(ctx context.Context, address string, threshold float64) (bool, error) {
	result, err := c.Analyze(ctx, address)
	if err != nil {
		return false, err
	}
	return result.RiskScore >= threshold, nil
}

// Health checks the API health status
func (c *Client) Health(ctx context.Context) (map[string]interface{}, error) {
	body, err := c.doRequest(ctx, "GET", "/health", nil)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	return result, nil
}

// Ping checks connectivity to the API
func (c *Client) Ping(ctx context.Context) bool {
	_, err := c.Health(ctx)
	return err == nil
}
