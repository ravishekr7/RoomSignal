# RoomSignal

A WiFi network analyzer for macOS that helps you find the best network for your current location in your house.

## Features

- **Current Connection Analysis**: View detailed info about your connected network including signal strength, noise, SNR, latency, and TX rate
- **Band Detection**: See whether networks are 2.4GHz or 5GHz
- **Network Scoring**: Each network gets a grade (A-F) based on signal quality, band, bandwidth, and latency
- **Smart Recommendations**: Get suggestions on whether to switch networks based on your location
- **Clean Dashboard**: Dark-themed web UI that's easy to read

## Requirements

- macOS (uses `system_profiler` for WiFi data)
- Python 3.9+
- Web browser

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ravishekr7/RoomSignal.git
   cd RoomSignal
   ```

2. **Install dependencies**
   ```bash
   cd backend
   pip3 install -r requirements.txt
   ```

## Usage

1. **Start the server**
   ```bash
   cd backend
   python3 -m uvicorn main:app --port 8000
   ```

2. **Open in browser**
   ```
   http://localhost:8000
   ```

3. **Click "Scan Networks"** to analyze WiFi at your current location

4. **Move to different rooms** and scan again to compare signal quality

## How It Works

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Web Browser   │ ←──→ │  FastAPI Server │ ←──→ │ system_profiler │
│   (Frontend)    │      │   (Backend)     │      │   (macOS WiFi)  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

The backend uses macOS's `system_profiler SPAirPortDataType` to gather WiFi information including:
- Connected network details (RSSI, noise, channel, TX rate)
- Available nearby networks
- Band and channel width information

## Scoring System

Networks are scored 0-100 based on:

| Factor | Max Points | Description |
|--------|------------|-------------|
| Signal Strength | 40 | Based on RSSI (-30 dBm = best, -90 dBm = worst) |
| Band & Bandwidth | 25 | 5GHz with 80/160MHz preferred for speed |
| PHY Mode | 15 | WiFi 6 (ax) > WiFi 5 (ac) > WiFi 4 (n) |
| Latency | 20 | Only for current connection (< 20ms = best) |

### Grades
- **A**: 85-100 - Excellent
- **B**: 70-84 - Good
- **C**: 55-69 - Fair
- **D**: 40-54 - Poor
- **F**: Below 40 - Very Poor

## Tips

- **5GHz** networks are faster but have shorter range
- **2.4GHz** networks are slower but penetrate walls better
- If signal drops below -70 dBm, consider switching networks
- Use the scoring to find the best network for each room

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web UI |
| `GET /api/scan` | Scan networks and get analysis |
| `GET /api/latency?host=8.8.8.8&count=5` | Run latency test |
| `GET /api/health` | Health check |

## License

MIT
