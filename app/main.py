from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.profiles import router as profiles_router
from app.routes.cinema import router as cinema_router
from fastapi import Depends
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.core.docs import verify_docs_user

app = FastAPI(
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
    title="Online Cinema API",
    description=(
        "REST API for an online cinema platform with user authentication, "
        "profiles, movie discovery, and favorite movies."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


api_prefix = "/api"

app.include_router(
    auth_router, prefix=f"{api_prefix}/accounts", tags=["Authentication"]
)
app.include_router(profiles_router, prefix=f"{api_prefix}/users", tags=["Profiles"])
app.include_router(cinema_router, prefix=f"{api_prefix}/cinema", tags=["Movies"])


@app.get(
    "/docs",
    include_in_schema=False,
    dependencies=[Depends(verify_docs_user)],
)
async def swagger_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get(
    "/openapi.json",
    include_in_schema=False,
    dependencies=[Depends(verify_docs_user)],
)
async def openapi_schema():
    return JSONResponse(
        content=app.openapi(),
    )
