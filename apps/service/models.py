from django.db import models
from apps.common.models import BaseModel
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html


# Create your models here.


class Service(BaseModel):
    name_uz = models.CharField(max_length=255, verbose_name=_("Name (Uzbek)"), null=True, blank=True)
    name_ru = models.CharField(max_length=255, verbose_name=_("Name (Russian)"), null=True, blank=True)
    name_en = models.CharField(max_length=255, verbose_name=_("Name (English)"), null=True, blank=True)

    description_uz = models.TextField(verbose_name=_("Description (Uzbek)"), null=True, blank=True)
    description_ru = models.TextField(verbose_name=_("Description (Russian)"), null=True, blank=True)
    description_en = models.TextField(verbose_name=_("Description (English)"), null=True, blank=True)
    disabled = models.BooleanField(default=False, verbose_name=_("Disabled"), null=True, blank=True)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def __str__(self):
        return self.name_uz


class ServiceImage(BaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    image = models.ImageField(upload_to="service/", verbose_name=_("Image"))  # ✅ FIXED

    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" style="height: 60px; width: 60px" />', self.image.url)
        return "No Image"

    image_preview.short_description = "Image Preview"
