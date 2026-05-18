from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Broker(str, Enum):
    KIWOOM = "KIWOOM"
    KIS = "KIS"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    ETC = "ETC"


class NormalizedTrade(BaseModel):
    trade_id: str
    broker: Broker
    market: str
    ticker: str
    name: str
    side: TradeSide
    order_type: OrderType = OrderType.ETC
    trade_date: str
    trade_time: str
    price: float
    quantity: float
    gross_amount: float
    fee: float = 0
    tax: float = 0
    currency: str = "KRW"
    source_order_id: Optional[str] = None
    source_execution_id: Optional[str] = None
    raw_hash: Optional[str] = None
    strategy: Optional[str] = None
    journal_required: bool = True


class TradesResponse(BaseModel):
    status: str = "success"
    data: List[NormalizedTrade]


class BrokerStatus(BaseModel):
    default_broker: Broker
    first_integration_target: Broker
    adapters_ready: List[Broker]
    message: str
