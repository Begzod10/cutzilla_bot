from django.contrib import admin
from .models import Barber, BarberService, BarberServiceScore, BarberSchedule, BarberScheduleDetail


class BarberServiceInline(admin.TabularInline):
    model = BarberService
    extra = 1


class BarberAdmin(admin.ModelAdmin):
    list_display = ('user', 'score')
    list_filter = ('working_days', 'score')
    search_fields = ('user__username',)
    ordering = ('-score',)
    inlines = [BarberServiceInline]


class BarberServiceAdmin(admin.ModelAdmin):
    list_display = ('barber', 'service', 'price')
    search_fields = ('barber__user__username', 'service__name_uz')
    list_filter = ('barber', 'service')
    ordering = ('barber', 'service')


class BarberServiceScoreAdmin(admin.ModelAdmin):
    list_display = ('barber', 'service', 'comment', 'client', 'score')
    search_fields = ('barber__user__username', 'service__name_uz', 'client__username')
    list_filter = ('barber', 'service', 'client')
    ordering = ('score',)


admin.site.register(Barber, BarberAdmin)
admin.site.register(BarberService, BarberServiceAdmin)
admin.site.register(BarberServiceScore, BarberServiceScoreAdmin)
admin.site.register(BarberSchedule)
admin.site.register(BarberScheduleDetail)
