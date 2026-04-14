from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.db import Base, engine
from app.services.storage_service import storage_service
from app.web.routes import router as web_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/media", StaticFiles(directory=str(settings.media_root)), name="media")

    app.include_router(web_router)

    @app.on_event("startup")
    def on_startup() -> None:
        storage_service.ensure_dirs()
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
