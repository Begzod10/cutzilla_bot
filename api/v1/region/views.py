from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from apps.region.models import Region, Country, City
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from .serializers import RegionSerializer, CountrySerializer, CitySerializer
from typing import Dict, Any, List, Optional
from rest_framework import status


class CountryListView(ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]


def _get_token_from_request(request: Request) -> Optional[str]:
    # support either header
    token = request.headers.get("X-App-Token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Token "):
            token = auth.split(" ", 1)[1]
    return token


class LocationData(APIView):
    """
    Accepts nested country/region/city JSON and upserts into Django models.
    Payload: { "countries": [ { name_uz, name_ru, name_en, external_id?, regions: [ { ... cities: [ ... ] } ] } ] }
    """
    permission_classes = [AllowAny]  # using a shared secret token instead

    @transaction.atomic
    def post(self, request: Request, *args, **kwargs):
        # --- (optional) shared secret check ---
        expected = getattr(settings, "LOCATION_PUSH_TOKEN", None)
        if expected:
            provided = _get_token_from_request(request)
            if provided != expected:
                return JsonResponse({"detail": "Forbidden"}, status=403)

        data = request.data or {}
        countries: List[Dict[str, Any]] = data.get("countries", [])

        created_c = updated_c = created_r = updated_r = created_ci = updated_ci = 0

        for c in countries:
            c_kwargs = dict(
                name_en=c.get("name_en") or None,
            )
            # Prefer unique key by English name; if absent, fall back to Uzbek name
            if not c_kwargs["name_en"]:
                c_kwargs["name_en"] = c.get("name_uz") or c.get("name_ru") or None

            defaults_c = dict(
                name_uz=c.get("name_uz"),
                name_ru=c.get("name_ru"),
                name_en=c_kwargs["name_en"],
            )

            country_obj, c_created = Country.objects.get_or_create(
                name_en=c_kwargs["name_en"], defaults=defaults_c
            )
            if not c_created:
                # update fields if changed
                changed = False
                for f, v in defaults_c.items():
                    if getattr(country_obj, f) != v:
                        setattr(country_obj, f, v)
                        changed = True
                if changed:
                    country_obj.save()
                    updated_c += 1
            else:
                created_c += 1

            for r in c.get("regions", []) or []:
                r_key = r.get("name_en") or r.get("name_uz") or r.get("name_ru")
                defaults_r = dict(
                    name_uz=r.get("name_uz"),
                    name_ru=r.get("name_ru"),
                    name_en=r_key,
                    country=country_obj,
                )
                region_obj, r_created = Region.objects.get_or_create(
                    name_en=r_key, country=country_obj, defaults=defaults_r
                )
                if not r_created:
                    changed = False
                    for f in ("name_uz", "name_ru", "name_en"):
                        v = defaults_r[f]
                        if getattr(region_obj, f) != v:
                            setattr(region_obj, f, v)
                            changed = True
                    if changed:
                        region_obj.save()
                        updated_r += 1
                else:
                    created_r += 1

                for ct in r.get("cities", []) or []:
                    ci_key = ct.get("name_en") or ct.get("name_uz") or ct.get("name_ru")
                    defaults_ci = dict(
                        name_uz=ct.get("name_uz"),
                        name_ru=ct.get("name_ru"),
                        name_en=ci_key,
                        country=country_obj,
                        region=region_obj,
                    )
                    city_obj, ci_created = City.objects.get_or_create(
                        name_en=ci_key, region=region_obj, defaults=defaults_ci
                    )
                    if not ci_created:
                        changed = False
                        for f in ("name_uz", "name_ru", "name_en"):
                            v = defaults_ci[f]
                            if getattr(city_obj, f) != v:
                                setattr(city_obj, f, v)
                                changed = True
                        # always ensure FKs are correct
                        if city_obj.country_id != country_obj.id or city_obj.region_id != region_obj.id:
                            city_obj.country = country_obj
                            city_obj.region = region_obj
                            changed = True
                        if changed:
                            city_obj.save()
                            updated_ci += 1
                    else:
                        created_ci += 1

        return JsonResponse({
            "ok": True,
            "created": {
                "countries": created_c,
                "regions": created_r,
                "cities": created_ci,
            },
            "updated": {
                "countries": updated_c,
                "regions": updated_r,
                "cities": updated_ci,
            },
            "total_countries_received": len(countries),
        }, status=200)


