import sqlite3

DATABASE = "busmate.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def normalize_existing_bus_numbers(cursor):
    """
    Convert older bus numbers such as 01, 01A, 02 into
    R01, R01A, R02 without unnecessarily changing bus IDs.
    """
    cursor.execute("SELECT id, bus_number FROM buses ORDER BY id")
    rows = cursor.fetchall()

    for old_id, old_number in rows:
        old_number = str(old_number).strip().upper()

        if old_number.startswith("R"):
            continue

        new_number = "R" + old_number

        cursor.execute(
            "SELECT id FROM buses WHERE bus_number = ?",
            (new_number,)
        )
        target = cursor.fetchone()

        if target is None:
            cursor.execute(
                "UPDATE buses SET bus_number = ? WHERE id = ?",
                (new_number, old_id)
            )
        else:
            target_id = target[0]

            if target_id == old_id:
                continue

            # Preserve existing stop references.
            cursor.execute(
                "UPDATE stops SET bus_id = ? WHERE bus_id = ?",
                (target_id, old_id)
            )

            # Preserve return-bus references if that table exists.
            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'return_buses'
            """)
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE return_buses SET bus_id = ? WHERE bus_id = ?",
                    (target_id, old_id)
                )

            cursor.execute(
                "DELETE FROM buses WHERE id = ?",
                (old_id,)
            )


def add_route(cursor, bus_number, route_name, stops):
    # Keep every route number in the format used by main.py:
    # R01, R01A, R01B, R02, ...
    bus_number = str(bus_number).strip().upper()
    if not bus_number.startswith("R"):
        bus_number = "R" + bus_number

    cursor.execute("""
        INSERT INTO buses (bus_number, route_name)
        VALUES (?, ?)
        ON CONFLICT(bus_number) DO UPDATE SET route_name = excluded.route_name
    """, (bus_number, route_name))

    cursor.execute(
        "SELECT id FROM buses WHERE bus_number = ?",
        (bus_number,)
    )
    bus_id = cursor.fetchone()[0]

    # Replace only morning stops.
    # Existing return_buses keep their bus_id.
    cursor.execute("""
        DELETE FROM stops
        WHERE bus_id = ? AND direction = 'MORNING'
    """, (bus_id,))

    for order, (stop_name, stop_time) in enumerate(stops, start=1):
        cursor.execute("""
            INSERT INTO stops
            (bus_id, stop_name, stop_time, stop_order, direction)
            VALUES (?, ?, ?, ?, 'MORNING')
        """, (bus_id, stop_name, stop_time, order))


def seed_data():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Repair older 01/01A/02-style records before loading the PDF data.
        normalize_existing_bus_numbers(cursor)

        add_route(cursor, 'R01', 'Ennore', [
            ('Lift Gate', '5:50 AM'),
            ('Wimco Market', '5:55 AM'),
            ('Ajax', '6:00 AM'),
            ('Periyar Nagar', '6:03 AM'),
            ('Thiruvortiyur Market', '6:08 AM'),
            ('Theradi', '6:10 AM'),
            ('Ellaimman Koil', '6:12 AM'),
            ('Raja Kadai', '6:14 AM'),
            ('Toll Gate', '6:15 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R01A', 'Tondiarpet', [
            ('New vannarpettai', '6:17 AM'),
            ('Apollo', '6:18 AM'),
            ('Tondiarpet', '6:19 AM'),
            ('Maharani', '6:21 AM'),
            ('Mint', '6:22 AM'),
            ('New Bus Stand Mint', '6:27 AM'),
            ('Thirupalli street', '6:33 AM'),
            ('Aminijkarai', '7:00 AM'),
            ('Skywalk', '7:02 AM'),
            ('Arumbakkam', '7:07 AM'),
            ('Koyambedu Metro', '7:10 AM'),
            ('Vengaya mandi', '7:16 AM'),
            ('Ration stop (Nerkundram)', '7:20 AM'),
            ('Maduravoyal', '7:21 AM'),
            ('Maduravoyal Erikarai', '7:25 AM'),
            ('Vanagaram', '7:29 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R01B', 'Kasimedu', [
            ('Kasimedu', '6:15 AM'),
            ('Kalmandapam', '6:21 AM'),
            ('Royapuram Bridge', '6:27 AM'),
            ('Beach Station', '6:30 AM'),
            ("Parry's", '6:34 AM'),
            ('Central', '6:37 AM'),
            ('Egmore', '6:40 AM'),
            ('Dasprakash', '6:44 AM'),
            ('Eaga Theatre', '6:48 AM'),
            ('Amjikarai Market', '6:51 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R02', 'Triplicane', [
            ('Chintadripet (Post Offiec)', '6:20 AM'),
            ('D1 Police Station', '6:25 AM'),
            ('Triplicane -High Way', '6:29 AM'),
            ('Ice House Police Station', '6:32 AM'),
            ('Meersahibpet-Market', '6:35 AM'),
            ('Royapettah New College', '6:39 AM'),
            ('Sterling Road (Bharath Petrol Bunk)', '6:40 AM'),
            ('Choolaimedu Subway', '6:43 AM'),
            ('Choolaimedu bus stop', '6:45 AM'),
            ('Anna Arch', '6:50 AM'),
            ('Arumbakkam Panchaliamman Koil', '6:53 AM'),
            ('NSK', '6:55 AM'),
            ('Maduravoyal- Murugan Store', '6:58 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R03', 'Choolai', [
            ('Pulianthope', '6:20 AM'),
            ('Choolai Post Office', '6:25 AM'),
            ('Purasaivakkam Doveton', '6:30 AM'),
            ('Kellys Signal', '6:33 AM'),
            ('Water tank road signal', '6:40 AM'),
            ('Kilpauk Garden', '6:45 AM'),
            ('Chinthamani', '6:50 AM'),
            ('Anna Nagar Roundtana', '6:55 AM'),
            ('Thirumangalam Blue star', '6:57 AM'),
            ('VR Mall', '7:00 AM'),
            ('Maduravoyal Ration Shop', '7:10 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R03A', 'Collector nagar', [
            ('Collector nagar', '6:50 AM'),
            ('Golden flat', '6:55 AM'),
            ('Mogappair West depot', '7:00 AM'),
            ('Nolambur', '7:03 AM'),
            ('MGR University', '7:08 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R03B', 'Water Tank', [
            ('Gangaiamman koil', '6:40 AM'),
            ('Madina masjid', '6:43 AM'),
            ('New Avadi Road', '6:45 AM'),
            ('Chintamani', '6:50 AM'),
            ('Nalli Store', '6:58 AM'),
            ('Anna Nagar Metro', '7:05 AM'),
            ('Thirumangalam Metro', '7:10 AM'),
            ('Nerkundram', '7:15 AM'),
            ('Maduravaoyal Ration Shop', '7:25 AM'),
            ('Maduravoyal Erikarai', '7:27 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R04', 'East Mogappair', [
            ('JJ Nagar Police Station', '6:30 AM'),
            ('HDFC Bank', '6:32 AM'),
            ('IOB Bank', '6:35 AM'),
            ('7 H Bus Depot', '6:40 AM'),
            ('Amutha School', '6:50 AM'),
            ('D.R.Super Market', '6:52 AM'),
            ('Nolambur', '6:55 AM'),
            ('Meadows Apprtment', '6:57 AM'),
            ('MGR University', '7:00 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R05', 'CIT Nagar', [
            ('CIT Nagar', '6:10 AM'),
            ('Aranganathan Subway', '6:12 AM'),
            ('Srinivasa Theatre', '6:14 AM'),
            ('Metupalayam', '6:16 AM'),
            ('Sangamam Hotel', '6:19 AM'),
            ('Aryagowda Road', '6:24 AM'),
            ('Vivek', '6:29 AM'),
            ('Usman Road', '6:34 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R05A', 'Loyola College', [
            ('Loyola College', '6:40 AM'),
            ('Choolaimedu', '6:45 AM'),
            ('Metha Nagar', '6:49 AM'),
            ('NSK Nagar', '6:55 AM'),
            ('Arumbakkam (SBI Bank)', '7:00 AM'),
            ('MMDA Cholan Street', '7:05 AM'),
            ('MMDA Vallavan Hotel', '7:10 AM'),
            ('CMBT (Koyambedu)', '7:15 AM'),
            ('Rohini (Theatre)', '7:18 AM'),
            ('Nerkundram Vengaya Mandi', '7:22 AM'),
            ('Maduravoyal Erikarai', '7:25 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R06', 'Chinmaiya Nagar', [
            ('Chinmaiya Nagar', '6:10 AM'),
            ('Sai Nagar', '6:12 AM'),
            ('Natesan Nagar', '6:13 AM'),
            ('Elango Nagar', '6:14 AM'),
            ('Virugampakkam', '6:17 AM'),
            ('KK Nagar', '6:20 AM'),
            ('KK Nagar ESI', '6:27 AM'),
            ('Ashok Pillar', '6:32 AM'),
            ('Kasi Theatre', '6:37 AM'),
            ('Ekkatuthangal', '6:42 AM'),
            ('Olympia', '6:43 AM'),
            ('Porur Saravana Store', '6:55 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R07', 'Santhome', [
            ('Mandaveli Bus Depot', '6:10 AM'),
            ('Pattinapakkam', '6:15 AM'),
            ('Kutchery Road', '6:20 AM'),
            ('Luz Corner', '6:25 AM'),
            ('P.S.Sivasamy Road', '6:27 AM'),
            ('SIET College', '6:32 AM'),
            ('Nanthanam Signal', '6:37 AM'),
            ('Saidapet Vetrinary Hospital', '6:42 AM'),
            ('Saidapet Bus Stop', '6:47 AM'),
            ('Guindy', '6:49 AM'),
            ('Butt Road', '6:55 AM'),
            ('Chennai Trade Centre', '7:10 AM'),
            ('Porur', '7:15 AM'),
            ('Ayyapanthangal', '7:18 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R08', 'Kovilambakkam', [
            ('Kovilampakkam', '6:10 AM'),
            ('Keelkattalai Bus Stop', '6:12 AM'),
            ('Madipakkam UTI Bank', '6:15 AM'),
            ('Madipakkam Koot Road Bus stop', '6:16 AM'),
            ('Ranga Theatre', '6:18 AM'),
            ('Nanganallur Chidambaram Stores', '6:10 AM'),
            ('Nanganallur Saravana Hotel', '6:22 AM'),
            ('Vanuvampet Church', '6:25 AM'),
            ('Surendhar Nagar Bus Stop', '6:27 AM'),
            ('Jayalakshmi Theatre', '6:29 AM'),
            ('Thillai Ganga Nagar Sub Way', '6:32 AM'),
            ('Aazar Khana Bus Stop', '6:35 AM'),
            ('Butt Road', '6:37 AM'),
            ('Ramavaram', '6:39 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R08A', 'Adambakkam', [
            ('Seasons', '6:30 AM'),
            ('Kakkan Bridge', '6:33 AM'),
            ('Adambakkam Bus Depot', '6:35 AM'),
            ('St Thomas Mount', '6:38 AM'),
            ('Deepam Foods', '6:40 AM'),
            ('Maharaja traders', '6:45 AM'),
            ('Vanuvampet church', '6:50 AM'),
            ('Thilaiganga nagar subway', '6:55 AM'),
            ('Butt road', '7:00 AM'),
            ('Poonamallee', '7:35 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R09', 'MKB Nagar', [
            ('Vyasarpadi', '6:00 AM'),
            ('MKB Nagar', '6:05 AM'),
            ('E.B. Stop', '6:08 AM'),
            ('Kannadhasan Nagar', '6:10 AM'),
            ('M.R.Nagar', '6:13 AM'),
            ('lakshmi Amman Nagar', '6:22 AM'),
            ('B.B.Road', '6:26 AM'),
            ('Perumbur Market', '6:34 AM'),
            ('Agaram', '6:40 AM'),
            ('Peravalur Road', '6:42 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R10', 'Thachoor', [
            ('Thachoor Koot Road', '5:50 AM'),
            ('Panjetty', '5:52 AM'),
            ('Janappanchatram Bypass', '5:54 AM'),
            ('Karanodai Bypass', '5:56 AM'),
            ('Vijaya Nallur', '5:59 AM'),
            ('Toll Gate', '6:01 AM'),
            ('Padianallur Checkpost', '6:03 AM'),
            ('Padianallur', '6:05 AM'),
            ('Redhills (GRT)', '6:10 AM'),
            ('Redhills Market', '6:12 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R11', 'Chengalpattu', [
            ('Chengalpattu Rattinakinaru', '6:00 AM'),
            ('New Bus Stand', '6:02 AM'),
            ('Old Bus Stand', '6:04 AM'),
            ('Chengalpattu Bypass', '6:07 AM'),
            ('SP Kovil', '6:18 AM'),
            ('MM Nagar Samiyar Gate', '6:23 AM'),
            ('MM Nagar Bus Stand', '6:28 AM'),
            ('KattanKulathur', '6:30 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R11A', 'Guduvanchery', [
            ('Guduvanchery', '6:30 AM'),
            ('Urapakkam', '6:35 AM'),
            ('Vandalur', '6:40 AM'),
            ('Perungalathur', '6:45 AM'),
            ('Vandalur Bridge', '6:55 AM'),
            ('Mannivakkam', '7:05 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R12', 'Minjur', [
            ('Minjur Bus Stand', '5:45 AM'),
            ('Minjur Railway Station', '5:50 AM'),
            ('BDO Office', '5:52 AM'),
            ('Nandiyambakkam', '5:54 AM'),
            ('Pattamandiri', '6:00 AM'),
            ('Napalayam', '6:05 AM'),
            ('Manali Pudhu nagar', '6:08 AM'),
            ('Manali Market', '6:15 AM'),
            ('MMDA 3rd Main Road', '6:18 AM'),
            ('Mathur', '6:22 AM'),
            ('Veterinary Hospital', '6:25 AM'),
            ('Madhavaram Milk Colony', '6:28 AM'),
            ('Arul Nagar', '6:30 AM'),
            ('Thapalpetti', '6:32 AM'),
            ('Moolakadai', '6:38 AM'),
            ('Kalpana Lamp', '6:45 AM'),
            ('Madhavaram Roundana', '6:47 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R13', 'Vyasarpadi', [
            ('Ganeshapuram', '6:10 AM'),
            ('G3 Police Station', '6:15 AM'),
            ('Pattalam', '6:18 AM'),
            ('Otteri', '6:20 AM'),
            ('Podi Kadai', '6:23 AM'),
            ('T.B.Hospital', '6:25 AM'),
            ('Ayanawaram Signal', '6:27 AM'),
            ('Sayyani', '6:30 AM'),
            ('Ayanawaram Noor Hotel', '6:33 AM'),
            ('Joint Office', '6:35 AM'),
            ('Ayanawaram Railway Quarters', '6:37 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R13A', 'ICF', [
            ('ICF Signal', '6:45 AM'),
            ('Villivakkam Bus Stand', '6:50 AM'),
            ('Korattur Signal', '6:55 AM'),
            ('Nolambur Signal', '7:05 AM'),
            ('Vanagaram', '7:15 AM'),
            ('Velappanchavadi', '7:23 AM'),
            ('Poonamallee Bypass', '7:30 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R14', 'Thiruvallur', [
            ('Sevapetai', '6:25 AM'),
            ('Kakkalur', '6:30 AM'),
            ('Poonga Nagar', '6:35 AM'),
            ('GRT', '6:50 AM'),
            ('Manavalanagar Signal', '6:55 AM'),
            ('Manavalanagar Railway Station', '6:57 AM'),
            ('Putlur', '7:10 AM'),
            ('Aranvoyal', '7:15 AM'),
            ('Puthuchatram (India Jappan Company)', '7:20 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R14B', 'Kakkalur', [
            ('Kakkalur Signal', '6:55 AM'),
            ('SBI Bank', '6:58 AM'),
            ('Vellavedu', '7:20 AM'),
            ('Thirumazhisai', '7:25 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R15', 'Cheyyar', [
            ('Cheyyar-SBI', '5:30 AM'),
            ('Soundarya Theatre', '5:31 AM'),
            ('Mangal X Road', '5:55 AM'),
            ('Ayyangarkulam', '6:05 AM'),
            ('Punjarasanthangal', '6:07 AM'),
            ('Sevlimedu', '6:07 AM'),
            ('Housing Board', '6:12 AM'),
            ('Collector Office', '6:18 AM'),
            ('Mettu street Signal', '6:20 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R15A', 'Orikkai', [
            ('Orikkai', '6:15 AM'),
            ('JJ Nagar', '6:17 AM'),
            ('Keerai Mandapam', '6:20 AM'),
            ('Tollgate', '6:23 AM'),
            ("Pachaiyappa's College", '6:30 AM'),
            ('Ayyampettai', '6:32 AM'),
            ('Rajampettai', '6:40 AM'),
            ('Walajabad', '6:50 AM'),
            ('Natha nallur', '7:00 AM'),
            ('Panrutti', '7:03 AM'),
            ('Oragadam', '7:12 AM'),
            ('Arun Excello', '7:15 AM'),
            ('Sriperumbudur High School', '7:20 AM'),
            ('Sriperumbudur Tollgate', '7:25 AM'),
            ('Irungattukottai bus stand', '7:30 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R15B', 'Kancheepuram', [
            ('Kancheepuram Bus Stand', '6:25 AM'),
            ('Pookadai Chatram', '6:28 AM'),
            ('Kammala street', '6:30 AM'),
            ('Railway Station', '6:32 AM'),
            ('Ponnerikarai', '6:35 AM'),
            ('Pappankuli', '6:50 AM'),
            ('Santhavellore', '6:52 AM'),
            ('Sunguvarchatram', '7:00 AM'),
            ('Mambakkam', '7:05 AM'),
            ('Vadamangalam', '7:10 AM'),
            ('Sathya Grand Resorts', '7:12 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R16', 'Neelangkarai', [
            ('Prathana Theatre', '6:10 AM'),
            ('Vetuvankeni', '6:15 AM'),
            ('Thiruvanmiyur RTO Office', '6:20 AM'),
            ('Adyar Depot', '6:29 AM'),
            ('Madyakailash', '6:35 AM'),
            ('Guindy', '6:42 AM'),
            ('Mugalivakkam', '6:55 AM'),
            ('Karayanchavadi', '7:10 AM'),
            ('Poonamallee Bus Stand', '7:15 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R16B', 'Sholinganallur', [
            ('Sholinganallur', '6:10 AM'),
            ('Karapakkam', '6:16 AM'),
            ('Karapakkam - TCS', '6:19 AM'),
            ('PTC (KFC)', '6:24 AM'),
            ('Mettukuppam', '6:26 AM'),
            ('Medavakkam nilgiris', '6:35 AM'),
            ('Santhoshpuram', '6:37 AM'),
            ('Sembakkam', '6:40 AM'),
            ('Tambaram Railway Station', '6:45 AM'),
            ('Krishna nagar bridge', '6:48 AM'),
            ('Kulakarai street', '6:50 AM'),
            ('Padmavathy Kalyana Mandapam', '6:55 AM'),
            ('Joshua School', '7:00 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R17', 'Valluvarkottam', [
            ('Valluvarkottam', '6:15 AM'),
            ('Liberty', '6:20 AM'),
            ('Power House', '6:25 AM'),
            ('Lakshman Sruthi', '6:30 AM'),
            ('Thai Sathya', '6:35 AM'),
            ('Virugambakkam', '6:40 AM'),
            ('Alwar Thirunagar', '6:42 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R17A', 'Valasaravakkam', [
            ('Valasaravakkam Shivan Koil', '6:45 AM'),
            ('Valasaravakkam', '6:50 AM'),
            ('Saravana Bhavan Hotel', '6:53 AM'),
            ('Lakshmi Nagar', '6:55 AM'),
            ('Porur Bridge', '7:00 AM'),
            ('Iyyappanthangal', '7:05 AM'),
            ('Kattupakkam', '7:10 AM'),
            ('Kumanachavadi', '7:15 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R18', 'Velachery', [
            ('Murugan Kalyana mandapam', '6:10 AM'),
            ('Velachery Bus Stand', '6:15 AM'),
            ('Kaiveli', '6:18 AM'),
            ('Balaji Dental College', '6:20 AM'),
            ('Pallikaranai', '6:23 AM'),
            ('Jeyachandran', '6:27 AM'),
            ('Rajakilpakam Signal', '6:35 AM'),
            ('Camp Road ICICI Bank', '6:38 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R18A', 'Sembakkam', [
            ('Sembakkam', '6:25 AM'),
            ('Poondi Bazaar', '6:45 AM'),
            ('Tambaram Sanatorium', '6:50 AM'),
            ('Chrompet', '6:55 AM'),
            ('Nagalkeni (nayara Petrol Bunk)', '7:00 AM'),
            ('Thiruneermalai', '7:05 AM'),
            ('Thirumudivakkam', '7:10 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R18B', 'Kelambakkam', [
            ('Kelambakkam - GH', '6:00 AM'),
            ('Pudupakkam', '6:10 AM'),
            ('Mambakkam (Samathuvapuram)', '6:15 AM'),
            ('Mambakkam Kulam', '6:20 AM'),
            ('Sithalapakkam', '6:30 AM'),
            ('Medavakkam Koot Road', '6:40 AM'),
            ('Kamarajapuram', '6:43 AM'),
            ('Tambaram Airforce signal', '6:45 AM'),
            ('Krishna nagar', '6:52 AM'),
            ('Bharathi nagar', '6:54 AM'),
            ('old Perungalathur', '6:57 AM'),
            ('mathanapuram', '7:00 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R19', 'Poombukar', [
            ('Poombukar', '6:10 AM'),
            ('Ganga Cinima', '6:25 AM'),
            ('Donbosco', '6:28 AM'),
            ('Poombukar', '6:30 AM'),
            ('Korattur Bus Stop', '6:55 AM'),
            ('Padi Britania', '6:58 AM'),
            ('TVS Show Room', '7:10 AM'),
            ('Ambattur', '7:12 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R19A', 'Vinayagapuram', [
            ('Vinayagapuram Bus Stand', '6:45 AM'),
            ('Retteri RTO Office', '6:55 AM'),
            ('Retteri', '6:58 AM'),
            ('Senthil Nagar', '7:00 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R20', 'Veppampattu', [
            ('Veppampattu Railway Station', '6:35 AM'),
            ('Puriyamaram Stop', '6:37 AM'),
            ('Madha Kovil', '6:38 AM'),
            ('Angel School', '6:42 AM'),
            ('Thiruninravur Railway Station', '6:44 AM'),
            ('Thiruninravur PS Hotel', '6:45 AM'),
            ('Nadukuthagai', '6:47 AM'),
            ('Jaya College', '6:48 AM'),
            ('Velammal School', '7:15 AM'),
            ('Vethalai thottam', '7:20 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R20A', 'Pattabiram', [
            ('Pattabiram Gandhi Nagar', '6:45 AM'),
            ('Pattabiram Vasantha Mandapam', '6:46 AM'),
            ('Sekkadu Bus Stand', '6:49 AM'),
            ('Avadi Ponnu Store', '6:54 AM'),
            ('Avadi J.P.Garden', '6:56 AM'),
            ('Govarthanagiri Bus Stand', '6:59 AM'),
            ('Chennirkuppam', '7:09 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R21', 'Ayappakkam', [
            ('Ayappakkam Parking', '6:20 AM'),
            ('Ayappakkam SBI ATM', '6:25 AM'),
            ('Ayappakkam Petrol Bunk', '6:28 AM'),
            ('ICF Church', '6:30 AM'),
            ('Ganesh Bhavan', '6:34 AM'),
            ('Selvi Mahal', '6:37 AM'),
            ('Bharat bunk', '6:40 AM'),
            ('ICMR', '6:43 AM'),
            ('Water Tank', '6:45 AM'),
            ('Canara Bank', '6:50 AM'),
            ('Singapore Shopping', '6:53 AM'),
            ('24 Hospital', '6:57 AM'),
            ('Vaishnavi Nagar', '7:03 AM'),
            ('Murugappan Polytechnic', '7:06 AM'),
            ('Avadi Bus Stand', '7:10 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R22', 'Thiruthani', [
            ('Thiruthani Bypass', '5:55 AM'),
            ('Thiruvallur Bypass X Road', '6:00 AM'),
            ('Nagalamman Nagar', '6:08 AM'),
            ('Krishna Poly', '6:10 AM'),
            ('Jothi Nagar', '6:12 AM'),
            ('Indira Gandhi Nagar', '6:15 AM'),
            ('Swalpetaih', '6:16 AM'),
            ('Government Hospital', '6:17 AM'),
            ('Old Bus stand', '6:18 AM'),
            ('Railway Station', '6:20 AM'),
            ('New Bus Stand', '6:22 AM'),
            ('Navy Gate', '6:30 AM'),
            ('Venkatesapuram', '6:31 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R22A', 'Sholinghur', [
            ('Sholinghur', '5:35 AM'),
            ('Banavaram koot', '5:40 AM'),
            ('Gudalore', '5:55 AM'),
            ('Salai', '6:00 AM'),
            ('Chitteri', '6:05 AM'),
            ('SR Gate', '6:25 AM'),
            ('Thakkolam Koot Road', '6:35 AM'),
            ('Thakkolam', '6:40 AM'),
            ('Narasimapuram', '6:55 AM'),
            ('Perambakkam', '7:00 AM'),
            ('Koovam Bus Stop', '7:02 AM'),
            ('Valarpuram', '7:30 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R23', 'K4 Police Station', [
            ('Nathamuni Theatre ` 6.35 am K4 Police Station', '6:40 AM'),
            ('Labour officers Quarters', '6:52 AM'),
            ('Vijaya Maruthi (Nuts & Spices)', '6:44 AM'),
            ('Udayam colony', '6:46 AM'),
            ('Kambar Colony', '6:48 AM'),
            ('Anna Nagar West Depot', '6:50 AM'),
            ('Thirumangalam Bridge', '6:52 AM'),
            ('Thirumangalam Waves', '6:56 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R24', 'Arcot', [
            ('Arcot Bus Stand', '5:20 AM'),
            ('Muthukadai', '5:25 AM'),
            ('VC Motor', '5:28 AM'),
            ('Walajapettai', '5:30 AM'),
            ('Walajapettai Housing Board', '5:32 AM'),
            ('Arignar Anna Gov College', '5:33 AM'),
            ('Walajapettai Toll gate', '5:40 AM'),
            ('Kaveripakkam', '5:50 AM'),
            ('Ocheri', '5:55 AM'),
            ('Perumpullipakkam', '6:05 AM'),
            ('Dhamal Erikarai', '6:10 AM'),
            ('Dhamal Kovil', '6:12 AM'),
            ('Baluchetty', '6:15 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R25', 'Kallikuppam', [
            ('Jio Bunk', '6:40 AM'),
            ('Pudur Bus Stop', '6:45 AM'),
            ('PTR Mahal', '6:48 AM'),
            ('Ponnu Super Market', '6:50 AM'),
            ('Saraswathi Nagar', '6:57 AM'),
            ('Manikandapuram', '7:00 AM'),
            ('Thirumullaivoyal', '7:03 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R25A', 'Kavangarai', [
            ('Kavangarai', '6:15 AM'),
            ('Puzhal Jail', '6:18 AM'),
            ('Puzhal Camp', '6:20 AM'),
            ('Lake', '6:22 AM'),
            ('Velammal college', '6:25 AM'),
            ('Surapattu', '6:30 AM'),
            ('Surapattu Dhaba', '6:30 AM'),
            ('Kallikuppam Tea Kadai', '6:35 AM'),
            ('Kallikuppam Arch', '6:38 AM'),
            ('Kallikuppam Wireless', '6:40 AM'),
            ('Mallika Mahal', '6:42 AM'),
            ('Oragadam HP Pump', '6:47 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R26', 'Andarkuppam', [
            ('Andarkuppam', '6:35 AM'),
            ('Kundrathur', '6:40 AM'),
            ('Kundrathur Thandalam', '6:43 AM'),
            ('Kovur', '6:45 AM'),
            ('Gerugambakkam', '6:50 AM'),
            ('Bai Kadai', '6:53 AM'),
            ('Mathanandapuram', '6:55 AM'),
            ('Venkateswara Nagar', '6:58 AM'),
            ('Porur', '7:05 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R26A', 'Poonamallee', [
            ('Poonamallee Bypass', '7:30 AM'),
            ('Nazarathpettai', '7:31 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R27', 'Avadi Checkpost', [
            ('Avadi Checkpost', '7:05 AM'),
            ('Rama Rathna Theatre', '7:06 AM'),
            ('Ponnu Super Market', '7:08 AM'),
            ('Chinnamman Kovil', '7:09 AM'),
            ('JP Esate', '7:10 AM'),
            ('Vasantham Nagar', '7:12 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R27A', 'Kollumedu', [
            ('Kollumedu', '6:20 AM'),
            ('Vel Tech College', '6:30 AM'),
            ('Kovilpathagai', '6:40 AM'),
            ('Ajeya Stadium', '6:45 AM'),
            ('CRPF', '6:50 AM'),
            ('Mittanemili', '6:55 AM'),
            ('Palavedu Police Booth', '7:00 AM'),
            ('Nemilichery Tollgate', '7:05 AM'),
            ('Nazarathpettai', '7:25 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R28', 'Agaram', [
            ('Agaram', '6:20 AM'),
            ('Periyar Nagar', '6:22 AM'),
            ('Thiruvalluvar Thirumanamandapam', '6:24 AM'),
            ('Permal Koil', '6:26 AM'),
            ('Kamban Nagar', '6:28 AM'),
            ('E.B', '6:30 AM'),
            ('Shanmugam Mahal', '6:32 AM'),
            ('Senthil Nagar', '6:35 AM'),
            ('Thathankuppam', '6:38 AM'),
            ('Kalyan Jewalrs', '6:45 AM'),
            ('Collector Nagar', '6:47 AM'),
            ('Cheriyan Hospital', '6:48 AM'),
            ('Golden Flats', '6:50 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R29', 'Medavakkam Koot Road', [
            ('Vellakal', '6:20 AM'),
            ('Rajakilpakkam Bus Stand', '6:30 AM'),
            ('Kozhi Pannai', '6:33 AM'),
            ('Bharath College', '6:40 AM'),
            ('Camp Road Singal', '6:45 AM'),
            ('Kishkintha Road', '6:55 AM'),
            ('Erumaiyur', '7:00 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R29A', 'Pammal', [
            ('Pammal', '6:35 AM'),
            ('Arunmathi theatre', '6:37 AM'),
            ('Anagaputhur', '6:39 AM'),
            ('Manikandan Nagar', '6:41 AM'),
            ('Karima Nagar', '6:45 AM'),
            ('Kundrathur (theradi)', '6:48 AM'),
            ('RIT Campus', '7:40 AM'),
        ])

        add_route(cursor, 'R29B', 'Sivanthangal', [
            ('Sivanthangal', '7:05 AM'),
            ('Muthukumaran College', '7:10 AM'),
            ('Pattu Koot Road', '7:13 AM'),
            ('Mangadu', '7:15 AM'),
            ('Kankaiyamman Kovil', '7:20 AM'),
            ('MGR Nagar', '7:23 AM'),
            ('Kumananchavadi', '7:25 AM'),
            ('Aravind Hospital', '7:30 AM'),
            ('RIT Campus', '7:40 AM'),
        ])
        connection.commit()
    finally:
        connection.close()

    print("52 RIT bus routes and morning stops loaded successfully!")

if __name__ == "__main__":
    seed_data()
