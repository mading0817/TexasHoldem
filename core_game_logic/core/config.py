"""
游戏配置相关类的实现
包含玩家配置和游戏设置
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PlayerConfig:
    """
    单个玩家的配置信息
    """
    seat: int                           # 座位号 (0-based)
    type: str                          # 玩家类型: "human" | "ai" 
    model: str = "random"              # AI模型类型: "gemini" | "chatgpt" | "random"
    api_key: Optional[str] = None      # API密钥（AI玩家使用）
    name: Optional[str] = None         # 玩家名称
    
    def __post_init__(self):
        """验证配置的有效性"""
        if self.seat < 0:
            raise ValueError(f"座位号不能为负数: {self.seat}")
        
        if self.type not in ["human", "ai"]:
            raise ValueError(f"无效的玩家类型: {self.type}")
        
        if self.type == "ai" and self.model not in ["gemini", "chatgpt", "random"]:
            raise ValueError(f"无效的AI模型类型: {self.model}")
        
        # 设置默认名称
        if self.name is None:
            if self.type == "human":
                self.name = f"玩家{self.seat + 1}"
            else:
                self.name = f"AI-{self.model.upper()}-{self.seat + 1}"

    @property
    def is_human(self) -> bool:
        """检查是否为人类玩家"""
        return self.type == "human"

    @property
    def is_ai(self) -> bool:
        """检查是否为AI玩家"""
        return self.type == "ai"


@dataclass
class GameConfig:
    """
    游戏配置类
    包含所有游戏相关的设置参数
    """
    # 玩家配置
    players: List[PlayerConfig] = field(default_factory=list)
    
    # 筹码和盲注设置
    starting_chips: int = 1000         # 初始筹码
    small_blind: int = 1               # 小盲注
    big_blind: int = 2                 # 大盲注
    
    # 游戏规则设置
    max_players: int = 9               # 最大玩家数
    min_players: int = 2               # 最小玩家数
    
    # AI相关设置
    ai_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 调试和测试设置
    random_seed: Optional[int] = None   # 随机种子，用于可重现的游戏
    debug_mode: bool = False           # 调试模式
    
    def __post_init__(self):
        """验证配置的有效性"""
        self._validate_basic_settings()
        self._validate_players()
        self._set_default_ai_settings()

    def _validate_basic_settings(self):
        """验证基础设置"""
        if self.starting_chips <= 0:
            raise ValueError(f"初始筹码必须大于0: {self.starting_chips}")
        
        if self.small_blind <= 0:
            raise ValueError(f"小盲注必须大于0: {self.small_blind}")
        
        if self.big_blind <= self.small_blind:
            raise ValueError(f"大盲注({self.big_blind})必须大于小盲注({self.small_blind})")
        
        if self.max_players < self.min_players:
            raise ValueError(f"最大玩家数({self.max_players})不能小于最小玩家数({self.min_players})")

    def _validate_players(self):
        """验证玩家配置"""
        if not self.players:
            return  # 允许空配置，后续可以添加玩家
        
        if len(self.players) > self.max_players:
            raise ValueError(f"玩家数量({len(self.players)})超过最大限制({self.max_players})")
        
        if len(self.players) < self.min_players:
            raise ValueError(f"玩家数量({len(self.players)})少于最小要求({self.min_players})")
        
        # 检查座位号重复
        seats = [p.seat for p in self.players]
        if len(seats) != len(set(seats)):
            raise ValueError("存在重复的座位号")
        
        # 检查座位号范围
        for player in self.players:
            if player.seat >= self.max_players:
                raise ValueError(f"座位号({player.seat})超出范围(0-{self.max_players-1})")
        
        # 检查是否有人类玩家
        human_players = [p for p in self.players if p.is_human]
        if len(human_players) == 0:
            raise ValueError("至少需要一个人类玩家")
        
        if len(human_players) > 1:
            raise ValueError("只能有一个人类玩家")

    def _set_default_ai_settings(self):
        """设置默认的AI配置"""
        if "gemini" not in self.ai_settings:
            self.ai_settings["gemini"] = {
                "model": "gemini-pro",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        
        if "chatgpt" not in self.ai_settings:
            self.ai_settings["chatgpt"] = {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            }

    def add_player(self, player_config: PlayerConfig):
        """添加玩家配置"""
        # 检查座位是否已被占用
        if any(p.seat == player_config.seat for p in self.players):
            raise ValueError(f"座位{player_config.seat}已被占用")
        
        self.players.append(player_config)
        self._validate_players()

    def get_human_player(self) -> Optional[PlayerConfig]:
        """获取人类玩家配置"""
        human_players = [p for p in self.players if p.is_human]
        return human_players[0] if human_players else None

    def get_ai_players(self) -> List[PlayerConfig]:
        """获取所有AI玩家配置"""
        return [p for p in self.players if p.is_ai]

    @classmethod
    def default_4_player(cls) -> 'GameConfig':
        """
        创建默认的4人游戏配置
        座位0为人类玩家，其他为AI
        """
        players = [
            PlayerConfig(seat=0, type="human", name="玩家"),
            PlayerConfig(seat=1, type="ai", model="random", name="AI-1"),
            PlayerConfig(seat=2, type="ai", model="random", name="AI-2"),
            PlayerConfig(seat=3, type="ai", model="random", name="AI-3")
        ]
        
        return cls(
            players=players,
            starting_chips=1000,
            small_blind=1,
            big_blind=2,
            max_players=4
        )

    @classmethod
    def default_heads_up(cls) -> 'GameConfig':
        """
        创建默认的单挑游戏配置
        """
        players = [
            PlayerConfig(seat=0, type="human", name="玩家"),
            PlayerConfig(seat=1, type="ai", model="random", name="AI对手")
        ]
        
        return cls(
            players=players,
            starting_chips=1000,
            small_blind=1,
            big_blind=2,
            max_players=2,
            min_players=2
        ) 