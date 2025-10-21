from fastapi import FastAPI, Request,status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from .routers import blog,login_log
from contextlib import asynccontextmanager
from db import engine
from sqlmodel import SQLModel



@asynccontextmanager
async def lifespan(app:FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI()


app.mount("/app/static",StaticFiles(directory="app/static"),name="static")


app.include_router(blog.router)
app.include_router(login_log.router)