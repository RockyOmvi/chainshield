"""
ChainShield Entity Reputation Database

Known legitimate entities that should not be flagged as high-risk.
This includes major exchanges, stablecoin contracts, DeFi protocols, and bridges.

Usage:
    from app.services.risk.entity_reputation import get_entity_reputation
    
    reputation = get_entity_reputation()
    entity = reputation.get_entity(address)
    if entity:
        adjusted_score = score * (1 - entity.trust_score)
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set
import structlog

logger = structlog.get_logger()


@dataclass
class KnownEntity:
    """A known, trusted entity in the blockchain ecosystem."""
    name: str
    category: str  # exchange, token, defi, bridge, etc.
    trust_score: float  # 0.0 to 1.0 (higher = more trusted)
    chain: str  # ethereum, bitcoin, multi, etc.
    verified: bool = True
    notes: str = ""


# =============================================================================
# BITCOIN KNOWN ENTITIES
# =============================================================================

BITCOIN_ENTITIES: Dict[str, KnownEntity] = {
    # Major Exchanges - Cold Wallets
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": KnownEntity("Binance", "exchange", 0.9, "bitcoin"),
    "3FpYfDGJSdkMAvZvCrwPHDqdmGqUkTsJys": KnownEntity("BitMEX", "exchange", 0.85, "bitcoin"),
    "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64": KnownEntity("Bitstamp", "exchange", 0.9, "bitcoin"),
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6": KnownEntity("Coinbase Custody", "exchange", 0.95, "bitcoin"),
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": KnownEntity("Bitfinex", "exchange", 0.85, "bitcoin"),
    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": KnownEntity("OKX", "exchange", 0.85, "bitcoin"),
    "bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfc27a4": KnownEntity("Gemini", "exchange", 0.9, "bitcoin"),
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a": KnownEntity("Blockchain.com", "wallet_provider", 0.85, "bitcoin"),
    "bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6": KnownEntity("Kraken", "exchange", 0.9, "bitcoin"),
    
    # Custodians
    "1FzWLkAahHooV3kzv4sS4wXXgBuNZHjZPZ": KnownEntity("Kraken Cold", "exchange", 0.9, "bitcoin"),
    "385cR5DM96n1HvBDMzLHPYcw89fZAXULJP": KnownEntity("Binance Cold 2", "exchange", 0.9, "bitcoin"),
}

# =============================================================================
# ETHEREUM KNOWN ENTITIES
# =============================================================================

ETHEREUM_ENTITIES: Dict[str, KnownEntity] = {
    # Major Exchanges
    "0x28C6c06298d514Db089934071355E5743bf21d60": KnownEntity("Binance Hot Wallet", "exchange", 0.9, "ethereum"),
    "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": KnownEntity("Binance", "exchange", 0.9, "ethereum"),
    "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": KnownEntity("Binance Cold", "exchange", 0.9, "ethereum"),
    "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503": KnownEntity("Binance Cold 2", "exchange", 0.9, "ethereum"),
    "0x564286362092D8e7936f0549571a803B203aAceD": KnownEntity("Binance Cold 3", "exchange", 0.9, "ethereum"),
    "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE": KnownEntity("Binance Old Hot", "exchange", 0.9, "ethereum"),
    
    "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43": KnownEntity("Coinbase Cold", "exchange", 0.95, "ethereum"),
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3": KnownEntity("Coinbase Commerce", "exchange", 0.95, "ethereum"),
    "0x503828976D22510aad0201ac7EC88293211D23Da": KnownEntity("Coinbase Hot", "exchange", 0.95, "ethereum"),
    
    "0x2B5634C42055806a59e9107ED44D43c426E58258": KnownEntity("Kraken Hot", "exchange", 0.9, "ethereum"),
    "0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0": KnownEntity("Kraken Cold", "exchange", 0.9, "ethereum"),
    
    "0x6Cc5F688a315f3dC28A7781717a9A798a59fDA7b": KnownEntity("OKX", "exchange", 0.85, "ethereum"),
    "0x98EC059Dc3adfBdd63429454aEB0C990fbA4A128": KnownEntity("OKX Cold", "exchange", 0.85, "ethereum"),
    
    "0xc098B2a3Aa256D2140208C3de6543aAEf5cd3A94": KnownEntity("FTX Bankruptcy", "exchange", 0.5, "ethereum", notes="Bankrupt"),
    
    "0x1151314c646Ce4E0eFD76d1aF4760aE66a9Fe30F": KnownEntity("Bitfinex Hot", "exchange", 0.85, "ethereum"),
    "0x876EabF441B2EE5B5b0554Fd502a8E0600950cFa": KnownEntity("Bitfinex Multisig", "exchange", 0.85, "ethereum"),
    
    # Stablecoins
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": KnownEntity("USDT", "stablecoin", 0.95, "ethereum"),
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": KnownEntity("USDC", "stablecoin", 0.98, "ethereum"),
    "0x6B175474E89094C44Da98b954EescdeCB5f58dC": KnownEntity("DAI", "stablecoin", 0.95, "ethereum"),
    "0x4Fabb145d64652a948d72533023f6E7A623C7C53": KnownEntity("BUSD", "stablecoin", 0.85, "ethereum"),
    "0x8E870D67F660D95d5be530380D0eC0bd388289E1": KnownEntity("USDP (Pax)", "stablecoin", 0.9, "ethereum"),
    "0x0000000000085d4780B73119b644AE5ecd22b376": KnownEntity("TUSD", "stablecoin", 0.85, "ethereum"),
    
    # Wrapped Tokens
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": KnownEntity("WETH", "wrapped", 0.98, "ethereum"),
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": KnownEntity("WBTC", "wrapped", 0.95, "ethereum"),
    
    # DeFi Protocols - Uniswap
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": KnownEntity("Uniswap V2 Router", "defi", 0.95, "ethereum"),
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": KnownEntity("Uniswap V3 Router", "defi", 0.95, "ethereum"),
    "0xE592427A0AEce92De3Edee1F18E0157C05861564": KnownEntity("Uniswap V3 Router 1", "defi", 0.95, "ethereum"),
    "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f": KnownEntity("Uniswap V2 Factory", "defi", 0.95, "ethereum"),
    "0x1F98431c8aD98523631AE4a59f267346ea31F984": KnownEntity("Uniswap V3 Factory", "defi", 0.95, "ethereum"),
    
    # DeFi Protocols - Others
    "0x1111111254EEB25477B68fb85Ed929f73A960582": KnownEntity("1inch Router", "defi", 0.9, "ethereum"),
    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F": KnownEntity("SushiSwap Router", "defi", 0.85, "ethereum"),
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": KnownEntity("0x Exchange", "defi", 0.9, "ethereum"),
    "0x881D40237659C251811CEC9c364ef91dC08D300C": KnownEntity("Metamask Swap", "defi", 0.9, "ethereum"),
    
    # Lending Protocols
    "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9": KnownEntity("Aave V2 Pool", "lending", 0.95, "ethereum"),
    "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2": KnownEntity("Aave V3 Pool", "lending", 0.95, "ethereum"),
    "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B": KnownEntity("Compound Comptroller", "lending", 0.95, "ethereum"),
    
    # Bridges
    "0x3ee18B2214AFF97000D974cf647E7C347E8fa585": KnownEntity("Wormhole", "bridge", 0.7, "ethereum"),
    "0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf": KnownEntity("Polygon Bridge", "bridge", 0.85, "ethereum"),
    "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1": KnownEntity("Optimism Bridge", "bridge", 0.9, "ethereum"),
    "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f": KnownEntity("Arbitrum Bridge", "bridge", 0.9, "ethereum"),
    "0xa3A7B6F88361F48403514059F1F16C8E78d60EeC": KnownEntity("Arbitrum Outbox", "bridge", 0.9, "ethereum"),
    "0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820": KnownEntity("Hop Protocol", "bridge", 0.8, "ethereum"),
    "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497": KnownEntity("Stargate Router", "bridge", 0.8, "ethereum"),
    
    # NFT Marketplaces
    "0x00000000006c3852cbEf3e08E8dF289169EdE581": KnownEntity("OpenSea Seaport", "nft", 0.85, "ethereum"),
    "0x7Be8076f4EA4A4AD08075C2508e481d6C946D12b": KnownEntity("OpenSea Legacy", "nft", 0.85, "ethereum"),
    "0x74312363e45DCaBA76c59ec49a7Aa8A65a67EeD3": KnownEntity("X2Y2", "nft", 0.8, "ethereum"),
    
    # Liquid Staking
    "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84": KnownEntity("Lido stETH", "staking", 0.95, "ethereum"),
    "0xbE9895146f7AF43049ca1c1AE358B0541Ea49704": KnownEntity("Coinbase cbETH", "staking", 0.95, "ethereum"),
    "0xac3E018457B222d93114458476f3E3416Abbe38F": KnownEntity("Frax sfrxETH", "staking", 0.85, "ethereum"),
    "0xae78736Cd615f374D3085123A210448E74Fc6393": KnownEntity("Rocket Pool rETH", "staking", 0.9, "ethereum"),
}

# =============================================================================
# SOLANA KNOWN ENTITIES
# =============================================================================

SOLANA_ENTITIES: Dict[str, KnownEntity] = {
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": KnownEntity("Binance", "exchange", 0.9, "solana"),
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": KnownEntity("USDC Mint", "stablecoin", 0.98, "solana"),
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": KnownEntity("USDT Mint", "stablecoin", 0.95, "solana"),
    "So11111111111111111111111111111111111111112": KnownEntity("Wrapped SOL", "wrapped", 0.98, "solana"),
    
    # DEXs
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": KnownEntity("Jupiter", "defi", 0.9, "solana"),
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": KnownEntity("Orca Whirlpool", "defi", 0.9, "solana"),
    "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": KnownEntity("Serum DEX", "defi", 0.8, "solana"),
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": KnownEntity("Raydium AMM", "defi", 0.85, "solana"),
    
    # Validators
    "CertusDeBmqN8ZawdkxK5kFGMwBXdudvWHYwtNgNhvLu": KnownEntity("Certus One", "validator", 0.9, "solana"),
    "7Np41oeYqPefeNQEHSv1UDhYrehxin3NStELsSKCT4K2": KnownEntity("Jito", "validator", 0.9, "solana"),
}


# =============================================================================
# ENTITY REPUTATION SERVICE
# =============================================================================

class EntityReputation:
    """Service for looking up known entities and adjusting risk scores."""
    
    def __init__(self):
        self.logger = logger.bind(module="entity_reputation")
        
        # Combine all entities, normalizing addresses to lowercase
        self.entities: Dict[str, KnownEntity] = {}
        
        for addr, entity in BITCOIN_ENTITIES.items():
            self.entities[addr.lower()] = entity
        
        for addr, entity in ETHEREUM_ENTITIES.items():
            self.entities[addr.lower()] = entity
            
        for addr, entity in SOLANA_ENTITIES.items():
            self.entities[addr.lower()] = entity
        
        self.logger.info("entity_reputation_loaded", count=len(self.entities))
    
    def get_entity(self, address: str) -> Optional[KnownEntity]:
        """Look up an entity by address."""
        return self.entities.get(address.lower())
    
    def is_trusted(self, address: str, min_trust: float = 0.7) -> bool:
        """Check if an address belongs to a trusted entity."""
        entity = self.get_entity(address)
        if entity and entity.trust_score >= min_trust:
            return True
        return False
    
    def adjust_score(self, address: str, raw_score: float) -> float:
        """
        Adjust risk score based on entity reputation.
        
        For trusted entities, reduce the score proportionally.
        A trust_score of 0.9 means reduce risk by 90%.
        """
        entity = self.get_entity(address)
        if entity:
            adjustment = raw_score * (1 - entity.trust_score)
            self.logger.debug(
                "score_adjusted_for_entity",
                address=address[:16],
                entity=entity.name,
                trust=entity.trust_score,
                raw_score=raw_score,
                adjusted_score=adjustment
            )
            return adjustment
        return raw_score
    
    def get_entity_info(self, address: str) -> Optional[Dict]:
        """Get full entity info as dictionary."""
        entity = self.get_entity(address)
        if entity:
            return {
                "name": entity.name,
                "category": entity.category,
                "trust_score": entity.trust_score,
                "chain": entity.chain,
                "verified": entity.verified,
                "notes": entity.notes
            }
        return None
    
    def get_all_by_category(self, category: str) -> Dict[str, KnownEntity]:
        """Get all entities of a specific category."""
        return {
            addr: entity 
            for addr, entity in self.entities.items() 
            if entity.category == category
        }


# Singleton instance
_entity_reputation: Optional[EntityReputation] = None


def get_entity_reputation() -> EntityReputation:
    """Get or create the entity reputation service."""
    global _entity_reputation
    if _entity_reputation is None:
        _entity_reputation = EntityReputation()
    return _entity_reputation
