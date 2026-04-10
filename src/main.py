from fastapi import FastAPI
from sqladmin import Admin
from src.core.database import engine
from src.admin import admin_views
from src.core.config import settings
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# Router imports
from src.api.v1.auth import router as auth_router
from src.api.v1.barber import router as barber_router
from src.api.v1.client import router as client_router
from src.api.v1.service import router as service_router
from src.api.v1.region import router as region_router
from src.api.v1.user import router as user_router

app = FastAPI(title=settings.PROJECT_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach sqladmin
admin = Admin(app, engine)
for view in admin_views:
    admin.add_view(view)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(barber_router, prefix="/api/v1/barber", tags=["Barber"])
app.include_router(client_router, prefix="/api/v1/client", tags=["Client"])
app.include_router(service_router, prefix="/api/v1/service", tags=["Service"])
app.include_router(region_router, prefix="/api/v1/region", tags=["Region"])
app.include_router(user_router, prefix="/api/v1/user", tags=["User"])

# Serve Mini App static files
# Ensure the directory exists to avoid errors on startup
frontend_dist = os.path.join(os.getcwd(), "mini-app", "dist")
if os.path.exists(frontend_dist):
    app.mount("/mini-app", StaticFiles(directory=frontend_dist, html=True), name="mini-app")

@app.get("/")
async def root():
    return {"message": "Welcome to Cutzilla FastAPI backend"}
