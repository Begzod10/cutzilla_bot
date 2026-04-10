from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import List, Union, Dict, Any
from src.core.database import get_db
from src.models.region import Region, Country, City
from src.schemas.region import RegionResponse, CountryResponse, LocationDataPayload, LocationPushPayload
from src.core.config import settings

router = APIRouter()

@router.get("/", response_model=List[RegionResponse])
async def read_regions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).offset(skip).limit(limit))
    regions = result.scalars().all()
    return regions

@router.get("/countries", response_model=List[CountryResponse])
async def read_countries(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Country).offset(skip).limit(limit))
    countries = result.scalars().all()
    return countries

@router.post("/location-data")
async def location_data(payload: LocationDataPayload, db: AsyncSession = Depends(get_db), x_app_token: str = Header(None), authorization: str = Header(None)):
    token = x_app_token
    if not token and authorization and authorization.startswith("Token "):
        token = authorization.split(" ", 1)[1]
        
    expected = settings.LOCATION_PUSH_TOKEN
    if expected and token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    created_c = updated_c = created_r = updated_r = created_ci = updated_ci = 0

    for c in payload.countries:
        name_en = c.name_en or c.name_uz or c.name_ru
        if not name_en:
            continue
            
        c_res = await db.execute(select(Country).where(Country.name_en == name_en))
        country_obj = c_res.scalars().first()
        
        if not country_obj:
            country_obj = Country(name_uz=c.name_uz, name_ru=c.name_ru, name_en=name_en)
            db.add(country_obj)
            await db.commit()
            await db.refresh(country_obj)
            created_c += 1
        else:
            updates = {}
            if c.name_uz and country_obj.name_uz != c.name_uz: updates["name_uz"] = c.name_uz
            if c.name_ru and country_obj.name_ru != c.name_ru: updates["name_ru"] = c.name_ru
            if updates:
                await db.execute(update(Country).where(Country.id == country_obj.id).values(**updates))
                await db.commit()
                updated_c += 1

        for r in c.regions:
            r_key = r.name_en or r.name_uz or r.name_ru
            if not r_key: continue
            
            r_res = await db.execute(select(Region).where(Region.name_en == r_key, Region.country_id == country_obj.id))
            region_obj = r_res.scalars().first()
            
            if not region_obj:
                region_obj = Region(name_uz=r.name_uz, name_ru=r.name_ru, name_en=r_key, country_id=country_obj.id)
                db.add(region_obj)
                await db.commit()
                await db.refresh(region_obj)
                created_r += 1
            else:
                updates = {}
                if r.name_uz and region_obj.name_uz != r.name_uz: updates["name_uz"] = r.name_uz
                if r.name_ru and region_obj.name_ru != r.name_ru: updates["name_ru"] = r.name_ru
                if updates:
                    await db.execute(update(Region).where(Region.id == region_obj.id).values(**updates))
                    await db.commit()
                    updated_r += 1

            for ct in r.cities:
                ci_key = ct.name_en or ct.name_uz or ct.name_ru
                if not ci_key: continue
                
                ci_res = await db.execute(select(City).where(City.name_en == ci_key, City.region_id == region_obj.id))
                city_obj = ci_res.scalars().first()
                
                if not city_obj:
                    city_obj = City(name_uz=ct.name_uz, name_ru=ct.name_ru, name_en=ci_key, country_id=country_obj.id, region_id=region_obj.id)
                    db.add(city_obj)
                    await db.commit()
                    created_ci += 1
                else:
                    updates = {}
                    if ct.name_uz and city_obj.name_uz != ct.name_uz: updates["name_uz"] = ct.name_uz
                    if ct.name_ru and city_obj.name_ru != ct.name_ru: updates["name_ru"] = ct.name_ru
                    if city_obj.country_id != country_obj.id: updates["country_id"] = country_obj.id
                    if updates:
                        await db.execute(update(City).where(City.id == city_obj.id).values(**updates))
                        await db.commit()
                        updated_ci += 1

    return {
        "ok": True,
        "created": {"countries": created_c, "regions": created_r, "cities": created_ci},
        "updated": {"countries": updated_c, "regions": updated_r, "cities": updated_ci},
        "total_countries_received": len(payload.countries)
    }

@router.post("/location-push")
async def location_push(payload: Union[LocationPushPayload, List[LocationPushPayload]], db: AsyncSession = Depends(get_db)):
    items = payload if isinstance(payload, list) else [payload]
    
    created_counts = {"countries": 0, "regions": 0, "cities": 0}
    results = []

    for raw in items:
        # Require at minimum uz names to key by
        country_key = raw.country_uz or raw.country_ru
        region_key = raw.region_uz or raw.region_ru
        city_key = raw.city_uz or raw.city_ru
        
        if not country_key or not region_key or not city_key:
            results.append({"status": "skipped", "reason": "missing required names", "item": raw.model_dump()})
            continue

        # Upsert Country
        c_res = await db.execute(select(Country).where(Country.name_uz == country_key))
        country = c_res.scalars().first()
        if not country:
            country = Country(name_uz=country_key, name_ru=raw.country_ru, name_en=raw.country_en)
            db.add(country)
            await db.commit()
            await db.refresh(country)
            created_counts["countries"] += 1
        else:
            updates = {}
            if not country.name_ru and raw.country_ru: updates["name_ru"] = raw.country_ru
            if not country.name_en and raw.country_en: updates["name_en"] = raw.country_en
            if updates:
                await db.execute(update(Country).where(Country.id == country.id).values(**updates))
                await db.commit()

        # Upsert Region
        r_res = await db.execute(select(Region).where(Region.name_uz == region_key, Region.country_id == country.id))
        region = r_res.scalars().first()
        if not region:
            region = Region(name_uz=region_key, name_ru=raw.region_ru, name_en=raw.region_en, country_id=country.id)
            db.add(region)
            await db.commit()
            await db.refresh(region)
            created_counts["regions"] += 1
        else:
            updates = {}
            if not region.name_ru and raw.region_ru: updates["name_ru"] = raw.region_ru
            if not region.name_en and raw.region_en: updates["name_en"] = raw.region_en
            if updates:
                await db.execute(update(Region).where(Region.id == region.id).values(**updates))
                await db.commit()

        # Upsert City
        ci_res = await db.execute(select(City).where(City.name_uz == city_key, City.region_id == region.id))
        city = ci_res.scalars().first()
        if not city:
            city = City(name_uz=city_key, name_ru=raw.city_ru, name_en=raw.city_en, region_id=region.id, country_id=country.id)
            db.add(city)
            await db.commit()
            await db.refresh(city)
            created_counts["cities"] += 1
        else:
            updates = {}
            if city.country_id != country.id: updates["country_id"] = country.id
            if not city.name_ru and raw.city_ru: updates["name_ru"] = raw.city_ru
            if not city.name_en and raw.city_en: updates["name_en"] = raw.city_en
            if updates:
                await db.execute(update(City).where(City.id == city.id).values(**updates))
                await db.commit()

        results.append({
            "status": "ok",
            "country_id": country.id,
            "region_id": region.id,
            "city_id": city.id
        })

    return {"created": created_counts, "results": results}