def _norm(s: Any):
    if s is None:
        return None
    s = str(s).strip()
    return s or None


def _auth_ok(request) -> bool:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Token "):
        return False
    token = header.split(" ", 1)[1].strip()
    expected = getattr(settings, "DJANGO_LOCATION_TOKEN", "")
    return bool(expected) and token == expected


class LocationPushView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request):
        payload = request.data
        if isinstance(payload, dict):
            items: List[Dict[str, Any]] = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            return JsonResponse({"detail": "Invalid payload"}, status=400)

        created_counts = {"countries": 0, "regions": 0, "cities": 0}
        results: List[Dict[str, Any]] = []

        with transaction.atomic():
            for raw in items:
                c_uz = _norm(raw.get("country_uz"))
                c_ru = _norm(raw.get("country_ru"))
                c_en = _norm(raw.get("country_en"))

                r_uz = _norm(raw.get("region_uz"))
                r_ru = _norm(raw.get("region_ru"))
                r_en = _norm(raw.get("region_en"))

                ct_uz = _norm(raw.get("city_uz"))
                ct_ru = _norm(raw.get("city_ru"))
                ct_en = _norm(raw.get("city_en"))

                # Require at minimum uz names to key by (fall back to ru if uz empty)
                country_key = c_uz or c_ru
                region_key = r_uz or r_ru
                city_key = ct_uz or ct_ru

                if not country_key or not region_key or not city_key:
                    # skip invalid item, but continue others
                    results.append({"status": "skipped", "reason": "missing required names", "item": raw})
                    continue

                # --- Country upsert ---
                country, country_created = Country.objects.get_or_create(
                    name_uz=country_key,
                    defaults={"name_ru": c_ru, "name_en": c_en},
                )
                # Fill missing translations if arrive later
                updated = False
                if not country.name_ru and c_ru:
                    country.name_ru = c_ru;
                    updated = True
                if not country.name_en and c_en:
                    country.name_en = c_en;
                    updated = True
                if updated:
                    country.save(update_fields=["name_ru", "name_en"])
                if country_created:
                    created_counts["countries"] += 1

                # --- Region upsert (scoped to country) ---
                region, region_created = Region.objects.get_or_create(
                    country=country,
                    name_uz=region_key,
                    defaults={"name_ru": r_ru, "name_en": r_en},
                )
                updated = False
                if not region.name_ru and r_ru:
                    region.name_ru = r_ru;
                    updated = True
                if not region.name_en and r_en:
                    region.name_en = r_en;
                    updated = True
                if updated:
                    region.save(update_fields=["name_ru", "name_en"])
                if region_created:
                    created_counts["regions"] += 1

                # --- City upsert (scoped to region) ---
                city, city_created = City.objects.get_or_create(
                    region=region,
                    name_uz=city_key,
                    defaults={
                        "name_ru": ct_ru,
                        "name_en": ct_en,
                        "country": country,
                    },
                )
                updated = False
                # keep country reference in sync
                if city.country_id != country.id:
                    city.country = country;
                    updated = True
                if not city.name_ru and ct_ru:
                    city.name_ru = ct_ru;
                    updated = True
                if not city.name_en and ct_en:
                    city.name_en = ct_en;
                    updated = True
                if updated:
                    city.save(update_fields=["country", "name_ru", "name_en"])
                if city_created:
                    created_counts["cities"] += 1

                results.append({
                    "status": "ok",
                    "country_id": country.id,
                    "region_id": region.id,
                    "city_id": city.id,
                })

        return JsonResponse(
            {"created": created_counts, "results": results},
            status=status.HTTP_200_OK
        )
