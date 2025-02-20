import json
from pathlib import Path
import sys
import time
import aiohttp
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from functools import wraps

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config.config import proxy_config

@dataclass
class ProxyStatus:
    url: str
    is_working: bool = True
    fails_count: int = 0
    last_used: float = field(default_factory=time.time)
    cooldown_until: Optional[float] = None
    requests_count: int = 0

class ProxyManager:
    def __init__(self):
        self.config = proxy_config
        self.proxies: Dict[str, ProxyStatus] = {}
        self.current_proxy_index = 0
        self._load_proxies()
        self._load_proxy_data()

    def _load_proxies(self) -> None:
        """Загрузка прокси из файла конфигурации"""
        try:
            with open('config/proxies.txt', 'r') as f:
                proxy_list = [line.strip() for line in f.readlines() if line.strip()]
                
            for proxy in proxy_list:
                if not proxy.startswith('http'):
                    proxy = f'http://{proxy}'
                if proxy not in self.proxies:
                    self.proxies[proxy] = ProxyStatus(url=proxy)
        except FileNotFoundError:
            raise Exception("Файл с прокси не найден")

    def _load_proxy_data(self) -> None:
        """Загрузка данных о состоянии прокси"""
        os.makedirs('.scratch', exist_ok=True)
        try:
            with open(self.config.DATA_FILE, 'r') as f:
                data = json.load(f)
                for proxy_url, status in data.items():
                    if proxy_url in self.proxies:
                        self.proxies[proxy_url] = ProxyStatus(**status)
        except (FileNotFoundError, json.JSONDecodeError):
            self._save_proxy_data()

    def _save_proxy_data(self) -> None:
        """Сохранение данных о состоянии прокси"""
        with open(self.config.DATA_FILE, 'w') as f:
            json.dump({k: v.__dict__ for k, v in self.proxies.items()}, f, indent=2)

    def _get_next_available_proxy(self) -> Optional[str]:
        """Получение следующего доступного прокси"""
        attempts = len(self.proxies)
        while attempts > 0:
            attempts -= 1
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            proxy_url = list(self.proxies.keys())[self.current_proxy_index]
            proxy_status = self.proxies[proxy_url]
            
            if not proxy_status.is_working:
                continue
                
            if proxy_status.cooldown_until and time.time() < proxy_status.cooldown_until:
                continue
                
            if proxy_status.requests_count >= self.config.MAX_REQUESTS_PER_PROXY:
                self._set_cooldown(proxy_url)
                continue
                
            return proxy_url
            
        return None

    def _set_cooldown(self, proxy_url: str) -> None:
        """Установка cooldown для прокси"""
        proxy_status = self.proxies[proxy_url]
        proxy_status.cooldown_until = time.time() + self.config.COOLDOWN_TIME
        proxy_status.requests_count = 0
        self._save_proxy_data()

    def _handle_proxy_error(self, proxy_url: str) -> None:
        """Обработка ошибки прокси"""
        proxy_status = self.proxies[proxy_url]
        proxy_status.fails_count += 1
        
        if proxy_status.fails_count >= self.config.MAX_FAILS:
            proxy_status.is_working = False
            self._set_cooldown(proxy_url)
            
        self._save_proxy_data()

    def _handle_proxy_success(self, proxy_url: str) -> None:
        """Обработка успешного использования прокси"""
        proxy_status = self.proxies[proxy_url]
        proxy_status.fails_count = 0
        proxy_status.requests_count += 1
        proxy_status.last_used = time.time()
        self._save_proxy_data()

    @classmethod
    def with_proxy(cls, func):
        """Декоратор для автоматического управления прокси"""
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'proxy_manager'):
                self.proxy_manager = cls()
            
            proxy_url = self.proxy_manager._get_next_available_proxy()
            if not proxy_url:
                raise Exception("Нет доступных прокси")

            try:
                kwargs['proxy'] = proxy_url
                result = await func(self, *args, **kwargs)
                self.proxy_manager._handle_proxy_success(proxy_url)
                return result
            except Exception as e:
                self.proxy_manager._handle_proxy_error(proxy_url)
                raise e

        return wrapper

    async def check_proxy(self, proxy_url: str) -> bool:
        """Проверка работоспособности прокси"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org', proxy=proxy_url, timeout=10) as response:
                    return response.status == 200
        except:
            return False

    async def validate_all_proxies(self) -> None:
        """Проверка всех прокси на работоспособность"""
        tasks = []
        for proxy_url in self.proxies:
            tasks.append(self.check_proxy(proxy_url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for proxy_url, is_working in zip(self.proxies.keys(), results):
            self.proxies[proxy_url].is_working = isinstance(is_working, bool) and is_working
        
        self._save_proxy_data()

    def get_proxy_stats(self) -> Dict[str, Dict]:
        """Получение статистики использования прокси"""
        return {
            proxy_url: {
                "is_working": status.is_working,
                "fails_count": status.fails_count,
                "requests_count": status.requests_count,
                "cooldown_until": status.cooldown_until
            }
            for proxy_url, status in self.proxies.items()
        }

async def test_proxy_manager():
    """
    Тестовая функция для демонстрации работы ProxyManager
    """
    proxy_manager = ProxyManager()
    
    # Проверяем все прокси на работоспособность
    print("\n1. Проверка работоспособности всех прокси:")
    await proxy_manager.validate_all_proxies()
    stats = proxy_manager.get_proxy_stats()
    for proxy, stat in stats.items():
        print(f"Прокси {proxy}: {'Работает' if stat['is_working'] else 'Не работает'}")
    
    # Тестируем отправку запросов через прокси
    @proxy_manager.with_proxy
    async def test_request(self, url: str, proxy: str = None):
        print(f"\nОтправка запроса через прокси: {proxy}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, proxy=proxy, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
                    return f"Ошибка: статус {response.status}"
            except Exception as e:
                return f"Ошибка: {str(e)}"
    
    # Делаем несколько тестовых запросов
    print("\n2. Тестовые запросы:")
    test_urls = [
        "https://api.ipify.org",
        "https://httpbin.org/ip",
        "https://ifconfig.me"
    ]
    
    for url in test_urls:
        try:
            result = await test_request(proxy_manager, url)
            print(f"URL: {url}")
            print(f"Результат: {result}")
        except Exception as e:
            print(f"Ошибка при запросе к {url}: {str(e)}")
    
    # Проверяем статистику использования прокси
    print("\n3. Статистика использования прокси:")
    stats = proxy_manager.get_proxy_stats()
    for proxy, stat in stats.items():
        print(f"\nПрокси: {proxy}")
        print(f"Работает: {'Да' if stat['is_working'] else 'Нет'}")
        print(f"Количество ошибок: {stat['fails_count']}")
        print(f"Количество запросов: {stat['requests_count']}")
        if stat['cooldown_until']:
            cooldown_remaining = stat['cooldown_until'] - time.time()
            if cooldown_remaining > 0:
                print(f"Cooldown: {cooldown_remaining:.2f} секунд")
            else:
                print("Cooldown: завершен")

if __name__ == "__main__":
    # Запускаем тестовую функцию
    asyncio.run(test_proxy_manager())
