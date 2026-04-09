# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a **harness engineering kata** — the same feature (`feature.md`) is implemented repeatedly, while the harness (this file, skills, scripts, docs) is iteratively improved to produce better agent output. The kata tracks 9 steps of increasing harness sophistication.

## Commands

### Java
```bash
cd java && mvn -q compile                              # compile
cd java && java -cp target/classes com.kata.warehouse.Main  # run
cd java && mvn -q test                                 # test
```

### Python
```bash
cd python && python main.py   # run
cd python && python -m pytest # test
```

### Toolchain
```bash
mise install   # install correct JDK 25, Maven, Python versions
```

## Architecture

Both `java/` and `python/` implement the same warehouse desk application with identical behaviour. Keeping them in sync is intentional — the kata uses both languages.

**Core design** (single-class, in-memory):
- Commands are parsed from semicolon-delimited strings and dispatched imperatively.
- State lives in plain collections: stock levels, reservations, cash balance, event log.
- No persistence, no external dependencies.

**Java entry point:** `java/src/main/java/com/kata/warehouse/Main.java` → `WarehouseDeskApp`
**Python entry point:** `python/main.py` → `python/src/warehouse/warehouse_desk_app.py`

## Feature to Implement

See `feature.md`. The feature is **Stock reservation with expiry**:
- `RESERVE;<customer>;<sku>;<qty>;<minutes>` — reserve if stock available
- `CONFIRM;<reservationId>` — convert reservation to shipped order
- `RELEASE;<reservationId>` — manually release reserved stock
- Auto-expiry: reservations expire after configured minutes, returning stock to availability

## Add full test coverage for new features.

