#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Classes para o Bot de Trading BingX
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Dict, Any

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class OrderStatus(Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELED = "CANCELED"

class SignalStrength(Enum):
    WEAK = 2
    NEUTRAL = 3
    STRONG = 4
    VERY_STRONG = 5

@dataclass
class FuturesPosition:
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    margin_used: float = 0.0
    leverage: int = 1
    entry_time: datetime = None

@dataclass
class FuturesTrade:
    timestamp: datetime
    symbol: str
    side: str
    size: float
    price: float
    fee: float
    pnl: float = 0.0
    confidence: float = 0.0

@dataclass
class TradingSignal:
    action: str
    strength: SignalStrength
    confidence: float
    indicators: Dict[str, Any]
    timestamp: datetime
    reason: str

@dataclass
class BingXOrder:
    orderId: str
    symbol: str
    side: str
    positionSide: str
    type: str
    quantity: float
    price: float = 0.0
    status: OrderStatus = OrderStatus.NEW

@dataclass
class BingXPosition:
    symbol: str
    positionSide: str
    size: float
    entryPrice: float
    markPrice: float = 0.0
    unrealizedPnl: float = 0.0
    marginUsed: float = 0.0
    leverage: int = 1
