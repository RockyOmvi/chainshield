"""
ChainShield OFAC Sanctions Database

Contains addresses sanctioned by OFAC (Office of Foreign Assets Control)
and other regulatory bodies.

These addresses trigger CRITICAL risk and potential transaction blocking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import structlog

logger = structlog.get_logger()


@dataclass
class SanctionedEntity:
    """A sanctioned entity or address."""
    name: str
    reason: str
    sanction_date: str
    source: str  # OFAC, EU, etc.
    chain: str
    blocked: bool = True  # If True, transactions should be blocked
    programs: List[str] = field(default_factory=list)  # IFSR, SDGT, CYBER2, DPRK3, etc.


# =============================================================================
# OFAC SANCTIONED ADDRESSES
# =============================================================================

# Iran Cyber / Ransomware Sanctioned Entities (OFAC - September 14, 2022 - IFSR & SDGT Programs)
# Key Individuals: Arash Estaki Alivand, Mansour Ahmadi, Ahmad Khatibi Aghda, Amir Hossein Nikaeen Ravari
IRAN_RANSOMWARE_ADDRESSES = {
    # ALIVAND, Arash Estaki (IRGC / Afkar System Yazd Co - Ransomware & Cyber Exploits)
    "0x532b77b33a040587e9fd1800088225f99b8b0e8a": {
        "name": "ALIVAND, Arash Estaki",
        "reason": "OFAC Sanctioned - IFSR & SDGT Programs (Iran Cyber / Ransomware - Afkar System Yazd Co)",
        "programs": ["IFSR", "SDGT"],
        "date": "2022-09-14",
    },
    # AHMADI, Mansour
    "0x7db418b5d567a4e0e8c59ad71be1fce48f3e6107": {
        "name": "AHMADI, Mansour",
        "reason": "OFAC Sanctioned - IFSR & SDGT Programs (Iran Cyber / Ransomware)",
        "programs": ["IFSR", "SDGT"],
        "date": "2022-09-14",
    },
    # KHATIBI AGHDA, Ahmad
    "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a": {
        "name": "KHATIBI AGHDA, Ahmad",
        "reason": "OFAC Sanctioned - IFSR & SDGT Programs (Iran Cyber / Ransomware)",
        "programs": ["IFSR", "SDGT"],
        "date": "2022-09-14",
    },
    # NIKAEEN RAVARI, Amir Hossein
    "0x9f4cda013e354b8fc285bf4b9a60460cee7f7ea9": {
        "name": "NIKAEEN RAVARI, Amir Hossein",
        "reason": "OFAC Sanctioned - IFSR & SDGT Programs (Iran Cyber / Ransomware)",
        "programs": ["IFSR", "SDGT"],
        "date": "2022-09-14",
    },
}

# Tornado Cash - Sanctioned August 8, 2022
TORNADO_CASH_ADDRESSES = {
    # Main Contract Addresses
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": "Tornado Cash Router",
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384": "Tornado Cash 0.1 ETH",
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash 100 ETH",
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash 1 ETH",
    "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash 10 ETH",
    "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash 0.1 ETH Pool",
    "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": "Tornado Cash 0.1 ETH",
    "0x23773e65ed146a459791799d01336db287f25334": "Tornado Cash Git",
    "0xd21be7248e0197ee08e0c20d4a96debdac3d20af": "Tornado Cash Nova",
    "0x4736dcf1b7a3d580672cce6e7c65cd5cc9cfba9d": "Tornado Cash 1 ETH",
    "0x169ad27a470d064dede56a2d3ff727986b15d52b": "Tornado Cash 10 ETH",
    "0x0836222f2b2b24a3f36f98668ed8f0b38d1a872f": "Tornado Cash 1 ETH",
    "0xf67721a2d8f736e75a49fdd7fad2e31d8676542a": "Tornado Cash 10 ETH",
    "0x9ad122c22b14202b37174eaf7d72a98b1d8c4bbb": "Tornado Cash 100 ETH",
    "0x905b63fff465b9ffbf41dea908ceb12478ec7601": "Tornado Cash 10 ETH",
    "0x07687e702b410fa43f4cb4af7fa097918ffd2730": "Tornado Cash 0.1 ETH Pool",
    "0x94a1b5cdb22c43faab4abeb5c74999895464ddaf": "Tornado Cash 1 ETH",
    "0xb541fc07bc7619fd4062a54d96268525cbc6ffef": "Tornado Cash 10 ETH",
    "0x242654336ca2205714071898f67e254eb49acdce": "Tornado Cash",
    "0x776198ccf446dfa168347089d7338879273172cf": "Tornado Cash 100 ETH",
    "0xba214c1c1928a32bffe790263e38b4af9bfcd659": "Tornado Cash 100 ETH",
    "0xb1c8094b234dce6e03f10a5b673c1d8c69739a00": "Tornado Cash 100 ETH",
    "0x58e8dcc13be9780fc42e8723d8ead4cf46943df2": "Tornado Cash Router 2",
    "0xd691f27f38b395864ea86cfc7253969b409c362d": "Tornado Cash 100 ETH",
    "0xaeaac358560e11f52454d997aaff2c5731b6f8a6": "Tornado Cash 10 ETH",
    "0x1356c899d8c9467c7f71c195612f8a395abf2f0a": "Tornado Cash 1000 ETH",
    "0xa60c772958a3ed56c1f15dd055ba37ac8e523a0d": "Tornado Cash",
}

# North Korea (DPRK) Linked Addresses - Lazarus Group
LAZARUS_GROUP_ADDRESSES = {
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Lazarus Group (Main)",
    "0xa7e5d5a720f06526557c513402f2e6b5fa20b008": "Lazarus Group",
    "0x3cffd56b47b7b41c56258d9c7731abadc360e073": "Lazarus Group (Ronin Bridge)",
    "0x53b6936513e738f44fb50d2b9476730c0ab3bfc1": "Lazarus Group (Harmony Horizon)",
    "0xe708aa9e887980750c040a6a2cb901c37aa34f3b": "Lazarus Group",
    "0x8589427373d6d84e98730d7795d8f6f8731fda16": "Lazarus Group (Ronin Validator Exploit)",
    "0xd882cfc20f52f2599d84b8e8d58c7fb62cfe344b": "Lazarus Group Aggregator",
    "0x6ac44baeb64cb54c46f33d7b80894e6bf7cb625f": "Lazarus Group Consolidator",
    "0x35fca3920d32e0c457013acb1a461b58394c6325": "Lazarus Group (Atomic Wallet)",
    "0x0a5984f8620041589f382bfaf2612454b5ed6566": "Lazarus Group Relay",
}

# Other known sanctioned/high-risk addresses
OTHER_SANCTIONED = {
    # BlueNoroff (North Korea)
    "0x7f19720a857f834887fc9a7bc0a0fbe7fc7f8102": {
        "name": "Bluenoroff",
        "reason": "OFAC Sanctioned - DPRK State-Sponsored Actor",
        "programs": ["DPRK3", "CYBER2"],
    },
    # Hydra Market (Russian Dark Web)
    "0x6f1ca141a28907f78ebaa64fb83a9088b02a8352": {
        "name": "Hydra Market",
        "reason": "OFAC Sanctioned - Darknet Narcotics & Laundering Marketplace",
        "programs": ["CYBER2", "ILLICIT-DRUG"],
    },
    # Garantex (Russian exchange)
    "0x7ff9cfad3877f21d41da833e2f2a40b11c31ffba": {
        "name": "Garantex Europe OU",
        "reason": "OFAC Sanctioned - Facilitation of Ransomware Laundering",
        "programs": ["RUSSIA-EO14024", "CYBER2"],
    },
    "0x2f389ce8bd801c8d47fdab430335e3d78901ad9c": {
        "name": "Garantex Europe OU (Main Deposit)",
        "reason": "OFAC Sanctioned - Facilitation of Ransomware Laundering",
        "programs": ["RUSSIA-EO14024", "CYBER2"],
    },
    # SUEX OTC (Russian illicit OTC)
    "0x72a5843cc08275c80f1aed501b7435abf72c41b1": {
        "name": "SUEX OTC",
        "reason": "OFAC Sanctioned - Illicit Crypto Brokerage & Ransomware Laundering",
        "programs": ["CYBER2", "RUSSIA-EO14024"],
    },
    # Chatex (sanctioned exchange)
    "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c": {
        "name": "Chatex",
        "reason": "OFAC Sanctioned - Illicit Exchange & Ransomware Operations",
        "programs": ["CYBER2"],
    },
    # Sinbad Mixer
    "0x42da701c65d6c810d7a6411f181f087beee270dc": {
        "name": "Sinbad.io Mixer",
        "reason": "OFAC Sanctioned - DPRK Lazarus Laundering Service",
        "programs": ["CYBER2", "DPRK3"],
    },
    # Bitzlato Omnibus
    "0x19aa5fe80d33a7675f01a9704c56e1d7d93a534f": {
        "name": "Bitzlato Omnibus",
        "reason": "FinCEN / OFAC Primary Money Laundering Concern",
        "programs": ["RUSSIA-EO14024"],
    },
}


# =============================================================================
# SANCTIONS SERVICE
# =============================================================================

class SanctionsDatabase:
    """Database of OFAC and other sanctioned addresses."""
    
    def __init__(self):
        self.logger = logger.bind(module="sanctions_db")
        
        # Build complete sanctions list
        self.sanctioned_addresses: Dict[str, SanctionedEntity] = {}

        # Add Iran Cyber / Ransomware Entities (Arash Estaki Alivand, etc.)
        for addr, meta in IRAN_RANSOMWARE_ADDRESSES.items():
            self.sanctioned_addresses[addr.lower()] = SanctionedEntity(
                name=meta["name"],
                reason=meta["reason"],
                sanction_date=meta["date"],
                source="US OFAC SDN",
                chain="ethereum",
                blocked=True,
                programs=meta["programs"]
            )
        
        # Add Tornado Cash
        for addr, name in TORNADO_CASH_ADDRESSES.items():
            self.sanctioned_addresses[addr.lower()] = SanctionedEntity(
                name=name,
                reason="OFAC Sanctioned - Tornado Cash Privacy Mixer",
                sanction_date="2022-08-08",
                source="US OFAC SDN",
                chain="ethereum",
                blocked=True,
                programs=["CYBER2", "DPRK3"]
            )
        
        # Add Lazarus Group
        for addr, name in LAZARUS_GROUP_ADDRESSES.items():
            self.sanctioned_addresses[addr.lower()] = SanctionedEntity(
                name=name,
                reason="OFAC Sanctioned - North Korea Lazarus Group",
                sanction_date="2022-04-14",
                source="US OFAC SDN",
                chain="ethereum",
                blocked=True,
                programs=["DPRK3", "CYBER2"]
            )
        
        # Add other sanctioned
        for addr, meta in OTHER_SANCTIONED.items():
            self.sanctioned_addresses[addr.lower()] = SanctionedEntity(
                name=meta["name"],
                reason=meta["reason"],
                sanction_date="2022-01-01",
                source="US OFAC SDN",
                chain="ethereum",
                blocked=True,
                programs=meta.get("programs", ["OFAC-SDN"])
            )
        
        self.logger.info(
            "sanctions_db_loaded", 
            total_addresses=len(self.sanctioned_addresses),
            iran_ransomware=len(IRAN_RANSOMWARE_ADDRESSES),
            tornado_cash=len(TORNADO_CASH_ADDRESSES),
            lazarus=len(LAZARUS_GROUP_ADDRESSES)
        )
    
    def is_sanctioned(self, address: str) -> tuple[bool, Optional[SanctionedEntity]]:
        """Check if an address is sanctioned."""
        entity = self.sanctioned_addresses.get(address.lower())
        if entity:
            return True, entity
        return False, None
    
    def check_transaction(
        self, 
        from_address: str, 
        to_address: str
    ) -> tuple[bool, Optional[str], Optional[SanctionedEntity]]:
        """
        Check if a transaction involves a sanctioned address.
        
        Returns:
            (is_sanctioned, which_party, entity)
        """
        is_from_sanctioned, from_entity = self.is_sanctioned(from_address)
        if is_from_sanctioned:
            return True, "sender", from_entity
        
        is_to_sanctioned, to_entity = self.is_sanctioned(to_address)
        if is_to_sanctioned:
            return True, "receiver", to_entity
        
        return False, None, None
    
    def get_all_addresses(self) -> Set[str]:
        """Get all sanctioned addresses."""
        return set(self.sanctioned_addresses.keys())
    
    def get_tornado_cash_addresses(self) -> Set[str]:
        """Get only Tornado Cash addresses."""
        return {addr.lower() for addr in TORNADO_CASH_ADDRESSES.keys()}


# Singleton instance
_sanctions_db: Optional[SanctionsDatabase] = None


def get_sanctions_database() -> SanctionsDatabase:
    """Get or create the sanctions database."""
    global _sanctions_db
    if _sanctions_db is None:
        _sanctions_db = SanctionsDatabase()
    return _sanctions_db
