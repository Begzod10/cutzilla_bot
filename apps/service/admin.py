# services/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Service, ServiceImage

class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Image Preview"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'description_uz', 'disabled')
    list_filter  = ('disabled',)
    inlines = [ServiceImageInline]

    # ---------- Replace "Delete selected" with a soft-disable ----------
    actions = ['action_disable_selected', 'action_enable_selected']

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Remove the built-in hard delete
        actions.pop('delete_selected', None)
        return actions

    @admin.action(description="Disable selected services")
    def action_disable_selected(self, request, queryset):
        updated = queryset.update(disabled=True)
        self.message_user(request, f"{updated} service(s) were disabled.", messages.SUCCESS)

    @admin.action(description="Enable selected services")
    def action_enable_selected(self, request, queryset):
        updated = queryset.update(disabled=False)
        self.message_user(request, f"{updated} service(s) were enabled.", messages.SUCCESS)

    # ---------- Intercept single-object delete button ----------
    def delete_model(self, request, obj):
        obj.disabled = True
        obj.save(update_fields=['disabled'])
        self.message_user(request, f'The Service “{obj}” was disabled (soft-deleted).', messages.SUCCESS)

    # ---------- Intercept queryset delete (used by default bulk delete) ----------
    def delete_queryset(self, request, queryset):
        updated = queryset.update(disabled=True)
        self.message_user(request, f"{updated} service(s) were disabled (soft-deleted).", messages.SUCCESS)

    # Optional: hide the red "Delete" button in change form if already disabled
    # def get_readonly_fields(self, request, obj=None):
    #     return super().get_readonly_fields(request, obj=obj)

@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ('service', 'image_preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Image Preview"
