from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Ship:
    name: str
    size: int
    coordinates: List[Tuple[int, int]] = None
    horizontal: bool = True

    def rotate(self):
        self.horizontal = not self.horizontal

@dataclass
class Player:
    id: str
    ip: str
    ships: List[Ship] = None
    board: List[List[int]] = None  # 0=empty, 1=miss, 2=hit

    def __post_init__(self):
        if self.board is None:
            self.board = [[0 for _ in range(10)] for _ in range(10)]
        if self.ships is None:
            self.ships = []

class GameState:
    def __init__(self):
        self.players = {}
        self.current_turn = None
        self.started = False