import os
import logging
from typing import List, Optional, Iterator
from itertools import cycle
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApiKeyManager:
    """Менеджер для управления API ключами"""
    def __init__(self, api_keys_file: str = None):
        if api_keys_file is None:
            api_keys_file = os.path.join(ROOT_DIR, "config", "chainbase_api_keys.txt")
        self.api_keys_file = api_keys_file
        self._api_keys = self._load_api_keys()
        self._key_cycle: Optional[Iterator[str]] = None
        self._initialize_cycle()
    
    def _load_api_keys(self) -> List[str]:
        try:
            with open(self.api_keys_file, 'r') as file:
                keys = [key.strip() for key in file.readlines() if key.strip()]
                if not keys:
                    logger.error("Файл с API ключами пуст")
                    return []
                logger.info(f"Загружено {len(keys)} API ключей")
                return keys
        except FileNotFoundError:
            logger.error(f"Файл с API ключами не найден: {self.api_keys_file}")
            return []

    def _initialize_cycle(self) -> None:
        """Инициализирует цикл API ключей"""
        if self._api_keys:
            self._key_cycle = cycle(self._api_keys)
        else:
            self._key_cycle = None
            
    def get_next_key(self) -> Optional[str]:
        """
        Получает следующий API ключ из цикла.
        
        Returns:
            Optional[str]: Следующий API ключ или None, если ключи не загружены
        """
        if not self._key_cycle:
            logger.error("Нет доступных API ключей")
            return None
        return next(self._key_cycle)

    @property
    def api_keys_count(self) -> int:
        """Возвращает количество доступных API ключей"""
        return len(self._api_keys) 