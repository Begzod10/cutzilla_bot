# notifications/utils.py
from typing import Optional, Tuple, List, Dict
from datetime import datetime
from zoneinfo import ZoneInfo


def _get_lang(user) -> str:
    code = (getattr(user, "lang", None) or "").strip().lower()
    return "ru" if code.startswith("ru") else "uz"


def _service_name_localized(service, lang: str) -> str:
    if service is None:
        return "—"
    if lang == "ru":
        return getattr(service, "name_ru", None) or getattr(service, "name_uz", None) or getattr(service, "name_en",
                                                                                                 None) or "—"
    return getattr(service, "name_uz", None) or getattr(service, "name_ru", None) or getattr(service, "name_en",
                                                                                             None) or "—"


def _format_sum_uzs(amount: Optional[int]) -> str:
    if amount is None:
        return "—"
    s = f"{int(amount):,}".replace(",", " ")
    return f"{s} so'm"


def _apply_discount(total: int, discount: Optional[int], percent: bool = False) -> Tuple[int, str]:
    """
    Default: discount is absolute so'm (UZS). If your discount is percent, pass percent=True.
    """
    if not discount:
        return total, "0"
    if percent:
        value = (total * int(discount)) // 100
        return max(total - value, 0), f"{discount}%"
    return max(total - int(discount), 0), _format_sum_uzs(int(discount))


def _fmt_dt_range_local(cr, tz: ZoneInfo) -> Tuple[str, str]:
    ft = cr.from_time.astimezone(tz) if cr.from_time else None
    tt = cr.to_time.astimezone(tz) if cr.to_time else None
    date_text = ft.strftime("%d.%m.%Y") if ft else "—"
    time_text = f"{ft.strftime('%H:%M')}–{tt.strftime('%H:%M')}" if ft and tt else "—"
    return date_text, time_text


def aggregate_request_totals(cr) -> Dict[str, object]:
    """
    Sums duration & price over ClientRequest.services.
    - duration: ClientRequestService.duration if present, else BarberService.duration
    - price: BarberService.price
    Returns dict with:
      items: List[{name_uz, name_ru, price, duration}]
      total_duration_min, total_price_uzs, final_price_uzs, discount_text
      lang_client, lang_barber
    """
    lang_client = _get_lang(getattr(cr.client, "user", None))
    lang_barber = _get_lang(getattr(cr.barber, "user", None))

    items: List[Dict[str, object]] = []
    total_minutes = 0
    total_price = 0

    for crs in (cr.services or []):
        bs = getattr(crs, "barber_service", None)
        svc = getattr(bs, "service", None)

        # duration: CR-service override then fallback
        d_val = getattr(crs, "duration", None)
        if d_val is None:
            d_val = getattr(bs, "duration", None)
        d = int(d_val) if d_val is not None else 0

        p_val = getattr(bs, "price", None)
        p = int(p_val) if p_val is not None else 0

        name_uz = _service_name_localized(svc, "uz")
        name_ru = _service_name_localized(svc, "ru")

        items.append({"name_uz": name_uz, "name_ru": name_ru, "price": p, "duration": d})
        total_minutes += d
        total_price += p

    final_price, discount_text = _apply_discount(total_price, getattr(cr, "discount", None), percent=False)

    return {
        "items": items,
        "total_duration_min": total_minutes,
        "total_price_uzs": total_price,
        "final_price_uzs": final_price,
        "discount_text": discount_text,
        "lang_client": lang_client,
        "lang_barber": lang_barber,
    }


def make_messages_ru_uz(cr, tz: ZoneInfo) -> Tuple[str, str]:
    """
    Returns (msg_for_client, msg_for_barber) localized with totals and service names.
    """
    agg = aggregate_request_totals(cr)
    date_text, time_text = _fmt_dt_range_local(cr, tz)

    services_uz = ", ".join([str(it["name_uz"]) for it in agg["items"]]) or "—"
    services_ru = ", ".join([str(it["name_ru"]) for it in agg["items"]]) or "—"

    total_min = agg["total_duration_min"]
    total_price_txt = _format_sum_uzs(int(agg["total_price_uzs"]))
    final_price_txt = _format_sum_uzs(int(agg["final_price_uzs"]))
    discount_txt = str(agg["discount_text"])

    barber_name = getattr(cr.barber, "full_name", "—")
    client_name = getattr(cr.client, "full_name", "—")
    note_text = cr.comment or "—"

    # Client messages
    msg_client_uz = (
        "🗓 <b>Yaqinlashayotgan yozuv</b>\n"
        f"👨‍🔧 Barber: {barber_name}\n"
        f"📅 Sana: {date_text}\n"
        f"⏰ Vaqt: {time_text}\n"
        f"🧾 Xizmatlar: {services_uz}\n"
        f"⏱ Jami davomiylik: {total_min} daqiqa\n"
        f"💵 Jami narx: {total_price_txt}\n"
        f"🎯 Chegirma: {discount_txt}\n"
        f"✅ Yakuniy narx: {final_price_txt}\n"
        f"💬 Izoh: {note_text}"
    )
    msg_client_ru = (
        "🗓 <b>Ближайшая запись</b>\n"
        f"👨‍🔧 Барбер: {barber_name}\n"
        f"📅 Дата: {date_text}\n"
        f"⏰ Время: {time_text}\n"
        f"🧾 Услуги: {services_ru}\n"
        f"⏱ Общая длительность: {total_min} минут\n"
        f"💵 Общая стоимость: {total_price_txt}\n"
        f"🎯 Скидка: {discount_txt}\n"
        f"✅ Итоговая цена: {final_price_txt}\n"
        f"💬 Комментарий: {note_text}"
    )

    # Barber messages
    msg_barber_uz = (
        "🗓 <b>Yaqinlashayotgan mijoz</b>\n"
        f"🧍 Mijoz: {client_name}\n"
        f"📅 Sana: {date_text}\n"
        f"⏰ Vaqt: {time_text}\n"
        f"🧾 Xizmatlar: {services_uz}\n"
        f"⏱ Jami davomiylik: {total_min} daqiqa\n"
        f"💵 Jami narx: {total_price_txt}\n"
        f"🎯 Chegirma: {discount_txt}\n"
        f"✅ Yakuniy narx: {final_price_txt}\n"
        f"💬 Izoh: {note_text}"
    )
    msg_barber_ru = (
        "🗓 <b>Ближайший клиент</b>\n"
        f"🧍 Клиент: {client_name}\n"
        f"📅 Дата: {date_text}\n"
        f"⏰ Время: {time_text}\n"
        f"🧾 Услуги: {services_ru}\n"
        f"⏱ Общая длительность: {total_min} минут\n"
        f"💵 Общая стоимость: {total_price_txt}\n"
        f"🎯 Скидка: {discount_txt}\n"
        f"✅ Итоговая цена: {final_price_txt}\n"
        f"💬 Комментарий: {note_text}"
    )

    client_lang = str(agg["lang_client"])
    barber_lang = str(agg["lang_barber"])
    msg_for_client = msg_client_ru if client_lang == "ru" else msg_client_uz
    msg_for_barber = msg_barber_ru if barber_lang == "ru" else msg_barber_uz
    return msg_for_client, msg_for_barber
