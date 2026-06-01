from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BotState:
    paused: bool = False
    start_time: datetime = field(default_factory=datetime.now)
    last_market_count: int = 0
    consecutive_failures: int = 0


state = BotState()
