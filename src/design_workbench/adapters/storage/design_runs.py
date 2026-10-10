"""Durable AI task records and immutable full SQLite candidate snapshots."""

import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from design_workbench.domain.errors import WorkbenchError


class DesignStore:
    def __init__(self, data_dir: Path, timeout: float = 10) -> None:
        self.directory = data_dir / "design-candidates"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "design-runs.sqlite3"
        self.timeout = timeout
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise WorkbenchError(
                    "FUTURE_SCHEMA", f"设计任务 schema {version} 高于当前支持的 1。"
                )
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, body TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS receipts(key TEXT PRIMARY KEY, digest TEXT NOT NULL,"
                " result TEXT NOT NULL);"
            )
            connection.execute("PRAGMA user_version=1")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        except sqlite3.OperationalError as error:
            raise WorkbenchError("DESIGN_BUSY", "设计任务正在更新，请稍后重试。") from error
        except sqlite3.DatabaseError as error:
            raise WorkbenchError("DESIGN_CORRUPT", "设计任务数据库损坏，原文件仍保留。") from error
        finally:
            connection.close()

    @contextmanager
    def edit(self, identifier: str) -> Iterator[dict[str, Any]]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT body FROM runs WHERE id=?", (identifier,)
                ).fetchone()
                if row is None:
                    raise WorkbenchError("DESIGN_NOT_FOUND", "设计任务不存在。")
                record: dict[str, Any] = json.loads(row[0])
                yield record
                connection.execute(
                    "UPDATE runs SET body=? WHERE id=?", (json.dumps(record), identifier)
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def create(self, identifier: str, digest: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT body FROM runs WHERE id=?", (identifier,)).fetchone()
            if row is not None:
                existing: dict[str, Any] = json.loads(row[0])
                if existing["digest"] != digest:
                    raise WorkbenchError("REQUEST_ID_REUSED", "任务 request_id 已用于另一组参数。")
                return existing
            for row in connection.execute("SELECT body FROM runs"):
                other = json.loads(row[0])
                if other["project"] == record["project"] and other["status"] in {
                    "active",
                    "awaiting_approval",
                }:
                    raise WorkbenchError(
                        "DESIGN_BUSY", "此项目已有进行中的设计任务，请先取消或完成。"
                    )
            record["digest"] = digest
            connection.execute("INSERT INTO runs VALUES(?,?)", (identifier, json.dumps(record)))
            connection.commit()
            return record

    def list(self, project: str) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute("SELECT body FROM runs ORDER BY rowid DESC").fetchall()
            return [record for row in rows if (record := json.loads(row[0]))["project"] == project]

    def snapshot(self, project: Path, identifier: str, revision: int) -> tuple[str, int]:
        target = self.candidate_path(identifier)
        temporary = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
        try:
            with closing(sqlite3.connect(project, timeout=self.timeout)) as source:
                source.execute("BEGIN")
                metadata = json.loads(
                    source.execute("SELECT value FROM meta WHERE key='scene'").fetchone()[0]
                )
                if metadata["revision"] != revision:
                    raise WorkbenchError(
                        "REVISION_CONFLICT",
                        "保存候选稿前场景已变化。",
                        revision=metadata["revision"],
                    )
                with closing(sqlite3.connect(temporary)) as destination:
                    source.backup(destination)
            payload = temporary.read_bytes()
            if target.exists():
                # A crash before the task receipt may leave an already published snapshot.
                with closing(sqlite3.connect(target)) as existing:
                    row = existing.execute("SELECT value FROM meta WHERE key='scene'").fetchone()
                if row is None or json.loads(row[0])["revision"] != revision:
                    raise WorkbenchError("CANDIDATE_CORRUPT", "候选稿编号已有不同修订的快照。")
                return hashlib.sha256(target.read_bytes()).hexdigest(), target.stat().st_size
            os.link(temporary, target)
            return hashlib.sha256(payload).hexdigest(), len(payload)
        finally:
            temporary.unlink(missing_ok=True)

    def candidate_path(self, identifier: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise WorkbenchError("INVALID_CANDIDATE", "候选稿标识非法。")
        return self.directory / f"{identifier}.dwbench"

    def open_candidate(
        self, identifier: str, request_id: str, projects: Path, name: str, sha256: str
    ) -> str:
        target_id = hashlib.sha256(f"{identifier}:{request_id}".encode()).hexdigest()[:32]
        source_path = self.candidate_path(identifier)
        if (
            not source_path.is_file()
            or hashlib.sha256(source_path.read_bytes()).hexdigest() != sha256
        ):
            raise WorkbenchError("CANDIDATE_CORRUPT", "候选稿快照缺失或校验失败。")
        target = projects / f"{target_id}.dwbench"
        key = f"candidate:{identifier}:{request_id}"
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT result FROM receipts WHERE key=?", (key,)).fetchone()
            if row:
                return str(json.loads(row[0])["project_id"])
            if target.exists():
                # A crash after the backup but before the receipt is recoverable.
                with closing(sqlite3.connect(target)) as existing:
                    marker = existing.execute(
                        "SELECT value FROM meta WHERE key='candidate_origin'"
                    ).fetchone()
                if marker is None or marker[0] != key:
                    raise WorkbenchError("PROJECT_EXISTS", "候选稿项目路径已经存在。")
            else:
                temporary = projects / f".{target_id}.{uuid.uuid4().hex}.tmp"
                try:
                    with (
                        closing(sqlite3.connect(source_path)) as source,
                        closing(sqlite3.connect(temporary)) as destination,
                    ):
                        source.backup(destination)
                        metadata = json.loads(
                            destination.execute(
                                "SELECT value FROM meta WHERE key='scene'"
                            ).fetchone()[0]
                        )
                        metadata.update(id=str(uuid.uuid4()), name=name)
                        destination.execute(
                            "UPDATE meta SET value=? WHERE key='scene'", (json.dumps(metadata),)
                        )
                        destination.execute(
                            "INSERT OR REPLACE INTO meta VALUES('candidate_origin',?)", (key,)
                        )
                        destination.commit()
                    os.link(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
            connection.execute(
                "INSERT INTO receipts VALUES(?,?,?)",
                (key, sha256, json.dumps({"project_id": target_id})),
            )
            connection.commit()
        return target_id
