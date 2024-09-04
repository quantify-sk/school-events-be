from datetime import datetime, time
import sys

from app.context_manager import context_db_session
from app.data_adapter import User
from app.dependencies import SessionLocal, get_password_hash
from app.data_adapter.event import Event, EventDate
from app.data_adapter.school import School
from app.models.user import UserRole, UserStatus
from app.models.event import EventType, TargetGroup


def seed_only_admin_user():
    """Seed only admin user"""
    print("SEED ADMIN USER")

    db = SessionLocal()

    context_db_session.set(db)

    # Manually defined users
    manual_users = [
        ("root", "root", "admin@admin.com"),
        ("root", "root", "test@test.com"),
        ("root", "root", "test1@test1.com"),
    ]
    password_hash = get_password_hash("root")

    for first_name, last_name, email in manual_users:
        user = User(
            first_name=first_name,
            last_name=last_name,
            user_email=email,
            password_hash=password_hash,
            role="admin",
            status=UserStatus.ACTIVE,
            phone_number="0901234567",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    print("SEED ADMIN USER OK")


def seed_users():
    """Seed admin, organizer, and school representative users"""
    print("SEEDING USERS")

    db = SessionLocal()
    context_db_session.set(db)

    # Manually defined users with roles
    manual_users = [
        ("Organizer", "One", "organizer1@example.com", "organizer", "0901234567", None),
        ("Organizer", "Two", "organizer2@example.com", "organizer", "0907654321", None),
        (
            "School",
            "Rep One",
            "schoolrep1@example.com",
            "school_representative",
            "0900123456",
            {
                "name": "Základná škola Jána Amosa Komenského",
                "ico": "12345678",
                "address": "Majerská cesta 68",
                "psc": "974 01",  # Added PSČ
                "city": "Banská Bystrica",
                "district": "Banská Bystrica",
                "region": "Banskobystrický kraj",
                "number_of_students": 500,
                "number_of_employees": 50,
            },
        ),
        (
            "School",
            "Rep Two",
            "schoolrep2@example.com",
            "school_representative",
            "0909876543",
            {
                "name": "Gymnázium Ľudovíta Štúra",
                "ico": "87654321",
                "address": "1. mája 170/2",
                "psc": "911 35",  # Added PSČ
                "city": "Trenčín",
                "district": "Trenčín",
                "region": "Trenčiansky kraj",
                "number_of_students": 800,
                "number_of_employees": 80,
            },
        ),
    ]
    password_hash = get_password_hash("password123")

    for first_name, last_name, email, role, phone_number, school_data in manual_users:
        if role == "school_representative" and school_data:
            # Create school first
            school = School(
                name=school_data["name"],
                ico=school_data["ico"],
                address=school_data["address"],
                psc=school_data["psc"],  # Added PSČ
                city=school_data["city"],  # Added city
                district=school_data["district"],
                region=school_data["region"],
                number_of_students=school_data["number_of_students"],
                number_of_employees=school_data["number_of_employees"],
            )
            db.add(school)
            db.flush()  # This will assign an ID to the school without committing the transaction

            # Create user with school_id
            user = User(
                first_name=first_name,
                last_name=last_name,
                user_email=email,
                password_hash=password_hash,
                role=role,
                school_id=school.id,
                phone_number=phone_number,
            )
        else:
            # Create user without school_id for non-school representatives
            user = User(
                first_name=first_name,
                last_name=last_name,
                user_email=email,
                password_hash=password_hash,
                role=role,
                phone_number=phone_number,
            )

        db.add(user)

    db.commit()
    db.refresh(user)

    print("USERS AND SCHOOLS SEEDED SUCCESSFULLY")


def seed_events():
    """Seed events"""
    print("SEEDING EVENTS")

    db = SessionLocal()
    context_db_session.set(db)

    # Helper function to create organizer and employee
    def create_organizer_and_employee(institution_name, email_prefix):
        organizer = User(
            first_name=institution_name,
            last_name="Organizer",
            user_email=f"{email_prefix}_organizer@example.com",
            password_hash=get_password_hash("password123"),
            role=UserRole.ORGANIZER,
            phone_number="0900123456",
        )
        db.add(organizer)
        db.flush()

        employee = User(
            first_name=institution_name,
            last_name="Employee",
            user_email=f"{email_prefix}_employee@example.com",
            password_hash=get_password_hash("password123"),
            role=UserRole.EMPLOYEE,
            parent_organizer_id=organizer.user_id,
            phone_number="0909876543",
        )
        db.add(employee)
        db.flush()

        return organizer

    def create_event_dates(event_id, dates, times, capacity):
        event_dates = []
        for date in dates:
            for t in times:
                event_date = EventDate(
                    event_id=event_id,
                    date=datetime.combine(date, t),
                    time=datetime.combine(date, t),
                    capacity=capacity,
                )
                event_dates.append(event_date)
        return event_dates

    # Kino Lumière events
    kino_lumiere = create_organizer_and_employee("Kino Lumière", "kino_lumiere")

    kino_lumiere_events = [
        Event(
            title="Filmový kabinet deťom",
            institution_name="Kino Lumière",
            address="Špitálska 4, 811 08 Bratislava",
            city="Bratislava",
            capacity=44,
            description="Workshop zoznámi deti so základmi filmovej animácie a súčasnou slovenskou animovanou tvorbou.",
            annotation="Pokiaľ hľadáte filmový program pre svoje študenstvo, v Kine Lumière sme tu pre vás.",
            target_group=TargetGroup.ELEMENTARY_SCHOOL,
            age_from=6,
            age_to=10,
            event_type=EventType.WORKSHOP,
            duration=90,
            organizer_id=kino_lumiere.user_id,
            district="bratislava_i", 
            region="bratislavsky",
        ),
        Event(
            title="Školské predstavenie s lektorským úvodom",
            institution_name="Kino Lumière",
            address="Špitálska 4, 811 08 Bratislava",
            city="Bratislava",
            capacity=195,
            description="Školské predstavenie s lektorským úvodom.",
            annotation="Ponuka filmu bude dohodnutá priamo so školou na základe vekovej skupiny žiakov a preferovanej témy.",
            target_group=TargetGroup.ALL,
            age_from=6,
            age_to=19,
            event_type=EventType.SCREENING,
            duration=120,
            organizer_id=kino_lumiere.user_id,
            district="bratislava_i",
            region="bratislavsky", 
        ),
        Event(
            title="Školské predstavenie bez lektorského úvodu",
            institution_name="Kino Lumière",
            address="Špitálska 4, 811 08 Bratislava",
            city="Bratislava",
            capacity=195,
            description="Školské predstavenie bez lektorského úvodu.",
            annotation="Ponuka filmu bude dohodnutá priamo so školou na základe vekovej skupiny žiakov a preferovanej témy.",
            target_group=TargetGroup.ALL,
            age_from=6,
            age_to=19,
            event_type=EventType.SCREENING,
            duration=120,
            organizer_id=kino_lumiere.user_id,
            district="bratislava_i",
            region="bratislavsky",
        ),
    ]

    kino_lumiere_dates = [
        datetime(2024, 9, 10),
        datetime(2024, 9, 11),
        datetime(2024, 9, 12),
        datetime(2024, 9, 17),
        datetime(2024, 9, 18),
        datetime(2024, 9, 24),
        datetime(2024, 9, 25),
        datetime(2024, 9, 26),
        datetime(2024, 10, 1),
        datetime(2024, 10, 2),
        datetime(2024, 10, 3),
        datetime(2024, 10, 8),
        datetime(2024, 10, 15),
        datetime(2024, 10, 16),
        datetime(2024, 10, 22),
        datetime(2024, 10, 23),
        datetime(2024, 10, 24),
        datetime(2024, 10, 29),
        datetime(2024, 10, 30),
        datetime(2024, 10, 31),
        datetime(2024, 11, 5),
        datetime(2024, 11, 6),
        datetime(2024, 11, 7),
        datetime(2024, 11, 12),
        datetime(2024, 11, 13),
        datetime(2024, 11, 19),
        datetime(2024, 11, 20),
        datetime(2024, 11, 21),
        datetime(2024, 11, 26),
        datetime(2024, 11, 27),
        datetime(2024, 11, 28),
        datetime(2024, 12, 3),
        datetime(2024, 12, 4),
        datetime(2024, 12, 5),
        datetime(2024, 12, 10),
        datetime(2024, 12, 11),
        datetime(2024, 12, 12),
        datetime(2024, 12, 17),
        datetime(2024, 12, 18),
    ]

    for event in kino_lumiere_events:
        db.add(event)
        db.flush()
        event_dates = create_event_dates(
            event.id, kino_lumiere_dates, [time(9, 0)], event.capacity
        )
        db.add_all(event_dates)

    # Štátny komorný orchester Žilina event
    sko_zilina = create_organizer_and_employee(
        "Štátny komorný orchester Žilina", "sko_zilina"
    )

    sko_zilina_event = Event(
        title="Malá čarovná flauta",
        institution_name="Štátny komorný orchester Žilina",
        address="Dom umenia Fatra Žilina, Dolný val 47",
        city="Žilina",
        capacity=350,
        description="Obľúbený hudobno-dramatický cyklus 'Opera nás zabáva' s rozprávkovým príbehom o čarovnej flaute (a s magickou Mozartovou hudbou), ktorá všetkým pomôže, aby nakoniec všetko dobre dopadlo. Moderuje Martin Vanek.",
        annotation="Hudobno-dramatický cyklus s rozprávkovým príbehom o čarovnej flaute.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=5,
        age_to=10,
        event_type=EventType.CONCERT,
        duration=60,
        organizer_id=sko_zilina.user_id,
        more_info_url="https://skozilina.sk/",
        district="zilina",  # Set to the appropriate district value
        region="zilinsky",
    )
    db.add(sko_zilina_event)
    db.flush()

    # Add event dates
    sko_zilina_dates = [datetime(2024, 10, 15), datetime(2024, 10, 16)]
    sko_zilina_times = [time(9, 0), time(11, 0)]
    sko_zilina_event_dates = create_event_dates(
        sko_zilina_event.id,
        sko_zilina_dates,
        sko_zilina_times,
        sko_zilina_event.capacity,
    )
    db.add_all(sko_zilina_event_dates)

    # Štátna filharmónia Košice event
    sfk = create_organizer_and_employee("Štátna filharmónia Košice", "sfk")

    sfk_event = Event(
        title="Vianočný koncert pre deti a mládež",
        institution_name="Štátna filharmónia Košice",
        address="Dom umenia Košice, Moyzesova 66",
        city="Košice",
        capacity=700,
        description="Vianočný koncert pre deti a mládež",
        annotation="Vianočný koncert pre deti a mládež (bude ešte doplnená ŠFK)",
        target_group=TargetGroup.ALL,
        age_from=7,
        age_to=15,
        event_type=EventType.CONCERT,
        duration=60,
        organizer_id=sfk.user_id,
        more_info_url="https://www.sfk.sk/koncerty-pre-deti-a-mladez",
    district="kosice_i",  # Set to the appropriate district value
    region="kosicky",  # Set to the appropriate region value
    )
    db.add(sfk_event)
    db.flush()

    sfk_dates = [datetime(2024, 12, 11), datetime(2024, 12, 12), datetime(2024, 12, 13)]
    sfk_event_dates = create_event_dates(
        sfk_event.id, sfk_dates, [time(9, 0), time(11, 0)], sfk_event.capacity
    )
    db.add_all(sfk_event_dates)

    # Štátna opera event
    statna_opera = create_organizer_and_employee("Štátna opera", "statna_opera")

    statna_opera_event = Event(
        title="Malý princ",
        institution_name="Štátna opera",
        address="Sála Štátnej opery, Národná 11, Banská Bystrica",
        city="Banská Bystrica",
        capacity=289,
        description="Hudobno-dramatické dielo s podnadpisom „magická opera“ je zhudobnením najvýznamnejšieho rozprávkového príbehu modernej literatúry, nadčasovej knihy Antoine de Saint-Exupéryho.",
        annotation="Stvárňuje príbeh pilota (samotného autora - spisovateľa), ktorý počas vojny uviazne s havarovaným lietadlom v saharskej púšti. Stretáva sa tu s Malým princom, ktorý prišiel z ďalekej planétky a vedie s ním rozhovor o zmysle života, o priateľstve i láske, o pýche i pokore.",
        target_group=TargetGroup.ALL,
        age_from=5,
        age_to=15,
        event_type=EventType.THEATER,
        duration=120,
        organizer_id=statna_opera.user_id,
        more_info_url="https://www.stateopera.sk/sk/program",
    district="banska_bystrica",  # Set to the appropriate district value
    region="banskobystricky",  # Set to the appropriate region value
    )
    db.add(statna_opera_event)
    db.flush()

    statna_opera_dates = [datetime(2024, 10, 24), datetime(2024, 10, 25)]
    statna_opera_event_dates = create_event_dates(
        statna_opera_event.id,
        statna_opera_dates,
        [time(10, 30)],
        statna_opera_event.capacity,
    )
    db.add_all(statna_opera_event_dates)

    # Divadlo Nová scéna event
    nova_scena = create_organizer_and_employee("Divadlo Nová scéna", "nova_scena")

    nova_scena_punk_rock = Event(
        title="PUNK ROCK",
        institution_name="Divadlo Nová scéna",
        address="Veľká sála Divadla Nová scéna, Živnostenská 1",
        city="Bratislava",
        capacity=581,
        description="Hra známeho britského autora školskej drámy Simona Stephensa, ktorú s úspechom uvádzajú divadlá na celom svete a ktorá veľmi prirodzeným a mladému divákovi blízkym jazykom hovorí o tolerancii a násilí.",
        annotation="Hra PUNK ROCK skúma problémy a svet skupiny dnešných tínedžerov, ktorí sa pripravujú na maturitu a plánujú štúdium na vysokej škole. Žijú svoje každodenné životy. Sú šťastní aj otrávení zo života, zo školy, z rodičov...",
        target_group=TargetGroup.HIGH_SCHOOL,
        age_from=15,
        age_to=19,
        event_type=EventType.THEATER,
        duration=130,  # 100 minutes performance + 30 minutes discussion
        organizer_id=nova_scena.user_id,
        more_info_url="https://www.novascena.sk/repertoar",
  district="bratislava_i",  # Set to the appropriate district value
    region="bratislavsky",  # Set to the appropriate region value
    )
    db.add(nova_scena_punk_rock)
    db.flush()

    # Add event dates (1x monthly from September to December 2024)
    punk_rock_dates = [datetime(2024, m, 1) for m in range(9, 13)]
    punk_rock_event_dates = create_event_dates(
        nova_scena_punk_rock.id,
        punk_rock_dates,
        [time(10, 30)],
        nova_scena_punk_rock.capacity,
    )
    db.add_all(punk_rock_event_dates)

    nova_scena_event = Event(
        title="Nepovinne po víne",
        institution_name="Divadlo Nová scéna",
        address="Štúdio Olympia, Živnostenská 1",
        city="Bratislava",
        capacity=90,
        description="Hudobno-poetické pásmo Nepovinne po víne je venované slovenskej poézii v inom šate.",
        annotation="Tzv. povinná literatúra, ako ju poznáme zo školy, vstúpi do dialógu s nepovinnou, ktorá by sa však možno mala stať povinnou. Divák sa dozvie viac aj zo života samotných autorov, ich prepletenia vo vzťahoch i tvorbe a bude ich vedieť zaradiť historicky aj do kontextu doby, v ktorej tvorili.",
        target_group=TargetGroup.HIGH_SCHOOL,
        age_from=14,
        age_to=19,
        event_type=EventType.THEATER,
        duration=60,
        organizer_id=nova_scena.user_id,
        more_info_url="https://www.novascena.sk/repertoar",
  district="bratislava_i",  # Set to the appropriate district value
    region="bratislavsky",  # Set to the appropriate region value
    )
    db.add(nova_scena_event)
    db.flush()

    nova_scena_dates = [datetime(2024, m, 1) for m in range(9, 13) for _ in range(2)]
    nova_scena_event_dates = create_event_dates(
        nova_scena_event.id, nova_scena_dates, [time(10, 30)], nova_scena_event.capacity
    )
    db.add_all(nova_scena_event_dates)

    # Národné divadlo Košice events
    nd_kosice = create_organizer_and_employee("Národné divadlo Košice", "nd_kosice")

    # O Paľovi, čo sa ani čerta nebál
    nd_kosice_event1 = Event(
        title="O Paľovi, čo sa ani čerta nebál",
        institution_name="Národné divadlo Košice",
        address="Malá scéna Národného divadla Košice, Hlavná 41",
        city="Košice",
        capacity=131,
        description="Rozprávkový príbeh napísaný na motívy štyroch rozprávok zozbieraných a spísaných Pavlom Dobšinským.",
        annotation="Je to celistvý príbeh, v ktorom sa prelínajú štyri spomínané motívy plné dobrodružstva, fantázie a morálnych hodnôt. Rozprávka je o veselom i nebezpečnom putovaní chlapca v čase, do doby našich predkov, počas ktorého sa nakoniec z neho stane mladý muž.",
        target_group=TargetGroup.ALL,
        age_from=6,
        age_to=12,
        event_type=EventType.THEATER,
        duration=90,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",

    )
    db.add(nd_kosice_event1)
    db.flush()

    nd_kosice_event1_dates = [
        (datetime(2024, 9, 15), time(16, 0)),
        (datetime(2024, 9, 16), time(10, 0)),
        (datetime(2024, 10, 27), time(16, 0)),
        (datetime(2024, 10, 28), time(10, 0)),
        (datetime(2024, 11, 24), time(16, 0)),
        (datetime(2024, 11, 25), time(10, 0)),
    ]
    nd_kosice_event1_dates = [
        EventDate(
            event_id=nd_kosice_event1.id,
            date=datetime.combine(d, t),
            time=datetime.combine(d, t),
            capacity=131,
        )
        for d, t in nd_kosice_event1_dates
    ]
    db.add_all(nd_kosice_event1_dates)

    # Národné divadlo Košice events (continuation)

    # Harún a more nápadov
    nd_kosice_event2 = Event(
        title="Harún a more nápadov",
        institution_name="Národné divadlo Košice",
        address="Malá scéna Národného divadla Košice, Hlavná 41",
        city="Košice",
        capacity=145,
        description="Divadelná adaptácia rozprávkového románu známeho britského spisovateľa indického pôvodu Salmana Rushdieho.",
        annotation="Ide o príbeh chlapca Harúna, ktorý chce pomôcť zachrániť svoju rodinu a oceán príbehov. Počas deja sa odkrýva množstvo metafor, obrazov a posolstiev, ktoré presahujú príbeh a stávajú sa aktuálnymi aj pre súčasného detského a dospelého diváka.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=8,
        age_to=12,
        event_type=EventType.THEATER,
        duration=90,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event2)
    db.flush()

    nd_kosice_event2_dates = [
        (datetime(2024, 10, 20), time(10, 0)),
        (datetime(2024, 12, 1), time(16, 0)),
        (datetime(2024, 12, 2), time(10, 0)),
    ]
    nd_kosice_event2_dates = [
        EventDate(
            event_id=nd_kosice_event2.id,
            date=datetime.combine(d, t),
            time=datetime.combine(d, t),
            capacity=145,
        )
        for d, t in nd_kosice_event2_dates
    ]
    db.add_all(nd_kosice_event2_dates)

    # Amadeus
    nd_kosice_event3 = Event(
        title="Amadeus",
        institution_name="Národné divadlo Košice",
        address="Historická budova Národného divadla Košice, Hlavná 58",
        city="Košice",
        capacity=555,
        description="V divadelnej hre Amadeus od anglického dramatika a scenáristu Petra Shaffera sa ponoríte do 18. storočia, kedy politické machinácie a rivalita sprevádzali génia hudby Wolfganga Amadea Mozarta a jeho rivala, skladateľa Antonia Salieriho.",
        annotation="Podobne ako v majstrovskom filme Miloša Formana, aj táto inscenácia odhalí temné stránky slávy a vášne, zvukovo a vizuálne prevedené do vynikajúcej podoby.",
        target_group=TargetGroup.HIGH_SCHOOL,
        age_from=15,
        age_to=19,
        event_type=EventType.THEATER,
        duration=140,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event3)
    db.flush()

    db.add(
        EventDate(
            event_id=nd_kosice_event3.id,
            date=datetime(2024, 9, 30, 10, 0),
            time=datetime(2024, 9, 30, 10, 0),
            capacity=555,
        )
    )
    # Pygmalion
    nd_kosice_event4 = Event(
        title="Pygmalion",
        institution_name="Národné divadlo Košice",
        address="Historická budova Národného divadla Košice, Hlavná 58",
        city="Košice",
        capacity=555,
        description="Pygmalion, najúspešnejšia hra zakladateľa modernej anglickej drámy a nositeľa Nobelovej ceny za literatúru Bernarda Shawa.",
        annotation="Naštudovanie Pygmaliona v košickom Národnom divadle posilňuje tému ženskej emancipácie, ľudskej dôstojnosti a spoločenských predsudkov. Profesor fonetiky Higgins uzavrie stávku, že dieťa ulice - chudobnú predavačku kvetov Lízu, pretvorí na skutočnú dámu.",
        target_group=TargetGroup.HIGH_SCHOOL,
        age_from=15,
        age_to=19,
        event_type=EventType.THEATER,
        duration=150,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event4)
    db.flush()

    db.add(
        EventDate(
            event_id=nd_kosice_event4.id,
            date=datetime(2024, 12, 17, 10, 0),
            time=datetime(2024, 12, 17, 10, 0),
            capacity=555,
        )
    )

    # Mačka Ivanka
    nd_kosice_event5 = Event(
        title="Mačka Ivanka",
        institution_name="Národné divadlo Košice",
        address="Malá scéna Národného divadla Košice, Hlavná 41",
        city="Košice",
        capacity=145,
        description="Rodinná opera Very Nemirovej a Massimiliana Matesica je o mačke Ivanke, ktorá miluje operu, rada spieva a túži sa vyrovnať primadone.",
        annotation="Je to pútavý príbeh, v ktorom Ivanka ako spievajúca mačka spôsobí obrovský rozruch v bežnom chode operného domu. Okolo mačacieho príbehu autorka zoskupila mnoho detailných postrehov o fungovaní opery.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=6,
        age_to=19,
        event_type=EventType.OPERA,
        duration=90,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",     
    )
    db.add(nd_kosice_event5)
    db.flush()

    nd_kosice_event5_dates = [
        datetime(2024, 9, 23),
        datetime(2024, 12, 16),
        datetime(2024, 12, 17),
    ]
    nd_kosice_event5_dates = create_event_dates(
        nd_kosice_event5.id,
        nd_kosice_event5_dates,
        [time(10, 0)],
        capacity=nd_kosice_event5.capacity,
    )
    db.add_all(nd_kosice_event5_dates)

    # Orchestríček
    nd_kosice_event6 = Event(
        title="Orchestríček",
        institution_name="Národné divadlo Košice",
        address="Malá scéna Národného divadla Košice, Hlavná 41",
        city="Košice",
        capacity=145,
        description="Zábavný výchovný koncert pre deti, ktoré sa ocitnú na Malej scéne obklopené hudobníkmi a spevákmi, zvukmi a vibráciami hlasov a nástrojov, v uvoľnenej atmosfére, do ktorej je zapojené telo a pohyb, myseľ a emócie.",
        annotation="Deti spoločne s dvoma obľúbenými bratmi Tomom a Elom objavujú čaro hudobných nástrojov. Počas koncertov majú deti veľmi dôležitú úlohu - pomôcť znova napísať zničenú knihu o hudobných nástrojoch.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=5,
        age_to=14,
        event_type=EventType.CONCERT,
        duration=60,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event6)
    db.flush()

    db.add(
        EventDate(
            event_id=nd_kosice_event6.id,
            date=datetime(2024, 10, 15, 10, 0),
            time=datetime(2024, 10, 15, 10, 0),
            capacity=145,
        )
    )

    # Malý princ
    nd_kosice_event7 = Event(
        title="Malý princ",
        institution_name="Národné divadlo Košice",
        address="Historická budova Národného divadla Košice, Hlavná 58",
        city="Košice",
        capacity=555,
        description="Baletná rozprávka Antoine de Saint-Exupéry, Malý princ ešte i dnes prekvapuje svojou čistotou a láskavým pochopením sveta, v ktorom žijeme.",
        annotation="Tanečníci jednotlivých postáv zapájajú deti do príbehu predstavenia, aby na ňom participovali. Táto hravá a zábavná interakcia pomáha vytvoriť prostredie, v ktorom sa deti cítia byť jeho súčasťou a majú pocit, že môžu príbeh ovplyvniť.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=6,
        age_to=14,
        event_type=EventType.BALLET,
        duration=108,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event7)
    db.flush()

    nd_kosice_event7_dates = [
        (datetime(2024, 10, 31), time(18, 0)),
        (datetime(2024, 11, 9), time(18, 0)),
        (datetime(2024, 11, 10), time(16, 0)),
    ]
    nd_kosice_event7_dates = [
        EventDate(
            event_id=nd_kosice_event7.id,
            date=datetime.combine(d, t),
            time=datetime.combine(d, t),
            capacity=555,
        )
        for d, t in nd_kosice_event7_dates
    ]
    db.add_all(nd_kosice_event7_dates)

    # Luskáčik
    nd_kosice_event8 = Event(
        title="Luskáčik",
        institution_name="Národné divadlo Košice",
        address="Historická budova Národného divadla Košice, Hlavná 58",
        city="Košice",
        capacity=555,
        description="Jedna z najkrajších baletných rozprávok - Luskáčik. Rozprávkové bytosti Princ a Myší kráľ, ale aj Klára, dievčatko s dobrým srdcom a odvahou, ožijú v nádhernej hudbe Petra Iljiča Čajkovského.",
        annotation="Klasická baletná rozprávka pre celú rodinu.",
        target_group=TargetGroup.ALL,
        age_from=3,
        age_to=19,
        event_type=EventType.BALLET,
        duration=80,
        organizer_id=nd_kosice.user_id,
        more_info_url="http://www.sdke.sk/sk/divadlo/program",
        district="kosice",
        region="kosicky",
    )
    db.add(nd_kosice_event8)
    db.flush()

    nd_kosice_event8_dates = [
        datetime(2024, 12, 4),
        datetime(2024, 12, 5),
        datetime(2024, 12, 9),
    ]
    nd_kosice_event8_dates = create_event_dates(
        nd_kosice_event8.id,
        nd_kosice_event8_dates,
        [time(10, 0)],
        capacity=nd_kosice_event8.capacity,
    )
    db.add_all(nd_kosice_event8_dates)

    # Slovenský ľudový umelecký kolektív events
    sluk = create_organizer_and_employee("Slovenský ľudový umelecký kolektív", "sluk")

    # Gašparko
    sluk_event1 = Event(
        title="Gašparko",
        institution_name="Slovenský ľudový umelecký kolektív",
        address="Balkánska 31/66, 853 08 Bratislava - Rusovce",
        city="Bratislava",
        capacity=184,
        description="Gašparko interaktívne hudobno-tanečné predstavenie s bábkami.",
        annotation="Tanečná veselohra je určená deťom od 4-9 rokov. Scénická forma je postavená na spojení tradičného bábkového divadla a ľudového tanca a hudby. Program si kladie za cieľ aktivizovať deti a zapájať ich priamo do diania na scéne.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=4,
        age_to=9,
        event_type=EventType.THEATER,
        duration=60,
        organizer_id=sluk.user_id,
        more_info_url="https://www.sluk.sk/predstavenia/gasparko/",
        district="bratislava_i",
        region="bratislavsky",
    )
    db.add(sluk_event1)
    db.flush()

    # Zvuky nie sú muky
    sluk_event2 = Event(
        title="Zvuky nie sú muky",
        institution_name="Slovenský ľudový umelecký kolektív",
        address="Balkánska 31/66, 853 08 Bratislava - Rusovce",
        city="Bratislava",
        capacity=184,
        description="Muzikantská veselohra Zvuky nie sú muky formou hry a vtipu zoznámi deti vo veku od 5 do 10 rokov s rôznymi ľudovými hudobnými nástrojmi a hudobnými hračkami.",
        annotation="Počas interaktívneho predstavenia sa detskí diváci naučia hudbu nielen vnímať, ale aj tvoriť. Spolu s muzikantami si majú možnosť zaspievať, vyskúšať svoju rytmickú zdatnosť a zahrať malú divadelnú etudu priamo na javisku.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=5,
        age_to=10,
        event_type=EventType.THEATER,
        duration=60,
        organizer_id=sluk.user_id,
        more_info_url="https://www.sluk.sk/predstavenia/zvuky-nie-su-muky/",
        district="bratislava_i",
        region="bratislavsky",
    )
    db.add(sluk_event2)
    db.flush()

    # Slovensko
    sluk_event3 = Event(
        title="Slovensko",
        institution_name="Slovenský ľudový umelecký kolektív",
        address="Balkánska 31/66, 853 08 Bratislava - Rusovce",
        city="Bratislava",
        capacity=184,
        description="Atraktívny program tancov a piesní rôznych regiónov Slovenska.",
        annotation="Autori sa pri javiskovom spracovaní pôvodného folklórneho materiálu opierali o atribúty typické pre ľudové umenie: improvizácia, inovácia, grotesknosť, komika, exotika i teatrálnosť.",
        target_group=TargetGroup.HIGH_SCHOOL,
        age_from=11,
        age_to=19,
        event_type=EventType.PERFORMANCE,
        duration=80,
        organizer_id=sluk.user_id,
        more_info_url="https://www.sluk.sk/predstavenia/slovensko/",
        district="bratislava_i",
        region="bratislavsky",
    )
    db.add(sluk_event3)
    db.flush()

    sluk_dates = [datetime(2024, m, 1) for m in [9, 10]]
    sluk_event1_dates = create_event_dates(
        sluk_event1.id, sluk_dates, [time(9, 0), time(13, 0)], sluk_event1.capacity
    )
    sluk_event2_dates = create_event_dates(
        sluk_event2.id, sluk_dates, [time(9, 0), time(11, 0)], sluk_event2.capacity
    )
    sluk_event3_dates = create_event_dates(
        sluk_event3.id, sluk_dates, [time(9, 0), time(11, 0)], sluk_event3.capacity
    )
    db.add_all(sluk_event1_dates + sluk_event2_dates + sluk_event3_dates)

    # Tanečné divadlo Ifjú Szivek events
    ifju_szivek = create_organizer_and_employee(
        "Tanečné divadlo Ifjú Szivek", "ifju_szivek"
    )

    # Škola tanca - Tánciskola
    ifju_szivek_event1 = Event(
        title="Škola tanca - Tánciskola",
        institution_name="Tanečné divadlo Ifjú Szivek",
        address="Mostová 6, Bratislava",
        city="Bratislava",
        capacity=76,
        description="Škola tanca je najúspešnejším matiné-programom umeleckého kolektívu, ktorý za desať rokov predstavili vyše dvesto krát doma i v zahraničí.",
        annotation="Predstavenie približuje atmosféru školy, kde sa počas nezvyčajnej hodiny tanca môžu detskí diváci oboznámiť s tancami národov Karpatskej kotliny podľa geografického členenia.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=6,
        age_to=15,
        event_type=EventType.DANCE,
        duration=50,
        organizer_id=ifju_szivek.user_id,
        more_info_url="https://ifjuszivek.sk/sk/repertoar/skola-madarskeho-tanca",
        district="bratislava_i",
        region="bratislavsky",
    )
    db.add(ifju_szivek_event1)
    db.flush()

    ifju_szivek_event1_dates = [
        datetime(2024, 9, 23),
        datetime(2024, 9, 24),
        datetime(2024, 9, 25),
        datetime(2024, 10, 14),
        datetime(2024, 10, 15),
        datetime(2024, 10, 16),
    ]
    ifju_szivek_event1_dates = create_event_dates(
        ifju_szivek_event1.id,
        ifju_szivek_event1_dates,
        [time(9, 0), time(11, 0), time(13, 0)],
        capacity=ifju_szivek_event1.capacity,
    )
    db.add_all(ifju_szivek_event1_dates)

    # Kukučie vajíčko
    ifju_szivek_event2 = Event(
        title="Kukučie vajíčko",
        institution_name="Tanečné divadlo Ifjú Szivek - Tánczinház",
        address="Mostová 6, Bratislava",
        city="Bratislava",
        capacity=76,
        description="Cieľom predstavenia je zbúrať faktami nepodložené, ale na našom území rozšírené predsudky, ktoré obklopujú folklorizmus.",
        annotation="Predstavenie sprevádzané živou hudbou spracováva vzťah populárnych žánrov s tradičnou ľudovou kultúrou vo forme, vďaka ktorej sa divák v zásade dobre zabaví ale dostane sa aj o krok bližšie k autentickej ľudovej kultúre.",
        target_group=TargetGroup.ELEMENTARY_SCHOOL,
        age_from=6,
        age_to=15,
        event_type=EventType.DANCE,
        duration=45,
        organizer_id=ifju_szivek.user_id,
        more_info_url="https://ifjuszivek.sk/sk/repertoar/kukucie-vajicko-0",
        district="bratislava_i",
        region="bratislavsky",
    )
    db.add(ifju_szivek_event2)
    db.flush()

    ifju_szivek_event2_dates = [datetime(2024, m, 1) for m in [9, 10]]
    ifju_szivek_event2_dates = create_event_dates(
        ifju_szivek_event2.id,
        ifju_szivek_event2_dates,
        [time(9, 0), time(11, 0), time(13, 0)],
        ifju_szivek_event2.capacity,
    )
    db.add_all(ifju_szivek_event2_dates)

    # Slovenská ústredná hvezdáreň event
    suh = create_organizer_and_employee("Slovenská ústredná hvezdáreň", "suh")

    suh_event = Event(
        title="Stála programová ponuka",
        institution_name="Slovenská ústredná hvezdáreň",
        address="Komárňanská 137, 947 01 Hurbanovo",
        city="Hurbanovo",
        capacity=36,
        description="Ponuka spočíva v aktivitách v priestoroch stálej expozície múzea, program v planetáriu a prehliadka priestorov historickej budovy a astronomickej techniky, s možnosťou astronomického pozorovania v prípade priaznivého počasia.",
        annotation="Návšteva hvezdárne s programom v planetáriu a možnosťou astronomického pozorovania.",
        target_group=TargetGroup.ALL,
        age_from=6,
        age_to=19,
        event_type=EventType.EXHIBITION,
        duration=90,
        organizer_id=suh.user_id,
        more_info_url="https://www.suh.sk/navstivte-nas-menu/filmy-v-planetariu/",
        district="nove_zamky",
        region="nitriansky",
    )
    db.add(suh_event)
    db.flush()

    suh_dates = [datetime(2024, 9, day) for day in range(1, 31)]
    suh_event_dates = create_event_dates(
        suh_event.id, suh_dates, [time(9, 0)], suh_event.capacity
    )
    db.add_all(suh_event_dates)

    # Combined events from ÚĽUV and Slovenská vedecká knižnica
    uluv_svk = create_organizer_and_employee(
        "ÚĽUV a Slovenská vedecká knižnica", "uluv_svk"
    )

    # Event 1: Tvorivé remeselné dielne a interaktívna prehliadka expozície Ľudové hudobné nástroje na Slovensku
    uluv_svk_event1 = Event(
        title="Tvorivé remeselné dielne a interaktívna prehliadka expozície Ľudové hudobné nástroje na Slovensku",
        institution_name="Ústredie ľudovej umeleckej výroby - Regionálne centrum remesiel ÚĽUV v Banskej Bystrici a Slovenská vedecká knižnica v Banskej Bystrici",
        address="Dolná 14, 974 01 Banská Bystrica a Lazovná 240/9, 975 58 Banská Bystrica",
        city="Banská Bystrica",
        capacity=24,
        description="Tvorivé remeselné dielne a interaktívna prehliadka expozície Ľudové hudobné nástroje na Slovensku",
        annotation="Kombinovaná ponuka tvorivých dielní a prehliadky expozície.",
        target_group=TargetGroup.ALL,
        age_from=6,
        age_to=19,
        event_type=EventType.WORKSHOP,
        duration=180,  # 120 + 60 minutes
        organizer_id=uluv_svk.user_id,
        district="banska_bystrica",
        region="banskobystricky",
            )
    db.add(uluv_svk_event1)
    db.flush()

    uluv_svk_event1_dates = [
        datetime(2024, 10, 8),
        datetime(2024, 10, 15),
        datetime(2024, 10, 22),
        datetime(2024, 10, 29),
    ]
    uluv_svk_event1_dates = create_event_dates(
        uluv_svk_event1.id,
        uluv_svk_event1_dates,
        [time(9, 0), time(13, 0)],
        uluv_svk_event1.capacity,
    )
    db.add_all(uluv_svk_event1_dates)

    # Event 2: Tvorivé remeselné dielne a interaktívna výstava: Bábkarský salón
    uluv_svk_event2 = Event(
        title="Tvorivé remeselné dielne a interaktívna výstava: Bábkarský salón",
        institution_name="Ústredie ľudovej umeleckej výroby - Regionálne centrum remesiel ÚĽUV v Banskej Bystrici a Slovenská vedecká knižnica v Banskej Bystrici",
        address="Dolná 14, 974 01 Banská Bystrica a Lazovná 240/9, 975 58 Banská Bystrica",
        city="Banská Bystrica",
        capacity=24,
        description="Tvorivé remeselné dielne a interaktívna výstava: Bábkarský salón",
        annotation="Kombinovaná ponuka tvorivých dielní a interaktívnej výstavy.",
        target_group=TargetGroup.ALL,
        age_from=6,
        age_to=19,
        event_type=EventType.WORKSHOP,
        duration=180,  # 120 + 60 minutes
        organizer_id=uluv_svk.user_id,
        district="banska_bystrica",
        region="banskobystricky",
    )
    db.add(uluv_svk_event2)
    db.flush()

    uluv_svk_event2_dates = [
        datetime(2024, 10, 3),
        datetime(2024, 10, 10),
        datetime(2024, 10, 17),
        datetime(2024, 10, 24),
    ]
    uluv_svk_event2_dates = create_event_dates(
        uluv_svk_event2.id,
        uluv_svk_event2_dates,
        [time(9, 0), time(13, 0)],
        uluv_svk_event2.capacity,
    )
    db.add_all(uluv_svk_event2_dates)

    db.commit()
    print("EVENTS SEEDED SUCCESSFULLY")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "users":
            seed_users()
        elif sys.argv[1] == "events":
            seed_events()
        elif sys.argv[1] == "admin":
            seed_only_admin_user()
        elif sys.argv[1] == "all":
            seed_users()
            seed_events()
    else:
        print("Usage: python -m app.db seed [users|events|all]")
