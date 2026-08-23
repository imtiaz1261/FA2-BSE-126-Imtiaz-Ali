import os
import time
import threading

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _HAS_WATCHDOG = True
except ImportError:
    _HAS_WATCHDOG = False


class PollingWatcher:
    """Dependency-free fallback: snapshots mtimes and diffs on an interval.
    Good enough for incremental re-indexing without requiring `watchdog`."""

    def __init__(self, root: str, on_change, interval: float = 1.0):
        self.root, self.on_change, self.interval = root, on_change, interval
        self._mtimes: dict[str, float] = {}
        self._stop = threading.Event()

    def _snapshot(self) -> dict[str, float]:
        from .scanner import walk_repo
        return {p: os.path.getmtime(p) for p in walk_repo(self.root)}

    def start(self):
        self._mtimes = self._snapshot()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            time.sleep(self.interval)
            current = self._snapshot()
            changed = [p for p, m in current.items() if self._mtimes.get(p) != m]
            deleted = [p for p in self._mtimes if p not in current]
            for p in changed:
                self.on_change(p, deleted=False)
            for p in deleted:
                self.on_change(p, deleted=True)
            self._mtimes = current

    def stop(self):
        self._stop.set()


def make_watcher(root: str, on_change):
    """Returns a watcher with .start()/.stop(). Uses watchdog (event-driven,
    via git hooks or FS events) when available, else falls back to polling."""
    if not _HAS_WATCHDOG:
        return PollingWatcher(root, on_change)

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                on_change(event.src_path, deleted=False)

        def on_created(self, event):
            if not event.is_directory:
                on_change(event.src_path, deleted=False)

        def on_deleted(self, event):
            if not event.is_directory:
                on_change(event.src_path, deleted=True)

    class _WatchdogWatcher:
        def __init__(self):
            self._observer = Observer()
            self._observer.schedule(_Handler(), root, recursive=True)

        def start(self):
            self._observer.start()

        def stop(self):
            self._observer.stop()
            self._observer.join()

    return _WatchdogWatcher()
