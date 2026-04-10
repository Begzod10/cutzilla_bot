# app: client/api/views.py

from django.db import transaction, IntegrityError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.client.models import Client
from apps.users.models import Users


class SyncUserView(APIView):
    def post(self, request):
        data = request.data
        telegram_id = data.get("telegram_id")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        role = data.get("role") or "client"
        lang = data.get("lang") or "uz"
        username = data.get("username") or str(telegram_id)
        client_id = data.get("client_id")

        from django.contrib.auth.hashers import make_password

        raw_password = "12345678"  # (better: generate one)
        user, created = Users.objects.get_or_create(
            telegram_id=telegram_id,
            username=telegram_id,
            defaults=dict(
                first_name=first_name,
                last_name=last_name,
                role=role,

                password=make_password(raw_password),  # ← hashed
            ),
        )
        if not created:
            # update fields to keep in sync
            changed = False
            for fld, val in (
                    ("first_name", first_name),
                    ("last_name", last_name),
                    ("role", role),
                    ("username", username),
            ):
                if val is not None and getattr(user, fld) != val:
                    setattr(user, fld, val)
                    changed = True
            if changed:
                user.save(update_fields=["first_name", "last_name", "role", "username"])
        client, created = Client.objects.get_or_create(user=user, external_id=client_id)
        return Response({"id": user.id, "created": created}, status=200)
