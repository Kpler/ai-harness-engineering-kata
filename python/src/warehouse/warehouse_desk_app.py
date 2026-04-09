from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    BACKORDER = "BACKORDER"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"
    CANCELLED_AFTER_SHIP = "CANCELLED_AFTER_SHIP"


@dataclass
class Order:
    sku: str
    qty: int
    status: OrderStatus


class WarehouseDeskApp:
    def __init__(self):
        self._stock: dict[str, int] = {}
        self._reserved: dict[str, int] = {}
        self._price: dict[str, float] = {}
        self._orders: dict[str, Order] = {}
        self._event_log: list[str] = []
        self._cash_balance: float = 0.0
        self._next_order_number: int = 1001

    def seed_data(self):
        self._stock = {"PEN-BLACK": 40, "PEN-BLUE": 25, "NOTE-A5": 15, "STAPLER": 4}
        self._reserved = {}
        self._price = {"PEN-BLACK": 1.5, "PEN-BLUE": 1.6, "NOTE-A5": 4.0, "STAPLER": 12.0}
        self._cash_balance = 300.0
        self._next_order_number = 1001

    def run_demo_day(self):
        commands = [
            "RECV;NOTE-A5;5;2.20",
            "SELL;alice;PEN-BLACK;10",
            "SELL;bob;STAPLER;5",
            "CANCEL;O1002",
            "COUNT;STAPLER",
            "SELL;carol;STAPLER;2",
            "SELL;dan;NOTE-A5;14",
            "COUNT;NOTE-A5",
            "DUMP",
        ]
        for command in commands:
            self.process_line(command)
        self.print_end_of_day_report()

    def process_line(self, line: str):
        parts = line.split(";")
        cmd = parts[0]
        handlers = {
            "RECV": self._handle_recv,
            "SELL": self._handle_sell,
            "CANCEL": self._handle_cancel,
            "COUNT": self._handle_count,
            "DUMP": self._handle_dump,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(parts)
        else:
            self._event_log.append(f"unknown command: {line}")

    def _handle_recv(self, parts: list[str]):
        sku, qty, unit_cost = parts[1], int(parts[2].strip()), float(parts[3].strip())
        self._stock[sku] = self._stock.get(sku, 0) + qty
        self._cash_balance -= qty * unit_cost
        self._event_log.append(f"received {qty} of {sku} at {unit_cost}")

    def _handle_sell(self, parts: list[str]):
        customer, sku, qty = parts[1], parts[2], int(parts[3].strip())
        order_id = f"O{self._next_order_number}"
        self._next_order_number += 1

        available = self._stock.get(sku, 0) - self._reserved.get(sku, 0)
        if available < qty:
            self._orders[order_id] = Order(sku=sku, qty=qty, status=OrderStatus.BACKORDER)
            self._event_log.append(f"order {order_id} backordered for {customer} sku={sku} qty={qty}")
        else:
            self._stock[sku] -= qty
            order_total = self._price.get(sku, 0.0) * qty
            self._cash_balance += order_total
            self._orders[order_id] = Order(sku=sku, qty=qty, status=OrderStatus.SHIPPED)
            self._event_log.append(f"order {order_id} shipped to {customer} amount={order_total}")

    def _handle_cancel(self, parts: list[str]):
        order_id = parts[1]
        order = self._orders.get(order_id)
        if order is None:
            self._event_log.append(f"cannot cancel {order_id} because it does not exist")
            return
        if order.status == OrderStatus.BACKORDER:
            order.status = OrderStatus.CANCELLED
            self._event_log.append(f"cancelled backorder {order_id}")
            return
        if order.status == OrderStatus.SHIPPED:
            self._stock[order.sku] = self._stock.get(order.sku, 0) + order.qty
            self._cash_balance -= self._price.get(order.sku, 0.0) * order.qty
            order.status = OrderStatus.CANCELLED_AFTER_SHIP
            self._event_log.append(f"cancelled shipped order {order_id} with restock")
            return
        self._event_log.append(f"order {order_id} could not be cancelled from state {order.status.value}")

    def _handle_count(self, parts: list[str]):
        sku = parts[1]
        on_hand = self._stock.get(sku, 0)
        reserved = self._reserved.get(sku, 0)
        available = on_hand - reserved
        self._event_log.append(f"count {sku} onHand={on_hand} reserved={reserved} available={available}")

    def _handle_dump(self, _parts: list[str]):
        print("---- dump ----")
        print(f"stock={self._stock}")
        print(f"reserved={self._reserved}")
        print(f"orders={self._orders}")
        print(f"cashBalance={self._cash_balance}")

    def print_end_of_day_report(self):
        statuses = [o.status for o in self._orders.values()]
        shipped = statuses.count(OrderStatus.SHIPPED)
        backorder = statuses.count(OrderStatus.BACKORDER)
        cancelled = sum(1 for s in statuses if s in (OrderStatus.CANCELLED, OrderStatus.CANCELLED_AFTER_SHIP))
        low_stock = [sku for sku, qty in self._stock.items() if qty < 5]

        print()
        print("==== end of day ====")
        print(f"orders shipped: {shipped}")
        print(f"orders backordered: {backorder}")
        print(f"orders cancelled: {cancelled}")
        print(f"cash balance: {self._cash_balance:.2f}")
        print(f"low stock skus: {low_stock}")
        print()
        print("events:")
        for event in self._event_log:
            print(f" - {event}")
