# api/v1/users/views.py  (django project)
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny  # or your auth
# from rest_framework.authentication import TokenAuthentication  # if using token auth
from apps.users.models import Users

VALID_ROLES = {r[0] for r in Users.ROLES}


class SyncUserView(APIView):
    permission_classes = [AllowAny]  # adjust if you use token

    # authentication_classes = [TokenAuthentication]

    def post(self, request):
        data = request.data or {}
        telegram_id = data.get("telegram_id")

        if not telegram_id:
            return JsonResponse({"detail": "telegram_id is required"}, status=400)

        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""
        username = (data.get("username") or str(telegram_id))[:150]
        role = data.get("role") if data.get("role") in VALID_ROLES else Users.USER
        from django.contrib.auth.hashers import make_password

        try:
            with transaction.atomic():
                user, created = Users.objects.get_or_create(
                    telegram_id=telegram_id,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        # "username": username,
                        "role": role,
                        "password": make_password("12345678"),
                        # "username": telegram_id
                    },
                )

                # If it already exists, update changed fields (no-op if identical)
                updates = {}
                if first_name and user.first_name != first_name:
                    updates["first_name"] = first_name
                if last_name and user.last_name != last_name:
                    updates["last_name"] = last_name
                # if username and user.username != username:
                #     updates["username"] = username
                if role and user.role != role:
                    updates["role"] = role

                if updates:
                    for k, v in updates.items():
                        setattr(user, k, v)
                    user.save(update_fields=list(updates.keys()))

        except IntegrityError:
            # Handle rare race: on duplicate username or telegram_id
            user = Users.objects.get(telegram_id=telegram_id)

        return JsonResponse({"id": user.id, "created": created}, status=200)
