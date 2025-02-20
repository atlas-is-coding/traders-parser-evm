import asyncio
import sys
from typing import Optional
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.twitter.api import search_tweets, analyze_tweets

class TwitterSearcher:
    """Класс для поиска Twitter аккаунтов по адресу"""
    
    async def search_twitter(self, address: str) -> Optional[str]:
        """
        Поиск Twitter аккаунта по адресу кошелька
        
        Args:
            address: Адрес кошелька для поиска
            
        Returns:
            Optional[str]: Twitter аккаунт если найден, иначе None
        """
        try:
            tweets = await search_tweets(address)
            if not tweets:
                return None
                
            analysis_result = await analyze_tweets(tweets)
            if analysis_result and analysis_result.get('twitter_username'):
                return analysis_result['twitter_username']
                
            return None
            
        except Exception as e:
            print(f"Ошибка при поиске Twitter: {e}")
            return None

# Для тестирования
async def main():
    """
    Основная функция для демонстрации работы с Twitter API.
    """
    searcher = TwitterSearcher()
    address = "9p6HKAFAcy6NZDzPh9HDYEjbpxcrTxi5QMMAXS5CTQG4"
    
    result = await searcher.search_twitter(address)
    print(f"Найденный Twitter аккаунт: {result}")

if __name__ == "__main__":
    asyncio.run(main())
