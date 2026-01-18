import json
import ssl
import time
import socket
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from ftplib import FTP, error_perm

import paho.mqtt.client as mqtt

from config import get_settings

logger = logging.getLogger(__name__)


class SSLSocketWrapper:
    """Wrapper that prevents SSL unwrap() from hanging by skipping it."""

    def __init__(self, ssl_sock):
        self._sock = ssl_sock

    def __getattr__(self, name):
        return getattr(self._sock, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def unwrap(self):
        # Skip SSL shutdown - Bambu printer doesn't respond properly
        # Just close the underlying socket
        try:
            self._sock.close()
        except Exception:
            pass
        return self._sock

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass


class ImplicitFTPS(FTP):
    """FTP over TLS with implicit SSL (connects on port 990 with SSL from start)."""

    def __init__(self, host=None, port=990, timeout=120):
        self._timeout = timeout
        self.af = socket.AF_INET
        super().__init__()
        if host:
            self.connect(host, port)

    def connect(self, host, port=990, timeout=None):
        if timeout is None:
            timeout = self._timeout

        self.host = host
        self.port = port
        self.timeout = timeout

        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Create socket and wrap with SSL immediately (implicit TLS)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        self.sock = context.wrap_socket(sock, server_hostname=host)
        self.file = self.sock.makefile('r', encoding='utf-8')

        # Read the welcome message
        self.welcome = self.getresp()
        return self.welcome

    def ntransfercmd(self, cmd, rest=None):
        """Override to use SSL for data connection."""
        size = None
        if self.passiveserver:
            host, port = self.makepasv()

            # Create SSL context for data connection
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            conn.connect((host, port))
            ssl_conn = context.wrap_socket(conn, server_hostname=host)

            # Wrap to prevent unwrap() from hanging
            conn = SSLSocketWrapper(ssl_conn)

            if rest is not None:
                self.sendcmd(f"REST {rest}")
            resp = self.sendcmd(cmd)
            if resp[0] == '2':
                resp = self.getresp()
            if resp[0] != '1':
                raise error_perm(resp)
        else:
            raise NotImplementedError("Active mode not supported")

        if resp[:3] == '150':
            size_match = resp[4:].split('(')
            if len(size_match) > 1:
                try:
                    size = int(size_match[1].split()[0])
                except (ValueError, IndexError):
                    pass

        return conn, size


@dataclass
class PrinterStatus:
    """Current status of the printer."""
    state: str  # "IDLE", "RUNNING", "PAUSE", "FINISH", "FAILED"
    progress: int  # 0-100
    layer_num: int
    total_layers: int
    remaining_time: int  # minutes
    error_code: Optional[str] = None


class BambuPrinter:
    """Communicates with Bambu P1S printer via MQTT and FTP."""

    MQTT_PORT = 8883
    FTPS_PORT = 990

    def __init__(self):
        settings = get_settings()
        self.ip = settings.bambu_ip
        self.serial = settings.bambu_serial
        self.access_code = settings.bambu_access_code

        self._mqtt_client: Optional[mqtt.Client] = None
        self._status: Optional[PrinterStatus] = None
        self._status_lock = threading.Lock()
        self._connected = False
        self._on_status_update: Optional[Callable[[PrinterStatus], None]] = None

    @property
    def status(self) -> Optional[PrinterStatus]:
        with self._status_lock:
            return self._status

    def set_status_callback(self, callback: Callable[[PrinterStatus], None]):
        """Set callback for status updates."""
        self._on_status_update = callback

    def connect(self):
        """Connect to the printer's MQTT broker."""
        if self._mqtt_client is not None:
            return

        self._mqtt_client = mqtt.Client(
            client_id=f"pi-controller-{self.serial}",
            protocol=mqtt.MQTTv311,
        )
        self._mqtt_client.username_pw_set("bblp", self.access_code)

        # Configure TLS
        self._mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
        self._mqtt_client.tls_insecure_set(True)

        # Set callbacks
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect

        logger.info(f"Connecting to Bambu printer at {self.ip}:{self.MQTT_PORT}")
        self._mqtt_client.connect(self.ip, self.MQTT_PORT, keepalive=60)
        self._mqtt_client.loop_start()

        # Wait for connection
        timeout = 10
        start = time.time()
        while not self._connected and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not self._connected:
            raise ConnectionError("Failed to connect to printer MQTT broker")

        logger.info("Connected to Bambu printer")

    def disconnect(self):
        """Disconnect from the printer."""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_client = None
            self._connected = False
            logger.info("Disconnected from Bambu printer")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            # Subscribe to status reports
            topic = f"device/{self.serial}/report"
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")

            # Request initial status
            self._request_push_all()
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            self._parse_status(payload)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse MQTT message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _parse_status(self, payload: dict):
        """Parse printer status from MQTT message."""
        if "print" not in payload:
            return

        print_info = payload["print"]

        # Map Bambu states to our states
        gcode_state = print_info.get("gcode_state", "IDLE")

        status = PrinterStatus(
            state=gcode_state,
            progress=print_info.get("mc_percent", 0),
            layer_num=print_info.get("layer_num", 0),
            total_layers=print_info.get("total_layer_num", 0),
            remaining_time=print_info.get("mc_remaining_time", 0),
            error_code=print_info.get("print_error") if print_info.get("print_error") else None,
        )

        with self._status_lock:
            self._status = status

        if self._on_status_update:
            self._on_status_update(status)

        logger.debug(f"Printer status: {status.state}, progress: {status.progress}%")

    def _request_push_all(self):
        """Request the printer to send all status data."""
        if not self._mqtt_client:
            return

        topic = f"device/{self.serial}/request"
        payload = json.dumps({
            "pushing": {
                "sequence_id": "0",
                "command": "pushall"
            }
        })
        self._mqtt_client.publish(topic, payload)

    def upload_file(self, local_path: str, remote_filename: str) -> bool:
        """Upload a file to the printer via implicit FTPS."""
        try:
            logger.info(f"Uploading {local_path} to printer as {remote_filename}")

            # Connect via implicit FTPS (SSL from the start on port 990)
            ftps = ImplicitFTPS(self.ip, self.FTPS_PORT)
            ftps.login("bblp", self.access_code)

            # Upload to the cache directory
            with open(local_path, "rb") as f:
                ftps.storbinary(f"STOR /cache/{remote_filename}", f)

            ftps.quit()
            logger.info(f"Successfully uploaded {remote_filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False

    def start_print(self, filename: str) -> bool:
        """Start printing a file that's already on the printer."""
        if not self._mqtt_client or not self._connected:
            logger.error("Not connected to printer")
            return False

        try:
            # Clear any existing print errors first
            self._clear_print_error()
            time.sleep(1)

            topic = f"device/{self.serial}/request"
            seq_id = str(int(time.time()))
            payload = json.dumps({
                "print": {
                    "sequence_id": seq_id,
                    "command": "project_file",
                    "param": "Metadata/plate_1.gcode",
                    "subtask_name": filename,
                    "url": f"file:///sdcard/cache/{filename}",
                    "timelapse": False,
                    "bed_leveling": True,
                    "flow_cali": False,
                    "vibration_cali": False,
                    "layer_inspect": False,
                    "use_ams": False,
                }
            })
            self._mqtt_client.publish(topic, payload)
            logger.info(f"Started print job: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to start print: {e}")
            return False

    def _clear_print_error(self):
        """Clear any existing print errors."""
        if not self._mqtt_client:
            return
        topic = f"device/{self.serial}/request"
        payload = json.dumps({
            "print": {
                "sequence_id": "0",
                "command": "clean_print_error"
            }
        })
        self._mqtt_client.publish(topic, payload)

    def stop_print(self) -> bool:
        """Stop the current print."""
        if not self._mqtt_client or not self._connected:
            return False

        try:
            topic = f"device/{self.serial}/request"
            payload = json.dumps({
                "print": {
                    "sequence_id": "0",
                    "command": "stop"
                }
            })
            self._mqtt_client.publish(topic, payload)
            logger.info("Stopped print job")
            return True

        except Exception as e:
            logger.error(f"Failed to stop print: {e}")
            return False

    def is_idle(self) -> bool:
        """Check if the printer is idle and ready for a new job."""
        status = self.status
        if status is None:
            return False
        return status.state in ["IDLE", "FINISH", "FAILED"]

    def is_printing(self) -> bool:
        """Check if the printer is currently printing."""
        status = self.status
        if status is None:
            return False
        return status.state in ["RUNNING", "PAUSE"]

    def is_finished(self) -> bool:
        """Check if the print is finished."""
        status = self.status
        if status is None:
            return False
        return status.state == "FINISH"

    def has_error(self) -> bool:
        """Check if the printer has an error."""
        status = self.status
        if status is None:
            return False
        return status.state == "FAILED" or status.error_code is not None
