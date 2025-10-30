# admin_app/main.py
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
import os
from sqlalchemy.orm import selectinload
# Reuse your DB and models
from app.db import async_engine as engine  # ✅ import existing engine
from app.models import User, Barber, Client, Service, ClientRequest
from dotenv import load_dotenv

load_dotenv()


def _full_name(u):
    if not u:
        return "—"
    return (f"{u.name or ''} {u.surname or ''}").strip() or "—"


class SimpleAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if (form.get("username") == os.getenv("ADMIN_USER", "admin") and
                form.get("password") == os.getenv("ADMIN_PASS", "admin123")):
            request.session.update({"authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("authenticated", False)


app = FastAPI(title="CutZilla Admin")
app.secret_key = os.getenv("ADMIN_SECRET")


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, User.telegram_id, User.lang]
    column_searchable_list = [User.name, User.telegram_id]
    column_sortable_list = [User.id]
    page_size = 50


class BarberAdmin(ModelView, model=Barber):
    column_list = [Barber.id, Barber.user]
    column_labels = {Barber.user: "User"}
    page_size = 50
    column_formatters = {
        Barber.user: lambda m, a: _full_name(getattr(m, "user", None)),
    }

    async def scaffold_list_query(self, session):
        from sqlalchemy import select
        return select(Barber).options(selectinload(Barber.user))


class ClientAdmin(ModelView, model=Client):
    column_list = [Client.id, Client.user]
    column_labels = {Client.user: "User"}
    page_size = 50

    column_formatters = {
        Client.user: lambda m, a: _full_name(getattr(m, "user", None)),
    }

    async def scaffold_list_query(self, session):
        from sqlalchemy import select
        return select(Client).options(selectinload(Client.user))


class ServiceAdmin(ModelView, model=Service):
    column_list = [Service.id, Service.name_ru, Service.name_uz, Service.disabled]
    page_size = 50


class ClientRequestAdmin(ModelView, model=ClientRequest):
    column_list = [
        ClientRequest.id,
        ClientRequest.client,  # will be formatted below
        ClientRequest.barber,  # will be formatted below
        ClientRequest.status,
        ClientRequest.date,
        ClientRequest.from_time,
        ClientRequest.to_time,
    ]
    column_labels = {
        ClientRequest.client: "Client",
        ClientRequest.barber: "Barber",
    }
    page_size = 50

    column_formatters = {
        ClientRequest.client: lambda m, a: (
                f"{getattr(getattr(m.client, 'user', None), 'name', '')} "
                f"{getattr(getattr(m.client, 'user', None), 'surname', '')}".strip() or "—"
        ),
        ClientRequest.barber: lambda m, a: (
                f"{getattr(getattr(m.barber, 'user', None), 'name', '')} "
                f"{getattr(getattr(m.barber, 'user', None), 'surname', '')}".strip() or "—"
        ),
    }


admin = Admin(app, engine, authentication_backend=SimpleAuth(secret_key=app.secret_key))
admin.add_view(UserAdmin)
admin.add_view(BarberAdmin)
admin.add_view(ClientAdmin)
admin.add_view(ServiceAdmin)
admin.add_view(ClientRequestAdmin)


@app.get("/")
async def root():
    return RedirectResponse("/admin")
