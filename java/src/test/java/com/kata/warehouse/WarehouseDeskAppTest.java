package com.kata.warehouse;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.*;

class WarehouseDeskAppTest {

  private WarehouseDeskApp app;
  private static final Instant BASE_TIME = Instant.parse("2024-01-01T10:00:00Z");

  @BeforeEach
  void setUp() {
    app = new WarehouseDeskApp();
    app.setClock(Clock.fixed(BASE_TIME, ZoneOffset.UTC));
    app.seedData();
  }

  // ---- RESERVE ----

  @Test
  void reserve_reducesAvailableStock() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");
    app.processLine("COUNT;PEN-BLACK");

    String lastEvent = lastEvent();
    assertTrue(lastEvent.contains("onHand=40"), lastEvent);
    assertTrue(lastEvent.contains("reserved=10"), lastEvent);
    assertTrue(lastEvent.contains("available=30"), lastEvent);
  }

  @Test
  void reserve_failsWhenInsufficientStock() {
    app.processLine("RESERVE;alice;PEN-BLACK;50;30");

    assertTrue(lastEvent().contains("insufficient stock"));
  }

  @Test
  void reserve_failsWhenInsufficientAfterExistingReservation() {
    app.processLine("RESERVE;alice;PEN-BLACK;30;30");
    app.processLine("RESERVE;bob;PEN-BLACK;20;30");

    assertTrue(lastEvent().contains("insufficient stock"));
  }

  @Test
  void reserve_assignsSequentialIds() {
    app.processLine("RESERVE;alice;PEN-BLACK;5;30");
    app.processLine("RESERVE;bob;PEN-BLUE;5;30");

    String log = String.join("\n", eventLog());
    assertTrue(log.contains("RES-1"));
    assertTrue(log.contains("RES-2"));
  }

  // ---- CONFIRM ----

  @Test
  void confirm_shipsOrderAndDeductsStock() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");
    app.processLine("CONFIRM;RES-1");

    String event = lastEvent();
    assertTrue(event.contains("shipped to alice"), event);
    assertTrue(event.contains("amount=15.0"), event);

    app.processLine("COUNT;PEN-BLACK");
    String count = lastEvent();
    assertTrue(count.contains("onHand=30"), count);
    assertTrue(count.contains("reserved=0"), count);
  }

  @Test
  void confirm_failsForNonExistentReservation() {
    app.processLine("CONFIRM;RES-99");

    assertTrue(lastEvent().contains("does not exist"));
  }

  @Test
  void confirm_failsForAlreadyConfirmedReservation() {
    app.processLine("RESERVE;alice;PEN-BLACK;5;30");
    app.processLine("CONFIRM;RES-1");
    app.processLine("CONFIRM;RES-1");

    assertTrue(lastEvent().contains("status is CONFIRMED"));
  }

  @Test
  void confirm_failsForReleasedReservation() {
    app.processLine("RESERVE;alice;PEN-BLACK;5;30");
    app.processLine("RELEASE;RES-1");
    app.processLine("CONFIRM;RES-1");

    assertTrue(lastEvent().contains("status is RELEASED"));
  }

  // ---- RELEASE ----

  @Test
  void release_returnsStockToAvailability() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");
    app.processLine("RELEASE;RES-1");

    app.processLine("COUNT;PEN-BLACK");
    String count = lastEvent();
    assertTrue(count.contains("reserved=0"), count);
    assertTrue(count.contains("available=40"), count);
  }

  @Test
  void release_failsForNonExistentReservation() {
    app.processLine("RELEASE;RES-99");

    assertTrue(lastEvent().contains("does not exist"));
  }

  @Test
  void release_failsForAlreadyReleasedReservation() {
    app.processLine("RESERVE;alice;PEN-BLACK;5;30");
    app.processLine("RELEASE;RES-1");
    app.processLine("RELEASE;RES-1");

    assertTrue(lastEvent().contains("status is RELEASED"));
  }

  // ---- AUTO-EXPIRY ----

  @Test
  void expiry_returnsStockAfterTimeout() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");

    // Advance clock past expiry
    app.setClock(Clock.fixed(BASE_TIME.plusSeconds(31 * 60), ZoneOffset.UTC));
    app.processLine("COUNT;PEN-BLACK");

    // Expiry event should be logged
    String log = String.join("\n", eventLog());
    assertTrue(log.contains("RES-1") && log.contains("expired"), log);

    // Stock available again
    String count = lastEvent();
    assertTrue(count.contains("reserved=0"), count);
    assertTrue(count.contains("available=40"), count);
  }

  @Test
  void expiry_doesNotExpireBeforeTimeout() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");

    // Advance clock to just before expiry
    app.setClock(Clock.fixed(BASE_TIME.plusSeconds(29 * 60), ZoneOffset.UTC));
    app.processLine("COUNT;PEN-BLACK");

    String count = lastEvent();
    assertTrue(count.contains("reserved=10"), count);
  }

  @Test
  void expiry_confirmedReservationNotExpired() {
    app.processLine("RESERVE;alice;PEN-BLACK;10;30");
    app.processLine("CONFIRM;RES-1");

    // Advance clock past expiry
    app.setClock(Clock.fixed(BASE_TIME.plusSeconds(31 * 60), ZoneOffset.UTC));
    app.processLine("COUNT;PEN-BLACK");

    // Stock was already consumed by confirm, not returned
    String count = lastEvent();
    assertTrue(count.contains("onHand=30"), count);
    assertTrue(count.contains("reserved=0"), count);
  }

  @Test
  void expiry_sellCanUseExpiredStock() {
    app.processLine("RESERVE;alice;PEN-BLACK;35;30");

    // Advance past expiry
    app.setClock(Clock.fixed(BASE_TIME.plusSeconds(31 * 60), ZoneOffset.UTC));

    // Previously unavailable qty should now be sellable
    app.processLine("SELL;bob;PEN-BLACK;35");

    assertTrue(lastEvent().contains("shipped to bob"), lastEvent());
  }

  // ---- SELL still respects reservations ----

  @Test
  void sell_cannotUseReservedStock() {
    app.processLine("RESERVE;alice;PEN-BLACK;35;30");
    app.processLine("SELL;bob;PEN-BLACK;10");

    assertTrue(lastEvent().contains("backordered"), lastEvent());
  }

  // ---- helpers ----

  private java.util.List<String> eventLog() {
    // Capture event log via printEndOfDayReport output would be brittle;
    // instead expose via a test-friendly processLine round-trip using COUNT on a dummy SKU.
    // We instead collect from the app's internal state via a reflective approach —
    // but simpler: just track events in order from all processLine calls above.
    // The cleanest approach: add a package-private accessor.
    // Since eventLog is package-private after we adjust, use it directly.
    return app.eventLog;
  }

  private String lastEvent() {
    java.util.List<String> log = eventLog();
    return log.isEmpty() ? "" : log.get(log.size() - 1);
  }
}
