from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.profiles import router as profiles_router
from app.routes.cinema import router as cinema_router

app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
    title="Online Cinema API",
    description=(
        "REST API for an online cinema platform with user authentication, "
        "profiles, movie discovery, and favorite movies."
    ),
    version="1.0.0",
)

api_prefix = "/api"

app.include_router(
    auth_router, prefix=f"{api_prefix}/accounts", tags=["Authentication"]
)
app.include_router(profiles_router, prefix=f"{api_prefix}/users", tags=["Profiles"])
app.include_router(cinema_router, prefix=f"{api_prefix}/cinema", tags=["Movies"])
