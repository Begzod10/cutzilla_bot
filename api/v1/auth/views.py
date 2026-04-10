from rest_framework import generics, permissions
from .serializers import LoginSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from apps.users.models import Users
from rest_framework_simplejwt.tokens import RefreshToken
from apps.barber.models import Barber, BarberService
from api.v1.barber.serializers import BarberSerializer
from django.db import transaction


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print("login valid")
        user = serializer.validated_data['user']
        telegram_id = request.data.get('telegram_id')

        # Bind telegram_id safely (Option A: reassign)
        if telegram_id:
            with transaction.atomic():
                # free telegram_id from any other account
                Users.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).update(telegram_id=None)
                # bind to current user (use UPDATE to avoid race on save)
                Users.objects.filter(pk=user.pk).update(telegram_id=telegram_id)
                user.refresh_from_db(fields=['telegram_id'])

        # --- If you prefer to reject instead of reassign, replace the block above with:
        # if telegram_id:
        #     exists = Users.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).exists()
        #     if exists:
        #         return Response(
        #             {"detail": "This Telegram account is already linked to another user."},
        #             status=status.HTTP_409_CONFLICT,
        #         )
        #     Users.objects.filter(pk=user.pk).update(telegram_id=telegram_id)
        #     user.refresh_from_db(fields=['telegram_id'])
        # ---

        refresh = RefreshToken.for_user(user)

        payload = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'login': user.username,
            'role': user.role,
        }

        if user.role == 'barber':
            barber = Barber.objects.filter(user=user).first()
            if barber:
                payload['barber'] = BarberSerializer(barber).data
                payload['user_id'] = user.id
        print(payload)
        return Response(payload, status=status.HTTP_200_OK)
