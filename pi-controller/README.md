# Pi Controller for Bambu P1S

Raspberry Pi-based controller that polls for approved 3D print jobs and sends them to a Bambu P1S printer.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   fly-app   │◄────│ pi-controller│────►│  Bambu P1S  │
│   (API)     │     │   (Pi 5)    │     │  (Printer)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │   API Key Auth    │   MQTT (8883)     │
       │   HTTP REST       │   FTP (990)       │
```

## Features

- Polls the fly-app API for approved print jobs
- Downloads .3mf files from Tigris storage
- Uploads files to the Bambu P1S via FTPS
- Starts prints via MQTT commands
- Monitors print progress and updates the API
- Handles print completion and failures

## Requirements

- Python 3.10+
- Network access to:
  - fly-app API server
  - Bambu P1S printer on local network

## Installation

1. Clone the repository to your Raspberry Pi:

```bash
cd /home/pi
git clone <repository-url>
cd public-3d-printer/pi-controller
```

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
nano .env
```

## Configuration

Create a `.env` file with the following variables:

```env
# API Configuration
API_URL=https://print-queue-api.fly.dev
API_KEY=your-api-key-here

# Bambu P1S Configuration
BAMBU_IP=192.168.x.x
BAMBU_SERIAL=01P00A123456789
BAMBU_ACCESS_CODE=12345678

# Optional: Polling Configuration
POLL_INTERVAL_SECONDS=30
PROGRESS_UPDATE_INTERVAL_SECONDS=10

# Optional: File Storage
DOWNLOAD_DIR=/tmp/print-jobs
```

### Getting Bambu P1S Credentials

1. **IP Address**: Find in your router's DHCP client list or on the printer's network settings screen
2. **Serial Number**: Found in the printer's settings or on the device label
3. **Access Code**: On the printer, go to Settings → Network → LAN Only Mode → Access Code

## Usage

### Run manually

```bash
source venv/bin/activate
python main.py
```

### Run as a systemd service

1. Create a service file:

```bash
sudo nano /etc/systemd/system/pi-controller.service
```

2. Add the following content:

```ini
[Unit]
Description=Pi Controller for Bambu P1S
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/public-3d-printer/pi-controller
Environment=PATH=/home/pi/public-3d-printer/pi-controller/venv/bin
ExecStart=/home/pi/public-3d-printer/pi-controller/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-controller
sudo systemctl start pi-controller
```

4. Check status:

```bash
sudo systemctl status pi-controller
sudo journalctl -u pi-controller -f
```

## Job Workflow

1. User submits a job via the web frontend → status: `submitted`
2. Admin approves the job → status: `approved`
3. Pi controller picks up the job → status: `queued`
4. Pi controller starts printing → status: `printing`
5. Print completes → status: `done` (or `failed` if error)

## Troubleshooting

### Cannot connect to printer

- Verify the printer IP address is correct
- Ensure the printer is in LAN Mode (not Cloud Mode)
- Check that the access code is correct
- Verify the Pi can reach the printer: `ping <BAMBU_IP>`

### MQTT connection fails

- The printer must be powered on and connected to the network
- Check firewall rules aren't blocking port 8883

### FTP upload fails

- Check firewall rules aren't blocking port 990
- Verify there's enough storage space on the printer

### API errors

- Verify the API_URL is correct
- Check the API_KEY matches the one configured in fly-app
- Test connectivity: `curl -H "X-API-Key: $API_KEY" $API_URL/printer/jobs/next`

## Development

### Running tests

```bash
pytest
```

### Logging

Set the log level via environment variable:

```bash
export LOG_LEVEL=DEBUG
python main.py
```
