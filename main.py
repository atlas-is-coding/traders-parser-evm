import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from app.services.contract.services.token_holders_service import TokenHoldersService
from app.services.balance.check_balance import BalanceChecker
from app.services.twitter.search import TwitterSearcher
from app.config.config import balance_config, chain_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Contract:
    address: str
    chain: str

@dataclass
class HolderData:
    address: str
    balance: float
    twitter: Optional[str] = None

class TraderParser:
    def __init__(self):
        self.holders_parser = TokenHoldersService()
        self.balance_checker = BalanceChecker()
        self.twitter_searcher = TwitterSearcher()
        
    async def parse_contracts(self) -> List[Contract]:
        contracts: List[Contract] = []
        contracts_file = Path("contracts.txt")
        
        if not contracts_file.exists():
            logger.error("Файл contracts.txt не найден!")
            return contracts
            
        with open(contracts_file, 'r') as file:
            for line in file:
                if line.strip():  # Пропускаем пустые строки
                    address, chain = line.strip().split()
                    contracts.append(Contract(address=address, chain=chain))
                
        return contracts
    
    async def process_contract(self, contract: Contract) -> List[HolderData]:
        holders_data: List[HolderData] = []
        
        # Получаем держателей контракта
        holders = await self.holders_parser.get_holders(
            contract_address=contract.address,
            chain_id=contract.chain
        )
        
        for holder in holders:
            # Проверяем баланс
            balance = await self.balance_checker.check_balance(
                address=holder.address,
                chain=contract.chain
            )
            
            # Пропускаем если баланс не в допустимом диапазоне
            if not (balance_config.MIN_BALANCE <= balance <= balance_config.MAX_BALANCE):
                continue
                
            # Ищем Twitter
            twitter = await self.twitter_searcher.search_twitter(holder.address)
            
            holders_data.append(HolderData(
                address=holder.address,
                balance=balance,
                twitter=twitter
            ))
            
        return holders_data

    async def run(self):
        try:
            contracts = await self.parse_contracts()
            logger.info(f"Загружено {len(contracts)} контрактов")
            
            all_holders_data: Dict[str, List[HolderData]] = {}
            
            for contract in contracts:
                logger.info(f"Обработка контракта {contract.address} в сети {contract.chain}")
                holders_data = await self.process_contract(contract)
                all_holders_data[contract.address] = holders_data
                
                logger.info(
                    f"Найдено {len(holders_data)} подходящих держателей "
                    f"для контракта {contract.address}"
                )
            
            return all_holders_data
                
        except Exception as e:
            logger.error(f"Произошла ошибка: {str(e)}")
            raise

async def main():
    parser = TraderParser()
    results = await parser.run()
    
    # Вывод результатов
    for contract_address, holders in results.items():
        print(f"\nКонтракт: {contract_address}")
        for holder in holders:
            print(f"Адрес: {holder.address}")
            print(f"Баланс: {holder.balance}")
            print(f"Twitter: {holder.twitter or 'Не найден'}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
