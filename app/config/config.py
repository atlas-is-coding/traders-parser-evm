from dataclasses import dataclass
from typing import Dict

@dataclass
class ThreadConfig:
    MAX_THREADS: int = 5  # Максимальное количество потоков
    MAX_CONCURRENT_REQUESTS: int = 10  # Максимальное количество одновременных асинхронных запросов

@dataclass
class ChainbaseConfig:
    BASE_URL: str = "https://api.chainbase.online/v1"
    HOLDERS_ENDPOINT: str = "/token/holders"
    DEFAULT_LIMIT: int = 100
    DEFAULT_PAGE: int = 1
    MAX_CONCURRENT_REQUESTS: int = 5  # Максимальное количество одновременных запросов к Chainbase API

@dataclass
class ChainConfig:
    CHAIN_MAPPING: Dict[str, str] = None

    def __post_init__(self):
        self.CHAIN_MAPPING = {
            "ethereum": "1",
            "polygon": "137",
            "bsc": "56",
            "avalanche": "43114",
            "arbitrum": "42161",
            "optimism": "10",
            "base": "8453",
            "zksync": "324",
            "merlin": "4200"
        }

@dataclass
class DuneConfig:
    BASE_URL: str = "https://api.dune.com/api/echo/v1"
    BALANCES_ENDPOINT: str = "/balances/evm"
    CHAIN_IDS: str = "all"
    EXCLUDE_SPAM_TOKENS: str = "true"
    LIMIT: str = "500"
    MAX_CONCURRENT_REQUESTS: int = 20  # Максимальное количество одновременных запросов к Dune API
    REQUEST_TIMEOUT: int = 30  # Таймаут для запросов в секундах
    RETRY_ATTEMPTS: int = 3  # Количество попыток повторного запроса при ошибке


@dataclass
class ProxyConfig:
    COOLDOWN_TIME: int = 120  # 2 минуты
    MAX_FAILS: int = 20  # Максимальное количество ошибок перед cooldown
    MAX_REQUESTS_PER_PROXY: int = 200  # Максимальное количество запросов на один прокси
    LOAD_CHECK_INTERVAL: int = 60  # Интервал проверки нагрузки в секундах
    DATA_FILE: str = '.scratch/proxies_data.json'

@dataclass
class HeaderConfig:
    COOLDOWN_TIME: int = 300  # 5 минуты
    MAX_FAILS: int = 10  # Максимальное количество ошибок перед cooldown
    MAX_REQUESTS_PER_HEADER: int = 50  # Максимальное количество запросов на один прокси
    LOAD_CHECK_INTERVAL: int = 60  # Интервал проверки нагрузки в секундах
    DATA_FILE: str = '.scratch/headers_data.json'

@dataclass
class BalanceConfig:
    MIN_BALANCE: float = 0.01  # Минимальный баланс в нативной валюте
    MAX_BALANCE: float = 1000.0  # Максимальный баланс в нативной валюте

@dataclass
class TwitterConfig:
    TWITTER_API_BASE: str = "https://api.twitter.com/2"
    SEARCH_ENDPOINT: str = "/users/by"
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3

proxy_config = ProxyConfig()
chainbase_config = ChainbaseConfig()
chain_config = ChainConfig()
thread_config = ThreadConfig()
dune_config = DuneConfig()
balance_config = BalanceConfig()
twitter_config = TwitterConfig()
