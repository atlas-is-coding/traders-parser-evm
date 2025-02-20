import os
import logging
from typing import List
from pathlib import Path
from app.services.contract.models import Contract

ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContractLoader:
    """Загрузчик контрактов из файла"""
    def __init__(self, contracts_file: str = None):
        if contracts_file is None:
            contracts_file = os.path.join(ROOT_DIR, "contracts.txt")
        self.contracts_file = contracts_file
    
    def load_contracts(self) -> List[Contract]:
        """
        Загружает контракты из файла
        
        Returns:
            List[Contract]: Список контрактов
        """
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