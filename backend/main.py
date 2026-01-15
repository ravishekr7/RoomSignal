"""
RoomSignal - WiFi Network Analyzer Backend
FastAPI server that provides WiFi scanning and analysis endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from wifi_scanner import (
    scan_networks,
    measure_latency,
    calculate_score,
    NetworkInfo
)

app = FastAPI(
    title="RoomSignal",
    description="WiFi Network Analyzer for macOS",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from frontend directory
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def root():
    """Serve the frontend."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "RoomSignal API", "docs": "/docs"}


@app.get("/api/scan")
async def scan_wifi():
    """
    Scan for WiFi networks and return current connection + available networks.
    Includes signal strength, band, channel, and quality scores.
    """
    current, networks = scan_networks()

    # Measure latency for current connection
    latency = None
    if current:
        latency = measure_latency(count=3)  # Quick 3-ping test

    # Build response for current connection
    current_data = None
    if current:
        current_net = NetworkInfo(
            ssid=current.ssid,
            channel=current.channel,
            band=current.band,
            band_width=current.band_width,
            phy_mode=current.phy_mode,
            security=current.security,
            rssi=current.rssi,
            noise=current.noise
        )
        score = calculate_score(current_net, is_current=True, latency=latency)

        current_data = {
            "ssid": current.ssid,
            "channel": current.channel,
            "band": current.band,
            "band_width": current.band_width,
            "phy_mode": current.phy_mode,
            "security": current.security,
            "rssi": current.rssi,
            "noise": current.noise,
            "snr": current.signal_to_noise(),
            "tx_rate": current.tx_rate,
            "signal_quality": current.signal_quality(),
            "signal_percentage": current.signal_percentage(),
            "latency": latency,
            "score": score
        }

    # Build response for other networks
    networks_data = []
    for net in networks:
        score = calculate_score(net, is_current=False)
        networks_data.append({
            "ssid": net.ssid,
            "channel": net.channel,
            "band": net.band,
            "band_width": net.band_width,
            "phy_mode": net.phy_mode,
            "security": net.security,
            "rssi": net.rssi,
            "noise": net.noise,
            "signal_quality": net.signal_quality(),
            "signal_percentage": net.signal_percentage(),
            "score": score
        })

    # Sort networks by score (highest first)
    networks_data.sort(key=lambda x: x["score"]["total"], reverse=True)

    # Find best recommendation (excluding current if it's in the list)
    best_alternative = None
    if networks_data:
        for net in networks_data:
            if not current_data or net["ssid"] != current_data["ssid"]:
                best_alternative = net
                break

    return {
        "current": current_data,
        "networks": networks_data,
        "best_alternative": best_alternative,
        "summary": generate_summary(current_data, networks_data, best_alternative)
    }


@app.get("/api/latency")
async def check_latency(host: str = "8.8.8.8", count: int = 5):
    """Run a latency test to the specified host."""
    result = measure_latency(host=host, count=count)
    return {"latency": result}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "RoomSignal"}


def generate_summary(current: dict, networks: list, best_alt: dict) -> dict:
    """Generate a summary recommendation."""
    if not current:
        return {
            "status": "disconnected",
            "message": "Not connected to any WiFi network",
            "recommendation": "Connect to a network to see analysis"
        }

    score = current["score"]["total"]
    grade = current["score"]["grade"]

    if score >= 80:
        status = "excellent"
        message = f"Your current connection ({current['ssid']}) is excellent for this location."
        recommendation = "No change needed - you have optimal WiFi coverage here."
    elif score >= 60:
        status = "good"
        message = f"Your current connection ({current['ssid']}) is good for this location."
        if best_alt and best_alt["score"]["total"] > score + 10:
            recommendation = f"Consider switching to {best_alt['ssid']} for potentially better performance."
        else:
            recommendation = "Your current network is a good choice for this location."
    elif score >= 40:
        status = "fair"
        message = f"Your current connection ({current['ssid']}) is fair - you may experience some slowdowns."
        if best_alt:
            recommendation = f"Try switching to {best_alt['ssid']} ({best_alt['band']}) for better performance."
        else:
            recommendation = "Try moving closer to your router or reducing interference."
    else:
        status = "poor"
        message = f"Your current connection ({current['ssid']}) has poor signal at this location."
        if best_alt:
            recommendation = f"Strongly recommend switching to {best_alt['ssid']} ({best_alt['band']})."
        else:
            recommendation = "Move to a different location or check your router placement."

    return {
        "status": status,
        "grade": grade,
        "message": message,
        "recommendation": recommendation,
        "current_band": current["band"],
        "networks_found": len(networks)
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  RoomSignal - WiFi Network Analyzer")
    print("=" * 60)
    print("\n  Starting server at http://localhost:8000")
    print("  API docs available at http://localhost:8000/docs")
    print("\n  Press Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
