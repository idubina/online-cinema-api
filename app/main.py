from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.profiles import router as profiles_router
from app.routes.cinema import router as cinema_router

app = FastAPI()

api_prefix = "/api"

app.include_router(auth_router, prefix=f"{api_prefix}/accounts")
app.include_router(profiles_router, prefix=f"{api_prefix}/users")
app.include_router(cinema_router, prefix=f"{api_prefix}/cinema")
