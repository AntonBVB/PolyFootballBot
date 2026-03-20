from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: int
    action: Callable[[], None]
    last_run_monotonic: float = 0.0

    def should_run(self, now_monotonic: float) -> bool:
        return self.last_run_monotonic == 0.0 or now_monotonic - self.last_run_monotonic >= self.interval_seconds

    def run(self, now_monotonic: float) -> None:
        try:
            logger.info("TASK_START name=%s", self.name)
            self.action()
        except Exception:
            logger.exception("TASK_FAILED name=%s", self.name)
        finally:
            self.last_run_monotonic = now_monotonic


class Scheduler:
    def __init__(self, tasks: list[ScheduledTask], loop_sleep_seconds: int = 1) -> None:
        self.tasks = tasks
        self.loop_sleep_seconds = loop_sleep_seconds

    def run_forever(self) -> None:
        logger.info("SCHEDULER_STARTED tasks=%s", [task.name for task in self.tasks])
        while True:
            self.run_once()
            time.sleep(self.loop_sleep_seconds)

    def run_once(self) -> None:
        now_monotonic = time.monotonic()
        for task in self.tasks:
            if task.should_run(now_monotonic):
                task.run(now_monotonic)
