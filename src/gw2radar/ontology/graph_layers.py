from enum import Enum


class GraphLayer(str, Enum):
    PUBLIC_GAME = "public_game"
    PRIVATE_PLAYER_STATE = "private_player_state"
    PERSONAL_INTELLIGENCE = "personal_intelligence"
