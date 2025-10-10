from aiogram.filters.callback_data import CallbackData


class SchedPickSlotCBClient(CallbackData, prefix="sp", sep="|"):  # 👈 sep changed
    day: str  # e.g. "2025-01-15"
    hm: str  # keep "08:00"


class SchedPickSlotCBClientEdit(CallbackData, prefix="sched_edit"):
    day: str   # "YYYY-MM-DD"
    hm: str    # "HHMM"