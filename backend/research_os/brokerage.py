from abc import ABC, abstractmethod
from typing import Dict, List

from research_os.models import Broker, NormalizedTrade, OrderType, TradeSide


class BrokerageClient(ABC):
    broker: Broker

    @abstractmethod
    def fetch_recent_trades(self) -> List[NormalizedTrade]:
        raise NotImplementedError

    @abstractmethod
    def normalize_trade(self, raw_trade: Dict) -> NormalizedTrade:
        raise NotImplementedError


class KiwoomBrokerageClient(BrokerageClient):
    broker = Broker.KIWOOM

    def fetch_recent_trades(self) -> List[NormalizedTrade]:
        """
        키움증권 실제 연동 전까지 모바일 개발과 API 계약 검증을 위한 Mock 데이터를 반환합니다.
        실제 구현 시 이 메서드에서 키움 인증, 주문/체결 조회, 응답 정규화를 수행합니다.
        """
        raw_trades = [
            {
                "execution_id": "kiwoom-mock-exec-001",
                "order_id": "kiwoom-mock-order-001",
                "market": "KRX",
                "ticker": "005930",
                "name": "삼성전자",
                "side": "BUY",
                "order_type": "LIMIT",
                "date": "2026-05-07",
                "time": "09:05:12",
                "price": 80000,
                "quantity": 10,
                "fee": 120,
                "tax": 0,
                "strategy": "ORB",
            },
            {
                "execution_id": "kiwoom-mock-exec-002",
                "order_id": "kiwoom-mock-order-002",
                "market": "KRX",
                "ticker": "000270",
                "name": "기아",
                "side": "SELL",
                "order_type": "LIMIT",
                "date": "2026-05-07",
                "time": "14:32:44",
                "price": 120000,
                "quantity": 5,
                "fee": 90,
                "tax": 900,
                "strategy": "swing",
            },
        ]
        return [self.normalize_trade(raw_trade) for raw_trade in raw_trades]

    def normalize_trade(self, raw_trade: Dict) -> NormalizedTrade:
        price = float(raw_trade["price"])
        quantity = float(raw_trade["quantity"])
        return NormalizedTrade(
            trade_id=f"kiwoom-{raw_trade['execution_id']}",
            broker=self.broker,
            market=raw_trade["market"],
            ticker=raw_trade["ticker"],
            name=raw_trade["name"],
            side=TradeSide(raw_trade["side"]),
            order_type=OrderType(raw_trade.get("order_type", "ETC")),
            trade_date=raw_trade["date"],
            trade_time=raw_trade["time"],
            price=price,
            quantity=quantity,
            gross_amount=price * quantity,
            fee=float(raw_trade.get("fee", 0)),
            tax=float(raw_trade.get("tax", 0)),
            currency="KRW",
            source_order_id=raw_trade.get("order_id"),
            source_execution_id=raw_trade.get("execution_id"),
            raw_hash=None,
            strategy=raw_trade.get("strategy"),
            journal_required=True,
        )


def get_default_brokerage_client() -> BrokerageClient:
    return KiwoomBrokerageClient()
