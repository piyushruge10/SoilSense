# SoilSense

A local Django dashboard for Arduino UNO soil temperature, humidity, and moisture readings.

## Setup

Use the project's Python virtual environment in PyCharm, then install dependencies and initialize the SQLite database:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. Sign in or create an account to use the dashboard, plant library, live sharing, and sensor configuration. All application pages and sensor APIs require a signed-in account. Plant guides can be added at `/admin/` after creating a superuser with `python manage.py createsuperuser`.

Staff accounts can open the **Admin center** in the sidebar (or visit `/control/`) to view application totals and manage users, Arduino configurations, sensor readings, plant guides, and published sharing profiles. Create a staff administrator with `python manage.py createsuperuser`; the full Django admin is available at `/admin/`.

Each account has its own serial configuration and sensor history. To publish, sign in on **Live sharing** and choose **Publish my live readings**. Published users appear as separate live-reading cards on that page, so other signed-in users can browse their conditions without needing a link. Every account also has a unique share URL that its owner can copy; only the owner can publish or stop sharing that account's readings. All pages, including individual share URLs, require sign-in. Use **Log out** at the bottom of **Settings** to sign out.

The **Settings** page includes example Arduino UNO wiring for a capacitive soil-moisture sensor, a DHT22 humidity sensor, and a DS18B20 soil-temperature probe. Confirm module voltage and pin labels before wiring; calibrate the moisture sensor in your own soil. The plant library includes 100 common plant guides and 100 Indian crop guides, including cereals, pulses, oilseeds, spices, vegetables, fruits, cash crops, and fodder crops. Care ranges are general references; follow local agricultural guidance, especially for irrigation practices such as paddy rice.

If serial access to a COM port is denied, close Arduino IDE Serial Monitor/Plotter and any other program using the port. Check the assigned COM number in Windows Device Manager, choose the detected port in **Settings**, then select **Retry connection**.

## Arduino serial protocol

Set the COM port in **Settings** (for example `COM3`) and keep the Arduino sketch's serial baud rate at `9600` unless you change it in the app as well. Send one sensor reading per line in either CSV format:

```text
23.4,61.0,42.5
```

or JSON format:

```json
{"temperature":23.4,"humidity":61.0,"moisture":42.5}
```

Temperature is in Celsius; humidity and moisture are percentages from 0 to 100. On saving settings, the app queues `SET,<moisture_threshold>,<sample_interval>\n` for the board. The serial reader reconnects automatically and stores valid readings in SQLite.
