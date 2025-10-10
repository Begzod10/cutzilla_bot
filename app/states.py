from aiogram.fsm.state import StatesGroup, State


class LoginState(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


class BarberServiceStates(StatesGroup):
    waiting_for_price = State()


class FileUpload(StatesGroup):
    waiting_for_file = State()


class WorkingTime(StatesGroup):
    waiting_for_start = State()
    waiting_for_end = State()


class ChangeLocation(StatesGroup):
    waiting_for_location = State()
    location_for_client = State()


class EditAddress(StatesGroup):
    waiting_for_address = State()
    waiting_for_location_name = State()


class DurationStates(StatesGroup):
    waiting_for_duration = State()


class BookingState(StatesGroup):
    waiting_for_time = State()
    waiting_for_feedback = State()
    waiting_for_edit_time = State()


class ScoreState(StatesGroup):
    waiting_for_overall_comment = State()


class EditReqStates(StatesGroup):
    waiting_for_discount = State()
