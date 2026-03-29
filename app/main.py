from contextlib import contextmanager

from fastapi import FastAPI

from .api.v1.metrics import metric_router


@contextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI()
app.include_router(metric_router)
