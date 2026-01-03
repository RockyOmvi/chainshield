//! # ChainShield Rust SDK
//!
//! Official Rust SDK for the ChainShield Risk Assessment API.
//!
//! ## Quick Start
//!
//! ```rust
//! use chainshield::ChainShield;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), chainshield::Error> {
//!     let client = ChainShield::new("cs_your_api_key");
//!     
//!     let result = client.analyze("0x742d35Cc...").await?;
//!     
//!     println!("Risk Score: {}", result.risk_score);
//!     println!("Risk Level: {:?}", result.risk_level);
//!     
//!     if result.is_high_risk() {
//!         println!("High risk wallet!");
//!     }
//!     
//!     Ok(())
//! }
//! ```

use reqwest::Client as HttpClient;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use thiserror::Error;

/// Default API base URL
pub const DEFAULT_BASE_URL: &str = "https://api.chainshield.io";
/// SDK version
pub const SDK_VERSION: &str = "1.0.0";

/// Risk level categories
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Supported blockchain networks
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Chain {
    Ethereum,
    Polygon,
    Arbitrum,
    Bsc,
    Optimism,
    Base,
    Avalanche,
    Fantom,
    ZkSync,
    Bitcoin,
    Solana,
}

impl Default for Chain {
    fn default() -> Self {
        Chain::Ethereum
    }
}

/// Risk assessment result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskAssessment {
    pub address: String,
    pub chain: Chain,
    pub risk_score: f64,
    pub risk_level: RiskLevel,
    pub blocked: bool,
    #[serde(default)]
    pub factors: Vec<String>,
    pub entity: Option<Entity>,
    pub timestamp: Option<String>,
}

impl RiskAssessment {
    /// Check if the wallet is high or critical risk
    pub fn is_high_risk(&self) -> bool {
        matches!(self.risk_level, RiskLevel::High | RiskLevel::Critical)
    }

    /// Check if the wallet is sanctioned/blocked
    pub fn is_sanctioned(&self) -> bool {
        self.blocked
    }

    /// Check if the wallet is considered safe
    pub fn is_safe(&self) -> bool {
        matches!(self.risk_level, RiskLevel::Low) && !self.blocked
    }
}

/// Known entity information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub name: String,
    pub category: String,
}

/// SDK errors
#[derive(Error, Debug)]
pub enum Error {
    #[error("Authentication failed: {0}")]
    Authentication(String),

    #[error("Rate limit exceeded, retry after {retry_after:?} seconds")]
    RateLimit { retry_after: Option<u64> },

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("API error: {message} (status {status_code})")]
    Api { status_code: u16, message: String },

    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Analyze request
#[derive(Debug, Serialize)]
struct AnalyzeRequest {
    address: String,
    chain: Chain,
}

/// ChainShield API client
#[derive(Debug, Clone)]
pub struct ChainShield {
    api_key: String,
    base_url: String,
    client: HttpClient,
}

impl ChainShield {
    /// Create a new ChainShield client
    ///
    /// # Arguments
    /// * `api_key` - Your ChainShield API key (starts with "cs_")
    ///
    /// # Example
    /// ```
    /// let client = ChainShield::new("cs_your_api_key");
    /// ```
    pub fn new(api_key: &str) -> Self {
        Self::with_options(api_key, DEFAULT_BASE_URL, Duration::from_secs(30))
    }

    /// Create a client with custom options
    pub fn with_options(api_key: &str, base_url: &str, timeout: Duration) -> Self {
        let client = HttpClient::builder()
            .timeout(timeout)
            .build()
            .expect("Failed to create HTTP client");

        Self {
            api_key: api_key.to_string(),
            base_url: base_url.trim_end_matches('/').to_string(),
            client,
        }
    }

    /// Analyze a wallet address for risk
    ///
    /// # Arguments
    /// * `address` - Wallet address to analyze
    ///
    /// # Returns
    /// Risk assessment result with score and factors
    pub async fn analyze(&self, address: &str) -> Result<RiskAssessment, Error> {
        self.analyze_with_chain(address, Chain::Ethereum).await
    }

    /// Analyze a wallet on a specific chain
    pub async fn analyze_with_chain(
        &self,
        address: &str,
        chain: Chain,
    ) -> Result<RiskAssessment, Error> {
        let url = format!("{}/api/v1/wallet/analyze", self.base_url);

        let response = self
            .client
            .post(&url)
            .header("X-API-Key", &self.api_key)
            .header("Content-Type", "application/json")
            .header("User-Agent", format!("ChainShield-Rust-SDK/{}", SDK_VERSION))
            .json(&AnalyzeRequest {
                address: address.to_string(),
                chain,
            })
            .send()
            .await?;

        let status = response.status();

        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            
            return match status.as_u16() {
                401 => Err(Error::Authentication(body)),
                429 => Err(Error::RateLimit { retry_after: None }),
                400 => Err(Error::Validation(body)),
                _ => Err(Error::Api {
                    status_code: status.as_u16(),
                    message: body,
                }),
            };
        }

        let result: RiskAssessment = response.json().await?;
        Ok(result)
    }

    /// Quick check if an address is sanctioned
    pub async fn is_sanctioned(&self, address: &str) -> Result<bool, Error> {
        let result = self.analyze(address).await?;
        Ok(result.blocked)
    }

    /// Quick check if an address is high risk
    pub async fn is_high_risk(&self, address: &str, threshold: f64) -> Result<bool, Error> {
        let result = self.analyze(address).await?;
        Ok(result.risk_score >= threshold)
    }

    /// Check API health status
    pub async fn health(&self) -> Result<serde_json::Value, Error> {
        let url = format!("{}/api/v1/health", self.base_url);

        let response = self
            .client
            .get(&url)
            .header("X-API-Key", &self.api_key)
            .send()
            .await?;

        let result: serde_json::Value = response.json().await?;
        Ok(result)
    }

    /// Quick connectivity check
    pub async fn ping(&self) -> bool {
        self.health().await.is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_risk_level_high_risk() {
        let assessment = RiskAssessment {
            address: "0x123".to_string(),
            chain: Chain::Ethereum,
            risk_score: 85.0,
            risk_level: RiskLevel::High,
            blocked: false,
            factors: vec!["Test".to_string()],
            entity: None,
            timestamp: None,
        };

        assert!(assessment.is_high_risk());
        assert!(!assessment.is_safe());
    }
}
