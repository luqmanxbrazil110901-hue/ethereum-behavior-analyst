import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import wallets, stats, labels
from app.services.indexer import block_indexer
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

indexer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global indexer_task
    logger.info("Starting block indexer...")
    indexer_task = asyncio.create_task(block_indexer.start())
    yield
    logger.info("Stopping block indexer...")
    block_indexer.stop()
    if indexer_task:
        indexer_task.cancel()
        try:
            await indexer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Ethereum Behavior Analyst API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallets.router)
app.include_router(stats.router)
app.include_router(labels.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
