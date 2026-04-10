from django.db import models

data = {
    "Andijon": {
        "uz": "Andijon",
        "en": "Andijan",
        "ru": "Андижан",
        "cities": [
            {"uz": "Andijon", "en": "Andijan", "ru": "Андижан"},
            {"uz": "Xonobod", "en": "Khanabad", "ru": "Ханабад"},
            {"uz": "Asaka", "en": "Asaka", "ru": "Асака"},
            {"uz": "Jalaquduq", "en": "Jalakuduk", "ru": "Жалакудук"},
            {"uz": "Poytugʻ", "en": "Poytug", "ru": "Пайтуг"},
            {"uz": "Qoʻrgʻontepa", "en": "Kurgantepa", "ru": "Кургантепа"},
            {"uz": "Qorasuv", "en": "Karasu", "ru": "Карасу"},
            {"uz": "Marhamat", "en": "Markhamat", "ru": "Мархамат"},
            {"uz": "Shahrixon", "en": "Shahrikhan", "ru": "Шахрихан"},
            {"uz": "Paxtaobod", "en": "Pakhtaabad", "ru": "Пахтаабад"},
            {"uz": "Xoʻjaobod", "en": "Khojaabad", "ru": "Ходжаабад"}
        ]
    },
    "Buxoro": {
        "uz": "Buxoro",
        "en": "Bukhara",
        "ru": "Бухара",
        "cities": [
            {"uz": "Buxoro", "en": "Bukhara", "ru": "Бухара"},
            {"uz": "Kogon", "en": "Kogon", "ru": "Когон"},
            {"uz": "Gʻijduvon", "en": "Gijduvan", "ru": "Гиждуван"},
            {"uz": "Vobkent", "en": "Vabkent", "ru": "Вабкент"},
            {"uz": "Shofirkon", "en": "Shofirkon", "ru": "Шафиркан"},
            {"uz": "Romitan", "en": "Romitan", "ru": "Ромитан"},
            {"uz": "Qorakoʻl", "en": "Karakul", "ru": "Каракуль"},
            {"uz": "Olot", "en": "Alat", "ru": "Алат"},
            {"uz": "Peshku", "en": "Peshku", "ru": "Пешку"},
            {"uz": "Jondor", "en": "Jondor", "ru": "Жондор"}
        ]
    },
    "Fargʻona": {
        "uz": "Fargʻona",
        "en": "Fergana",
        "ru": "Фергана",
        "cities": [
            {"uz": "Fargʻona", "en": "Fergana", "ru": "Фергана"},
            {"uz": "Margʻilon", "en": "Margilan", "ru": "Маргилан"},
            {"uz": "Qoʻqon", "en": "Kokand", "ru": "Коканд"},
            {"uz": "Quvasoy", "en": "Kuvasay", "ru": "Кувасай"},
            {"uz": "Rishton", "en": "Rishton", "ru": "Риштан"},
            {"uz": "Quva", "en": "Kuva", "ru": "Кува"},
            {"uz": "Toshloq", "en": "Tashlak", "ru": "Ташлак"},
            {"uz": "Oltiariq", "en": "Altyaryk", "ru": "Алтыарык"},
            {"uz": "Beshariq", "en": "Besharik", "ru": "Бешарык"}
        ]
    },
    "Jizzax": {
        "uz": "Jizzax",
        "en": "Jizzakh",
        "ru": "Джизак",
        "cities": [
            {"uz": "Jizzax", "en": "Jizzakh", "ru": "Джизак"},
            {"uz": "Gʻallaorol", "en": "Gallaorol", "ru": "Галляарал"},
            {"uz": "Zomin", "en": "Zomin", "ru": "Зомин"},
            {"uz": "Doʻstlik", "en": "Dustlik", "ru": "Дустлик"},
            {"uz": "Paxtakor", "en": "Pakhtakor", "ru": "Пахтакор"},
            {"uz": "Yangiobod", "en": "Yangiyabad", "ru": "Янгиабад"},
            {"uz": "Baxmal", "en": "Bakhmal", "ru": "Бахмал"}
        ]
    },
    "Namangan": {
        "uz": "Namangan",
        "en": "Namangan",
        "ru": "Наманган",
        "cities": [
            {"uz": "Namangan", "en": "Namangan", "ru": "Наманган"},
            {"uz": "Chortoq", "en": "Chartak", "ru": "Чартак"},
            {"uz": "Chust", "en": "Chust", "ru": "Чуст"},
            {"uz": "Kosonsoy", "en": "Kasansay", "ru": "Касансай"},
            {"uz": "Pop", "en": "Pop", "ru": "Пап"},
            {"uz": "Toʻraqoʻrgʻon", "en": "Turakurgan", "ru": "Туракурган"},
            {"uz": "Uychi", "en": "Uychin", "ru": "Уйчин"},
            {"uz": "Uchkurgan", "en": "Uchkurgan", "ru": "Учкурган"},
            {"uz": "Mingbuloq", "en": "Mingbulak", "ru": "Мингбулак"}
        ]
    },
    "Navoiy": {
        "uz": "Navoiy",
        "en": "Navoi",
        "ru": "Навои",
        "cities": [
            {"uz": "Navoiy", "en": "Navoi", "ru": "Навои"},
            {"uz": "Zarafshon", "en": "Zarafshan", "ru": "Зарафшан"},
            {"uz": "Karmana", "en": "Karmana", "ru": "Кармана"},
            {"uz": "Konimex", "en": "Konimex", "ru": "Канимех"},
            {"uz": "Qiziltepa", "en": "Kiziltepa", "ru": "Кызылтепа"},
            {"uz": "Xatirchi", "en": "Khatirchi", "ru": "Хатирчи"}
        ]
    },
    "Qashqadaryo": {
        "uz": "Qashqadaryo",
        "en": "Kashkadarya",
        "ru": "Кашкадарья",
        "cities": [
            {"uz": "Qarshi", "en": "Karshi", "ru": "Карши"},
            {"uz": "Shahrisabz", "en": "Shahrisabz", "ru": "Шахрисабз"},
            {"uz": "Kitob", "en": "Kitab", "ru": "Китаб"},
            {"uz": "Muborak", "en": "Muborak", "ru": "Муборак"},
            {"uz": "Yakkabogʻ", "en": "Yakkabag", "ru": "Яккабаг"},
            {"uz": "Kasbi", "en": "Kasbi", "ru": "Касби"},
            {"uz": "Koson", "en": "Kasan", "ru": "Касан"},
            {"uz": "Guzor", "en": "Guzar", "ru": "Гузар"}
        ]
    },
    "Qoraqalpogʻiston": {
        "uz": "Qoraqalpogʻiston",
        "en": "Karakalpakstan",
        "ru": "Каракалпакстан",
        "cities": [
            {"uz": "Nukus", "en": "Nukus", "ru": "Нукус"},
            {"uz": "Beruniy", "en": "Beruniy", "ru": "Беруний"},
            {"uz": "Chimboy", "en": "Chimbay", "ru": "Чимбай"},
            {"uz": "Qoʻngʻirot", "en": "Kungrad", "ru": "Кунград"},
            {"uz": "Moʻynoq", "en": "Muynak", "ru": "Муйнак"},
            {"uz": "Taxiatosh", "en": "Takhiatash", "ru": "Тахиаташ"},
            {"uz": "Turtkul", "en": "Turtkul", "ru": "Турткуль"},
            {"uz": "Ellikqalʼa", "en": "Ellikkala", "ru": "Элликкала"}
        ]
    },
    "Samarqand": {
        "uz": "Samarqand",
        "en": "Samarkand",
        "ru": "Самарканд",
        "cities": [
            {"uz": "Samarqand", "en": "Samarkand", "ru": "Самарканд"},
            {"uz": "Kattaqoʻrgʻon", "en": "Kattakurgan", "ru": "Каттакурган"},
            {"uz": "Urgut", "en": "Urgut", "ru": "Ургут"},
            {"uz": "Ishtixon", "en": "Ishtikhan", "ru": "Иштихан"},
            {"uz": "Bulungʻur", "en": "Bulungur", "ru": "Булунгур"},
            {"uz": "Pastdargʻom", "en": "Pastdargom", "ru": "Пастдаргом"},
            {"uz": "Narpay", "en": "Narpay", "ru": "Нарпай"}
        ]
    },
    "Sirdaryo": {
        "uz": "Sirdaryo",
        "en": "Syrdarya",
        "ru": "Сырдарья",
        "cities": [
            {"uz": "Guliston", "en": "Gulistan", "ru": "Гулистан"},
            {"uz": "Yangiyer", "en": "Yangiyer", "ru": "Янгиер"},
            {"uz": "Shirin", "en": "Shirin", "ru": "Ширин"},
            {"uz": "Boyovut", "en": "Boyovut", "ru": "Баявут"},
            {"uz": "Sardoba", "en": "Sardoba", "ru": "Сардоба"},
            {"uz": "Sayxunobod", "en": "Saykhunabad", "ru": "Сайхунабад"},
            {"uz": "Xovos", "en": "Khovos", "ru": "Хавас"}
        ]
    },
    "Surxondaryo": {
        "uz": "Surxondaryo",
        "en": "Surkhandarya",
        "ru": "Сурхандарья",
        "cities": [
            {"uz": "Termiz", "en": "Termez", "ru": "Термез"},
            {"uz": "Denov", "en": "Denov", "ru": "Денау"},
            {"uz": "Sherobod", "en": "Sherabad", "ru": "Шерабад"},
            {"uz": "Boysun", "en": "Baysun", "ru": "Байсун"},
            {"uz": "Qumqoʻrgʻon", "en": "Kumkurgan", "ru": "Кумкурган"},
            {"uz": "Jarqoʻrgʻon", "en": "Jarkurgan", "ru": "Жаркурган"},
            {"uz": "Shoʻrchi", "en": "Shurchi", "ru": "Шурчи"}
        ]
    },
    "Toshkent": {
        "uz": "Toshkent",
        "en": "Tashkent",
        "ru": "Ташкент",
        "cities": [
            {"uz": "Angren", "en": "Angren", "ru": "Ангрен"},
            {"uz": "Bekobod", "en": "Bekabad", "ru": "Бекабад"},
            {"uz": "Olmaliq", "en": "Almalyk", "ru": "Алмалык"},
            {"uz": "Ohangaron", "en": "Akhangaran", "ru": "Ахангаран"},
            {"uz": "Chirchiq", "en": "Chirchik", "ru": "Чирчик"},
            {"uz": "Yangiyoʻl", "en": "Yangiyul", "ru": "Янгиюль"},
            {"uz": "Boʻka", "en": "Buka", "ru": "Бука"},
            {"uz": "Zangiota", "en": "Zangiata", "ru": "Зангиота"}
        ]
    },
    "Toshkent shahri": {
        "uz": "Toshkent shahri",
        "en": "Tashkent city",
        "ru": "Город Ташкент",
        "cities": [
            {"uz": "Yunusobod", "en": "Yunusabad", "ru": "Юнусабад"},
            {"uz": "Chilonzor", "en": "Chilanzar", "ru": "Чиланзар"},
            {"uz": "Mirzo Ulugʻbek", "en": "Mirzo Ulugbek", "ru": "Мирзо Улугбек"},
            {"uz": "Yakkasaroy", "en": "Yakkasaray", "ru": "Яккасарай"},
            {"uz": "Shayxontohur", "en": "Shaikhantokhur", "ru": "Шайхантахур"},
            {"uz": "Olmazor", "en": "Almazar", "ru": "Алмазар"},
            {"uz": "Uchtepa", "en": "Uchtepa", "ru": "Учтепа"},
            {"uz": "Mirobod", "en": "Mirobod", "ru": "Мирабад"},
            {"uz": "Yashnobod", "en": "Yashnabad", "ru": "Яшнабад"},
            {"uz": "Bektemir", "en": "Bektemir", "ru": "Бектемир"},
            {"uz": "Sergeli", "en": "Sergeli", "ru": "Сергели"}
        ]
    },
    "Xorazm": {
        "uz": "Xorazm",
        "en": "Khorezm",
        "ru": "Хорезм",
        "cities": [
            {"uz": "Urganch", "en": "Urgench", "ru": "Ургенч"},
            {"uz": "Xiva", "en": "Khiva", "ru": "Хива"},
            {"uz": "Hazorasp", "en": "Khazarasp", "ru": "Хазарасп"},
            {"uz": "Gurlan", "en": "Gurlan", "ru": "Гурлан"},
            {"uz": "Yangibozor", "en": "Yangibazar", "ru": "Янгибазар"},
            {"uz": "Shovot", "en": "Shavat", "ru": "Шават"},
            {"uz": "Bogʻot", "en": "Bagat", "ru": "Багат"}
        ]
    }
}


