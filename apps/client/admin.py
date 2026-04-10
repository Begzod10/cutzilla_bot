from django.contrib import admin
from .models import Client, ClientRequest, ClientFavouriteBarbers


# Register your models here.

class ClientRequestAdmin(admin.ModelAdmin):
    list_display = ('client', 'barber', 'date', 'from_time', 'to_time', 'status', 'comment')
    search_fields = ('client__user__username', 'barber__user__username', 'service__name_uz')
    list_filter = ('client', 'barber')
    ordering = ('date',)


class ClientFavouriteBarbersAdmin(admin.ModelAdmin):
    list_display = ('client', 'barber')


class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'blocked')


admin.site.register(Client, ClientAdmin)
admin.site.register(ClientRequest, ClientRequestAdmin)
admin.site.register(ClientFavouriteBarbers, ClientFavouriteBarbersAdmin)
