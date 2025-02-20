import os
import sys
from pathlib import Path
from datetime import datetime
import signal
import logging
from app.services.contract.services.token_holders_service import TokenHoldersService

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dataclasses import dataclass
from typing import List, Optional, Generator, Any, Iterator, Dict
import aiohttp
import asyncio
from itertools import cycle
from app.config.config import chainbase_config, thread_config
from app.utils.get_chain import get_chain_id
from app.services.contract.models import ApiResponse, SuccessResponse
from app.services.manager.thread_manager import ThreadManager, ThreadTask
from app.services.manager.db_manager import DBManager, ProcessedContract, TokenHolder, ParsingStatus, ParsingProgress
from app.services.manager.proxy_manager import ProxyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания сигнала прерывания
is_interrupted = False

def handle_interrupt(signum, frame):
    """Обработчик сигнала прерывания"""
    global is_interrupted
    logger.info("Получен сигнал прерывания. Graceful shutdown...")
    is_interrupted = True

# Регистрируем обработчик сигнала
signal.signal(signal.SIGINT, handle_interrupt)

@dataclass
class Contract:
    address: str
    chain: str
    
    @property
    def chain_id(self) -> Optional[str]:
        return get_chain_id(self.chain)

class ApiKeyManager:
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

class ContractLoader:
    def __init__(self, contracts_file: str = None):
        if contracts_file is None:
            contracts_file = os.path.join(ROOT_DIR, "contracts.txt")
        self.contracts_file = contracts_file
    
    def load_contracts(self) -> List[Contract]:
        contracts = []
        try:
            with open(self.contracts_file, 'r') as file:
                for line in file:
                    address, chain = line.strip().split()
                    contracts.append(Contract(address=address, chain=chain))
        except FileNotFoundError:
            logger.error(f"Файл с контрактами не найден: {self.contracts_file}")
        except ValueError:
            logger.error("Неверный формат данных в файле контрактов")
        return contracts

