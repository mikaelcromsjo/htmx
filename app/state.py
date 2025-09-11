# app/state.py

from typing import Dict, List
from fastapi import WebSocket

# Store shared variables per user
user_data: Dict[str, dict] = {}

# Store active WebSocket connections per user
active_connections: Dict[str, List[WebSocket]] = {}