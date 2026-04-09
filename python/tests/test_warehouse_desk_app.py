import pytest
from src.warehouse.warehouse_desk_app import WarehouseDeskApp


class TestRecv:
    def test_increases_stock(self):
        app = WarehouseDeskApp()
        app.process_line("RECV;PEN-BLACK;10;1.50")
        assert app._stock["PEN-BLACK"] == 10

    def test_adds_to_existing_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RECV;PEN-BLACK;10;1.50")
        assert app._stock["PEN-BLACK"] == 50

    def test_decreases_cash(self):
        app = WarehouseDeskApp()
        app._cash_balance = 100.0
        app.process_line("RECV;PEN-BLACK;10;1.50")
        assert app._cash_balance == 85.0

    def test_logs_event(self):
        app = WarehouseDeskApp()
        app.process_line("RECV;PEN-BLACK;10;1.50")
        assert "received 10 of PEN-BLACK at 1.5" in app._event_log


class TestSell:
    def test_ships_when_stock_available(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        assert app._order_status["O1001"] == "SHIPPED"

    def test_decreases_stock_on_ship(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        assert app._stock["PEN-BLACK"] == 30

    def test_increases_cash_on_ship(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        assert app._cash_balance == 315.0

    def test_logs_ship_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        assert any("shipped" in e and "alice" in e for e in app._event_log)

    def test_backordered_when_insufficient_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        assert app._order_status["O1001"] == "BACKORDER"

    def test_does_not_decrease_stock_on_backorder(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        assert app._stock["STAPLER"] == 4

    def test_logs_backorder_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        assert any("backordered" in e for e in app._event_log)

    def test_increments_order_number_per_order(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;1")
        app.process_line("SELL;bob;PEN-BLUE;1")
        assert "O1001" in app._order_status
        assert "O1002" in app._order_status

    def test_records_sku_and_qty(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        assert app._order_sku["O1001"] == "PEN-BLACK"
        assert app._order_qty["O1001"] == 10


class TestCancel:
    def test_cancel_backorder(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        app.process_line("CANCEL;O1001")
        assert app._order_status["O1001"] == "CANCELLED"

    def test_cancel_backorder_logs_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        app.process_line("CANCEL;O1001")
        assert any("cancelled backorder" in e for e in app._event_log)

    def test_cancel_shipped_marks_cancelled_after_ship(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        app.process_line("CANCEL;O1001")
        assert app._order_status["O1001"] == "CANCELLED_AFTER_SHIP"

    def test_cancel_shipped_restores_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        app.process_line("CANCEL;O1001")
        assert app._stock["PEN-BLACK"] == 40

    def test_cancel_shipped_refunds_cash(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        app.process_line("CANCEL;O1001")
        assert app._cash_balance == 300.0

    def test_cancel_shipped_logs_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;alice;PEN-BLACK;10")
        app.process_line("CANCEL;O1001")
        assert any("restock" in e for e in app._event_log)

    def test_cancel_nonexistent_order_logs_error(self):
        app = WarehouseDeskApp()
        app.process_line("CANCEL;O9999")
        assert any("does not exist" in e for e in app._event_log)

    def test_cancel_already_cancelled_logs_error(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("SELL;bob;STAPLER;5")
        app.process_line("CANCEL;O1001")
        app.process_line("CANCEL;O1001")
        assert any("could not be cancelled" in e for e in app._event_log)


class TestCount:
    def test_shows_on_hand_and_available(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("COUNT;STAPLER")
        assert any("onHand=4" in e and "available=4" in e for e in app._event_log)

    def test_shows_zero_reserved_when_no_reservations(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("COUNT;STAPLER")
        assert any("reserved=0" in e for e in app._event_log)


class TestUnknownCommand:
    def test_unknown_command_is_logged(self):
        app = WarehouseDeskApp()
        app.process_line("BOGUS;foo")
        assert any("unknown command" in e for e in app._event_log)
