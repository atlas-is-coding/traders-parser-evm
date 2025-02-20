from enum import Enum, auto

class AnalysisStatus(Enum):
    """
    Статусы анализа твитов.
    """
    GREEN = auto()
    YELLOW = auto()
    RED = auto()

    @classmethod
    def from_str(cls, status: str) -> 'AnalysisStatus':
        """
        Создает enum из строкового представления.
        
        Args:
            status (str): Строковое представление статуса
            
        Returns:
            AnalysisStatus: Соответствующий enum
            
        Raises:
            ValueError: Если статус неизвестен
        """
        try:
            return cls[status.upper()]
        except KeyError:
            raise ValueError(f"Неизвестный статус анализа: {status}")

# Константы для Twitter API
TWITTER_API_BASE_URL = "https://x.com/i/api/graphql"
TWITTER_SEARCH_ENDPOINT = "KI9jCXUx3Ymt-hDKLOZb9Q/SearchTimeline"
DEFAULT_TWEET_COUNT = 20

# Константы для анализа твитов
LOW_ACTIVITY_THRESHOLD = 3
SINGLE_USER_THRESHOLD = 1 