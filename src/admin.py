from sqladmin import ModelView
from src.models import (
    User, Barber, BarberService, BarberSchedule, BarberScheduleDetail, BarberServiceScore,
    Client, ClientRequest, ClientRequestService, ClientFavouriteBarbers,
    Service, ServiceImage, Country, Region, City, SystemSetting
)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.name, User.role, User.balance, User.is_active]
    form_columns = [User.username, User.name, User.surname, User.role, User.balance, User.referred_by_id, User.city_id, User.region_id, User.is_active, User.telegram_id]
    icon = "fa-solid fa-user"

class BarberAdmin(ModelView, model=Barber):
    column_list = [Barber.id, Barber.user, Barber.per_hour, Barber.score, Barber.total_clients_served]
    form_columns = [Barber.user, Barber.per_hour, Barber.start_time, Barber.end_time, Barber.img, Barber.loyalty_reward_type, Barber.loyalty_reward_value, Barber.total_clients_served]
    icon = "fa-solid fa-scissors"

class BarberServiceAdmin(ModelView, model=BarberService):
    column_list = [BarberService.id, BarberService.barber_id, BarberService.service_id, BarberService.price]
    icon = "fa-solid fa-list"

class BarberScheduleAdmin(ModelView, model=BarberSchedule):
    column_list = [BarberSchedule.id, BarberSchedule.barber_id, BarberSchedule.day, BarberSchedule.n_clients]

class ClientAdmin(ModelView, model=Client):
    column_list = [Client.id, Client.user_id, Client.score, Client.blocked]
    icon = "fa-solid fa-users"

class ClientRequestAdmin(ModelView, model=ClientRequest):
    column_list = [ClientRequest.id, ClientRequest.client_id, ClientRequest.barber_id, ClientRequest.status, ClientRequest.date]

class ServiceAdmin(ModelView, model=Service):
    column_list = [Service.id, Service.name_uz, Service.disabled]
    icon = "fa-brands fa-servicestack"

class CountryAdmin(ModelView, model=Country):
    column_list = [Country.id, Country.name_uz]

class RegionAdmin(ModelView, model=Region):
    column_list = [Region.id, Region.name_uz, Region.country_id]
    
class CityAdmin(ModelView, model=City):
    column_list = [City.id, City.name_uz, City.region_id]

class SystemSettingAdmin(ModelView, model=SystemSetting):
    column_list = [SystemSetting.key, SystemSetting.value, SystemSetting.description]
    icon = "fa-solid fa-gear"

# List to register all admins in main.py
admin_views = [
    UserAdmin, BarberAdmin, BarberServiceAdmin, BarberScheduleAdmin, 
    ClientAdmin, ClientRequestAdmin, ServiceAdmin, CountryAdmin, RegionAdmin, CityAdmin,
    SystemSettingAdmin
]
