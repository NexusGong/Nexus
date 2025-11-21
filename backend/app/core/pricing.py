"""
角色定价配置
定义不同稀有度角色的价格策略
"""

# 角色价格配置（单位：元）
CHARACTER_PRICES = {
    "legendary": 2.9,   # SSR
    "epic": 1.9,        # SR
    "rare": 0.0,        # R
    "common": 0.0,      # N (免费)
}

def get_character_price(rarity: str) -> float:
    """
    根据稀有度获取角色价格
    
    Args:
        rarity: 角色稀有度 (legendary/epic/rare/common)
        
    Returns:
        float: 角色价格（元）
    """
    return CHARACTER_PRICES.get(rarity, 0.0)

