import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Any, Optional
from app.config.config import chainbase_config
from app.services.contract.models import (
    Contract, TokenHolder, ProcessedContract, 
    ApiResponse, ParsingStatus, ParsingProgress
)
from app.services.contract.managers.api_key_manager import ApiKeyManager
from app.services.contract.managers.contract_loader import ContractLoader
from app.services.manager.thread_manager import ThreadManager, ThreadTask
from app.services.manager.db_manager import DBManager
from app.services.manager.proxy_manager import ProxyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenHoldersService:
    """Сервис для получения держателей токенов"""
    def __init__(self):
        self.api_key_manager = ApiKeyManager()
        self.contract_loader = ContractLoader()
        self.thread_manager = ThreadManager()
        self.db_manager = DBManager()
        self.proxy_manager = ProxyManager()
    
    async def get_holders(self, contract_address: str, chain_id: str) -> List[TokenHolder]:
        """
        Публичный метод для получения держателей токена
        
        Args:
            contract_address: Адрес контракта
            chain_id: ID сети
            
        Returns:
            List[TokenHolder]: Список держателей токена
        """
        contract = Contract(address=contract_address, chain=chain_id)
        holders_data = await self._get_holders_async(contract)
        
        return [
            TokenHolder(
                address=holder if isinstance(holder, str) else holder.get("address"),
                balance=holder.get("balance", "0") if not isinstance(holder, str) else "0"
            ) for holder in holders_data
        ]

    @ProxyManager.with_proxy
    async def _make_async_request(
        self, 
        session: aiohttp.ClientSession, 
        contract: Contract, 
        page: int = 1, 
        limit: int = chainbase_config.DEFAULT_LIMIT,
        proxy: str = None
    ) -> Optional[ApiResponse]:
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

    async def _get_holders_async(
        self, 
        contract: Contract, 
        limit: int = chainbase_config.DEFAULT_LIMIT
    ) -> List[Any]:
        """
        Асинхронно получает всех держателей токена
        
        Args:
            contract: Объект контракта
            limit: Количество результатов на странице
        """
        processed_contract = self.db_manager.get_processed_contract(contract.address)
        existing_holders = []
        
        if processed_contract:
            if processed_contract.status == ParsingStatus.COMPLETED:
                logger.info(f"Контракт {contract.address} уже полностью обработан, пропускаем")
                return []
            existing_holders = processed_contract.holders

        progress = self.db_manager.get_parsing_progress(contract.address)
        start_page = 1
        
        if progress and progress.status == ParsingStatus.IN_PROGRESS:
            start_page = progress.current_page
            logger.info(f"Продолжаем парсинг контракта {contract.address} со страницы {start_page}")

        all_holders = []
        current_page = start_page
        semaphore = asyncio.Semaphore(chainbase_config.MAX_CONCURRENT_REQUESTS)
        
        async with aiohttp.ClientSession() as session:
            while True:
                async with semaphore:
                    logger.info(f"Получение страницы {current_page} для контракта {contract.address}")
                    response = await self._make_async_request(
                        session, contract, page=current_page, limit=limit
                    )
                
                if not response or not response.is_success:
                    error_msg = response.response.message if response and response.response else "Неизвестная ошибка"
                    logger.error(f"Ошибка при получении держателей: {error_msg}")
                    
                    self._save_progress(
                        contract.address,
                        current_page,
                        None,
                        ParsingStatus.FAILED,
                        error_msg
                    )
                    break
                    
                all_holders.extend(response.response.data)
                
                self._save_progress(
                    contract.address,
                    current_page,
                    getattr(response.response, 'total_pages', None),
                    ParsingStatus.IN_PROGRESS
                )
                
                self._save_holders(
                    contract, 
                    all_holders, 
                    existing_holders, 
                    ParsingStatus.IN_PROGRESS
                )
                
                if not response.has_next_page:
                    break
                    
                current_page = response.response.next_page

        if all_holders or existing_holders:
            self._save_holders(contract, all_holders, existing_holders, ParsingStatus.COMPLETED)
                
        return all_holders

    def _save_progress(
        self,
        contract_address: str,
        current_page: int,
        total_pages: Optional[int],
        status: ParsingStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Сохраняет прогресс парсинга"""
        progress = ParsingProgress(
            contract_address=contract_address,
            current_page=current_page,
            total_pages=total_pages,
            last_processed_at=datetime.now(),
            status=status,
            error_message=error_message
        )
        self.db_manager.save_parsing_progress(progress)

    def _save_holders(
        self, 
        contract: Contract, 
        new_holders: List[Any], 
        existing_holders: List[TokenHolder], 
        status: ParsingStatus
    ) -> None:
        """Сохраняет держателей токенов"""
        existing_addresses = {h.address for h in existing_holders}
        
        new_token_holders = [
            TokenHolder(
                address=holder if isinstance(holder, str) else holder.get("address"),
                balance="0"
            ) for holder in new_holders
            if (holder if isinstance(holder, str) else holder.get("address")) not in existing_addresses
        ]
        
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
        if new_token_holders:
            self.db_manager.add_pending_holders(contract.address, new_token_holders)
        
        logger.info(
            f"Сохранена информация о контракте {contract.address} "
            f"и его {len(all_token_holders)} холдерах (статус: {status})"
        )

    def process_contract(self, task: ThreadTask[Contract]) -> List[Any]:
        """Обрабатывает один контракт в отдельном потоке"""
        contract = task.data
        logger.info(f"Начало обработки контракта {contract.address} в сети {contract.chain}")
        return asyncio.run(self._get_holders_async(contract))

    def process_all_contracts(self) -> List[List[Any]]:
        """Обрабатывает все контракты параллельно"""
        unfinished_contracts = self.db_manager.get_unfinished_contracts()
        if unfinished_contracts:
            logger.info(f"Найдено {len(unfinished_contracts)} незавершенных контрактов")
            
        all_contracts = self.contract_loader.load_contracts()
        
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
                if holders:
                    logger.info(f"Всего получено {len(holders)} держателей для контракта {contract.address}")
                else:
                    logger.info(f"Нет новых держателей для контракта {contract.address}")
            
            return results
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания. Сохраняем прогресс...")
            return [] 