import json
import logging
import math
import queue
import threading
import time

from django.db import close_old_connections

logger = logging.getLogger(__name__)


class SerialMonitor:
    """Maintain a single background reader for the configured Arduino port."""

    def __init__(self):
        self._lock = threading.Lock()
        self._port = ""
        self._baud_rate = 9600
        self._owner_id = None
        self._generation = 0
        self._connected = False
        self._error = ""
        self._commands = queue.Queue()
        self._thread = None

    def configure(self, port, baud_rate, owner_id):
        with self._lock:
            if (port, baud_rate, owner_id) != (
                self._port,
                self._baud_rate,
                self._owner_id,
            ):
                self._port, self._baud_rate, self._owner_id = (
                    port,
                    baud_rate,
                    owner_id,
                )
                self._generation += 1
                self._error = ""
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="soil-serial-reader", daemon=True
                )
                self._thread.start()

    def reconnect(self):
        with self._lock:
            self._generation += 1
            self._error = ""
            self._connected = False
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name="soil-serial-reader", daemon=True
                )
                self._thread.start()

    def status(self):
        with self._lock:
            return {
                "connected": self._connected,
                "port": self._port,
                "error": self._error,
            }

    def send_configuration(self, moisture_threshold, sample_interval):
        if not self.status()["port"]:
            raise RuntimeError("Configure a serial port before sending settings.")
        self._commands.put(
            f"SET,{moisture_threshold},{sample_interval}\n".encode("ascii")
        )

    def _run(self):
        import serial

        active_generation = -1
        connection = None
        retry_at = 0
        while True:
            with self._lock:
                port, baud_rate, owner_id, generation = (
                    self._port,
                    self._baud_rate,
                    self._owner_id,
                    self._generation,
                )

            if generation != active_generation:
                if connection is not None:
                    connection.close()
                    connection = None
                active_generation = generation
                with self._lock:
                    self._connected = False
                    self._error = ""
                retry_at = 0

            if not port:
                time.sleep(0.25)
                continue

            if connection is None and time.monotonic() >= retry_at:
                try:
                    connection = serial.Serial(port, baud_rate, timeout=1)
                    with self._lock:
                        self._connected = True
                        self._error = ""
                except (serial.SerialException, OSError) as exc:
                    error = self._friendly_error(port, exc)
                    with self._lock:
                        self._connected = False
                        changed = self._error != error
                        self._error = error
                    if changed:
                        logger.warning("Unable to open Arduino serial port %s: %s", port, error)
                    retry_at = time.monotonic() + 5
                    time.sleep(0.25)
                    continue

            if connection is None:
                time.sleep(0.25)
                continue

            try:
                while True:
                    command = self._commands.get_nowait()
                    connection.write(command)
                # The loop exits through queue.Empty when no command remains.
            except queue.Empty:
                pass
            except (serial.SerialException, OSError) as exc:
                self._disconnect(connection, port, exc)
                connection = None
                retry_at = time.monotonic() + 5
                continue

            try:
                line = connection.readline().decode("utf-8", errors="replace").strip()
                if line:
                    reading = self._parse_reading(line)
                    if reading is not None:
                        self._save_reading(reading, owner_id)
            except (serial.SerialException, OSError) as exc:
                self._disconnect(connection, port, exc)
                connection = None
                retry_at = time.monotonic() + 5

    @staticmethod
    def _friendly_error(port, error):
        error_text = str(error).lower()
        if (
            isinstance(error, PermissionError)
            or getattr(error, "errno", None) == 13
            or "permissionerror" in error_text
            or "access is denied" in error_text
            or "winerror 5" in error_text
        ):
            return (
                f"Access to {port} was denied. Close Arduino IDE Serial Monitor/Plotter "
                "and any other app using this port, check that the selected COM port "
                "is correct in Windows Device Manager, then choose Retry connection."
            )
        if (
            isinstance(error, FileNotFoundError)
            or getattr(error, "errno", None) == 2
            or "filenotfounderror" in error_text
            or "file not found" in error_text
            or "winerror 2" in error_text
        ):
            return (
                f"{port} was not found. Reconnect the Arduino, check its COM number in "
                "Windows Device Manager, select the detected port, then choose Retry "
                "connection."
            )
        return f"Could not connect to {port}: {error}"

    @staticmethod
    def _parse_reading(line):
        try:
            if line.startswith("{"):
                values = json.loads(line)
                temperature = float(values["temperature"])
                humidity = float(values["humidity"])
                moisture = float(values["moisture"])
            else:
                temperature, humidity, moisture = map(float, line.split(","))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            logger.warning("Ignoring malformed Arduino reading: %r", line)
            return None

        if (
            not all(math.isfinite(value) for value in (temperature, humidity, moisture))
            or not 0 <= humidity <= 100
            or not 0 <= moisture <= 100
        ):
            logger.warning("Ignoring out-of-range Arduino reading: %r", line)
            return None
        return temperature, humidity, moisture

    @staticmethod
    def _save_reading(reading, owner_id):
        from .models import SensorData

        close_old_connections()
        try:
            SensorData.objects.create(
                user_id=owner_id,
                temperature=reading[0],
                humidity=reading[1],
                moisture=reading[2],
            )
        finally:
            close_old_connections()

    def _disconnect(self, connection, port, error):
        connection.close()
        friendly_error = self._friendly_error(port, error)
        with self._lock:
            self._connected = False
            changed = self._error != friendly_error
            self._error = friendly_error
        if changed:
            logger.warning("Arduino serial connection was lost: %s", friendly_error)


_monitors_lock = threading.Lock()
_user_monitors = {}


def serial_monitor_for(user_id):
    with _monitors_lock:
        if user_id not in _user_monitors:
            _user_monitors[user_id] = SerialMonitor()
        return _user_monitors[user_id]


def available_serial_ports():
    from serial.tools import list_ports

    return [
        {"device": port.device, "description": port.description}
        for port in list_ports.comports()
    ]
