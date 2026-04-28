import os

replacements = {
    "users_users": "users",
    "service_service": "services",
    "service_serviceimage": "service_images",
    "region_country": "country",
    "region_region": "region",
    "region_city": "city",
    "client_client": "client",
    "client_clientrequest": "client_requests",
    "client_clientrequestservice": "client_requests_services",
    "client_clientfavouritebarbers": "client_barbers",
    "barber_barber": "barbers",
    "barber_barberservice": "barber_services",
    "barber_barberservicescore": "barber_service_scores",
    "barber_barberschedule": "barber_schedule",
    "barber_barberscheduledetail": "barber_schedule_details"
}

# Backend papkasidagi modellar yo'lagi
directory = r"c:\Users\Administrator\Downloads\Новая папка (3)\src\models"

for filename in os.listdir(directory):
    if filename.endswith(".py"):
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Eskirgan ForeignKey ismlarini yangilariga almashtirish
        for old, new in replacements.items():
            content = content.replace(old, new)
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

print("✅ Backenddagi barcha jadvallar (jumladan ForeignKey'lar ham) muvaffaqiyatli tozalandi (Bot bilan bir xil qilindi)!")
