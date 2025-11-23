from aiogram.filters.callback_data import CallbackData


class DayBySidCB(CallbackData, prefix="ds"):
    sid: int  # BarberSchedule.id


class SchedListCB(CallbackData, prefix="sl"):
    sid: int
    page: int


class ReqOpenCB(CallbackData, prefix="ro"):
    req_id: int
    sid: int
    page: int


class ReqStatusCB(CallbackData, prefix="rs"):
    req_id: int
    sid: int
    action: str  # "accept" | "decline"
    page: int


class ReqDiscountCB(CallbackData, prefix="rd"):
    req_id: int
    sid: int
    page: int


class ReqAddSvcCB(CallbackData, prefix="ras"):
    req_id: int
    sid: int
    page: int


class ReqAddSvcPickCB(CallbackData, prefix="rasp"):
    req_id: int
    sid: int
    bs_id: int
    page: int


class SchedPickSlotCB(CallbackData, prefix="sp", sep="|"):  # 👈 sep changed
    day: str  # e.g. "2025-01-15"
    hm: str  # keep "08:00"


class SchedPickSlotCBForBarber(CallbackData, prefix="spb", sep="|"):  # 👈 sep changed
    day: str  # e.g. "2025-01-15"
    hm: str  # keep "08:00"
