from typing import Optional
from app.config.config import chain_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_chain_id(chain_name: str) -> Optional[str]:
    """
    Преобразует название сети в chain_id.
    
    Args:
        chain_name: Название сети (например, 'bsc', 'ethereum')
        
    Returns:
        str: Chain ID или None, если сеть не найдена
    """
    chain_name = chain_name.lower()
    chain_id = chain_config.CHAIN_MAPPING.get(chain_name)
    
    if chain_id is None:
        logger.warning(f"Неподдерживаемая сеть: {chain_name}")
        logger.info(f"Доступные сети: {', '.join(chain_config.CHAIN_MAPPING.keys())}")
        return None
        
    return chain_id