class Country(models.Model):
    name_uz = models.CharField(max_length=100, null=True, blank=True)
    name_ru = models.CharField(max_length=100, null=True, blank=True)
    name_en = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name_uz

    class Meta:
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'


class Region(models.Model):
    name_uz = models.CharField(max_length=100, null=True, blank=True)
    name_ru = models.CharField(max_length=100, null=True, blank=True)
    name_en = models.CharField(max_length=100, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    # @classmethod
    # def update_regions(cls):
    #     country = Country.objects.get(name_en="Uzbekistan")  # Adjust as needed
    #     for region_key, region_data in data.items():
    #         region = Region.objects.create(
    #             name_uz=region_data["uz"],
    #             name_en=region_data["en"],
    #             name_ru=region_data["ru"],
    #             country=country
    #         )
    #
    #         for city in region_data["cities"]:
    #             City.objects.create(
    #                 name_uz=city["uz"],
    #                 name_en=city["en"],
    #                 name_ru=city["ru"],
    #                 region=region,
    #                 country=country
    #             )
    #     return cls.objects.all()

    def __str__(self):
        return self.name_uz

    class Meta:
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'


class City(models.Model):
    name_uz = models.CharField(max_length=100, null=True, blank=True)
    name_ru = models.CharField(max_length=100, null=True, blank=True)
    name_en = models.CharField(max_length=100, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
