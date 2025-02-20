import json
import urllib.parse
from typing import Dict, List, Optional

import aiohttp

from app.services.twitter.model import TweetAnalysisResult, TwitterResponse
from app.services.manager.proxy_manager import ProxyManager
from app.services.manager.headers_manager import HeaderManager, with_header_management
from app.services.twitter.analyzer import Analyzer

class TwitterSearchAPI:
    """
    Класс для работы с Twitter Search API.
    """
    
    def __init__(self):
        self.base_url = "https://x.com/i/api/graphql/KI9jCXUx3Ymt-hDKLOZb9Q/SearchTimeline"
        self.proxy_manager = ProxyManager()
        self.header_manager = HeaderManager()

    def _build_url(self, query: str) -> str:
        """
        Построение URL для поиска.
        
        Args:
            query (str): Поисковый запрос
            
        Returns:
            str: Полный URL для запроса
        """
        variables = {
            "rawQuery": query,
            "count": 20,
            "querySource": "typed_query",
            "product": "Latest"
        }
        
        features = {
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "premium_content_api_read_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            "responsive_web_grok_analyze_post_followups_enabled": True,
            "responsive_web_jetfuel_frame": False,
            "responsive_web_grok_share_attachment_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_grok_image_annotation_enabled": True,
            "responsive_web_enhance_cards_enabled": False
        }

        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(features)
        }

        return f"{self.base_url}?{urllib.parse.urlencode(params)}"

    @ProxyManager.with_proxy
    @with_header_management()
    async def search(self, headers: dict, query: str, proxy: str = None) -> TwitterResponse:
        """
        Выполнение поиска в Twitter.
        
        Args:
            headers (dict): Заголовки запроса
            query (str): Поисковый запрос
            proxy (str, optional): Прокси-сервер
            
        Returns:
            TwitterResponse: Результат поиска
            
        Raises:
            Exception: При ошибке API или некорректном ответе
        """
        url = self._build_url(query)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, proxy=proxy) as response:
                if response.status != 200:
                    raise Exception(f"Ошибка API Twitter: {response.status}")
                    
                data = await response.json()
                if 'data' not in data:
                    raise Exception("Некорректный ответ API: отсутствует поле 'data'")
                
                if 'responseObjects' not in data:
                    data['responseObjects'] = {}
                    
                return TwitterResponse(**data)

    @staticmethod
    async def process_tweets(tweets: List[Dict]) -> Dict[str, Dict]:
        """
        Обработка твитов и извлечение информации о пользователях.
        
        Args:
            tweets (List[Dict]): Список твитов
            
        Returns:
            Dict[str, Dict]: Словарь с информацией о пользователях
        """
        users_mentions = {}
        
        for entry in tweets:
            try:
                if entry['entryId'].startswith('cursor-top'):
                    break
                    
                result = entry['content']['itemContent']['tweet_results']['result']
                core = result['core']
                core_result = core['user_results']['result']
                    
                twitter_username = core_result['legacy']['screen_name']
                users_mentions[twitter_username] = {
                    'is_dm_open': core_result['legacy']['can_dm'],
                    'followers_count': core_result['legacy']['followers_count'],
                    'tweets_count': users_mentions.get(twitter_username, {}).get('tweets_count', 0) + 1
                }
            except (KeyError, TypeError):
                continue
                
        return users_mentions

async def search_tweets(query: str) -> List[Dict]:
    """
    Удобная функция для выполнения поиска в Twitter.
    
    Args:
        query (str): Поисковый запрос
        
    Returns:
        List[Dict]: Список найденных твитов
    """
    api = TwitterSearchAPI()
    response = await api.search(query=query)
    return response.data['search_by_raw_query']['search_timeline']['timeline']['instructions'][0]['entries']

async def analyze_tweets(tweets: List[Dict]) -> Optional[TweetAnalysisResult]:
    """
    Анализ твитов и определение статуса активности.
    
    Args:
        tweets (List[Dict]): Список твитов для анализа
        
    Returns:
        Optional[TweetAnalysisResult]: Результат анализа
    """
    api = TwitterSearchAPI()
    users_mentions = await api.process_tweets(tweets)
    return Analyzer.analyze_user_activity(users_mentions) 