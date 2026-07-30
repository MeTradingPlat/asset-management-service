import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.server import create_app
from app.config import settings
from app.db.init_schema import apply_schema
from app.discovery.symbol_poller import SymbolPoller
from app.ingestion.scheduler import Scheduler

logging.basicConfig(level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _run_symbol_poller_loop(poller: SymbolPoller, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            poller.poll()
        except Exception as e:
            logger.error("SymbolPoller loop failed: %s", e)
        stop_event.wait(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_schema()

    poller = SymbolPoller()
    poller_stop = threading.Event()
    poller_thread = threading.Thread(
        target=_run_symbol_poller_loop, args=(poller, poller_stop), name="hd-symbol-poller", daemon=True,
    )
    poller_thread.start()

    scheduler = Scheduler()
    scheduler.start()

    logger.info("historical-data-service started")
    yield

    poller_stop.set()
    scheduler.stop()


app = create_app(lifespan=lifespan)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)
