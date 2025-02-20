from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum

class ParsingStatus(Enum):
    """Статусы парсинга"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

@dataclass
class ErrorResponse:
    """Модель для ответа с ошибкой"""
    code: int
    message: str

@dataclass
class SuccessResponse:
    """Модель для успешного ответа"""
    code: int
    message: str
    data: List[Any]
    next_page: Optional[int]
    count: int

@dataclass
class ApiResponse:
    """Обертка для ответа API"""
    status_code: int
    response: Optional[SuccessResponse | ErrorResponse] = None

    @classmethod
    def from_response(cls, status_code: int, data: dict) -> 'ApiResponse':
        """Фабричный метод для создания объекта ApiResponse из ответа API"""
        if 200 <= status_code < 300:
            return cls(
                status_code=status_code,
                response=SuccessResponse(
                    code=data.get('code', 0),
                    message=data.get('message', ''),
                    data=data.get('data', []),
                    next_page=data.get('next_page'),
                    count=data.get('count', 0)
                )
            )
        else:
            return cls(
                status_code=status_code,
                response=ErrorResponse(
                    code=data.get('code', 0),
                    message=data.get('message', '')
                )
            )

    @property
    def is_success(self) -> bool:
        """Проверяет, является ли ответ успешным"""
        return 200 <= self.status_code < 300

    @property
    def has_next_page(self) -> bool:
        """Проверяет, есть ли следующая страница"""
        if not self.is_success or not isinstance(self.response, SuccessResponse):
            return False
        return self.response.next_page is not None

@dataclass
class Contract:
    """Модель контракта"""
    address: str
    chain: str
    
    @property
    def chain_id(self) -> Optional[str]:
        from app.utils.get_chain import get_chain_id
        return get_chain_id(self.chain)

@dataclass
class TokenHolder:
    """Модель держателя токенов"""
    address: str
    balance: str

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "address": self.address,
            "balance": self.balance
        }

@dataclass
class ProcessedContract:
    """Модель обработанного контракта"""
    address: str
    chain: str
    processed_at: datetime
    holders_count: int
    holders: List[TokenHolder]
    status: ParsingStatus

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "address": self.address,
            "chain": self.chain,
            "processed_at": self.processed_at.isoformat(),
            "holders_count": self.holders_count,
            "holders": [holder.to_dict() for holder in self.holders],
            "status": self.status.value
        }

@dataclass
class ParsingProgress:
    """Модель прогресса парсинга"""
    contract_address: str
    current_page: int
    total_pages: Optional[int]
    last_processed_at: datetime
    status: ParsingStatus
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "contract_address": self.contract_address,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "last_processed_at": self.last_processed_at.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message
        }
