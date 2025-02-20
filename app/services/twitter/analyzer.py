from typing import Dict, Optional
from dataclasses import dataclass

from app.services.twitter.model import TweetAnalysisResult

class Analyzer:
    """
    Класс для анализа твитов и определения статуса активности пользователей.
    """
    
    @staticmethod
    def analyze_user_activity(users_mentions: Dict[str, Dict]) -> Optional[TweetAnalysisResult]:
        """
        Анализирует активность пользователей на основе их упоминаний.
        
        Args:
            users_mentions (Dict[str, Dict]): Словарь с данными об активности пользователей
            
        Returns:
            Optional[TweetAnalysisResult]: Результат анализа или None, если нет твитов
        """
        total_tweets = sum(user['tweets_count'] for user in users_mentions.values())
        unique_users = len(users_mentions)
        
        if total_tweets == 0:
            return None

        result = TweetAnalysisResult(
            status=None,
            selected_user=None,
            user_data=None,
            total_tweets=total_tweets,
            unique_users=unique_users
        )

        return Analyzer._analyze_low_activity(users_mentions, total_tweets, unique_users) if total_tweets <= 3 \
            else Analyzer._analyze_high_activity(users_mentions, total_tweets, unique_users)

    @staticmethod
    def _analyze_low_activity(users_mentions: Dict[str, Dict], total_tweets: int, unique_users: int) -> TweetAnalysisResult:
        """
        Анализирует низкую активность (1-3 твита).
        
        Args:
            users_mentions (Dict[str, Dict]): Данные об активности пользователей
            total_tweets (int): Общее количество твитов
            unique_users (int): Количество уникальных пользователей
            
        Returns:
            TweetAnalysisResult: Результат анализа с определенным статусом и выбранным пользователем
        """
        result = TweetAnalysisResult(
            status=None,
            selected_user=None,
            user_data=None,
            total_tweets=total_tweets,
            unique_users=unique_users
        )

        if total_tweets == 1:
            result.status = 'YELLOW'
            result.selected_user = list(users_mentions.keys())[0]
        elif total_tweets == 2:
            if unique_users == 1:
                result.status = 'GREEN'
                result.selected_user = list(users_mentions.keys())[0]
            else:
                result.status = 'YELLOW'
                result.selected_user = list(users_mentions.keys())[0]
        elif unique_users == 1:
            result.status = 'GREEN'
            result.selected_user = list(users_mentions.keys())[0]
        elif unique_users == 3:
            result.status = 'RED'
        else:
            result.status = 'YELLOW'
            result.selected_user = max(users_mentions.items(), 
                                     key=lambda x: x[1]['tweets_count'])[0]

        if result.selected_user:
            result.user_data = users_mentions[result.selected_user]

        return result

    @staticmethod
    def _analyze_high_activity(users_mentions: Dict[str, Dict], total_tweets: int, unique_users: int) -> TweetAnalysisResult:
        """
        Анализирует высокую активность (4+ твита).
        
        Args:
            users_mentions (Dict[str, Dict]): Данные об активности пользователей
            total_tweets (int): Общее количество твитов
            unique_users (int): Количество уникальных пользователей
            
        Returns:
            TweetAnalysisResult: Результат анализа с определенным статусом и выбранным пользователем
        """
        result = TweetAnalysisResult(
            status=None,
            selected_user=None,
            user_data=None,
            total_tweets=total_tweets,
            unique_users=unique_users
        )

        if unique_users == total_tweets:
            result.status = 'RED'
        else:
            result.status = 'GREEN' if unique_users == 1 else 'YELLOW'
            result.selected_user = max(users_mentions.items(), 
                                     key=lambda x: x[1]['tweets_count'])[0]
            result.user_data = users_mentions[result.selected_user]

        return result 