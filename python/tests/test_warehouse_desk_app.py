import pytest
from src.warehouse.warehouse_desk_app import Order, OrderStatus, WarehouseDeskApp


@pytest.fixture
def app():
    a = WarehouseDeskApp()
    a.seed_data()
    return a


# --- RECV ---

def test_recv_adds_stock_and_deducts_cash(app):
    app.process_line("RECV;NOTE-A5;5;2.20")
    assert app._stock["NOTE-A5"] == 20
    assert app._cash_balance == pytest.approx(300.0 - 5 * 2.20)
    assert app._event_log[-1] == "received 5 of NOTE-A5 at 2.2"


def test_recv_creates_new_sku(app):
    app.process_line("RECV;TAPE;10;0.50")
    assert app._stock["TAPE"] == 10
    assert app._cash_balance == pytest.approx(300.0 - 5.0)


# --- SELL ---

def test_sell_ships_when_stock_available(app):
    app.process_line("SELL;alice;PEN-BLACK;10")
    assert app._stock["PEN-BLACK"] == 30
    assert app._cash_balance == pytest.approx(300.0 + 10 * 1.5)
    assert app._orders["O1001"].status == OrderStatus.SHIPPED
    assert app._event_log[-1] == "order O1001 shipped to alice amount=15.0"


def test_sell_backordered_when_insufficient_stock(app):
    app.process_line("SELL;bob;STAPLER;5")
    assert app._stock["STAPLER"] == 4  # unchanged
    assert app._cash_balance == 300.0  # unchanged
    assert app._orders["O1001"].status == OrderStatus.BACKORDER
    assert app._event_log[-1] == "order O1001 backordered for bob sku=STAPLER qty=5"


def test_sell_order_ids_increment(app):
    app.process_line("SELL;alice;PEN-BLACK;1")
    app.process_line("SELL;bob;PEN-BLUE;1")
    assert "O1001" in app._orders
    assert "O1002" in app._orders


# --- CANCEL ---

def test_cancel_nonexistent_order(app):
    app.process_line("CANCEL;O9999")
    assert app._event_log[-1] == "cannot cancel O9999 because it does not exist"


def test_cancel_backorder(app):
    app.process_line("SELL;bob;STAPLER;5")  # O1001 -> BACKORDER
    app.process_line("CANCEL;O1001")
    assert app._orders["O1001"].status == OrderStatus.CANCELLED
    assert app._event_log[-1] == "cancelled backorder O1001"


def test_cancel_shipped_order_restocks_and_deducts_cash(app):
    app.process_line("SELL;alice;PEN-BLACK;10")  # O1001 shipped, cash += 15.0
    app.process_line("CANCEL;O1001")
    assert app._stock["PEN-BLACK"] == 40  # restored
    assert app._cash_balance == pytest.approx(300.0)
    assert app._orders["O1001"].status == OrderStatus.CANCELLED_AFTER_SHIP
    assert app._event_log[-1] == "cancelled shipped order O1001 with restock"


def test_cancel_already_cancelled_order_is_rejected(app):
    app.process_line("SELL;bob;STAPLER;5")  # O1001 -> BACKORDER
    app.process_line("CANCEL;O1001")        # -> CANCELLED
    app.process_line("CANCEL;O1001")        # second cancel rejected
    assert app._event_log[-1] == "order O1001 could not be cancelled from state CANCELLED"


# --- COUNT ---

def test_count_logs_stock_info(app):
    app.process_line("COUNT;STAPLER")
    assert app._event_log[-1] == "count STAPLER onHand=4 reserved=0 available=4"


# --- UNKNOWN ---

def test_unknown_command_is_logged(app):
    app.process_line("FOO;bar;baz")
    assert app._event_log[-1] == "unknown command: FOO;bar;baz"


# --- END OF DAY REPORT ---

def test_end_of_day_report_counts(app, capsys):
    app.process_line("SELL;alice;PEN-BLACK;10")  # O1001 SHIPPED
    app.process_line("SELL;bob;STAPLER;5")        # O1002 BACKORDER
    app.process_line("SELL;carol;PEN-BLUE;1")     # O1003 SHIPPED
    app.process_line("CANCEL;O1003")              # O1003 CANCELLED_AFTER_SHIP
    app.print_end_of_day_report()
    out = capsys.readouterr().out
    assert "orders shipped: 1" in out
    assert "orders backordered: 1" in out
    assert "orders cancelled: 1" in out


def test_end_of_day_report_cash_balance(app, capsys):
    app.process_line("SELL;alice;PEN-BLACK;10")
    app.print_end_of_day_report()
    out = capsys.readouterr().out
    assert "cash balance: 315.00" in out


def test_end_of_day_report_low_stock(app, capsys):
    app.print_end_of_day_report()
    out = capsys.readouterr().out
    assert "STAPLER" in out  # STAPLER has qty=4, below threshold of 5


def test_end_of_day_report_events_listed(app, capsys):
    app.process_line("SELL;alice;PEN-BLACK;1")
    app.print_end_of_day_report()
    out = capsys.readouterr().out
    assert "events:" in out
    assert "order O1001 shipped to alice amount=1.5" in out
