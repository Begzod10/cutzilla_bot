from django.contrib import admin
from .models import Region, City, Country
from django.contrib import messages


@admin.action(description="Update Regions")
def update_region_action(modeladmin, request, queryset):
    Region.update_regions()
    modeladmin.message_user(request, "Successfully updated all tariffs", messages.SUCCESS)


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'country')
    search_fields = ('name_uz',)
    list_filter = ('country',)

    ordering = ('country', 'name_uz')

    actions = [update_region_action]


class CityAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'region', 'country')
    list_filter = ('region', 'country')


admin.site.register(Region, RegionAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Country)
