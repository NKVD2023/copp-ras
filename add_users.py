from app import create_app, db
from app.models import User

app = create_app()

users_data = [
    {
        "description": "ГБПОУ РК «Сакский технологический техникум»",
        "username": "saki_tech",
        "password": "saki_tech234112",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Симферопольский колледж радиоэлектроники»",
        "username": "simf_radio",
        "password": "V4!nL9xW",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Симферопольский политехнический колледж имени князя Л.С. Голицына»",
        "username": "simf_polytech",
        "password": "j7$Bv3Nc",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Симферопольский колледж сферы обслуживания и дизайна»",
        "username": "simf_design",
        "password": "T2@hF8rM",
        "group": "СПО"
    },
    {
        "description": "Судомеханический техникум ФГБОУВО «Керченский государственный морской технологический университет»",
        "username": "kerch_sudo",
        "password": "q9*Zd5Kp",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Крымское художественное училище имени Н.С. Самокиша»",
        "username": "crimea_art",
        "password": "L5#wX2bR",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Керченский морской технический колледж»",
        "username": "kerch_marine",
        "password": "N3!pC7vY",
        "group": "СПО"
    },
    {
        "description": "АНО ПОО «Финансово-экономический колледж»",
        "username": "fec_college",
        "password": "x8$Gk4Mt",
        "group": "СПО"
    },
    {
        "description": "ГА ОУСПО РК «Ялтинский медицинский колледж»",
        "username": "yalta_med",
        "password": "R6@yH9dW",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Ялтинский экономико-технологический колледж»",
        "username": "yalta_eco",
        "password": "p4*Tn2Fq",
        "group": "СПО"
    },
    {
        "description": "АНПОО Медицинский колледж «Монада»",
        "username": "monada_med",
        "password": "B9#mK5vL",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК Бахчисарайский техникум строительства и транспорта",
        "username": "bah_stroy",
        "password": "w2!Xz8Pr",
        "group": "СПО"
    },
    {
        "description": "ГБОУВО РК «Крымский инженерно-педагогический университет имени Февзи Якубова» ИПК",
        "username": "kipu_ipk",
        "password": "Z7$cR3nJ",
        "group": "ВУЗ"
    },
    {
        "description": "ГБПОУ «Крымское среднее профессиональное училище (техникум) олимпийского резерва имени Л.Ф. Ярового»",
        "username": "olimp_rezerv",
        "password": "M4@vL9tK",
        "group": "СПО"
    },
    {
        "description": "ГАОУСПО РК «Евпаторийский медицинский колледж»",
        "username": "evp_med",
        "password": "f8*Hw2Dq",
        "group": "СПО"
    },
    {
        "description": "ГАОУСПО РК «Крымский медицинский колледж»",
        "username": "crimea_med",
        "password": "K3#pY7bN",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Феодосийский политехнический техникум»",
        "username": "feo_polytech",
        "password": "y5!Rz4Vw",
        "group": "СПО"
    },
    {
        "description": "ГБОУВО РК «Крымский университет культуры, искусств и туризма»",
        "username": "kukiit_main",
        "password": "G2$mL8cX",
        "group": "ВУЗ"
    },
    {
        "description": "ГБПОУ РК «Евпаторийский индустриальный техникум имени С.Л. Соколова»",
        "username": "evp_ind",
        "password": "t9@Wk5Pz",
        "group": "СПО"
    },
    {
        "description": "Театральный колледж ГБОУ ВО РК «КУКиТ»",
        "username": "kukiit_theatre",
        "password": "C7*vN3rF",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Красногвардейский агропромышленный техникум имени Н.И. Скворцова»",
        "username": "krasnogvard_agro",
        "password": "n4#Xw9Lq",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Романовский колледж индустрии гостеприимства»",
        "username": "romanov_college",
        "password": "J8!bK2mR",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Армянский колледж химической промышленности»",
        "username": "arm_chem",
        "password": "d3$Vp7Zt",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Белогорский технологический техникум»",
        "username": "belogorsk_tech",
        "password": "P5@cN4wY",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Керченский политехнический колледж»",
        "username": "kerch_polytech",
        "password": "x2*Lz8Hk",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Прудовский аграрный техникум имени Л.П. Симиренко»",
        "username": "prudov_agro",
        "password": "W9#rF5vM",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Симферопольский автотранспортный техникум»",
        "username": "simf_auto",
        "password": "b4!Tn2Pq",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Евпаторийский техникум строительных технологий и сферы обслуживания»",
        "username": "evp_stroy",
        "password": "m2@Vz8Rj",
        "group": "СПО"
    },
    {
        "description": "КрФ ФГБОУ ВО «Российский государственный университет правосудия»",
        "username": "rgup_crimea",
        "password": "Q9*pL5cN",
        "group": "ВУЗ"
    },
    {
        "description": "ГАОУПО РК «Керченский медицинский колледж имени Г.К. Петровой»",
        "username": "kerch_med",
        "password": "z4#Xw2Kt",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Крымский колледж общественного питания и торговли»",
        "username": "crimea_pit",
        "password": "F8!mR7bV",
        "group": "СПО"
    },
    {
        "description": "ГАБПОУ РК «Крымский многопрофильный колледж»",
        "username": "crimea_multi",
        "password": "v3$Lp9Zq",
        "group": "СПО"
    },
    {
        "description": "ПО ЧУ Крымский экономико-правовой колледж",
        "username": "crimea_ecolaw",
        "password": "N5@wK4cY",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Керченский технологический техникум»",
        "username": "kerch_tech",
        "password": "r2*Vz8Xm",
        "group": "СПО"
    },
    {
        "description": "ФГАОУВО «Крымский федеральный университет имени В.И. Вернадского»",
        "username": "cfu_vernadsky",
        "password": "D9#bF5pL",
        "group": "ВУЗ"
    },
    {
        "description": "ГБПОУ РК «Симферопольское музыкальное училище имени П.И. Чайковского»",
        "username": "simf_music",
        "password": "k4!Tn2Wr",
        "group": "СПО"
    },
    {
        "description": "АНО ПОО «Открытый Таврический колледж»",
        "username": "tavr_college",
        "password": "Y7$cK3mR",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Приморский профессиональный техникум»",
        "username": "primorsk_tech",
        "password": "p2@Lz8Vw",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Джанкойский профессиональный техникум»",
        "username": "djankoy_tech",
        "password": "T9*wX5qN",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК «Феодосийский техникум строительства и курортного сервиса»",
        "username": "feo_stroy",
        "password": "j4#Rz2Fk",
        "group": "СПО"
    },
    {
        "description": "ГБПОУ РК \"Чапаевский агротехнологический техникум им. И. Н. Шатилова\"",
        "username": "chapaev_agro",
        "password": "M8!pL7bC",
        "group": "СПО"
    },
    {
        "description": "Филиал ФГБОУ ВО «Керченский государственный морской технологический университет» г. Феодосия",
        "username": "kgmtu_feo",
        "password": "c3$Vw9Zt",
        "group": "ВУЗ"
    },
    {
        "description": "ФГБОУ ВО «Керченский государственный морской технологический университет»",
        "username": "kgmtu_main",
        "password": "K5@mR4cY",
        "group": "ВУЗ"
    },
    {
        "description": "КФУ имени В. И. Вернадского Ордена Трудового Красного Знамени агропромышленного колледжа имени Э. А. Верновского",
        "username": "cfu_agro",
        "password": "w2*Xz8Hq",
        "group": "ВУЗ"
    },
    {
        "description": "Крымский юридический институт (филиал) ФГКОУ ВО «Университет прокуратуры Российской Федерации»",
        "username": "krym_prokuratura",
        "password": "krym_prokuratura_pwd1",
        "group": "ВУЗ"
    },
    {
        "description": "Крымский филиал ФГКОУ ВО «Краснодарский университет Министерства внутренних дел Российской Федерации»",
        "username": "krym_mvd",
        "password": "krym_mvd_pwd2",
        "group": "ВУЗ"
    },
    {
        "description": "АНО «Образовательная организация высшего образования «Университет экономики и управления»",
        "username": "ueu",
        "password": "ueu_pwd3",
        "group": "ВУЗ"
    }
]

with app.app_context():
    db.create_all()  # ensure db exists
    added_count = 0
    updated_count = 0
    for ud in users_data:
        existing = User.query.filter_by(username=ud['username']).first()
        if not existing:
            user = User(username=ud['username'], description=ud['description'], role='user', group=ud['group'])
            user.set_password(ud['password'])
            db.session.add(user)
            added_count += 1
        else:
            # ПРОПУСКАЕМ ОБНОВЛЕНИЕ ГРУППЫ.
            # Если перезаписывать группу из словаря, это будет стирать
            # ручные изменения, которые админ сделал через интерфейс.
            pass
    db.session.commit()
    print(f"Successfully added {added_count} users. Updated groups for {updated_count} users.")
