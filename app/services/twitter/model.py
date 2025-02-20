from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ImageSize:
    h: int
    w: int
    resize: str

@dataclass 
class ImageSizes:
    large: ImageSize
    medium: ImageSize
    small: ImageSize
    thumb: ImageSize

@dataclass
class FocusRect:
    x: int
    y: int
    w: int
    h: int

@dataclass
class OriginalInfo:
    height: int
    width: int
    focus_rects: List[FocusRect]

@dataclass
class MediaResult:
    media_key: str

@dataclass
class MediaItem:
    display_url: str
    expanded_url: str
    id_str: str
    indices: List[int]
    media_key: str
    media_url_https: str
    type: str
    url: str
    ext_media_availability: Dict[str, str]
    features: Dict[str, Dict]
    sizes: ImageSizes
    original_info: OriginalInfo
    media_results: Dict[str, MediaResult]

@dataclass
class Url:
    display_url: str
    expanded_url: str
    url: str
    indices: List[int]

@dataclass
class Entities:
    description: Dict[str, List]
    url: Optional[Dict[str, List[Url]]] = None
    hashtags: Optional[List[Dict[str, Any]]] = None
    media: Optional[List[MediaItem]] = None
    symbols: Optional[List] = None
    timestamps: Optional[List] = None
    urls: Optional[List[Url]] = None
    user_mentions: Optional[List] = None

@dataclass
class Legacy:
    following: bool
    can_dm: bool
    can_media_tag: bool
    created_at: str
    default_profile: bool
    default_profile_image: bool
    description: str
    entities: Entities
    fast_followers_count: int
    favourites_count: int
    followers_count: int
    friends_count: int
    has_custom_timelines: bool
    is_translator: bool
    listed_count: int
    location: str
    media_count: int
    name: str
    normal_followers_count: int
    pinned_tweet_ids_str: List[str]
    possibly_sensitive: bool
    profile_banner_url: Optional[str]
    profile_image_url_https: str
    profile_interstitial_type: str
    screen_name: str
    statuses_count: int
    translator_type: str
    verified: bool
    want_retweets: bool
    withheld_in_countries: List[str]
    url: Optional[str] = None
    bookmark_count: Optional[int] = None
    bookmarked: Optional[bool] = None
    conversation_id_str: Optional[str] = None
    display_text_range: Optional[List[int]] = None
    favorite_count: Optional[int] = None
    favorited: Optional[bool] = None
    full_text: Optional[str] = None
    is_quote_status: Optional[bool] = None
    lang: Optional[str] = None
    quote_count: Optional[int] = None
    reply_count: Optional[int] = None
    retweet_count: Optional[int] = None
    retweeted: Optional[bool] = None
    user_id_str: Optional[str] = None
    id_str: Optional[str] = None
    extended_entities: Optional[Dict[str, List[MediaItem]]] = None

@dataclass
class Professional:
    rest_id: str
    professional_type: str
    category: List[Dict[str, str]]

@dataclass
class UserResult:
    __typename: str
    id: str
    rest_id: str
    affiliates_highlighted_label: Dict
    has_graduated_access: bool
    parody_commentary_fan_label: str
    is_blue_verified: bool
    profile_image_shape: str
    legacy: Legacy
    tipjar_settings: Dict
    professional: Optional[Professional] = None

@dataclass
class UserResults:
    result: UserResult

@dataclass
class Core:
    user_results: UserResults

@dataclass
class EditControl:
    edit_tweet_ids: List[str]
    editable_until_msecs: str
    is_edit_eligible: bool
    edits_remaining: str

@dataclass
class Views:
    state: str

@dataclass
class TweetResult:
    __typename: str
    rest_id: str
    core: Core
    unmention_data: Dict
    edit_control: EditControl
    is_translatable: bool
    views: Views
    source: str
    grok_analysis_button: bool
    legacy: Legacy
    quoted_status_result: Optional[Dict] = None

@dataclass
class TweetResults:
    result: TweetResult

@dataclass
class ItemContent:
    itemType: str
    __typename: str
    user_results: UserResults
    userDisplayType: str

@dataclass
class Item:
    itemContent: ItemContent
    clientEventInfo: Dict

@dataclass
class Content:
    entryType: str
    __typename: str
    items: Optional[List[Item]] = None
    displayType: Optional[str] = None
    header: Optional[Dict] = None
    footer: Optional[Dict] = None
    clientEventInfo: Optional[Dict] = None
    itemContent: Optional[Dict] = None
    tweetDisplayType: Optional[str] = None
    highlights: Optional[Dict] = None
    feedbackInfo: Optional[Dict] = None

@dataclass
class Entry:
    entryId: str
    sortIndex: str
    content: Content

@dataclass
class Instruction:
    type: str
    entries: List[Entry]

@dataclass
class Timeline:
    instructions: List[Instruction]

@dataclass
class SearchTimeline:
    timeline: Timeline

@dataclass
class SearchByRawQuery:
    search_timeline: SearchTimeline

@dataclass
class Data:
    search_by_raw_query: SearchByRawQuery

@dataclass
class TwitterResponse:
    data: Data
    responseObjects: Dict[str, List[Dict[str, Any]]]

@dataclass
class TweetAnalysisResult:
    """
    Результат анализа твитов.
    
    Attributes:
        status (str): Статус анализа ('GREEN', 'YELLOW', 'RED')
        selected_user (Optional[str]): Выбранный пользователь Twitter (если есть)
        user_data (Optional[Dict]): Данные выбранного пользователя
        total_tweets (int): Общее количество проанализированных твитов
        unique_users (int): Количество уникальных пользователей
    """
    status: str
    selected_user: Optional[str]
    user_data: Optional[Dict]
    total_tweets: int
    unique_users: int
