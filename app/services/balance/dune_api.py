import random
from dataclasses import dataclass, field
from typing import List
import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config.config import dune_config
from app.services.manager.proxy_manager import ProxyManager
from app.services.balance.models import WalletBalance

@dataclass
class DuneApiKeyManager:
    """Менеджер API ключей для Dune."""
    api_keys_file: str = "config/dune_api_keys.txt"
    _api_keys: List[str] = field(default=None, init=False)
    _semaphore: asyncio.Semaphore = field(default=None, init=False)

    def __post_init__(self):
        self._load_api_keys()
        self._semaphore = asyncio.Semaphore(dune_config.MAX_CONCURRENT_REQUESTS)

    def _load_api_keys(self) -> None:
        """Загружает API ключи из файла."""
        try:
            with open(self.api_keys_file, 'r') as file:
                self._api_keys = [key.strip() for key in file.readlines() if key.strip()]
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл с API ключами не найден: {self.api_keys_file}")

    def get_random_api_key(self) -> str:
        """Возвращает случайный API ключ."""
        if not self._api_keys:
            raise ValueError("Список API ключей пуст")
        return random.choice(self._api_keys)

@dataclass
class DuneApiClient:
    """Клиент для работы с Dune API."""
    api_key_manager: DuneApiKeyManager
    session: aiohttp.ClientSession = field(default=None, init=False)

    async def __aenter__(self):
        """Создает сессию при входе в контекстный менеджер."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает сессию при выходе из контекстного менеджера."""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(dune_config.RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    @ProxyManager.with_proxy
    async def get_wallet_balance(self, wallet_address: str, proxy: str = None) -> WalletBalance:
        """
        Асинхронно получает баланс кошелька через Dune API с использованием прокси.
        
        Args:
            wallet_address: Адрес кошелька для проверки
            proxy: Прокси для запроса (добавляется автоматически декоратором)

        Returns:
            WalletBalance: Объект с информацией о балансе кошелька
            
        Raises:
            aiohttp.ClientError: При ошибке запроса
            asyncio.TimeoutError: При превышении таймаута
        """
        async with self.api_key_manager._semaphore:
            url = f"{dune_config.BASE_URL}{dune_config.BALANCES_ENDPOINT}/{wallet_address}"
            
            params = {
                "chain_ids": dune_config.CHAIN_IDS,
                "exclude_spam_tokens": dune_config.EXCLUDE_SPAM_TOKENS,
                "limit": dune_config.LIMIT
            }
            
            headers = {
                "X-Dune-Api-Key": self.api_key_manager.get_random_api_key()
            }

            async with self.session.get(
                url,
                headers=headers,
                params=params,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=dune_config.REQUEST_TIMEOUT)
            ) as response:
                print(response)
                response.raise_for_status()
                data = await response.json()
                return WalletBalance.from_dune_response(wallet_address, data) 