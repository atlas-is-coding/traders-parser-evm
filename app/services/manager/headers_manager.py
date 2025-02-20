from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional
import asyncio
from functools import wraps

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.config import HeaderConfig
from app.config.twitter_headers import TWITTER_BASE_HEADERS

@dataclass
class HeaderStatus:
    """Модель для хранения статуса заголовка"""
    is_active: bool = True
    fail_count: int = 0
    last_used: datetime = None
    cooldown_until: Optional[datetime] = None
    total_requests: int = 0
    last_success: Optional[datetime] = None

class HeaderManager:
    def __init__(self):
        self.headers = TWITTER_BASE_HEADERS
        self.config = HeaderConfig()
        self.headers_status: Dict[int, HeaderStatus] = {}
        self.current_header_index = 0
        self._lock = asyncio.Lock()
        
        # Создаем директорию .scratch если она не существует
        os.makedirs('.scratch', exist_ok=True)
        
        # Инициализируем статусы заголовков
        self._init_headers_status()
        
    def _init_headers_status(self):
        """Инициализация статусов заголовков"""
        if os.path.exists(self.config.DATA_FILE):
            self._load_headers_status()
        else:
            self.headers_status = {
                i: HeaderStatus() for i in range(len(self.headers))
            }
            self._save_headers_status()

    def _load_headers_status(self):
        """Загрузка статусов заголовков из файла"""
        try:
            with open(self.config.DATA_FILE, 'r') as f:
                data = json.load(f)
                self.headers_status = {
                    int(k): HeaderStatus(
                        is_active=v['is_active'],
                        fail_count=v['fail_count'],
                        last_used=datetime.fromisoformat(v['last_used']) if v['last_used'] else None,
                        cooldown_until=datetime.fromisoformat(v['cooldown_until']) if v['cooldown_until'] else None,
                        total_requests=v['total_requests'],
                        last_success=datetime.fromisoformat(v['last_success']) if v['last_success'] else None
                    ) for k, v in data.items()
                }
        except (FileNotFoundError, json.JSONDecodeError):
            self.headers_status = {
                i: HeaderStatus() for i in range(len(self.headers))
            }

    def _save_headers_status(self):
        """Сохранение статусов заголовков в файл"""
        data = {
            str(k): {
                'is_active': v.is_active,
                'fail_count': v.fail_count,
                'last_used': v.last_used.isoformat() if v.last_used else None,
                'cooldown_until': v.cooldown_until.isoformat() if v.cooldown_until else None,
                'total_requests': v.total_requests,
                'last_success': v.last_success.isoformat() if v.last_success else None
            } for k, v in self.headers_status.items()
        }
        with open(self.config.DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    async def get_next_header(self) -> dict:
        """Получение следующего доступного заголовка"""
        async with self._lock:
            start_index = self.current_header_index
            while True:
                status = self.headers_status[self.current_header_index]
                
                # Проверяем, можно ли использовать текущий заголовок
                if (status.is_active and 
                    (status.cooldown_until is None or datetime.now() > status.cooldown_until) and
                    status.total_requests < self.config.MAX_REQUESTS_PER_HEADER):
                    
                    # Обновляем статус
                    status.last_used = datetime.now()
                    status.total_requests += 1
                    self._save_headers_status()
                    
                    # Возвращаем заголовок
                    header = self.headers[self.current_header_index]
                    
                    # Обновляем индекс для следующего запроса
                    self.current_header_index = (self.current_header_index + 1) % len(self.headers)
                    
                    return header
                
                # Переходим к следующему заголовку
                self.current_header_index = (self.current_header_index + 1) % len(self.headers)
                
                # Если мы проверили все заголовки и не нашли подходящий
                if self.current_header_index == start_index:
                    await asyncio.sleep(1)  # Небольшая задержка перед повторной попыткой

    async def mark_header_failed(self, header_index: int):
        """Отметить заголовок как неудачный"""
        async with self._lock:
            status = self.headers_status[header_index]
            status.fail_count += 1
            
            if status.fail_count >= self.config.MAX_FAILS:
                status.is_active = False
                status.cooldown_until = datetime.now().timestamp() + self.config.COOLDOWN_TIME
            
            self._save_headers_status()

    async def mark_header_success(self, header_index: int):
        """Отметить успешное использование заголовка"""
        async with self._lock:
            status = self.headers_status[header_index]
            status.fail_count = 0
            status.last_success = datetime.now()
            self._save_headers_status()

def with_header_management():
    """Декоратор для автоматического управления заголовками"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            header = await self.header_manager.get_next_header()
            header_index = self.header_manager.headers.index(header)
            
            try:
                result = await func(self, header, *args, **kwargs)
                await self.header_manager.mark_header_success(header_index)
                return result
            except Exception as e:
                await self.header_manager.mark_header_failed(header_index)
                raise e
                
        return wrapper
    return decorator

async def test_header_manager():
    """Тестовая функция для демонстрации работы HeaderManager"""
    
    class TestAPI:
        def __init__(self):
            self.header_manager = HeaderManager()
            
        @with_header_management()
        async def make_request(self, header, success: bool = True):
            """Имитация запроса к API
            
            Args:
                header (dict): Заголовки для запроса
                success (bool): Флаг успешности запроса
            """
            print(f"\nИспользуется заголовок с User-Agent: {header.get('user-agent', 'Не указан')}")
            
            if not success:
                raise Exception("Симуляция ошибки запроса")
            
            return {"status": "success"}

    # Создаем экземпляр тестового API
    api = TestAPI()
    
    # Тест успешных запросов
    print("\n=== Тест успешных запросов ===")
    for _ in range(3):
        try:
            result = await api.make_request(success=True)
            print(f"Результат запроса: {result}")
        except Exception as e:
            print(f"Ошибка: {e}")
        await asyncio.sleep(0.5)
    
    # Тест неудачных запросов
    print("\n=== Тест неудачных запросов ===")
    for _ in range(5):
        try:
            await api.make_request(success=False)
        except Exception as e:
            print(f"Ожидаемая ошибка: {e}")
        await asyncio.sleep(0.5)
    
    # Проверка статуса заголовков
    print("\n=== Статус заголовков ===")
    for idx, status in api.header_manager.headers_status.items():
        print(f"\nЗаголовок {idx}:")
        print(f"Активен: {status.is_active}")
        print(f"Количество ошибок: {status.fail_count}")
        print(f"Последнее использование: {status.last_used}")
        print(f"Кулдаун до: {status.cooldown_until}")
        print(f"Всего запросов: {status.total_requests}")

if __name__ == "__main__":
    # Запускаем тестовую функцию
    asyncio.run(test_header_manager())
