"""Bounded process memoization for verified, read-only analytical snapshots."""

from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from threading import Event, Lock


def file_stamp(path):
    path = Path(path)
    try:
        stat = path.stat()
    except FileNotFoundError:
        return (str(path), None)
    return (str(path), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def snapshot_token(database, root):
    database, root = Path(database).resolve(), Path(root).resolve()
    paths = [database, Path(str(database) + '-wal')]
    for folder in ('app/config/analytics', 'app/sql/analytics'):
        paths.extend(sorted(path for path in (root / folder).rglob('*') if path.is_file()))
    return tuple(file_stamp(path) for path in paths)


class SnapshotMemo:
    """Share successful immutable results, never connections or failed checks."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.entries = OrderedDict()
        self.inflight = {}
        self.lock = Lock()

    def get(self, key, build, valid):
        while True:
            with self.lock:
                if key in self.entries:
                    self.entries.move_to_end(key)
                    return deepcopy(self.entries[key])
                event = self.inflight.get(key)
                if event is None:
                    self.inflight[key] = Event()
                    break
            event.wait()
        try:
            result = build()
            # A reader can finish on its original SQLite transaction after the
            # live file changes. That result must not validate the new snapshot.
            if valid():
                with self.lock:
                    self.entries[key] = deepcopy(result)
                    while len(self.entries) > self.capacity:
                        self.entries.popitem(last=False)
            return result
        finally:
            with self.lock:
                self.inflight.pop(key).set()
