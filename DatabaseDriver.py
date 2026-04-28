import sqlite3
from datetime import datetime
from typing import Callable, List, Optional, Sequence, Union
import AbstractionLayers
import IntellegentInterface as API_interface

from pathlib import Path

DB_PATH = "snapshots.db"
PathLikeOrMany = Union[str, Sequence[str]]


class SnapshotDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                raw_text TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                path TEXT NOT NULL,
                cache_result INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
            """
        )
        self.conn.commit()

    def save_snapshot(self, lines: Sequence[str], source: str = "FatCache") -> int:
        captured_at = datetime.now().isoformat(timespec="seconds")
        raw_text = "".join(lines)

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO snapshots (source, captured_at, raw_text) VALUES (?, ?, ?)",
            (source, captured_at, raw_text),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def save_cache_attempt(
        self,
        path: str,
        cache_result: int,
        snapshot_id: Optional[int] = None,
    ) -> int:
        checked_at = datetime.now().isoformat(timespec="seconds")

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO cache_attempts (snapshot_id, path, cache_result, checked_at)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, path, cache_result, checked_at),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def close(self) -> None:
        self.conn.close()


class SnapshotReceiver:
    def __init__(self, db: SnapshotDB):
        self.db = db
        self.last_snapshot_id: Optional[int] = None

    def handle_snapshot(self, strings_from_paul: Sequence[str]) -> int:
        snapshot_id = self.db.save_snapshot(strings_from_paul, source="FatCache")
        self.last_snapshot_id = snapshot_id

        print(f"\n=== SNAPSHOT {snapshot_id} ===")
        print("Data:")
        for line in strings_from_paul:
            print(line.rstrip("\n"))

        return snapshot_id

    def display_suggestions(self, suggestions: Sequence[str]) -> None:
        print("Suggestions:")
        if not suggestions:
            print("  (none)")
            return

        for suggestion in suggestions:
            print(f"  - {suggestion}")

    def handle_trycache_results(
        self,
        paths: Sequence[str],
        results: Sequence[int],
    ) -> None:
        print("Cache results:")
        if not paths:
            print("  (nothing to cache)")
            return

        for path, result in zip(paths, results):
            self.db.save_cache_attempt(
                path=path,
                cache_result=result,
                snapshot_id=self.last_snapshot_id,
            )
            print(f"  - {path}: {result}")


def normalize_paths(paths: PathLikeOrMany) -> List[str]:
    if isinstance(paths, str):
        return [paths]
    return [str(path) for path in paths]


def fetch_suggestions(
    what_to_send_to_ai: Sequence[str],
    original_batch_send: Callable[[Sequence[str]], PathLikeOrMany],
) -> PathLikeOrMany:
    # Preferred path once your API layer exists
    if API_interface is not None and hasattr(API_interface, "get_file_suggestions"):
        return API_interface.get_file_suggestions(what_to_send_to_ai)

    # Fallback to Paul's current shim/stub
    return original_batch_send(what_to_send_to_ai)


def patched_batch_send_factory(
    receiver: SnapshotReceiver,
    original_batch_send: Callable[[Sequence[str]], PathLikeOrMany],
):
    def patched_batch_send(what_to_send_to_ai: Sequence[str]) -> PathLikeOrMany:
        receiver.handle_snapshot(what_to_send_to_ai)

        suggestions = fetch_suggestions(what_to_send_to_ai, original_batch_send)
        receiver.display_suggestions(normalize_paths(suggestions))
        return suggestions

    return patched_batch_send


def patched_trycache_factory(
    receiver: SnapshotReceiver,
    original_try_cache: Callable[[str], int],
):
    def patched_try_cache(paths_to_cache: PathLikeOrMany):
        paths = normalize_paths(paths_to_cache)
        results = [original_try_cache(path) for path in paths]

        receiver.handle_trycache_results(paths, results)

        # Preserve a sensible return shape
        if isinstance(paths_to_cache, str):
            return results[0] if results else -1
        return results

    return patched_try_cache


def graph_cache_results(db_path: str = DB_PATH) -> None:
    """Create a simple SVG bar graph of cache attempt result counts."""
    graph_conn = sqlite3.connect(db_path)

    try:
        cursor = graph_conn.cursor()
        cursor.execute(
            """
            SELECT cache_result, COUNT(*)
            FROM cache_attempts
            GROUP BY cache_result
            ORDER BY cache_result
            """
        )
        rows = cursor.fetchall()
    finally:
        graph_conn.close()

    if not rows:
        print("\nNo cache attempts found yet, so no graph was created.")
        return

    max_count = max(count for _, count in rows)

    width = 600
    height = 400
    margin = 60
    bar_gap = 20
    bar_width = (width - 2 * margin - bar_gap * (len(rows) - 1)) / len(rows)
    graph_height = height - 2 * margin

    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="20">Cache Attempt Results</text>',
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="black"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="black"/>',
    ]

    for index, (cache_result, count) in enumerate(rows):
        bar_height = (count / max_count) * graph_height
        x = margin + index * (bar_width + bar_gap)
        y = height - margin - bar_height

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="steelblue"/>'
        )

        svg_parts.append(
            f'<text x="{x + bar_width / 2}" y="{height - margin + 20}" text-anchor="middle" font-size="12">Result {cache_result}</text>'
        )

        svg_parts.append(
            f'<text x="{x + bar_width / 2}" y="{y - 5}" text-anchor="middle" font-size="12">{count}</text>'
        )

    svg_parts.append("</svg>")

    output_file = Path(__file__).parent / "cache_attempt_results.svg"

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("\n".join(svg_parts))

    print(f"\nGraph saved as: {output_file.resolve()}")


def main() -> None:
    db = SnapshotDB(DB_PATH)
    receiver = SnapshotReceiver(db)

    original_batch_send = AbstractionLayers.BatchSend
    original_try_cache = AbstractionLayers.TryCache

    AbstractionLayers.BatchSend = patched_batch_send_factory(
        receiver, original_batch_send
    )

    AbstractionLayers.TryCache = patched_trycache_factory(
        receiver, original_try_cache
    )

    try:
        AbstractionLayers.FAstream(["fatrace", "-p", "1234"], DB_PATH)
    finally:
        db.close()
        graph_cache_results(DB_PATH)


if __name__ == "__main__":
    main()
