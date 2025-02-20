from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class WalletBalance:
    """Модель для хранения информации о балансе кошелька."""
    address: str
    balance: float = 0.0

    def to_token_holder(self) -> 'TokenHolder':
        """Преобразует WalletBalance в TokenHolder."""
        return TokenHolder(
            address=self.address,
            balance=str(self.balance),
            processed=True,
            processed_at=datetime.now()
        )

    @classmethod
    def from_dune_response(cls, address: str, response: Dict) -> 'WalletBalance':
        """
        Создает объект WalletBalance из ответа Dune API.
        
        Args:
            address: Адрес кошелька
            response: Ответ от API Dune

        Returns:
            WalletBalance: Объект с балансом кошелька
        """
        total_balance = 0.0
        if isinstance(response, dict) and 'balances' in response:
            for token in response['balances']:
                if 'value_usd' in token and token['value_usd']:
                    total_balance += float(token['value_usd'])
        
        return cls(address=address, balance=total_balance)

@dataclass
class TokenHolder:
    """Модель для хранения информации о держателе токенов."""
    address: str
    balance: str
    processed: bool = False
    processed_at: Optional[datetime] = None

@dataclass
class DuneApiConfig:
    """Конфигурация для работы с Dune API."""
    BASE_URL: str
    BALANCES_ENDPOINT: str
    CHAIN_IDS: List[int]
    EXCLUDE_SPAM_TOKENS: bool
    LIMIT: int
    MAX_CONCURRENT_REQUESTS: int
    RETRY_ATTEMPTS: int
    REQUEST_TIMEOUT: int
