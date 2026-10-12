import base64
import hashlib
import json
import os
import sqlite3
import uuid
import zlib
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Point, Scene, chunk_key
from design_workbench.domain.paintings import Painting

SCHEMA_VERSION = 3


def encode(value: Any) -> bytes:
    return zlib.compress(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def decode(value: bytes) -> Any:
    return json.loads(zlib.decompress(value))


def cell_from(value: dict[str, Any] | None) -> Cell | None:
    if value is None:
        return None
    return Cell(
        BlockState.make(value["name"], value.get("properties", {})),
        value.get("group", "main"),
        value.get("region", "design"),
    )


def metadata(scene: Scene) -> dict[str, Any]:
    return {
        "id": scene.id,
        "name": scene.name,
        "minecraft_version": scene.minecraft_version,
        "data_version": scene.data_version,
        "bounds": scene.bounds.as_dict(),
        "protected": sorted(scene.protected),
        "paintings": [p.as_dict() for p in scene.paintings],
    }


@dataclass(slots=True)
class RenderRead:
    data_version: int
    metadata: dict[str, Any]
    chunks: dict[Point, bytes]
    source: bytes | None
    history: dict[str, Any]


def decode_chunk(key: Point, value: bytes) -> dict[Point, Cell]:
    try:
        payload = decode(value)
        palette = [
            BlockState.make(state["name"], state["properties"]) for state in payload["palette"]
        ]
        return {
            (
                key[0] * 16 + index % 16,
                key[1] * 16 + index // 256,
                key[2] * 16 + index // 16 % 16,
            ): Cell(palette[state], group, region)
            for index, state, group, region in payload["cells"]
        }
    except (zlib.error, UnicodeDecodeError, ValueError, KeyError, TypeError, IndexError) as error:
        raise WorkbenchError("DATABASE_CORRUPT", f"项目分块 {key} 损坏或格式不受支持。") from error


class SqliteStore:
    def __init__(self, path: Path, timeout: float = 10.0) -> None:
        self.path = path.resolve()
        self.timeout = timeout
        if not self.path.is_file():
            raise WorkbenchError("PROJECT_NOT_FOUND", f"项目不存在：{self.path}。")
        self._ensure_schema()

    @classmethod
    def create(
        cls,
        path: Path,
        name: str,
        version: str,
        data_version: int,
        bounds: Bounds,
        timeout: float = 10.0,
        creation: dict[str, Any] | None = None,
    ) -> "SqliteStore":
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise WorkbenchError("PROJECT_EXISTS", "项目已存在；不会覆盖。") from error
        os.close(descriptor)
        store = cls(path, timeout)
        scene = Scene(str(uuid.uuid4()), name, version, data_version, 0, bounds)
        with store.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO meta(key,value) VALUES('scene',?)",
                (json.dumps({**metadata(scene), "revision": 0, "cursor": 0}),),
            )
            if creation is not None:
                connection.execute(
                    "INSERT INTO meta(key,value) VALUES('creation',?)", (json.dumps(creation),)
                )
            connection.commit()
        return store

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        except sqlite3.OperationalError as error:
            connection.rollback()
            code = "DATABASE_BUSY" if "locked" in str(error) else "DATABASE_ERROR"
            raise WorkbenchError(code, str(error)) from error
        except sqlite3.DatabaseError as error:
            connection.rollback()
            raise WorkbenchError("DATABASE_CORRUPT", "项目数据库损坏或格式不受支持。") from error
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise WorkbenchError(
                    "FUTURE_SCHEMA", f"数据库 schema {version} 高于当前 {SCHEMA_VERSION}。"
                )
            if version == 0:
                existing = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if existing:
                    raise WorkbenchError("UNKNOWN_SCHEMA", "未识别的数据库；不自动改写。")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("BEGIN IMMEDIATE")
                for statement in (
                    "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)",
                    "CREATE TABLE chunks(x INTEGER,y INTEGER,z INTEGER,payload BLOB NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(x,y,z))",
                    "CREATE TABLE commands(sequence INTEGER PRIMARY KEY,payload BLOB NOT NULL)",
                    "CREATE TABLE events(revision INTEGER PRIMARY KEY,kind TEXT NOT NULL,changed INTEGER NOT NULL,request_id TEXT NOT NULL,created TEXT NOT NULL)",
                    "CREATE TABLE attachments(key TEXT PRIMARY KEY,payload BLOB NOT NULL)",
                    "CREATE TABLE requests(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,response TEXT NOT NULL)",
                ):
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                connection.commit()
            elif version in {1, 2}:
                backup = self.path.with_name(
                    self.path.name + f".v{version}-backup-{uuid.uuid4().hex[:8]}"
                )
                with sqlite3.connect(backup) as backup_connection:
                    connection.backup(backup_connection)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    if version == 1:
                        connection.execute(
                            "CREATE TABLE requests(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,response TEXT NOT NULL)"
                        )
                    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                    connection.commit()
                except sqlite3.DatabaseError:
                    connection.rollback()
                    raise

    @staticmethod
    def _meta(connection: sqlite3.Connection) -> dict[str, Any]:
        row = connection.execute("SELECT value FROM meta WHERE key='scene'").fetchone()
        if row is None:
            raise WorkbenchError("INVALID_PROJECT", "项目没有场景元数据。")
        return json.loads(row[0])  # type: ignore[no-any-return]

    @staticmethod
    def _cells(connection: sqlite3.Connection) -> dict[Point, Cell]:
        cells: dict[Point, Cell] = {}
        for row in connection.execute("SELECT x,y,z,payload FROM chunks"):
            cells.update(decode_chunk((row["x"], row["y"], row["z"]), row["payload"]))
        return cells

    def open_render_reader(self) -> sqlite3.Connection:
        """A persistent read-only observer; callers serialize access and close it."""
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=ro",
            uri=True,
            timeout=self.timeout,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def read_render_data(
        self, connection: sqlite3.Connection, previous_version: int | None
    ) -> RenderRead | None:
        """Read a coherent projection without decompressing any cells.

        data_version is meaningful only on this same long-lived connection. It
        detects all other connections' commits, including writes that do not
        advance scene/chunk revisions. Unchanged requests read no chunk BLOBs.
        """
        try:
            connection.execute("BEGIN")
            version = int(connection.execute("PRAGMA data_version").fetchone()[0])
            if previous_version == version:
                return None
            data = self._meta(connection)
            chunks = {
                (row["x"], row["y"], row["z"]): bytes(row["payload"])
                for row in connection.execute("SELECT x,y,z,payload FROM chunks")
            }
            row = connection.execute(
                "SELECT payload FROM attachments WHERE key='litematic'"
            ).fetchone()
            return RenderRead(
                version,
                data,
                chunks,
                bytes(row[0]) if row else None,
                self._history_info(connection, data),
            )
        except sqlite3.OperationalError as error:
            code = "DATABASE_BUSY" if "locked" in str(error) else "DATABASE_ERROR"
            raise WorkbenchError(code, str(error)) from error
        except sqlite3.DatabaseError as error:
            raise WorkbenchError("DATABASE_CORRUPT", "项目数据库损坏或格式不受支持。") from error
        finally:
            connection.rollback()

    def load(self) -> Scene:
        return self.snapshot(include_source=False)[0]

    def game_version(self) -> tuple[str, int]:
        """Read version metadata without decoding the project's chunks."""
        with self.connection() as connection:
            data = self._meta(connection)
            return str(data["minecraft_version"]), int(data["data_version"])

    def snapshot(self, include_source: bool = True) -> tuple[Scene, bytes | None]:
        """Read cells and their NBT source in one SQLite read transaction."""
        with self.connection() as connection:
            connection.execute("BEGIN")
            data = self._meta(connection)
            cells = self._cells(connection)
            protected = {tuple(point) for point in data.get("protected", [])}
            source = (
                connection.execute(
                    "SELECT payload FROM attachments WHERE key='litematic'"
                ).fetchone()
                if include_source
                else None
            )
            return Scene(
                data["id"],
                data["name"],
                data["minecraft_version"],
                data["data_version"],
                data["revision"],
                Bounds(tuple(data["bounds"]["low"]), tuple(data["bounds"]["high"])),
                cells,
                protected,
                [Painting.from_dict(value) for value in data.get("paintings", [])],
            ), bytes(source[0]) if source else None

    def creation(self) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute("SELECT value FROM meta WHERE key='creation'").fetchone()
            return json.loads(row[0]) if row else None

    def replay(self, request_id: str, fingerprint: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            return self._replay(connection, request_id, fingerprint)

    def receipt(
        self, request_id: str, fingerprint: str, operation: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        """Serialize an external asset publication and persist its retry result."""
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            result = self._replay(connection, request_id, fingerprint)
            if result is not None:
                return result
            result = operation()
            connection.execute(
                "INSERT INTO requests VALUES(?,?,?)", (request_id, fingerprint, json.dumps(result))
            )
            connection.commit()
            return result

    @staticmethod
    def _replay(
        connection: sqlite3.Connection, request_id: str, fingerprint: str
    ) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT fingerprint,response FROM requests WHERE id=?", (request_id,)
        ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != fingerprint:
            raise WorkbenchError("REQUEST_ID_REUSED", "同一个 request_id 不能用于不同请求。")
        return json.loads(row["response"])  # type: ignore[no-any-return]

    def _write_chunks(
        self,
        connection: sqlite3.Connection,
        cells: dict[Point, Cell],
        keys: set[Point],
        revision: int,
    ) -> None:
        if not keys:
            return
        grouped: dict[Point, list[tuple[Point, Cell]]] = defaultdict(list)
        if len(keys) * 16**3 <= len(cells):
            # A bounded spatial lookup avoids scanning a 100k-cell scene for a
            # single edited chunk. Large/sparse edits use the original scan.
            for key in keys:
                x0, y0, z0 = (value * 16 for value in key)
                for x in range(x0, x0 + 16):
                    for y in range(y0, y0 + 16):
                        for z in range(z0, z0 + 16):
                            point = (x, y, z)
                            cell = cells.get(point)
                            if cell is not None:
                                grouped[key].append((point, cell))
        else:
            for point, cell in cells.items():
                key = chunk_key(point)
                if key in keys:
                    grouped[key].append((point, cell))
        for key in keys:
            if not grouped[key]:
                connection.execute("DELETE FROM chunks WHERE x=? AND y=? AND z=?", key)
                continue
            palette: list[dict[str, object]] = []
            indices: dict[BlockState, int] = {}
            entries = []
            for point, cell in sorted(grouped[key]):
                if cell.state not in indices:
                    indices[cell.state] = len(palette)
                    palette.append(cell.state.as_dict())
                index = point[0] % 16 + (point[2] % 16) * 16 + (point[1] % 16) * 256
                entries.append([index, indices[cell.state], cell.group, cell.region])
            connection.execute(
                "INSERT INTO chunks VALUES(?,?,?,?,?) ON CONFLICT(x,y,z) DO UPDATE SET payload=excluded.payload,revision=excluded.revision",
                (*key, encode({"palette": palette, "cells": entries}), revision),
            )

    def commit(
        self,
        scene: Scene,
        changes: list[tuple[Point, Cell | None, Cell | None]],
        expected_revision: int,
        request_id: str,
        fingerprint: str,
        attachment: bytes | None = None,
    ) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(connection, request_id, fingerprint)
            if replay is not None:
                return replay
            before = self._meta(connection)
            if before["revision"] != expected_revision:
                raise WorkbenchError(
                    "REVISION_CONFLICT", "场景已被修改，请重新读取。", revision=before["revision"]
                )
            revision = expected_revision + 1
            keys = {chunk_key(point) for point, _, _ in changes}
            self._write_chunks(connection, scene.cells, keys, revision)
            delta: dict[str, Any] = {
                "changes": [
                    [point, old.as_dict() if old else None, new.as_dict() if new else None]
                    for point, old, new in changes
                ],
                "before": before,
                "after": metadata(scene),
            }
            if attachment is not None:
                previous = connection.execute(
                    "SELECT payload FROM attachments WHERE key='litematic'"
                ).fetchone()
                delta["attachment_before"] = (
                    base64.b64encode(previous[0]).decode() if previous else None
                )
                delta["attachment_after"] = base64.b64encode(attachment).decode()
                connection.execute(
                    "INSERT INTO attachments VALUES('litematic',?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload",
                    (attachment,),
                )
            sequence = before["cursor"] + 1
            connection.execute("DELETE FROM commands WHERE sequence>?", (before["cursor"],))
            connection.execute("INSERT INTO commands VALUES(?,?)", (sequence, encode(delta)))
            connection.execute(
                "UPDATE meta SET value=? WHERE key='scene'",
                (json.dumps({**metadata(scene), "revision": revision, "cursor": sequence}),),
            )
            response = {
                "revision": revision,
                "changed": len(changes),
                "paintings_changed": int(
                    before.get("paintings", []) != metadata(scene)["paintings"]
                ),
                "changed_chunks": [list(key) for key in sorted(keys)],
                "request_id": request_id,
            }
            kind = "import" if attachment is not None else "edit"
            if attachment is None and not changes and before["name"] != scene.name:
                kind = "rename"
            self._record(connection, response, fingerprint, kind)
            connection.commit()
            return response

    @staticmethod
    def _record(
        connection: sqlite3.Connection, response: dict[str, Any], fingerprint: str, kind: str
    ) -> None:
        connection.execute(
            "INSERT INTO requests VALUES(?,?,?)",
            (response["request_id"], fingerprint, json.dumps(response)),
        )
        connection.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)",
            (
                response["revision"],
                kind,
                response["changed"],
                response["request_id"],
                datetime.now(UTC).isoformat(),
            ),
        )

    def history(
        self, direction: str, expected_revision: int, request_id: str, fingerprint: str
    ) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = self._replay(connection, request_id, fingerprint)
            if replay is not None:
                return replay
            before = self._meta(connection)
            if before["revision"] != expected_revision:
                raise WorkbenchError(
                    "REVISION_CONFLICT", "场景已被修改，请重新读取。", revision=before["revision"]
                )
            undo = direction == "undo"
            sequence = before["cursor"] if undo else before["cursor"] + 1
            command = connection.execute(
                "SELECT payload FROM commands WHERE sequence=?", (sequence,)
            ).fetchone()
            if command is None or (undo and before["cursor"] == 0):
                raise WorkbenchError("HISTORY_EMPTY", "没有可撤销/重做的操作。")
            delta = decode(command[0])
            cells = self._cells(connection)
            keys = set()
            for point, old, new in delta["changes"]:
                position = tuple(point)
                cell = cell_from(old if undo else new)
                if cell is None:
                    cells.pop(position, None)
                else:
                    cells[position] = cell
                keys.add(chunk_key(position))
            revision = expected_revision + 1
            self._write_chunks(connection, cells, keys, revision)
            target = delta["before"] if undo else delta["after"]
            connection.execute(
                "UPDATE meta SET value=? WHERE key='scene'",
                (
                    json.dumps(
                        {
                            **target,
                            "revision": revision,
                            "cursor": sequence - 1 if undo else sequence,
                        }
                    ),
                ),
            )
            if "attachment_after" in delta:
                value = delta["attachment_before"] if undo else delta["attachment_after"]
                if value is None:
                    connection.execute("DELETE FROM attachments WHERE key='litematic'")
                else:
                    connection.execute(
                        "INSERT INTO attachments VALUES('litematic',?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload",
                        (base64.b64decode(value),),
                    )
            response = {
                "revision": revision,
                "changed": len(delta["changes"]),
                "changed_chunks": [list(key) for key in sorted(keys)],
                "request_id": request_id,
            }
            self._record(connection, response, fingerprint, direction)
            connection.commit()
            return response

    def attachment(self) -> bytes | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload FROM attachments WHERE key='litematic'"
            ).fetchone()
            return bytes(row[0]) if row else None

    def history_info(self) -> dict[str, Any]:
        with self.connection() as connection:
            data = self._meta(connection)
            return self._history_info(connection, data)

    @staticmethod
    def _history_info(connection: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
        count = connection.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
        events = [
            dict(row)
            for row in connection.execute("SELECT * FROM events ORDER BY revision DESC LIMIT 30")
        ]
        return {
            "undo_available": data["cursor"],
            "redo_available": count - data["cursor"],
            "events": events,
        }

    def chunk_versions(self) -> dict[str, str]:
        with self.connection() as connection:
            return {
                f"{row['x']},{row['y']},{row['z']}": hashlib.sha256(row["payload"]).hexdigest()[:16]
                for row in connection.execute("SELECT x,y,z,payload FROM chunks")
            }
