"""
Основной пакет приложения traders-parser-evm
"""

from app.services.contract.get_holders import TokenHoldersService, Contract
from app.config.config import chainbase_config, chain_config

__all__ = [
    'TokenHoldersService',
    'Contract',
    'chainbase_config',
    'chain_config'
]
