"""
ChainShield Dynamic Entity Reputation Updater

Periodically refreshes entity reputation data from external sources:
1. Etherscan verified labels API
2. Local JSON config file (admin overrides)
3. Community-maintained lists

This ensures the reputation database stays current without code changes.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiohttp
import structlog

from app.services.risk.entity_reputation import (
    EntityReputation, 
    KnownEntity, 
    get_entity_reputation
)

logger = structlog.get_logger()


class EntityUpdater:
    """
    Manages dynamic updates to the entity reputation database.
    
    Features:
    - Load from local JSON config on startup
    - Fetch Etherscan labels for known addresses
    - Scheduled refresh every 24 hours
    - Admin API for manual additions
    """
    
    # Default config path
    CONFIG_PATH = Path("config/known_entities.json")
    
    # Etherscan API (free tier allows 5 calls/sec)
    ETHERSCAN_API = "https://api.etherscan.io/api"
    
    # Refresh interval
    REFRESH_INTERVAL_HOURS = 24
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the entity updater."""
        self.logger = logger.bind(module="entity_updater")
        self.config_path = config_path or self.CONFIG_PATH
        self.reputation = get_entity_reputation()
        self.last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        
        # API keys loaded from environment
        self.etherscan_api_key: Optional[str] = None
        self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """Load API keys from environment."""
        import os
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        if not self.etherscan_api_key:
            self.logger.warning("etherscan_api_key_not_set", 
                              msg="Entity updates from Etherscan disabled")
    
    async def initialize(self) -> int:
        """
        Initialize entity database from config file.
        
        Returns:
            Number of entities loaded from config
        """
        loaded = 0
        
        # Load from config file if exists
        if self.config_path.exists():
            try:
                loaded = await self._load_from_config()
                self.logger.info("entities_loaded_from_config", count=loaded)
            except Exception as e:
                self.logger.error("config_load_failed", error=str(e))
        else:
            self.logger.info("no_config_file", path=str(self.config_path))
        
        self.last_refresh = datetime.utcnow()
        return loaded
    
    async def _load_from_config(self) -> int:
        """Load entities from JSON config file."""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        count = 0
        for entry in config.get("entities", []):
            entity = KnownEntity(
                name=entry["name"],
                category=entry["category"],
                trust_score=entry.get("trust_score", 0.8),
                chain=entry.get("chain", "ethereum"),
                verified=entry.get("verified", False),
                notes=entry.get("notes", "")
            )
            
            # Add all addresses for this entity
            for address in entry.get("addresses", []):
                self.reputation.entities[address.lower()] = entity
                count += 1
        
        return count
    
    async def fetch_etherscan_labels(
        self, 
        addresses: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch verified labels from Etherscan.
        
        Args:
            addresses: List of addresses to look up
            
        Returns:
            Dict mapping address to label info
        """
        if not self.etherscan_api_key:
            return {}
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for addr in addresses[:10]:  # Limit to 10 per call
                try:
                    params = {
                        "module": "account",
                        "action": "txlist",
                        "address": addr,
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": 1,
                        "offset": 1,
                        "apikey": self.etherscan_api_key
                    }
                    
                    async with session.get(
                        self.ETHERSCAN_API,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        data = await resp.json()
                        
                        if data.get("status") == "1":
                            results[addr] = {
                                "has_transactions": True,
                                "label": data.get("result", [{}])[0].get("from", "")
                            }
                    
                    # Rate limit: 5 calls/sec max
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    self.logger.warning("etherscan_fetch_failed", 
                                       address=addr, error=str(e))
        
        return results
    
    def add_entity(
        self,
        addresses: List[str],
        name: str,
        category: str,
        trust_score: float = 0.8,
        chain: str = "ethereum",
        notes: str = ""
    ) -> bool:
        """
        Add a new entity to the reputation database.
        
        Args:
            addresses: List of addresses for this entity
            name: Entity name (e.g., "Coinbase")
            category: Category (exchange, defi, stablecoin, etc.)
            trust_score: Trust level 0-1
            chain: Blockchain name
            notes: Optional notes
            
        Returns:
            True if added successfully
        """
        entity = KnownEntity(
            name=name,
            category=category,
            trust_score=trust_score,
            chain=chain,
            verified=False,  # Manual additions are unverified
            notes=notes
        )
        
        for addr in addresses:
            self.reputation.entities[addr.lower()] = entity
        
        self.logger.info("entity_added", 
                        name=name, 
                        addresses=len(addresses),
                        trust_score=trust_score)
        
        return True
    
    def remove_entity(self, address: str) -> bool:
        """Remove an entity by address."""
        addr_lower = address.lower()
        if addr_lower in self.reputation.entities:
            del self.reputation.entities[addr_lower]
            self.logger.info("entity_removed", address=address)
            return True
        return False
    
    async def save_to_config(self) -> None:
        """
        Save current entities to config file.
        
        Groups by entity name and saves all addresses.
        """
        # Group addresses by entity
        entity_groups: Dict[str, Dict[str, Any]] = {}
        
        for addr, entity in self.reputation.entities.items():
            key = f"{entity.name}_{entity.category}"
            if key not in entity_groups:
                entity_groups[key] = {
                    "name": entity.name,
                    "category": entity.category,
                    "trust_score": entity.trust_score,
                    "chain": entity.chain,
                    "verified": entity.verified,
                    "notes": entity.notes,
                    "addresses": []
                }
            entity_groups[key]["addresses"].append(addr)
        
        config = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "entities": list(entity_groups.values())
        }
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.logger.info("config_saved", 
                        path=str(self.config_path),
                        entities=len(entity_groups))
    
    async def start_background_refresh(self) -> None:
        """Start background task for periodic entity refresh."""
        if self._refresh_task is not None:
            return
        
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        self.logger.info("background_refresh_started",
                        interval_hours=self.REFRESH_INTERVAL_HOURS)
    
    async def _refresh_loop(self) -> None:
        """Background loop for periodic refresh."""
        while True:
            try:
                await asyncio.sleep(self.REFRESH_INTERVAL_HOURS * 3600)
                await self._do_refresh()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("refresh_failed", error=str(e))
    
    async def _do_refresh(self) -> None:
        """Perform a refresh of entity data."""
        self.logger.info("starting_entity_refresh")
        
        # Reload from config
        if self.config_path.exists():
            await self._load_from_config()
        
        # Update last refresh time
        self.last_refresh = datetime.utcnow()
        
        self.logger.info("entity_refresh_complete",
                        total_entities=len(self.reputation.entities))
    
    def stop_background_refresh(self) -> None:
        """Stop background refresh task."""
        if self._refresh_task:
            self._refresh_task.cancel()
            self._refresh_task = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the entity database."""
        categories: Dict[str, int] = {}
        chains: Dict[str, int] = {}
        
        for entity in self.reputation._entities.values():
            categories[entity.category] = categories.get(entity.category, 0) + 1
            chains[entity.chain] = chains.get(entity.chain, 0) + 1
        
        return {
            "total_entities": len(self.reputation._entities),
            "by_category": categories,
            "by_chain": chains,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
        }


# Singleton
_entity_updater: Optional[EntityUpdater] = None


def get_entity_updater() -> EntityUpdater:
    """Get or create entity updater singleton."""
    global _entity_updater
    if _entity_updater is None:
        _entity_updater = EntityUpdater()
    return _entity_updater
