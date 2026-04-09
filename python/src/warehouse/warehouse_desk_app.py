import time


class WarehouseDeskApp:
    def __init__(self):
        self._stock: dict[str, int] = {}
        self._price: dict[str, float] = {}
        self._order_status: dict[str, str] = {}
        self._order_sku: dict[str, str] = {}
        self._order_qty: dict[str, int] = {}
        self._reservations: dict[str, dict] = {}
        self._event_log: list[str] = []
        self._cash_balance: float = 0.0
        self._next_order_number: int = 1001
        self._next_reservation_number: int = 1

    def seed_data(self):
        self._stock = {"PEN-BLACK": 40, "PEN-BLUE": 25, "NOTE-A5": 15, "STAPLER": 4}
        self._price = {"PEN-BLACK": 1.5, "PEN-BLUE": 1.6, "NOTE-A5": 4.0, "STAPLER": 12.0}
        self._cash_balance = 300.0
        self._next_order_number = 1001
        self._reservations = {}
        self._next_reservation_number = 1

    def _reserved_qty(self, sku: str) -> int:
        """Returns total qty of active (non-expired) reservations for a sku."""
        now = time.time()
        for res in self._reservations.values():
            if res["status"] == "ACTIVE" and now >= res["expiry"]:
                res["status"] = "EXPIRED"
        return sum(
            r["qty"]
            for r in self._reservations.values()
            if r["sku"] == sku and r["status"] == "ACTIVE"
        )

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

        if cmd == "RECV":
            sku, qty, unit_cost = parts[1], int(parts[2].strip()), float(parts[3].strip())
            self._stock[sku] = self._stock.get(sku, 0) + qty
            self._cash_balance -= qty * unit_cost
            self._event_log.append(f"received {qty} of {sku} at {unit_cost}")
            return

        if cmd == "SELL":
            customer, sku, qty = parts[1], parts[2], int(parts[3].strip())
            order_id = f"O{self._next_order_number}"
            self._next_order_number += 1
            self._order_sku[order_id] = sku
            self._order_qty[order_id] = qty

            available = self._stock.get(sku, 0) - self._reserved_qty(sku)
            if available < qty:
                self._order_status[order_id] = "BACKORDER"
                self._event_log.append(f"order {order_id} backordered for {customer} sku={sku} qty={qty}")
            else:
                self._stock[sku] = self._stock.get(sku, 0) - qty
                order_total = self._price.get(sku, 0.0) * qty
                self._cash_balance += order_total
                self._order_status[order_id] = "SHIPPED"
                self._event_log.append(f"order {order_id} shipped to {customer} amount={order_total}")
            return

        if cmd == "CANCEL":
            order_id = parts[1]
            status = self._order_status.get(order_id)
            if status is None:
                self._event_log.append(f"cannot cancel {order_id} because it does not exist")
                return
            if status == "BACKORDER":
                self._order_status[order_id] = "CANCELLED"
                self._event_log.append(f"cancelled backorder {order_id}")
                return
            if status == "SHIPPED":
                sku = self._order_sku[order_id]
                qty = self._order_qty[order_id]
                self._stock[sku] = self._stock.get(sku, 0) + qty
                self._cash_balance -= self._price.get(sku, 0.0) * qty
                self._order_status[order_id] = "CANCELLED_AFTER_SHIP"
                self._event_log.append(f"cancelled shipped order {order_id} with restock")
                return
            self._event_log.append(f"order {order_id} could not be cancelled from state {status}")
            return

        if cmd == "COUNT":
            sku = parts[1]
            on_hand = self._stock.get(sku, 0)
            reserved = self._reserved_qty(sku)
            available = on_hand - reserved
            self._event_log.append(f"count {sku} onHand={on_hand} reserved={reserved} available={available}")
            return

        if cmd == "RESERVE":
            customer, sku, qty, minutes = parts[1], parts[2], int(parts[3].strip()), int(parts[4].strip())
            available = self._stock.get(sku, 0) - self._reserved_qty(sku)
            if available < qty:
                self._event_log.append(
                    f"reservation failed for {customer} sku={sku} qty={qty} insufficient stock"
                )
                return
            reservation_id = f"R{self._next_reservation_number}"
            self._next_reservation_number += 1
            self._reservations[reservation_id] = {
                "customer": customer,
                "sku": sku,
                "qty": qty,
                "expiry": time.time() + minutes * 60,
                "status": "ACTIVE",
            }
            self._event_log.append(
                f"reserved {qty} of {sku} for {customer} reservation={reservation_id} expires_in={minutes}min"
            )
            return

        if cmd == "CONFIRM":
            reservation_id = parts[1]
            res = self._reservations.get(reservation_id)
            if res is None:
                self._event_log.append(f"cannot confirm {reservation_id} because it does not exist")
                return
            if res["status"] == "ACTIVE" and time.time() >= res["expiry"]:
                res["status"] = "EXPIRED"
            if res["status"] != "ACTIVE":
                self._event_log.append(
                    f"cannot confirm {reservation_id} from state {res['status']}"
                )
                return
            res["status"] = "CONFIRMED"
            sku, qty, customer = res["sku"], res["qty"], res["customer"]
            order_id = f"O{self._next_order_number}"
            self._next_order_number += 1
            self._order_sku[order_id] = sku
            self._order_qty[order_id] = qty
            self._stock[sku] = self._stock.get(sku, 0) - qty
            order_total = self._price.get(sku, 0.0) * qty
            self._cash_balance += order_total
            self._order_status[order_id] = "SHIPPED"
            self._event_log.append(
                f"confirmed reservation {reservation_id} order {order_id} shipped to {customer} amount={order_total}"
            )
            return

        if cmd == "RELEASE":
            reservation_id = parts[1]
            res = self._reservations.get(reservation_id)
            if res is None:
                self._event_log.append(f"cannot release {reservation_id} because it does not exist")
                return
            if res["status"] == "ACTIVE" and time.time() >= res["expiry"]:
                res["status"] = "EXPIRED"
            if res["status"] != "ACTIVE":
                self._event_log.append(
                    f"cannot release {reservation_id} from state {res['status']}"
                )
                return
            res["status"] = "RELEASED"
            self._event_log.append(
                f"released reservation {reservation_id} sku={res['sku']} qty={res['qty']}"
            )
            return

        if cmd == "DUMP":
            print("---- dump ----")
            print(f"stock={self._stock}")
            print(f"reservations={self._reservations}")
            print(f"orders={self._order_status}")
            print(f"cashBalance={self._cash_balance}")
            return

        self._event_log.append(f"unknown command: {line}")

    def print_end_of_day_report(self):
        shipped = sum(1 for s in self._order_status.values() if s == "SHIPPED")
        backorder = sum(1 for s in self._order_status.values() if s == "BACKORDER")
        cancelled = sum(1 for s in self._order_status.values() if s.startswith("CANCELLED"))
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
