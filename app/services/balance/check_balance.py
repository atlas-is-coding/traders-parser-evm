import sys
import asyncio
from pathlib import Path
from typing import List, Union
from dataclasses import dataclass

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.manager.db_manager import DBManager
from app.services.manager.proxy_manager import ProxyManager
from app.services.balance.models import WalletBalance
from app.services.balance.dune_api import DuneApiKeyManager, DuneApiClient

@dataclass
class BalanceChecker:
    """Основной класс для проверки балансов кошельков."""
    db_manager: DBManager = DBManager()
    proxy_manager: ProxyManager = ProxyManager()

    async def check_balance(self, address: str, chain: str) -> float:
        """
        Проверяет баланс кошелька в определенной сети
        
        Args:
            address: Адрес кошелька
            chain: Сеть для проверки
            
        Returns:
            float: Баланс кошелька в USD
        """
        try:
            wallet_balance = await self.check_wallet_balance(address)
            return float(wallet_balance.balance)
        except Exception as e:
            print(f"Ошибка при проверке баланса {address}: {str(e)}")
            return 0.0

    def update_holder_balance(self, wallet_balance: WalletBalance) -> None:
        """
        Обновляет баланс холдера во всех контрактах в pending_holders.json
        
        Args:
            wallet_balance: Объект с новым балансом
        """
        data = self.db_manager._load_json(self.db_manager.pending_holders_file)
        pending = data.get("pending", {})
        updated = False

        for contract_address in pending:
            holders = pending[contract_address]
            for holder in holders:
                if holder["address"] == wallet_balance.address:
                    holder["balance"] = str(wallet_balance.balance)
                    holder["processed"] = False
                    holder["processed_at"] = None
                    updated = True

        if updated:
            self.db_manager._save_json(self.db_manager.pending_holders_file, data)

    async def check_wallet_balance(self, wallet_address: str) -> WalletBalance:
        """
        Проверяет баланс одного кошелька.
        
        Args:
            wallet_address: Адрес кошелька для проверки

        Returns:
            WalletBalance: Объект с информацией о балансе кошелька
        """
        api_key_manager = DuneApiKeyManager()
        async with DuneApiClient(api_key_manager) as client:
            wallet_balance = await client.get_wallet_balance(wallet_address)
            self.update_holder_balance(wallet_balance)
            return wallet_balance

    async def check_multiple_wallets(self, wallet_addresses: List[str]) -> List[Union[WalletBalance, Exception]]:
        """
        Проверяет балансы нескольких кошельков.
        
        Args:
            wallet_addresses: Список адресов кошельков

        Returns:
            List[Union[WalletBalance, Exception]]: Список результатов для каждого кошелька
        """
        api_key_manager = DuneApiKeyManager()
        async with DuneApiClient(api_key_manager) as client:
            tasks = [client.get_wallet_balance(address) for address in wallet_addresses]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обновляем балансы для успешных результатов
            for result in results:
                if isinstance(result, WalletBalance):
                    self.update_holder_balance(result)
                    
            return results

async def check_wallet_balance(wallet_address: str) -> WalletBalance:
    """
    Удобная функция-обертка для проверки баланса одного кошелька.
    
    Args:
        wallet_address: Адрес кошелька для проверки

    Returns:
        WalletBalance: Объект с информацией о балансе кошелька
    """
    checker = BalanceChecker()
    return await checker.check_wallet_balance(wallet_address)

async def check_multiple_wallets(wallet_addresses: List[str]) -> List[Union[WalletBalance, Exception]]:
    """
    Удобная функция-обертка для проверки балансов нескольких кошельков.
    
    Args:
        wallet_addresses: Список адресов кошельков

    Returns:
        List[Union[WalletBalance, Exception]]: Список результатов для каждого кошелька
    """
    checker = BalanceChecker()
    return await checker.check_multiple_wallets(wallet_addresses)

if __name__ == "__main__":
    wallets = [
        "0x0011834efe14dc0887b779bfd182110acf778668",
    ]
    
    results = asyncio.run(check_multiple_wallets(wallets))
    
    for result in results:
        if isinstance(result, WalletBalance):
            print(f"Баланс кошелька {result.address}: ${result.balance:.2f}")
        else:
            print(f"Ошибка при получении баланса: {result}")