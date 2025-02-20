from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import json
import os
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ParsingStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ParsingProgress:
    contract_address: str
    current_page: int
    total_pages: Optional[int]
    last_processed_at: datetime
    status: ParsingStatus
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "contract_address": self.contract_address,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "last_processed_at": self.last_processed_at.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsingProgress':
        return cls(
            contract_address=data["contract_address"],
            current_page=data["current_page"],
            total_pages=data.get("total_pages"),
            last_processed_at=datetime.fromisoformat(data["last_processed_at"]),
            status=ParsingStatus(data["status"]),
            error_message=data.get("error_message")
        )

@dataclass
class TokenHolder:
    address: str
    balance: str
    processed: bool = False
    processed_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenHolder':
        """Создает объект TokenHolder из словаря"""
        if isinstance(data, str):
            return cls(address=data, balance="0")
            
        return cls(
            address=str(data.get("address", "")),
            balance=str(data.get("balance", "0")),
            processed=bool(data.get("processed", False)),
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None
        )

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "address": self.address,
            "balance": self.balance,
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }

@dataclass
class ProcessedContract:
    address: str
    chain: str
    processed_at: datetime
    holders_count: int
    holders: List[TokenHolder]
    status: ParsingStatus = ParsingStatus.COMPLETED

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "chain": self.chain,
            "processed_at": self.processed_at.isoformat(),
            "holders_count": self.holders_count,
            "holders": [holder.to_dict() for holder in self.holders],
            "status": self.status.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['ProcessedContract']:
        try:
            holders_data = data.get("holders", [])
            holders = [TokenHolder.from_dict(holder_data) for holder_data in holders_data]
            
            return cls(
                address=str(data.get("address", "")),
                chain=str(data.get("chain", "")),
                processed_at=datetime.fromisoformat(data["processed_at"]) if isinstance(data.get("processed_at"), str) else datetime.now(),
                holders_count=int(data.get("holders_count", 0)),
                holders=holders,
                status=ParsingStatus(data.get("status", ParsingStatus.COMPLETED.value))
            )
        except Exception as e:
            logger.error(f"Ошибка при создании ProcessedContract из данных: {e}")
            return None

class DBManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "db"
        self.db_path = Path(db_path)
        self.processed_contracts_file = self.db_path / "processed_contracts.json"
        self.pending_holders_file = self.db_path / "pending_holders.json"
        self.parsing_progress_file = self.db_path / "parsing_progress.json"
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Инициализация файлов базы данных"""
        self.db_path.mkdir(exist_ok=True)
        
        if not self.processed_contracts_file.exists():
            self._save_json(self.processed_contracts_file, {"contracts": []})
            
        if not self.pending_holders_file.exists():
            self._save_json(self.pending_holders_file, {"pending": {}})
            
        if not self.parsing_progress_file.exists():
            self._save_json(self.parsing_progress_file, {"progress": {}})

    def _load_json(self, file_path: Path) -> dict:
        """Загрузка данных из JSON файла"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return self._get_default_data(file_path)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_data(file_path)

    def _get_default_data(self, file_path: Path) -> dict:
        """Получение структуры данных по умолчанию для файла"""
        if file_path == self.processed_contracts_file:
            return {"contracts": []}
        elif file_path == self.pending_holders_file:
            return {"pending": {}}
        elif file_path == self.parsing_progress_file:
            return {"progress": {}}
        return {}

    def _save_json(self, file_path: Path, data: Union[Dict, List]) -> None:
        """Сохранение данных в JSON файл"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4, default=str)
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в {file_path}: {e}")

    def save_parsing_progress(self, progress: ParsingProgress) -> None:
        """Сохранение прогресса парсинга контракта"""
        try:
            data = self._load_json(self.parsing_progress_file)
            data["progress"][progress.contract_address] = progress.to_dict()
            self._save_json(self.parsing_progress_file, data)
        except Exception as e:
            logger.error(f"Ошибка при сохранении прогресса парсинга для контракта {progress.contract_address}: {e}")

    def get_parsing_progress(self, contract_address: str) -> Optional[ParsingProgress]:
        """Получение прогресса парсинга контракта"""
        try:
            data = self._load_json(self.parsing_progress_file)
            progress_data = data["progress"].get(contract_address)
            if progress_data:
                return ParsingProgress.from_dict(progress_data)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении прогресса парсинга для контракта {contract_address}: {e}")
            return None

    def remove_parsing_progress(self, contract_address: str) -> None:
        """Удаление информации о прогрессе парсинга контракта"""
        try:
            data = self._load_json(self.parsing_progress_file)
            if contract_address in data["progress"]:
                del data["progress"][contract_address]
                self._save_json(self.parsing_progress_file, data)
        except Exception as e:
            logger.error(f"Ошибка при удалении прогресса парсинга для контракта {contract_address}: {e}")

    def get_unfinished_contracts(self) -> List[str]:
        """Получение списка контрактов с незавершенным парсингом"""
        try:
            data = self._load_json(self.parsing_progress_file)
            return [
                addr for addr, progress in data["progress"].items()
                if ParsingStatus(progress["status"]) in [ParsingStatus.IN_PROGRESS, ParsingStatus.FAILED]
            ]
        except Exception as e:
            logger.error(f"Ошибка при получении списка незавершенных контрактов: {e}")
            return []

    def save_processed_contract(self, contract: ProcessedContract) -> None:
        """Сохранение обработанного контракта"""
        try:
            data = self._load_json(self.processed_contracts_file)
            contracts = data.get("contracts", [])
            
            # Проверяем, существует ли уже контракт
            contract_exists = False
            for i, existing_contract in enumerate(contracts):
                if existing_contract.get("address") == contract.address:
                    # Получаем существующий контракт
                    existing = ProcessedContract.from_dict(existing_contract)
                    if existing:
                        # Создаем множество существующих адресов
                        existing_addresses = {h.address for h in existing.holders}
                        # Добавляем только новых холдеров
                        new_holders = [h for h in contract.holders if h.address not in existing_addresses]
                        
                        # Объединяем списки холдеров
                        all_holders = existing.holders + new_holders
                        
                        # Обновляем контракт
                        updated_contract = ProcessedContract(
                            address=contract.address,
                            chain=contract.chain,
                            processed_at=datetime.now(),
                            holders_count=len(all_holders),
                            holders=all_holders,
                            status=contract.status
                        )
                        contracts[i] = updated_contract.to_dict()
                    else:
                        contracts[i] = contract.to_dict()
                    contract_exists = True
                    break
                    
            if not contract_exists:
                contracts.append(contract.to_dict())
                
            self._save_json(self.processed_contracts_file, {"contracts": contracts})
            
            # Если контракт полностью обработан, удаляем информацию о прогрессе
            if contract.status == ParsingStatus.COMPLETED:
                self.remove_parsing_progress(contract.address)
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении контракта {contract.address}: {e}")
            raise

    def add_pending_holders(self, contract_address: str, holders: List[TokenHolder]) -> None:
        """Добавление холдеров в очередь на обработку"""
        try:
            data = self._load_json(self.pending_holders_file)
            pending = data.get("pending", {})
            
            # Объединяем существующих и новых холдеров
            existing_holders = self.get_pending_holders(contract_address)
            existing_addresses = {h.address for h in existing_holders}
            
            # Добавляем только новых холдеров
            new_holders = [h for h in holders if h.address not in existing_addresses]
            all_holders = existing_holders + new_holders
            
            pending[contract_address] = [holder.to_dict() for holder in all_holders]
            self._save_json(self.pending_holders_file, {"pending": pending})
        except Exception as e:
            logger.error(f"Ошибка при добавлении холдеров для контракта {contract_address}: {e}")

    def get_pending_holders(self, contract_address: str) -> List[TokenHolder]:
        """Получение списка холдеров, ожидающих обработки"""
        try:
            data = self._load_json(self.pending_holders_file)
            pending = data.get("pending", {})
            
            if contract_address in pending:
                return [TokenHolder.from_dict(holder_data) for holder_data in pending[contract_address]]
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении холдеров для контракта {contract_address}: {e}")
            return []

    def get_processed_contract(self, address: str) -> Optional[ProcessedContract]:
        """Получение информации об обработанном контракте"""
        try:
            data = self._load_json(self.processed_contracts_file)
            contracts = data.get("contracts", [])
            
            for contract_data in contracts:
                if contract_data.get("address") == address:
                    return ProcessedContract.from_dict(contract_data)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении контракта {address}: {e}")
            return None

    def is_contract_processed(self, address: str) -> bool:
        """Проверка, был ли контракт уже обработан"""
        contract = self.get_processed_contract(address)
        return contract is not None and contract.status == ParsingStatus.COMPLETED 