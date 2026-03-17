import logging
import time

from .config import Settings

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run_forever(self) -> None:
        logger.info("SCHEDULER_STARTED interval_seconds=%s", self.settings.scheduler_interval_seconds)
        while True:
            self._tick()
            time.sleep(self.settings.scheduler_interval_seconds)

    def run_once(self) -> None:
        self._tick()

    def _tick(self) -> None:
        logger.debug("SCHEDULER_TICK mode=%s", self.settings.app_mode)
        logger.info("NOOP_TICK no trading logic implemented yet")
