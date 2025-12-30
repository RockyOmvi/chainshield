"""
ChainShield Blockchain Services Package

Exposes blockchain client and service layers.
"""

from app.services.blockchain.client import (
    blockchain_client,
    BlockchainClient,
    WalletBalance,
    TokenBalance,
    TransactionData,
    TransactionReceipt,
)
from app.services.blockchain.wallet import wallet_service, WalletService
from app.services.blockchain.transaction import transaction_service, TransactionService

__all__ = [
    # Client
    "blockchain_client",
    "BlockchainClient",
    # Data classes
    "WalletBalance",
    "TokenBalance",
    "TransactionData",
    "TransactionReceipt",
    # Services
    "wallet_service",
    "WalletService",
    "transaction_service",
    "TransactionService",
]