class TokenHoldersService:
    def __init__(self):
        self.api_key_manager = ApiKeyManager()
        self.contract_loader = ContractLoader()
        self.thread_manager = ThreadManager()
        self.db_manager = DBManager()
        self.proxy_manager = ProxyManager()
    
    @ProxyManager.with_proxy
    async def _make_async_request(self, session: aiohttp.ClientSession, contract: Contract, 
                                page: int = 1, limit: int = chainbase_config.DEFAULT_LIMIT,
                                proxy: str = None) -> Optional[ApiResponse]:
        """
        Выполняет асинхронный запрос к API с использованием прокси
        
        Args:
            session: Сессия aiohttp
            contract: Объект контракта
            page: Номер страницы
            limit: Количество результатов на странице
            proxy: Прокси для запроса (добавляется автоматически декоратором)
        """
        if not contract.chain_id:
            return None
            
        api_key = self.api_key_manager.get_next_key()
        if not api_key:
            return None
            
        url = f"{chainbase_config.BASE_URL}{chainbase_config.HOLDERS_ENDPOINT}"
        
        params = {
            "chain_id": contract.chain_id,
            "limit": str(limit),
            "page": str(page),
            "contract_address": contract.address
        }
        
        headers = {"x-api-key": api_key}
        
        try:
            async with session.get(url, headers=headers, params=params, proxy=proxy) as response:
                json_response = await response.json()
                logger.debug(f"Использован API ключ: {api_key[:8]}... (страница {page})")
                return ApiResponse.from_response(response.status, json_response)
        except Exception as e:
            logger.error(f"Ошибка при получении держателей токена: {e}")
            return None

    async def _get_holders_async(self, contract: Contract, limit: int = chainbase_config.DEFAULT_LIMIT) -> List[Any]:
        """Асинхронно получает всех держателей токена"""
        # Проверяем статус обработки контракта
        processed_contract = self.db_manager.get_processed_contract(contract.address)
        existing_holders = []
        if processed_contract:
            if processed_contract.status == ParsingStatus.COMPLETED:
                logger.info(f"Контракт {contract.address} уже полностью обработан, пропускаем")
                return []
            existing_holders = processed_contract.holders

        # Получаем сохраненный прогресс
        progress = self.db_manager.get_parsing_progress(contract.address)
        start_page = 1
        
        if progress and progress.status == ParsingStatus.IN_PROGRESS:
            start_page = progress.current_page
            logger.info(f"Продолжаем парсинг контракта {contract.address} со страницы {start_page}")

        all_holders = []
        current_page = start_page
        semaphore = asyncio.Semaphore(thread_config.MAX_CONCURRENT_REQUESTS)
        
        async with aiohttp.ClientSession() as session:
            while not is_interrupted:
                async with semaphore:
                    logger.info(f"Получение страницы {current_page} для контракта {contract.address}")
                    response = await self._make_async_request(session, contract, page=current_page, limit=limit)
                
                if not response or not response.is_success:
                    error_msg = response.response.message if response and response.response else "Неизвестная ошибка"
                    logger.error(f"Ошибка при получении держателей: {error_msg}")
                    
                    # Сохраняем прогресс с ошибкой
                    progress = ParsingProgress(
                        contract_address=contract.address,
                        current_page=current_page,
                        total_pages=None,
                        last_processed_at=datetime.now(),
                        status=ParsingStatus.FAILED,
                        error_message=error_msg
                    )
                    self.db_manager.save_parsing_progress(progress)
                    break
                    
                if not isinstance(response.response, SuccessResponse):
                    logger.error("Неожиданный формат ответа")
                    break
                    
                all_holders.extend(response.response.data)
                
                # Сохраняем промежуточный прогресс и текущих холдеров
                progress = ParsingProgress(
                    contract_address=contract.address,
                    current_page=current_page,
                    total_pages=response.response.total_pages if hasattr(response.response, 'total_pages') else None,
                    last_processed_at=datetime.now(),
                    status=ParsingStatus.IN_PROGRESS
                )
                self.db_manager.save_parsing_progress(progress)
                
                # Сохраняем промежуточных холдеров
                if all_holders:
                    self._save_intermediate_holders(contract, all_holders, existing_holders, ParsingStatus.IN_PROGRESS)
                
                if not response.has_next_page:
                    break
                    
                current_page = response.response.next_page

        # Если парсинг был прерван или завершен с ошибкой, сохраняем текущий прогресс и холдеров
        if is_interrupted or (not response or not response.is_success):
            logger.info(f"Парсинг контракта {contract.address} прерван/завершен с ошибкой. Сохраняем прогресс и текущих холдеров...")
            
            # Сохраняем прогресс
            progress = ParsingProgress(
                contract_address=contract.address,
                current_page=current_page,
                total_pages=progress.total_pages if progress else None,
                last_processed_at=datetime.now(),
                status=ParsingStatus.IN_PROGRESS
            )
            self.db_manager.save_parsing_progress(progress)
            
            # Сохраняем полученных холдеров
            if all_holders:
                self._save_intermediate_holders(contract, all_holders, existing_holders, ParsingStatus.IN_PROGRESS)
            
            return all_holders

        # Если парсинг успешно завершен
        if all_holders or existing_holders:
            self._save_intermediate_holders(contract, all_holders, existing_holders, ParsingStatus.COMPLETED)
                
        return all_holders

    def _save_intermediate_holders(self, contract: Contract, new_holders: List[Any], 
                                 existing_holders: List[TokenHolder], status: ParsingStatus) -> None:
        """Сохраняет промежуточных холдеров в processed_contracts.json"""
        # Создаем множество существующих адресов
        existing_addresses = {h.address for h in existing_holders}
        
        # Создаем новые объекты TokenHolder только для новых адресов
        new_token_holders = [
            TokenHolder(
                address=holder if isinstance(holder, str) else holder.get("address"),
                balance="0"
            ) for holder in new_holders
            if (holder if isinstance(holder, str) else holder.get("address")) not in existing_addresses
        ]
        
        # Объединяем существующих и новых холдеров
        all_token_holders = existing_holders + new_token_holders
        
        processed_contract = ProcessedContract(
            address=contract.address,
            chain=contract.chain,
            processed_at=datetime.now(),
            holders_count=len(all_token_holders),
            holders=all_token_holders,
            status=status
        )
        
        self.db_manager.save_processed_contract(processed_contract)
        if new_token_holders:  # Добавляем в pending только новых холдеров
            self.db_manager.add_pending_holders(contract.address, new_token_holders)
        logger.info(f"Сохранена информация о контракте {contract.address} и его {len(all_token_holders)} холдерах (статус: {status.value})")

    def process_contract(self, task: ThreadTask[Contract]) -> List[Any]:
        """Обрабатывает один контракт в отдельном потоке"""
        contract = task.data
        logger.info(f"Начало обработки контракта {contract.address} в сети {contract.chain}")
        return asyncio.run(self._get_holders_async(contract))

    def process_all_contracts(self):
        """Обрабатывает все контракты параллельно"""
        # Получаем список незавершенных контрактов
        unfinished_contracts = self.db_manager.get_unfinished_contracts()
        if unfinished_contracts:
            logger.info(f"Найдено {len(unfinished_contracts)} незавершенных контрактов")
            
        # Загружаем все контракты
        all_contracts = self.contract_loader.load_contracts()
        
        # Приоритизируем незавершенные контракты
        contracts = []
        for contract in all_contracts:
            if contract.address in unfinished_contracts:
                contracts.insert(0, contract)
            else:
                contracts.append(contract)
        
        tasks = [ThreadTask(contract, f"contract_{i}") for i, contract in enumerate(contracts)]
        
        try:
            results = self.thread_manager.process_tasks(tasks, self.process_contract)
            
            for contract, holders in zip(contracts, results):
                if holders:  # Проверяем, были ли получены холдеры
                    logger.info(f"Всего получено {len(holders)} держателей для контракта {contract.address}")
                else:
                    logger.info(f"Нет новых держателей для контракта {contract.address}")
            
            return results
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания. Сохраняем прогресс...")
            return []

def main():
    """Точка входа в программу"""
    service = TokenHoldersService()
    service.process_all_contracts()

if __name__ == "__main__":
    main()

