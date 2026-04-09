from unittest.mock import patch
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


class TestReserve:
    def test_creates_reservation_when_stock_available(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        assert app._reservations["R1"]["status"] == "ACTIVE"
        assert app._reservations["R1"]["sku"] == "PEN-BLACK"
        assert app._reservations["R1"]["qty"] == 10

    def test_reduces_available_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        assert app._reserved_qty("PEN-BLACK") == 10

    def test_does_not_reduce_on_hand_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        assert app._stock["PEN-BLACK"] == 40

    def test_logs_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        assert any("reservation=R1" in e and "alice" in e for e in app._event_log)

    def test_fails_when_insufficient_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;STAPLER;5;5")  # only 4 in stock
        assert "R1" not in app._reservations
        assert any("insufficient stock" in e for e in app._event_log)

    def test_fails_when_stock_already_reserved(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;STAPLER;3;5")
        app.process_line("RESERVE;bob;STAPLER;2;5")  # only 1 left
        assert "R2" not in app._reservations

    def test_increments_reservation_id(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;1;5")
        app.process_line("RESERVE;bob;PEN-BLACK;1;5")
        assert "R1" in app._reservations
        assert "R2" in app._reservations


class TestConfirm:
    def test_ships_order_from_reservation(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        assert app._order_status["O1001"] == "SHIPPED"

    def test_decreases_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        assert app._stock["PEN-BLACK"] == 30

    def test_increases_cash(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        assert app._cash_balance == 315.0

    def test_marks_reservation_confirmed(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        assert app._reservations["R1"]["status"] == "CONFIRMED"

    def test_logs_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        assert any("confirmed reservation R1" in e for e in app._event_log)

    def test_fails_for_nonexistent_reservation(self):
        app = WarehouseDeskApp()
        app.process_line("CONFIRM;R99")
        assert any("does not exist" in e for e in app._event_log)

    def test_fails_for_already_confirmed(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("CONFIRM;R1")
        app.process_line("CONFIRM;R1")
        assert any("cannot confirm R1 from state CONFIRMED" in e for e in app._event_log)

    def test_fails_for_released_reservation(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("RELEASE;R1")
        app.process_line("CONFIRM;R1")
        assert any("cannot confirm R1 from state RELEASED" in e for e in app._event_log)

    def test_fails_for_expired_reservation(self):
        app = WarehouseDeskApp()
        app.seed_data()
        with patch("time.time", return_value=1000.0):
            app.process_line("RESERVE;alice;PEN-BLACK;10;1")  # expires at 1060.0
        with patch("time.time", return_value=2000.0):
            app.process_line("CONFIRM;R1")
        assert any("cannot confirm R1 from state EXPIRED" in e for e in app._event_log)


class TestRelease:
    def test_releases_active_reservation(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("RELEASE;R1")
        assert app._reservations["R1"]["status"] == "RELEASED"

    def test_restores_available_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("RELEASE;R1")
        assert app._reserved_qty("PEN-BLACK") == 0

    def test_logs_event(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("RELEASE;R1")
        assert any("released reservation R1" in e for e in app._event_log)

    def test_fails_for_nonexistent_reservation(self):
        app = WarehouseDeskApp()
        app.process_line("RELEASE;R99")
        assert any("does not exist" in e for e in app._event_log)

    def test_fails_for_already_released(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("RELEASE;R1")
        app.process_line("RELEASE;R1")
        assert any("cannot release R1 from state RELEASED" in e for e in app._event_log)


class TestReservationExpiry:
    def test_expired_reservation_frees_stock_for_sell(self):
        app = WarehouseDeskApp()
        app.seed_data()
        with patch("time.time", return_value=1000.0):
            app.process_line("RESERVE;alice;STAPLER;4;1")  # all 4 staplers reserved
        with patch("time.time", return_value=2000.0):
            app.process_line("SELL;bob;STAPLER;4")  # should succeed after expiry
        assert app._order_status["O1001"] == "SHIPPED"

    def test_expired_reservation_not_counted_as_reserved(self):
        app = WarehouseDeskApp()
        app.seed_data()
        with patch("time.time", return_value=1000.0):
            app.process_line("RESERVE;alice;PEN-BLACK;10;1")
        with patch("time.time", return_value=2000.0):
            assert app._reserved_qty("PEN-BLACK") == 0

    def test_active_reservation_blocks_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        with patch("time.time", return_value=1000.0):
            app.process_line("RESERVE;alice;STAPLER;4;60")
        with patch("time.time", return_value=1001.0):
            app.process_line("SELL;bob;STAPLER;1")  # should be backordered
        assert app._order_status["O1001"] == "BACKORDER"

    def test_count_reflects_reserved_stock(self):
        app = WarehouseDeskApp()
        app.seed_data()
        app.process_line("RESERVE;alice;PEN-BLACK;10;5")
        app.process_line("COUNT;PEN-BLACK")
        assert any("onHand=40" in e and "reserved=10" in e and "available=30" in e for e in app._event_log)
