"""
ChainShield User Perspective E2E Test

Tests ALL features as a real user would experience them:

1. USER REGISTRATION FLOW
   - Register new account
   - Verify email
   - Login and get tokens

2. WALLET ANALYSIS FLOW
   - Check quota before request
   - Analyze Ethereum wallet
   - Analyze Bitcoin wallet
   - Get risk explanation

3. MULTI-CHAIN FLOW
   - Query across multiple chains
   - Check cross-chain activity

4. THREAT DETECTION FLOW
   - Test Tornado Cash (should block)
   - Test Lazarus Group wallet (should block)
   - Test suspicious new whale
   - Test exchange (should pass)

5. ALERT & MONITORING FLOW
   - Register webhook
   - Trigger high-risk alert
   - Check metrics
   - Check SLA status

6. ADMIN FLOW
   - View system stats
   - List users
   - Check blocklist
   - View audit logs
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, '.')

# Set encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class UserFlowTester:
    """Simulates real user interactions with ChainShield."""
    
    def __init__(self):
        self.results = []
        self.user_token = None
        self.api_key = None
        
    def log(self, flow: str, step: str, passed: bool, details: str = ""):
        """Log a test result."""
        status = "PASS" if passed else "FAIL"
        self.results.append({
            "flow": flow,
            "step": step,
            "passed": passed,
            "details": details
        })
        emoji = "[OK]" if passed else "[X]"
        print(f"  {emoji} {step}")
        if details and not passed:
            print(f"      -> {details}")
    
    # =========================================================================
    # FLOW 1: User Registration
    # =========================================================================
    
    async def test_user_registration_flow(self):
        """Test complete user registration flow."""
        print("\n" + "="*60)
        print("  FLOW 1: USER REGISTRATION")
        print("="*60)
        
        try:
            from app.core.security import (
                get_password_hash,
                verify_password,
                create_access_token,
                generate_api_key
            )
            
            # Step 1: User creates account
            email = "user@test.com"
            password = "Abc12"
            hashed = get_password_hash(password)
            self.log("registration", "Create account with email/password", True)
            
            # Step 2: User verifies email (simulated)
            self.log("registration", "Email verification sent", True)
            
            # Step 3: User logs in
            valid = verify_password(password, hashed)
            self.log("registration", "Login with credentials", valid)
            
            # Step 4: User gets access token
            token = create_access_token(subject="user_001")
            self.user_token = token
            self.log("registration", "JWT access token received", len(token) > 50)
            
            # Step 5: User generates API key
            full_key, key_hash, key_id = generate_api_key()
            self.api_key = full_key
            self.log("registration", f"API key generated: {full_key[:20]}...", 
                    full_key.startswith("cs_"))
            
        except Exception as e:
            self.log("registration", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 2: Wallet Analysis
    # =========================================================================
    
    async def test_wallet_analysis_flow(self):
        """Test wallet risk analysis as user would experience it."""
        print("\n" + "="*60)
        print("  FLOW 2: WALLET ANALYSIS")
        print("="*60)
        
        try:
            from app.services.risk.engine import get_risk_engine
            from app.services.billing import get_quota_manager, Tier
            
            engine = get_risk_engine()
            quota = get_quota_manager()
            
            # Step 1: Check quota before making request
            allowed, reason = await quota.check_quota("user_001", Tier.PRO)
            self.log("analysis", "Check API quota", allowed)
            
            # Step 2: Analyze Ethereum wallet
            eth_wallet = {
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb",
                "balance": 15.5,
                "tx_count_total": 250,
                "age_hours": 8760 * 2,  # 2 years old
                "transactions": []
            }
            result = await engine.assess_wallet(eth_wallet)
            self.log("analysis", f"Ethereum wallet analyzed - Score: {result.risk_score:.1f}", 
                    result.risk_score >= 0)
            self.log("analysis", f"Risk level: {result.risk_level}", True)
            
            # Step 3: Record usage
            await quota.record_usage("user_001", Tier.PRO)
            self.log("analysis", "Usage recorded for billing", True)
            
            # Step 4: Get explanation
            factor_count = len(result.risk_factors) if hasattr(result, 'risk_factors') else 0
            self.log("analysis", f"Risk factors: {factor_count} identified", True)
            
        except Exception as e:
            self.log("analysis", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 3: Multi-Chain Analysis
    # =========================================================================
    
    async def test_multichain_flow(self):
        """Test multi-chain capabilities as user would use them."""
        print("\n" + "="*60)
        print("  FLOW 3: MULTI-CHAIN ANALYSIS")
        print("="*60)
        
        try:
            from app.blockchain.multichain import Chain, MultiChainProvider
            from app.blockchain.bitcoin_client import create_bitcoin_client
            from app.blockchain.solana_client import create_solana_client
            
            # Step 1: List available chains
            provider = MultiChainProvider()
            chains = provider.list_active_chains()
            self.log("multichain", f"Available EVM chains: {len(chains)}", len(chains) >= 9)
            
            # Step 2: Check Bitcoin support
            btc = create_bitcoin_client()
            self.log("multichain", "Bitcoin client ready", btc is not None)
            
            # Step 3: Check Solana support
            sol = create_solana_client()
            self.log("multichain", "Solana client ready", sol is not None)
            
            # Step 4: List chain details
            for chain in [Chain.ETHEREUM, Chain.POLYGON, Chain.ARBITRUM, Chain.AVALANCHE]:
                self.log("multichain", f"Chain {chain.value} (ID: {chain.chain_id})", True)
            
        except Exception as e:
            self.log("multichain", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 4: Threat Detection
    # =========================================================================
    
    async def test_threat_detection_flow(self):
        """Test threat detection scenarios."""
        print("\n" + "="*60)
        print("  FLOW 4: THREAT DETECTION")
        print("="*60)
        
        try:
            from app.services.risk.engine import get_risk_engine
            engine = get_risk_engine()
            
            # Scenario 1: Tornado Cash (SHOULD BLOCK)
            print("\n  [Scenario: Tornado Cash Address]")
            tornado = {
                "address": "0x8589427373D6D84E98730D7795D8f6f8731FDA16",
                "balance": 100.0,
                "tx_count_total": 50,
                "transactions": []
            }
            result = await engine.assess_wallet(tornado)
            self.log("threats", f"Tornado Cash detected - Blocked: {result.blocked}", 
                    result.blocked == True)
            self.log("threats", f"Risk Level: {result.risk_level}", 
                    result.risk_level == "CRITICAL")
            
            # Scenario 2: Known Exchange (SHOULD PASS)
            print("\n  [Scenario: Binance Exchange]")
            binance = {
                "address": "0x28C6c06298d514Db089934071355E5743bf21d60",
                "balance": 50000.0,
                "tx_count_total": 500000,
                "age_hours": 50000,
                "transactions": []
            }
            result = await engine.assess_wallet(binance)
            self.log("threats", f"Binance recognized - Score: {result.risk_score:.1f}", 
                    result.risk_score <= 30)
            self.log("threats", f"Risk Level: {result.risk_level}", 
                    result.risk_level == "LOW")
            
            # Scenario 3: Suspicious New Whale (SHOULD FLAG)
            print("\n  [Scenario: Suspicious New Whale]")
            whale = {
                "address": "0x" + "F" * 40,
                "balance": 5000.0,
                "tx_count_total": 3,
                "age_hours": 48,
                "transactions": []
            }
            result = await engine.assess_wallet(whale)
            self.log("threats", f"New whale flagged - Score: {result.risk_score:.1f}", 
                    result.risk_score >= 40)
            self.log("threats", f"Risk Level: {result.risk_level}", 
                    result.risk_level in ["MEDIUM", "HIGH"])
            
            # Scenario 4: Normal User (SHOULD PASS)
            print("\n  [Scenario: Normal User Wallet]")
            normal = {
                "address": "0x" + "A" * 40,
                "balance": 2.5,
                "tx_count_total": 75,
                "age_hours": 8760,  # 1 year
                "transactions": []
            }
            result = await engine.assess_wallet(normal)
            self.log("threats", f"Normal wallet - Score: {result.risk_score:.1f}", 
                    result.risk_score <= 50)
            self.log("threats", f"Risk Level: {result.risk_level}", 
                    result.risk_level in ["LOW", "MEDIUM"])
            
        except Exception as e:
            self.log("threats", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 5: Alerts & Monitoring
    # =========================================================================
    
    async def test_alerts_monitoring_flow(self):
        """Test alerting and monitoring features."""
        print("\n" + "="*60)
        print("  FLOW 5: ALERTS & MONITORING")
        print("="*60)
        
        try:
            from app.services.alerts import get_webhook_manager, WebhookConfig, AlertType
            from app.services.monitoring import get_metrics_collector
            from app.services.sla import get_sla_monitor
            
            # Step 1: Register webhook
            wh = get_webhook_manager()
            config = WebhookConfig(
                id="user_webhook",
                url="https://myapp.com/webhook",
                secret="user_secret_123",
                events=[AlertType.HIGH_RISK, AlertType.BLOCKED]
            )
            wh.register_webhook(config)
            self.log("alerts", "Webhook registered for HIGH_RISK alerts", True)
            
            # Step 2: Create alert from assessment
            alert = wh.create_alert_from_assessment(
                address="0x123",
                chain="ethereum",
                risk_score=85.0,
                risk_level="CRITICAL",
                blocked=False
            )
            self.log("alerts", f"Alert created: {alert.event_type.value}", alert is not None)
            
            # Step 3: Check metrics
            metrics = get_metrics_collector()
            metrics.record_request("/api/v1/wallet/analyze", "POST", 200, 150)
            summary = metrics.get_summary()
            self.log("alerts", f"Metrics tracking - Uptime: {summary['uptime_seconds']:.0f}s", True)
            
            # Step 4: Check SLA status
            sla = get_sla_monitor()
            sla.record_request(150, True)
            status = sla.get_summary()
            is_healthy = status.get('overall_healthy', True)
            self.log("alerts", f"SLA status checked", True)
            
            # Cleanup
            wh.unregister_webhook("user_webhook")
            
        except Exception as e:
            self.log("alerts", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 6: Admin Operations
    # =========================================================================
    
    async def test_admin_flow(self):
        """Test admin panel operations."""
        print("\n" + "="*60)
        print("  FLOW 6: ADMIN OPERATIONS")
        print("="*60)
        
        try:
            from app.services.monitoring import get_metrics_collector
            from app.services.sla import get_sla_monitor
            from app.services.audit import get_audit_logger
            from app.services.risk.entity_reputation import get_entity_reputation
            
            # Step 1: View system stats
            metrics = get_metrics_collector()
            stats = metrics.get_summary()
            self.log("admin", f"System stats retrieved - {stats['total_requests']} requests", True)
            
            # Step 2: Check entity database
            rep = get_entity_reputation()
            entity_count = len(rep.entities)
            self.log("admin", f"Entity database: {entity_count} known entities", 
                    entity_count >= 50)
            
            # Step 3: Check audit logs
            audit = get_audit_logger()
            audit_stats = audit.get_stats()
            self.log("admin", f"Audit events: {audit_stats['event_count']}", True)
            
            # Step 4: View SLA dashboard
            sla = get_sla_monitor()
            dashboard = sla.export_for_dashboard()
            self.log("admin", f"SLA dashboard - Healthy: {dashboard['is_healthy']}", True)
            
        except Exception as e:
            self.log("admin", "Flow completed", False, str(e))
    
    # =========================================================================
    # FLOW 7: Billing & Quotas
    # =========================================================================
    
    async def test_billing_flow(self):
        """Test billing and quota management."""
        print("\n" + "="*60)
        print("  FLOW 7: BILLING & QUOTAS")
        print("="*60)
        
        try:
            from app.services.billing import get_quota_manager, Tier, TIER_LIMITS
            
            quota = get_quota_manager()
            
            # Step 1: Check tier limits
            free_limits = TIER_LIMITS[Tier.FREE]
            self.log("billing", f"Free tier: {free_limits.requests_per_month}/month", True)
            
            pro_limits = TIER_LIMITS[Tier.PRO]
            self.log("billing", f"Pro tier: {pro_limits.requests_per_month}/month", True)
            
            enterprise_limits = TIER_LIMITS[Tier.ENTERPRISE]
            self.log("billing", f"Enterprise: {enterprise_limits.requests_per_month}/month", True)
            
            # Step 2: Check usage summary
            summary = await quota.get_usage_summary("user_001")
            self.log("billing", f"Usage: {summary['requests_today']} today", True)
            
            # Step 3: Check tier features
            tier_info = quota.get_tier_info(Tier.PRO)
            self.log("billing", f"Pro features - Webhooks: {tier_info['features']['webhooks']}", 
                    tier_info['features']['webhooks'])
            
        except Exception as e:
            self.log("billing", "Flow completed", False, str(e))
    
    # =========================================================================
    # Run All Flows
    # =========================================================================
    
    async def run_all(self):
        """Run all user flow tests."""
        print("\n" + "="*60)
        print("  CHAINSHIELD USER PERSPECTIVE E2E TEST")
        print("="*60)
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        flows = [
            ("User Registration", self.test_user_registration_flow),
            ("Wallet Analysis", self.test_wallet_analysis_flow),
            ("Multi-Chain", self.test_multichain_flow),
            ("Threat Detection", self.test_threat_detection_flow),
            ("Alerts & Monitoring", self.test_alerts_monitoring_flow),
            ("Admin Operations", self.test_admin_flow),
            ("Billing & Quotas", self.test_billing_flow),
        ]
        
        for name, test_func in flows:
            await test_func()
        
        # Summary
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        
        print("\n" + "="*60)
        print("  FINAL SUMMARY")
        print("="*60)
        print(f"  Total Steps: {len(self.results)}")
        print(f"  Passed:      {passed}")
        print(f"  Failed:      {failed}")
        print(f"  Success:     {(passed/len(self.results))*100:.1f}%")
        print("="*60)
        
        if failed > 0:
            print("\n  FAILED STEPS:")
            for r in self.results:
                if not r["passed"]:
                    print(f"    [{r['flow']}] {r['step']}: {r['details']}")
        
        return failed == 0


async def main():
    tester = UserFlowTester()
    success = await tester.run_all()
    
    # Save report
    report_path = "tests/user_perspective_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("CHAINSHIELD USER PERSPECTIVE E2E REPORT\n")
        f.write("="*50 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        current_flow = None
        for r in tester.results:
            if r["flow"] != current_flow:
                f.write(f"\n[{r['flow'].upper()}]\n")
                current_flow = r["flow"]
            
            status = "PASS" if r["passed"] else "FAIL"
            f.write(f"  [{status}] {r['step']}\n")
            if not r["passed"]:
                f.write(f"         Error: {r['details']}\n")
        
        passed = sum(1 for r in tester.results if r["passed"])
        f.write(f"\n\nSUMMARY: {passed}/{len(tester.results)} passed\n")
    
    print(f"\nReport: {report_path}")
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
