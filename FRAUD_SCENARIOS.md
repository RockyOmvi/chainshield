# 🔐 Comprehensive Crypto Fraud & Risk Scenarios

> **ChainShield Knowledge Base**  
> Created by: Senior Developer (60 Years Experience)  
> Last Updated: January 2, 2026

---

## Table of Contents

1. [Transaction-Based Fraud](#1-transaction-based-fraud)
2. [Wallet Behavior Patterns](#2-wallet-behavior-patterns)
3. [Smart Contract Exploits](#3-smart-contract-exploits)
4. [DeFi-Specific Attacks](#4-defi-specific-attacks)
5. [Social Engineering & Scams](#5-social-engineering--scams)
6. [Money Laundering Patterns](#6-money-laundering-patterns)
7. [Exchange & Platform Fraud](#7-exchange--platform-fraud)
8. [NFT & Token Fraud](#8-nft--token-fraud)
9. [Cross-Chain Attacks](#9-cross-chain-attacks)
10. [Regulatory & Compliance Violations](#10-regulatory--compliance-violations)
11. [Detection Signals Summary](#11-detection-signals-summary)

---

## 1. Transaction-Based Fraud

### 1.1 Pass-Through/Layering
**Description:** Funds flow through a wallet with minimal retention (<5%)  

**Detection Logic:**
```python
def detect_passthrough(wallet_data):
    total_received = wallet_data.get("total_received", 0)
    balance = wallet_data.get("balance", 0)
    
    if total_received == 0:
        return False, 0
    
    retention_ratio = balance / total_received
    passthrough_pct = (1 - retention_ratio) * 100
    
    # Thresholds
    if passthrough_pct >= 99:
        return True, 100  # CRITICAL: 99%+ passed through
    elif passthrough_pct >= 95:
        return True, 80   # HIGH
    elif passthrough_pct >= 80:
        return True, 50   # MEDIUM
    else:
        return False, 0
```

**Key Formula:** `pass_through_pct = (1 - balance / total_received) * 100`

**Risk Level:** MEDIUM to HIGH  
**ChainShield Status:** ✅ Implemented in `WalletFeatureExtractor`

---

### 1.2 Structuring (Smurfing)
**Description:** Breaking large amounts into smaller transactions to avoid detection  

**Detection Logic:**
```python
def detect_structuring(transactions, threshold=10000):
    """Detect transactions structured just below reporting threshold."""
    suspicious_count = 0
    near_threshold_band = threshold * 0.1  # Within 10% of threshold
    
    for tx in transactions:
        value = tx.get("value", 0)
        # Check if just below threshold (e.g., $9,000-$9,999 for $10k threshold)
        if (threshold - near_threshold_band) <= value < threshold:
            suspicious_count += 1
    
    # Multiple near-threshold transactions is suspicious
    if suspicious_count >= 3:
        return True, min(suspicious_count * 15, 100)
    
    # Check for round number patterns
    round_amounts = sum(1 for tx in transactions 
                       if tx.get("value", 0) % 1000 == 0)
    if round_amounts / len(transactions) > 0.8:
        return True, 60  # 80% round numbers is suspicious
    
    return False, 0
```

**Key Signals:**
- Transactions just below $10,000 threshold
- Round number amounts (9.9 ETH, 0.99 BTC)
- Regular intervals between transactions

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Implemented in `velocity_check` rule

---

### 1.3 Rapid Divestment
**Description:** Draining wallet within minutes of receiving funds  

**Detection Logic:**
```python
def detect_rapid_divestment(transactions, window_minutes=30, threshold_pct=90):
    """Detect rapid fund movement after receiving."""
    for i, receive_tx in enumerate(transactions):
        if receive_tx.get("direction") != "in":
            continue
            
        receive_time = receive_tx.get("timestamp")
        receive_amount = receive_tx.get("value", 0)
        
        # Check subsequent transactions within window
        total_sent = 0
        for send_tx in transactions[i+1:]:
            if send_tx.get("direction") != "out":
                continue
            
            send_time = send_tx.get("timestamp")
            time_diff = (send_time - receive_time).total_seconds() / 60
            
            if time_diff <= window_minutes:
                total_sent += send_tx.get("value", 0)
            else:
                break
        
        # Check if threshold exceeded
        if receive_amount > 0:
            divest_pct = (total_sent / receive_amount) * 100
            if divest_pct >= threshold_pct:
                return True, min(divest_pct, 100)
    
    return False, 0
```

**Key Formula:** `divestment_pct = (sent_within_window / received_amount) * 100`

**Thresholds:**
- `window_minutes = 30` (configurable)
- `threshold_pct = 90` (90%+ moved = suspicious)

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Configured in `VelocityLimits`

---

### 1.4 Dust Attacks
**Description:** Sending tiny amounts to many wallets to track them  

**Detection Logic:**
```python
def detect_dust_attack(transactions, dust_threshold=0.0001):
    """
    Detect dust attack patterns.
    Attacker: sends many tiny amounts
    Victim: receives many tiny amounts from same source
    """
    dust_txs = [tx for tx in transactions 
                if tx.get("value", 0) < dust_threshold]
    
    # Check if same sender sending dust to many recipients
    senders = {}
    for tx in dust_txs:
        sender = tx.get("from", "")
        senders[sender] = senders.get(sender, 0) + 1
    
    # Attacker pattern: 100+ dust transactions from same wallet
    max_from_sender = max(senders.values()) if senders else 0
    if max_from_sender >= 100:
        return "attacker", 70
    
    # Victim pattern: receiving dust from many sources
    if len(dust_txs) >= 10 and len(set(tx.get("from") for tx in dust_txs)) >= 5:
        return "victim", 20  # Low risk for victim
    
    return None, 0
```

**Risk Level:** LOW (victim) / MEDIUM (attacker)  
**ChainShield Status:** ⚠️ Partial - needs dedicated rule

---

### 1.5 Front-Running
**Description:** Detecting pending transactions and executing ahead of them  

**Detection Logic:**
```python
def detect_frontrunning(block_transactions, target_tx_hash):
    """
    Detect front-running by analyzing transaction ordering in block.
    Requires mempool monitoring for real-time detection.
    """
    target_idx = None
    suspect_buys = []
    suspect_sells = []
    
    for idx, tx in enumerate(block_transactions):
        if tx["hash"] == target_tx_hash:
            target_idx = idx
            continue
        
        # Check for same token/pair transactions
        if tx.get("token") == block_transactions[target_idx].get("token"):
            if idx < target_idx and tx.get("type") == "buy":
                suspect_buys.append(tx)
            elif idx > target_idx and tx.get("type") == "sell":
                suspect_sells.append(tx)
    
    # Classic front-run: buy before, sell after
    for buy in suspect_buys:
        for sell in suspect_sells:
            if buy.get("from") == sell.get("from"):
                profit = sell.get("value", 0) - buy.get("value", 0)
                if profit > 0:
                    return True, 90, {"profit": profit, "attacker": buy["from"]}
    
    return False, 0, {}
```

**Key Signals:**
- Transaction appears in mempool
- Higher gas price transaction submitted immediately
- Same address buys before and sells after target

**Risk Level:** HIGH  
**ChainShield Status:** ⚠️ Requires mempool monitoring (Phase 2)

---

### 1.6 Sandwich Attacks
**Description:** Surrounding a victim's trade with buy/sell orders  

**Detection Logic:**
```python
def detect_sandwich(block_transactions, victim_tx):
    """
    Sandwich pattern:
    1. Attacker buys (raises price)
    2. Victim buys (at higher price)
    3. Attacker sells (takes profit)
    
    All in same block, attacker txs have higher gas.
    """
    victim_idx = block_transactions.index(victim_tx)
    victim_token = victim_tx.get("token")
    
    # Look for buy before victim
    front_tx = None
    for i in range(victim_idx - 1, -1, -1):
        tx = block_transactions[i]
        if tx.get("token") == victim_token and tx.get("type") == "buy":
            front_tx = tx
            break
    
    # Look for sell after victim
    back_tx = None
    for i in range(victim_idx + 1, len(block_transactions)):
        tx = block_transactions[i]
        if tx.get("token") == victim_token and tx.get("type") == "sell":
            back_tx = tx
            break
    
    # Check if same attacker
    if front_tx and back_tx and front_tx.get("from") == back_tx.get("from"):
        attacker = front_tx["from"]
        profit = back_tx.get("value", 0) - front_tx.get("value", 0)
        
        return True, 95, {
            "attacker": attacker,
            "profit": profit,
            "victim_loss": profit * 0.5  # Approximate
        }
    
    return False, 0, {}
```

**Risk Level:** HIGH  
**ChainShield Status:** ⚠️ Requires block-level analysis (Phase 2)

---

## 2. Wallet Behavior Patterns

### 2.1 New Account Fraud
**Description:** Freshly created wallets used for scams  

**Detection Logic:**
```python
def detect_new_account_risk(wallet_data):
    """
    New accounts with high activity are suspicious.
    Score based on age vs activity ratio.
    """
    age_hours = wallet_data.get("age_hours", 0)
    tx_count = wallet_data.get("tx_count_total", 0)
    total_volume = wallet_data.get("total_received", 0)
    
    score = 0
    
    # Very new account (< 24 hours)
    if age_hours < 24:
        score += 30
        # High activity in new account
        if tx_count > 50:
            score += 30
        if total_volume > 10:  # 10 ETH/BTC
            score += 20
    
    # Young account (< 7 days)
    elif age_hours < 168:  # 7 * 24
        score += 15
        if tx_count > 100:
            score += 20
    
    # Activity velocity check
    if age_hours > 0:
        tx_per_hour = tx_count / age_hours
        if tx_per_hour > 10:
            score += 25
    
    return min(score, 100)
```

**Key Formula:** `tx_velocity = tx_count / age_hours`

**Thresholds:**
- Age < 24 hours = +30 points
- High TX in new account = +30 points
- TX velocity > 10/hour = +25 points

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Implemented in `AccountAgeHeuristic`

---

### 2.2 Dormant Account Activation
**Description:** Old unused wallet suddenly becomes active  

**Detection Logic:**
```python
def detect_dormant_activation(wallet_data, transactions):
    """
    Detect sudden activity in long-dormant accounts.
    Could indicate compromised keys.
    """
    if len(transactions) < 2:
        return False, 0
    
    # Sort by timestamp
    sorted_txs = sorted(transactions, key=lambda x: x.get("timestamp"))
    
    # Find longest gap between transactions
    max_gap_days = 0
    last_active_before_gap = None
    
    for i in range(1, len(sorted_txs)):
        prev_time = sorted_txs[i-1].get("timestamp")
        curr_time = sorted_txs[i].get("timestamp")
        gap_days = (curr_time - prev_time).days
        
        if gap_days > max_gap_days:
            max_gap_days = gap_days
            last_active_before_gap = prev_time
    
    # Dormant for 1+ year, now active
    if max_gap_days >= 365:
        # Check recent activity volume
        recent_txs = [tx for tx in transactions 
                     if tx.get("timestamp") > last_active_before_gap]
        recent_volume = sum(tx.get("value", 0) for tx in recent_txs)
        
        if recent_volume > 1:  # Significant movement
            return True, min(50 + max_gap_days // 30, 90)
    
    return False, 0
```

**Risk Level:** MEDIUM  
**ChainShield Status:** ⚠️ Needs implementation

---

### 2.3 Bot-Like Behavior
**Description:** Automated transaction patterns  

**Detection Logic:**
```python
import math
from collections import Counter

def detect_bot_behavior(transactions):
    """
    Bots have low entropy in timing patterns.
    Humans have random timing; bots are regular.
    """
    if len(transactions) < 10:
        return False, 0
    
    # Extract hours of activity
    hours = [tx.get("timestamp").hour for tx in transactions]
    
    # Calculate entropy of active hours
    hour_counts = Counter(hours)
    total = len(hours)
    entropy = 0
    
    for count in hour_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    max_entropy = math.log2(24)  # Max if uniform across 24 hours
    normalized_entropy = entropy / max_entropy
    
    # Low entropy = bot-like
    if normalized_entropy < 0.3:
        return True, 80  # Very bot-like
    elif normalized_entropy < 0.5:
        return True, 50  # Somewhat bot-like
    
    # Check for exact timing patterns
    time_diffs = []
    sorted_txs = sorted(transactions, key=lambda x: x.get("timestamp"))
    for i in range(1, len(sorted_txs)):
        diff = (sorted_txs[i]["timestamp"] - sorted_txs[i-1]["timestamp"]).seconds
        time_diffs.append(diff)
    
    # If most diffs are exactly the same, bot-like
    diff_counts = Counter(time_diffs)
    most_common_diff, count = diff_counts.most_common(1)[0]
    if count / len(time_diffs) > 0.5:
        return True, 70
    
    return False, 0
```

**Key Formula:** `entropy = -Σ(p * log2(p))` for each active hour

**Thresholds:**
- Entropy < 0.3 = Very bot-like (80 score)
- Entropy < 0.5 = Somewhat bot-like (50 score)

**Risk Level:** MEDIUM  
**ChainShield Status:** ✅ Implemented as `active_hours_entropy` feature

---

### 2.4 Sybil Wallets
**Description:** Multiple wallets controlled by same entity  

**Detection Logic:**
```python
def detect_sybil_pattern(wallets, transactions):
    """
    Sybil detection using graph analysis.
    Look for wallets that:
    1. Fund each other in circles
    2. Have similar patterns
    3. Created around same time
    """
    import networkx as nx
    
    # Build transaction graph
    G = nx.DiGraph()
    for tx in transactions:
        sender = tx.get("from")
        receiver = tx.get("to")
        value = tx.get("value", 0)
        G.add_edge(sender, receiver, weight=value)
    
    # Detect strongly connected components (circles)
    sccs = list(nx.strongly_connected_components(G))
    sybil_clusters = [scc for scc in sccs if len(scc) > 2]
    
    # Check for same-time creation
    creation_times = {w["address"]: w.get("first_seen") for w in wallets}
    for cluster in sybil_clusters:
        times = [creation_times.get(addr) for addr in cluster if addr in creation_times]
        if len(times) >= 2:
            time_span = (max(times) - min(times)).days
            if time_span < 1:  # Created within same day
                return True, 90, list(cluster)
    
    # Self-transfer ratio (sending to self via intermediary)
    for node in G.nodes():
        predecessors = set(G.predecessors(node))
        successors = set(G.successors(node))
        overlap = predecessors & successors
        if len(overlap) > 0:  # Circular funding
            return True, 70, list(overlap | {node})
    
    return False, 0, []
```

**Key Signals:**
- Strongly connected components in transaction graph
- Wallets created within same day
- Circular fund flows

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Implemented in `GraphMetricsExtractor`

---

### 2.5 Wash Trading
**Description:** Trading with yourself to inflate volume  

**Detection Logic:**
```python
def detect_wash_trading(wallet_address, transactions):
    """
    Wash trading = sending to self directly or via intermediary.
    """
    direct_self_transfers = 0
    total_transfers = 0
    
    # Build address sets
    sent_to = set()
    received_from = set()
    
    for tx in transactions:
        if tx.get("from") == wallet_address:
            receiver = tx.get("to")
            sent_to.add(receiver)
            total_transfers += 1
            
            # Direct self transfer
            if receiver == wallet_address:
                direct_self_transfers += 1
        
        if tx.get("to") == wallet_address:
            sender = tx.get("from")
            received_from.add(sender)
    
    # Check for circular: sent to X AND received from X
    circular_addresses = sent_to & received_from
    
    # Calculate wash trading ratio
    if total_transfers > 0:
        self_transfer_ratio = direct_self_transfers / total_transfers
        circular_ratio = len(circular_addresses) / len(sent_to) if sent_to else 0
        
        wash_score = (self_transfer_ratio * 50) + (circular_ratio * 50)
        
        if wash_score > 30:
            return True, min(wash_score * 2, 100)
    
    return False, 0
```

**Key Formula:** 
- `self_transfer_ratio = direct_self_transfers / total_transfers`
- `circular_ratio = len(sent_to ∩ received_from) / len(sent_to)`

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Implemented as `self_transfer_ratio` feature

---

### 2.6 Honeypot Wallets  
**Description:** Wallets that receive but never send  

**Detection Logic:**
```python
def detect_honeypot(wallet_data):
    """
    Honeypot = receives many transfers but sends none.
    Could be scam collection point or compromised wallet.
    """
    in_count = wallet_data.get("in_tx_count", 0)
    out_count = wallet_data.get("out_tx_count", 0)
    balance = wallet_data.get("balance", 0)
    total_received = wallet_data.get("total_received", 0)
    
    # Pure honeypot: receives but never sends
    if in_count > 0 and out_count == 0:
        if in_count >= 10:
            return True, 70
        elif in_count >= 5:
            return True, 50
        else:
            return True, 30
    
    # Near honeypot: very low outflow ratio
    if in_count > 0:
        in_out_ratio = out_count / in_count
        if in_out_ratio < 0.05:  # Less than 5% outflow
            return True, 60
    
    return False, 0
```

**Key Formula:** `in_out_ratio = out_tx_count / in_tx_count`

**Risk Level:** MEDIUM to HIGH  
**ChainShield Status:** ✅ Implemented as `honeypot_check` rule

---

## 3. Smart Contract Exploits

### 3.1 Reentrancy Attack
**Description:** Malicious contract calls back before state update  

**Detection Logic:**
```python
def detect_reentrancy(contract_calls, contract_address):
    """
    Reentrancy pattern:
    1. Contract A calls Contract B
    2. B calls back to A before A finishes
    3. A's state not yet updated
    4. B can withdraw multiple times
    
    Detection: Look for nested calls to same function.
    """
    call_stack = []
    reentrancy_detected = False
    
    for call in contract_calls:
        caller = call.get("from")
        callee = call.get("to")
        function = call.get("function")
        
        # Check if same function already in stack
        call_signature = (callee, function)
        if call_signature in call_stack:
            # Same function called while previous call still active
            reentrancy_detected = True
            withdrawals = sum(1 for c in call_stack if c == call_signature)
            return True, 100, {
                "nested_calls": withdrawals,
                "vulnerable_function": function
            }
        
        call_stack.append(call_signature)
        
        # Pop on return (simplified)
        if call.get("type") == "return":
            call_stack.pop()
    
    return False, 0, {}
```

**Static Analysis Pattern:**
```solidity
// VULNERABLE: External call before state update
function withdraw() external {
    uint amount = balances[msg.sender];
    msg.sender.call{value: amount}("");  // External call
    balances[msg.sender] = 0;            // State update AFTER (vulnerable!)
}

// SAFE: State update before external call
function withdraw() external {
    uint amount = balances[msg.sender];
    balances[msg.sender] = 0;            // State update FIRST
    msg.sender.call{value: amount}("");  // External call after
}
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ⚠️ Requires contract trace analysis

---

### 3.2 Flash Loan Attacks
**Description:** Borrow, manipulate, profit, repay in one transaction  

**Detection Logic:**
```python
def detect_flash_loan_attack(transaction):
    """
    Flash loan attack pattern (single transaction):
    1. Borrow large amount (no collateral)
    2. Use to manipulate price/state
    3. Extract profit
    4. Repay loan
    5. Keep profit
    
    All happens atomically in one tx.
    """
    internal_txs = transaction.get("internal_transactions", [])
    
    # Look for flash loan providers
    flash_loan_providers = {
        "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",  # Aave
        "0x6bdC1FCB2F13d1bA9D26ccEc3983d5D4bf318693",  # dYdX
    }
    
    borrow_amount = 0
    repay_amount = 0
    profit = 0
    
    for itx in internal_txs:
        if itx.get("to") in flash_loan_providers:
            if itx.get("type") == "borrow":
                borrow_amount = itx.get("value", 0)
            elif itx.get("type") == "repay":
                repay_amount = itx.get("value", 0)
    
    # Flash loan detected if borrow == repay in same tx
    if borrow_amount > 0 and abs(borrow_amount - repay_amount) < borrow_amount * 0.01:
        # Calculate profit from other transfers
        profit = transaction.get("profit", 0)
        
        if profit > borrow_amount * 0.001:  # >0.1% profit = suspicious
            return True, 95, {
                "borrowed": borrow_amount,
                "profit": profit,
                "roi": (profit / borrow_amount) * 100
            }
    
    return False, 0, {}
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ⚠️ Requires internal transaction analysis

---

### 3.3 Oracle Manipulation
**Description:** Feeding false price data to smart contracts  

**Detection Logic:**
```python
def detect_oracle_manipulation(price_feeds, threshold_pct=10):
    """
    Oracle manipulation detection:
    1. Compare on-chain price to off-chain sources
    2. Large deviation = manipulation
    """
    manipulated = False
    
    for oracle, on_chain_price in price_feeds.items():
        # Get off-chain reference (Chainlink, CoinGecko, etc.)
        off_chain_price = get_reference_price(oracle)
        
        if off_chain_price > 0:
            deviation = abs(on_chain_price - off_chain_price) / off_chain_price * 100
            
            if deviation > threshold_pct:
                return True, min(deviation * 5, 100), {
                    "oracle": oracle,
                    "on_chain": on_chain_price,
                    "off_chain": off_chain_price,
                    "deviation_pct": deviation
                }
    
    return False, 0, {}
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ⚠️ Requires price feed integration

---

## 4. DeFi-Specific Attacks

### 4.1 Rug Pull Detection
**Description:** Project team drains liquidity and abandons project  

**Detection Logic:**
```python
def detect_rugpull(token_address, transactions, liquidity_pools):
    """
    Rug pull indicators:
    1. Liquidity removal by team
    2. Token selling by insiders
    3. Contract ownership renounced after drain
    
    Types:
    - Hard rug: Instant liquidity removal
    - Soft rug: Slow selling over time
    """
    score = 0
    indicators = []
    
    # Check liquidity pool transactions
    for pool in liquidity_pools:
        if pool.get("token") == token_address:
            lp_txs = pool.get("transactions", [])
            
            # Look for large LP removals
            for tx in lp_txs:
                if tx.get("type") == "remove_liquidity":
                    removed_pct = tx.get("amount") / pool.get("total_liquidity", 1) * 100
                    
                    if removed_pct > 50:
                        score += 50
                        indicators.append(f"Large LP removal: {removed_pct:.1f}%")
    
    # Check team wallet selling
    team_wallets = get_team_wallets(token_address)
    for tx in transactions:
        if tx.get("from") in team_wallets and tx.get("type") == "sell":
            sell_amount = tx.get("amount", 0)
            score += min(sell_amount * 10, 30)
            indicators.append(f"Team selling: {sell_amount}")
    
    # Check LP lock status
    lp_lock = get_lp_lock_status(token_address)
    if not lp_lock.get("locked"):
        score += 20
        indicators.append("LP not locked")
    elif lp_lock.get("unlock_time_days", 365) < 30:
        score += 10
        indicators.append(f"LP unlocks in {lp_lock['unlock_time_days']} days")
    
    return score > 50, min(score, 100), indicators
```

**Key Signals:**
- LP tokens unlocked or short timelock
- Large liquidity removal (>50%)
- Team wallets selling
- Contract ownership changes

**Risk Level:** CRITICAL  
**ChainShield Status:** ⚠️ Partial - LP monitoring needed

---

### 4.2 Pump and Dump
**Description:** Artificially inflate price, then sell  

**Detection Logic:**
```python
def detect_pump_and_dump(token_address, price_history, volume_history):
    """
    Pump and dump pattern:
    1. Low volume → sudden spike
    2. Price increases 100%+ rapidly
    3. Peak volume at top
    4. Price crashes 80%+
    """
    # Find price peak
    peak_idx = price_history.index(max(price_history))
    peak_price = price_history[peak_idx]
    
    # Check pre-pump price
    pre_pump_window = price_history[max(0, peak_idx-24):peak_idx]  # 24 periods before
    pre_pump_avg = sum(pre_pump_window) / len(pre_pump_window) if pre_pump_window else 0
    
    # Check post-dump price
    post_dump_window = price_history[peak_idx:min(len(price_history), peak_idx+24)]
    post_dump_min = min(post_dump_window) if post_dump_window else peak_price
    
    # Calculate metrics
    pump_pct = ((peak_price - pre_pump_avg) / pre_pump_avg * 100) if pre_pump_avg > 0 else 0
    dump_pct = ((peak_price - post_dump_min) / peak_price * 100) if peak_price > 0 else 0
    
    # Volume spike at peak
    avg_volume = sum(volume_history) / len(volume_history) if volume_history else 0
    peak_volume = volume_history[peak_idx] if peak_idx < len(volume_history) else 0
    volume_spike = peak_volume / avg_volume if avg_volume > 0 else 0
    
    # Score
    score = 0
    if pump_pct > 100:
        score += 30
    if dump_pct > 80:
        score += 40
    if volume_spike > 10:
        score += 30
    
    return score > 50, min(score, 100), {
        "pump_pct": pump_pct,
        "dump_pct": dump_pct,
        "volume_spike": volume_spike
    }
```

**Risk Level:** HIGH  
**ChainShield Status:** ⚠️ Requires price/volume monitoring

---

## 5. Social Engineering & Scams

### 5.1 Phishing Detection
**Description:** Fake websites/apps stealing credentials  

**Detection Logic:**
```python
def detect_phishing_address(address, known_labels):
    """
    Phishing detection based on:
    1. Known phishing address lists
    2. Typosquatting detection
    3. Transaction patterns
    """
    # Check against known phishing list
    if address in KNOWN_PHISHING_ADDRESSES:
        return True, 100, "Known phishing address"
    
    # Check if receiving from many unique addresses (collection pattern)
    incoming_senders = get_unique_senders(address)
    if len(incoming_senders) > 100:
        avg_amount = get_average_received(address)
        if avg_amount < 0.1:  # Many small amounts = phishing
            return True, 70, "Phishing collection pattern"
    
    # Check for typosquatting (similar to known legitimate addresses)
    for legit_name, legit_address in known_labels.items():
        similarity = calculate_address_similarity(address, legit_address)
        if 0.8 < similarity < 1.0:  # Very similar but not exact
            return True, 80, f"Possible typosquat of {legit_name}"
    
    return False, 0, None
```

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Pattern check implemented

---

## 6. Money Laundering Patterns

### 6.1 Mixer/Tumbler Detection
**Description:** Using privacy protocols to obscure transaction trails  

**Detection Logic:**
```python
# Known mixer contract addresses
KNOWN_MIXERS = {
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": {"name": "Tornado 0.1 ETH", "risk": 90},
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": {"name": "Tornado 1 ETH", "risk": 90},
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": {"name": "Tornado 10 ETH", "risk": 90},
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": {"name": "Tornado 100 ETH", "risk": 95},
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": {"name": "Tornado Router", "risk": 95},
}

def detect_mixer_usage(wallet_address, transactions):
    """
    Detect direct or indirect mixer usage.
    """
    direct_mixer_use = 0
    indirect_mixer_use = 0
    mixer_names = []
    
    for tx in transactions:
        # Direct: sending to/receiving from mixer
        if tx.get("to") in KNOWN_MIXERS:
            direct_mixer_use += 1
            mixer_names.append(KNOWN_MIXERS[tx["to"]]["name"])
        
        if tx.get("from") in KNOWN_MIXERS:
            direct_mixer_use += 1
            mixer_names.append(KNOWN_MIXERS[tx["from"]]["name"])
    
    if direct_mixer_use > 0:
        return True, 90, {
            "type": "direct",
            "count": direct_mixer_use,
            "mixers": list(set(mixer_names))
        }
    
    # Check 1-hop indirect (counterparty used mixer)
    counterparties = set(tx.get("from") for tx in transactions) | set(tx.get("to") for tx in transactions)
    for counterparty in counterparties:
        counterparty_txs = get_transactions(counterparty)
        for ctx in counterparty_txs:
            if ctx.get("to") in KNOWN_MIXERS or ctx.get("from") in KNOWN_MIXERS:
                indirect_mixer_use += 1
    
    if indirect_mixer_use > 0:
        return True, 50, {
            "type": "indirect",
            "hops": 1,
            "contaminated_counterparties": indirect_mixer_use
        }
    
    return False, 0, {}
```

**Risk Level:** HIGH to CRITICAL  
**ChainShield Status:** ✅ Implemented in blacklist config

---

### 6.2 Chain Hopping Detection
**Description:** Moving funds across multiple blockchains  

**Detection Logic:**
```python
def detect_chain_hopping(wallet_addresses_by_chain, bridge_transactions):
    """
    Chain hopping pattern:
    ETH → Bridge → Polygon → Bridge → BSC → Exchange
    
    More hops = higher risk.
    """
    chain_count = len(wallet_addresses_by_chain)
    bridge_count = len(bridge_transactions)
    
    # Score based on complexity
    score = 0
    
    if chain_count >= 4:
        score += 50  # Using 4+ chains is suspicious
    elif chain_count >= 2:
        score += 20
    
    if bridge_count >= 5:
        score += 40  # Many bridge transactions
    elif bridge_count >= 2:
        score += 20
    
    # Check for high-risk bridges
    high_risk_bridges = [tx for tx in bridge_transactions 
                        if tx.get("bridge_risk") == "high"]
    score += len(high_risk_bridges) * 10
    
    # Check timing (rapid hopping = more suspicious)
    if len(bridge_transactions) >= 2:
        times = [tx.get("timestamp") for tx in bridge_transactions]
        total_time = (max(times) - min(times)).total_seconds() / 3600  # hours
        
        if total_time < 1:  # All hops within 1 hour
            score += 30
    
    return score > 40, min(score, 100), {
        "chains": list(wallet_addresses_by_chain.keys()),
        "bridge_count": bridge_count,
        "high_risk_bridges": len(high_risk_bridges)
    }
```

**Risk Level:** HIGH  
**ChainShield Status:** ✅ Implemented in `CrossChainResolver`

---

### 6.3 Peel Chain Detection
**Description:** Gradually "peeling" off small amounts through many hops  

**Detection Logic:**
```python
def detect_peel_chain(initial_address, transactions, depth=10):
    """
    Peel chain pattern:
    Large amount → Address A (sends most, keeps some)
                → Address B (sends most, keeps some)
                → Address C (sends most, keeps some)
                ... continues
    
    Each hop "peels" off a small percentage.
    """
    current_address = initial_address
    peel_pattern = []
    
    for hop in range(depth):
        txs = get_outgoing_transactions(current_address)
        
        if len(txs) == 0:
            break
        
        # Find the largest outgoing transaction (main flow)
        largest_tx = max(txs, key=lambda x: x.get("value", 0))
        total_out = sum(tx.get("value", 0) for tx in txs)
        
        # Check if this is a peel (one large, maybe some small)
        if largest_tx.get("value", 0) > total_out * 0.8:  # 80%+ goes to one address
            kept_pct = 100 - (total_out / get_balance_before(current_address) * 100)
            peel_pattern.append({
                "address": current_address,
                "kept_pct": kept_pct,
                "forwarded_to": largest_tx.get("to")
            })
            current_address = largest_tx.get("to")
        else:
            break
    
    # Score based on chain length
    if len(peel_pattern) >= 5:
        return True, 90, peel_pattern
    elif len(peel_pattern) >= 3:
        return True, 60, peel_pattern
    
    return False, 0, []
```

**Key Pattern:**
- 80%+ of funds forwarded to next address
- 5%+ kept at each hop
- Chain continues for 5+ hops

**Risk Level:** HIGH  
**ChainShield Status:** ⚠️ Needs graph traversal implementation

---

## 7. Exchange & Platform Fraud

### 7.1 Exit Scam Detection
**Description:** Centralized platform disappears with funds  

**Detection Logic:**
```python
def detect_exchange_exit_scam(exchange_address, transactions, time_window_days=7):
    """
    Exit scam indicators:
    1. Large outflows from hot wallets
    2. No new deposits accepted
    3. All funds moving to cold/unknown wallets
    """
    recent_cutoff = datetime.now() - timedelta(days=time_window_days)
    
    # Get recent transactions
    recent_txs = [tx for tx in transactions 
                 if tx.get("timestamp") > recent_cutoff]
    
    # Calculate net flow
    inflow = sum(tx.get("value", 0) for tx in recent_txs 
                if tx.get("to") == exchange_address)
    outflow = sum(tx.get("value", 0) for tx in recent_txs 
                 if tx.get("from") == exchange_address)
    
    # Check for massive outflow
    net_flow = inflow - outflow
    
    if outflow > 0 and inflow / outflow < 0.1:  # 10x more outflow than inflow
        # Check if outflow going to known cold wallets or unknown
        outflow_destinations = [tx.get("to") for tx in recent_txs 
                               if tx.get("from") == exchange_address]
        unknown_destinations = [d for d in outflow_destinations 
                               if not is_known_address(d)]
        
        unknown_pct = len(unknown_destinations) / len(outflow_destinations) * 100
        
        if unknown_pct > 50:
            return True, 95, {
                "outflow": outflow,
                "inflow": inflow,
                "unknown_destination_pct": unknown_pct
            }
    
    return False, 0, {}
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ✅ Known scam exchange list

---

## 8. NFT & Token Fraud

### 8.1 Honeypot Token Detection
**Description:** Tokens that can be bought but not sold  

**Detection Logic:**
```python
def detect_honeypot_token(token_address, transactions):
    """
    Honeypot token indicators:
    1. Many buys, zero or few sells
    2. Sell transactions fail
    3. Only owner can sell
    """
    buy_count = 0
    sell_count = 0
    failed_sells = 0
    unique_sellers = set()
    
    for tx in transactions:
        if tx.get("token") == token_address:
            if tx.get("type") == "buy":
                buy_count += 1
            elif tx.get("type") == "sell":
                if tx.get("status") == "success":
                    sell_count += 1
                    unique_sellers.add(tx.get("from"))
                else:
                    failed_sells += 1
    
    # Red flags
    score = 0
    
    # Very few successful sells compared to buys
    if buy_count > 10 and sell_count < buy_count * 0.1:
        score += 40
    
    # Many failed sells
    if failed_sells > 5:
        score += 30
    
    # Only 1-2 addresses can sell (likely owner only)
    if len(unique_sellers) <= 2 and buy_count > 20:
        score += 30
    
    return score > 50, min(score, 100), {
        "buys": buy_count,
        "successful_sells": sell_count,
        "failed_sells": failed_sells,
        "unique_sellers": len(unique_sellers)
    }
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ⚠️ Needs token transaction analysis

---

## 9. Cross-Chain Attacks

### 9.1 Bridge Exploit Detection
**Description:** Hacking cross-chain bridges  

**Detection Logic:**
```python
def detect_bridge_exploit(bridge_address, transactions):
    """
    Bridge exploit indicators:
    1. Large withdrawal without matching deposit
    2. Multiple withdrawals in short time
    3. Withdrawal to new addresses
    """
    deposits = []
    withdrawals = []
    
    for tx in transactions:
        if tx.get("type") == "deposit":
            deposits.append(tx)
        elif tx.get("type") == "withdrawal":
            withdrawals.append(tx)
    
    # Check for unmatched withdrawals
    total_deposits = sum(d.get("amount", 0) for d in deposits)
    recent_withdrawals = sum(w.get("amount", 0) for w in withdrawals[-10:])
    
    if recent_withdrawals > total_deposits * 1.5:  # Withdrawing more than deposited
        return True, 100, {
            "excess_withdrawal": recent_withdrawals - total_deposits,
            "exploit_likely": True
        }
    
    # Check for rapid withdrawals to new addresses
    withdrawal_addresses = [w.get("to") for w in withdrawals[-10:]]
    new_addresses = [addr for addr in withdrawal_addresses 
                    if is_new_address(addr)]
    
    if len(new_addresses) > 5:
        return True, 80, {
            "new_address_withdrawals": len(new_addresses),
            "suspicious_pattern": True
        }
    
    return False, 0, {}
```

**Risk Level:** CRITICAL  
**ChainShield Status:** ✅ Bridge transaction monitoring

---

## 10. Regulatory & Compliance Violations

### 10.1 OFAC Sanctions Check
**Description:** Transactions with sanctioned entities  

**Detection Logic:**
```python
# OFAC SDN List (sample - real list has thousands)
OFAC_SANCTIONED = {
    "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c",  # Tornado Cash
    "0xd882cfc20f52f2599d84b8e8d58c7fb62cfe344b",  # Tornado Cash
    "0x7f367cc41522ce07553e823bf3be79a889debe1b",  # Tornado Cash
    # ... thousands more
}

def check_ofac_sanctions(address, transactions):
    """
    Check for OFAC sanctions violations.
    Any interaction = immediate block.
    """
    # Direct match
    if address.lower() in OFAC_SANCTIONED:
        return True, 100, "Direct sanctioned address", True  # Block!
    
    # Transaction with sanctioned address
    for tx in transactions:
        counterparty = tx.get("to") if tx.get("from") == address else tx.get("from")
        if counterparty.lower() in OFAC_SANCTIONED:
            return True, 100, f"Transaction with sanctioned: {counterparty[:10]}...", True
    
    # 1-hop check (counterparty's counterparties)
    for tx in transactions:
        counterparty = tx.get("to") if tx.get("from") == address else tx.get("from")
        counterparty_txs = get_recent_transactions(counterparty, limit=100)
        
        for ctx in counterparty_txs:
            secondary = ctx.get("to") if ctx.get("from") == counterparty else ctx.get("from")
            if secondary.lower() in OFAC_SANCTIONED:
                return True, 70, f"1-hop from sanctioned via {counterparty[:10]}...", False
    
    return False, 0, None, False
```

**Risk Level:** CRITICAL (Legal liability)  
**ChainShield Status:** ✅ Implemented in blacklist rule

---

## 11. Detection Signals Summary

### Implemented Detection Methods ✅

| Category | Method | Feature/Logic |
|----------|--------|---------------|
| Pass-through | Balance vs Received ratio | `(1 - balance/received) * 100` |
| New Account | Age in hours | `age_hours < 24` |
| Bot Behavior | Timing entropy | `entropy < 0.3 = bot` |
| Mixer Usage | Known addresses | OFAC + Tornado Cash list |
| Sybil | Graph components | `strongly_connected_components()` |
| Wash Trading | Self-transfer ratio | `direct_self / total_transfers` |
| Honeypot | In/out ratio | `out_count / in_count < 0.05` |
| Velocity | TX per hour | `tx_count / age_hours > 10` |
| Blacklist | Address match | O(1) set lookup |
| Bridge Usage | Known bridges | Bridge registry match |
| Graph Hub | Centrality | PageRank, betweenness |

### Detection Priority Matrix

| Risk | Priority | Detection Method |
|------|----------|------------------|
| CRITICAL | P0 | Blacklist, OFAC, Known exploits |
| HIGH | P1 | ML score >80, Mixer, New+Volume |
| MEDIUM | P2 | Pass-through, Bot patterns |
| LOW | P3 | Normal patterns |

### Aggregation Formula

```python
final_score = max(
    weighted_average(rule, heuristic, ml),
    critical_signal * 0.7 + weighted_avg * 0.3  # If any signal > 80
) + anomaly_boost + graph_boost + crosschain_boost
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRAUD DETECTION QUICK REFERENCE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PASS-THROUGH:    (1 - balance/received) > 95%     → HIGH          │
│  NEW ACCOUNT:     age_hours < 24 AND tx_count > 50 → HIGH          │
│  BOT PATTERN:     entropy < 0.3                    → MEDIUM        │
│  MIXER:           address ∈ TORNADO_CASH           → CRITICAL      │
│  HONEYPOT:        out_count / in_count < 0.05      → HIGH          │
│  VELOCITY:        tx_count / age_hours > 10        → HIGH          │
│  WASH TRADE:      self_transfers / total > 0.3     → HIGH          │
│  SYBIL:           strongly_connected_components    → HIGH          │
│  CHAIN HOP:       bridge_count >= 5                → HIGH          │
│  BLACKLIST:       address ∈ OFAC                   → BLOCK         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

> **Senior Developer Note:** 
> 
> *"Every fraud pattern I've documented here follows a simple truth: fraudsters optimize for one thing while legitimate users optimize for another. Fraudsters optimize for SPEED and OBFUSCATION. Legitimate users optimize for UTILITY and COST.*
>
> *Build your detection around these opposing optimization functions, and you'll catch fraud before it completes."*

— 60 Years in the Trenches
