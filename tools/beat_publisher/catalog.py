from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import fields, replace
from datetime import UTC, datetime
from pathlib import Path

from .models import BeatRecord


VALID_STATUSES = {"draft", "ready", "published", "hidden", "removed"}
JSON_FIELDS = {"source_peaks", "preview_peaks", "warnings"}
BOOL_FIELDS = {"normalize", "managed_source"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class CatalogStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        columns = []
        for item in fields(BeatRecord):
            kind = "REAL" if item.name in {"source_duration", "suggested_start", "preview_start", "preview_duration"} else "INTEGER" if item.name in {"public_order", *BOOL_FIELDS} else "TEXT"
            columns.append(f"{item.name} {kind} NOT NULL")
        with closing(self.connect()) as connection:
            with connection:
                connection.execute(f"CREATE TABLE IF NOT EXISTS beats ({', '.join(columns)}, PRIMARY KEY(id), UNIQUE(slug), CHECK(status IN ('draft','ready','published','hidden','removed'))) ")
                connection.execute("CREATE INDEX IF NOT EXISTS beats_order_idx ON beats(public_order)")
                connection.execute("CREATE INDEX IF NOT EXISTS beats_fingerprint_idx ON beats(source_fingerprint)")
                connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('schema_version', '1')")

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _encode(record: BeatRecord) -> dict:
        values = record.to_dict()
        for name in JSON_FIELDS:
            values[name] = json.dumps(values[name], separators=(",", ":"))
        for name in BOOL_FIELDS:
            values[name] = int(values[name])
        return values

    @staticmethod
    def _decode(row: sqlite3.Row) -> BeatRecord:
        values = dict(row)
        for name in JSON_FIELDS:
            values[name] = tuple(json.loads(values[name] or "[]"))
        for name in BOOL_FIELDS:
            values[name] = bool(values[name])
        return BeatRecord(**values)

    @staticmethod
    def _validate(record: BeatRecord) -> None:
        if record.status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {record.status}")
        if not record.id or not record.slug:
            raise ValueError("id and slug are required")

    def upsert(self, record: BeatRecord) -> BeatRecord:
        self._validate(record)
        current = self.get(record.id)
        now = utc_now()
        record = replace(record, created_at=current.created_at if current else record.created_at or now, updated_at=now)
        values = self._encode(record)
        names = list(values)
        assignments = ", ".join(f"{name}=excluded.{name}" for name in names if name != "id")
        placeholders = ", ".join(f":{name}" for name in names)
        with self.transaction() as connection:
            connection.execute(
                f"INSERT INTO beats ({', '.join(names)}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {assignments}",
                values,
            )
        return record

    def get(self, beat_id: str) -> BeatRecord | None:
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM beats WHERE id = ?", (beat_id,)).fetchone()
        return self._decode(row) if row else None

    def list(self, status: str | None = None) -> list[BeatRecord]:
        params: tuple[str, ...] = ()
        query = "SELECT * FROM beats"
        if status:
            if status not in VALID_STATUSES:
                raise ValueError(f"invalid status: {status}")
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY public_order, created_at, id"
        with closing(self.connect()) as connection:
            return [self._decode(row) for row in connection.execute(query, params)]

    def update(self, beat_id: str, **changes) -> BeatRecord:
        current = self.get(beat_id)
        if not current:
            raise KeyError(beat_id)
        allowed = {item.name for item in fields(BeatRecord)} - {"id", "created_at", "updated_at"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
        return self.upsert(replace(current, **changes))

    def set_order(self, ids: list[str]) -> None:
        records = self.list()
        current_ids = [record.id for record in records]
        if len(ids) != len(set(ids)) or set(ids) != set(current_ids):
            raise ValueError("order must contain the complete unique beat list")
        now = utc_now()
        with self.transaction() as connection:
            for order, beat_id in enumerate(ids):
                connection.execute("UPDATE beats SET public_order = ?, updated_at = ? WHERE id = ?", (order, now, beat_id))

    def find_by_fingerprint(self, fingerprint: str) -> BeatRecord | None:
        if not fingerprint:
            return None
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM beats WHERE source_fingerprint = ?", (fingerprint,)).fetchone()
        return self._decode(row) if row else None

    def get_setting(self, key: str, default: str = "") -> str:
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.transaction() as connection:
            connection.execute("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
