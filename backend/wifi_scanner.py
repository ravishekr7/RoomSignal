"""
WiFi Scanner module for macOS
Uses system_profiler to scan networks and get connection details.
"""

import subprocess
import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class NetworkInfo:
    ssid: str
    channel: int
    band: str  # "2.4GHz" or "5GHz"
    band_width: str  # "20MHz", "40MHz", "80MHz", "160MHz"
    phy_mode: str  # "802.11ac", "802.11ax", etc.
    security: str
    rssi: Optional[int] = None  # Signal strength in dBm (only for some networks)
    noise: Optional[int] = None

    def signal_quality(self) -> str:
        """Convert RSSI to human-readable quality."""
        if self.rssi is None:
            return "Unknown"
        if self.rssi >= -50:
            return "Excellent"
        elif self.rssi >= -60:
            return "Good"
        elif self.rssi >= -70:
            return "Fair"
        else:
            return "Poor"

    def signal_percentage(self) -> int:
        """Convert RSSI to percentage (approximate)."""
        if self.rssi is None:
            return 0
        # RSSI typically ranges from -90 (worst) to -30 (best)
        if self.rssi >= -30:
            return 100
        elif self.rssi <= -90:
            return 0
        else:
            return min(100, max(0, int((self.rssi + 90) * 100 / 60)))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            **asdict(self),
            "signal_quality": self.signal_quality(),
            "signal_percentage": self.signal_percentage()
        }


@dataclass
class CurrentConnection:
    ssid: str
    channel: int
    band: str
    band_width: str
    phy_mode: str
    security: str
    rssi: int
    noise: int
    tx_rate: int  # Mbps
    mcs_index: Optional[int] = None

    def signal_quality(self) -> str:
        """Convert RSSI to human-readable quality."""
        if self.rssi >= -50:
            return "Excellent"
        elif self.rssi >= -60:
            return "Good"
        elif self.rssi >= -70:
            return "Fair"
        else:
            return "Poor"

    def signal_percentage(self) -> int:
        """Convert RSSI to percentage."""
        if self.rssi >= -30:
            return 100
        elif self.rssi <= -90:
            return 0
        else:
            return min(100, max(0, int((self.rssi + 90) * 100 / 60)))

    def signal_to_noise(self) -> int:
        """Calculate signal-to-noise ratio."""
        return self.rssi - self.noise

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            **asdict(self),
            "signal_quality": self.signal_quality(),
            "signal_percentage": self.signal_percentage(),
            "snr": self.signal_to_noise()
        }


def parse_channel_info(channel_str: str) -> tuple[int, str, str]:
    """
    Parse channel string like '149 (5GHz, 80MHz)' into components.
    Returns: (channel_number, band, bandwidth)
    """
    match = re.match(r'(\d+)\s*\((\d+(?:\.\d+)?GHz),\s*(\d+MHz)\)', channel_str)
    if match:
        return int(match.group(1)), match.group(2), match.group(3)

    # Fallback: try to parse just the channel number
    try:
        channel = int(channel_str.split()[0])
        band = "2.4GHz" if channel <= 14 else "5GHz"
        return channel, band, "Unknown"
    except:
        return 0, "Unknown", "Unknown"


def parse_signal_noise(signal_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse signal/noise string like '-45 dBm / -93 dBm'.
    Returns: (rssi, noise)
    """
    match = re.match(r'(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm', signal_str)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def get_wifi_data() -> dict:
    """
    Get all WiFi data using system_profiler.
    Returns raw parsed data structure.
    """
    try:
        result = subprocess.run(
            ["system_profiler", "SPAirPortDataType"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {"error": "Failed to get WiFi data"}

        return {"raw": result.stdout}

    except subprocess.TimeoutExpired:
        return {"error": "Timeout getting WiFi data"}
    except Exception as e:
        return {"error": str(e)}


def parse_wifi_data(raw_output: str) -> tuple[Optional[CurrentConnection], list[NetworkInfo]]:
    """
    Parse system_profiler output to extract current connection and nearby networks.
    """
    current_connection = None
    other_networks = []

    lines = raw_output.split('\n')

    # Known property keys in network info
    PROPERTY_KEYS = [
        "PHY Mode", "Channel", "Security", "Signal / Noise",
        "Network Type", "Country Code", "Transmit Rate", "MCS Index"
    ]

    # Section markers that end the other networks list
    SECTION_ENDS = ["awdl0:", "llw0:", "Bluetooth:"]

    in_current_network = False
    in_other_networks = False
    current_network_name = None
    current_network_data = {}

    network_name = None
    network_data = {}

    for line in lines:
        stripped = line.strip()

        # Check for section end markers
        if any(stripped.startswith(end) for end in SECTION_ENDS):
            # Save any pending network data
            if in_other_networks and network_name and network_data:
                net = build_network_info(network_name, network_data)
                if net:
                    other_networks.append(net)
            in_current_network = False
            in_other_networks = False
            continue

        # Detect section changes
        if "Current Network Information:" in line:
            in_current_network = True
            in_other_networks = False
            continue

        if "Other Local Wi-Fi Networks:" in line:
            # Save any pending current network data
            if current_network_name and current_network_data:
                current_connection = build_current_connection(
                    current_network_name, current_network_data
                )
            in_current_network = False
            in_other_networks = True
            continue

        # Parse current network
        if in_current_network:
            # Check if this is a property line (contains known property key)
            is_property = any(stripped.startswith(key + ":") for key in PROPERTY_KEYS)

            if stripped.endswith(":") and not is_property:
                # This is a network name
                if current_network_name and current_network_data:
                    current_connection = build_current_connection(
                        current_network_name, current_network_data
                    )
                current_network_name = stripped[:-1]
                current_network_data = {}
            elif ":" in stripped:
                key, _, value = stripped.partition(":")
                current_network_data[key.strip()] = value.strip()

        # Parse other networks
        if in_other_networks:
            # Check if this is a property line
            is_property = any(stripped.startswith(key + ":") for key in PROPERTY_KEYS)

            if stripped.endswith(":") and not is_property:
                # This is a network name - save previous network first
                if network_name and network_data:
                    net = build_network_info(network_name, network_data)
                    if net:
                        other_networks.append(net)
                network_name = stripped[:-1]
                network_data = {}
            elif ":" in stripped and network_name:
                key, _, value = stripped.partition(":")
                network_data[key.strip()] = value.strip()

    # Don't forget the last network
    if network_name and network_data:
        net = build_network_info(network_name, network_data)
        if net:
            other_networks.append(net)

    # Handle case where we have current network data but haven't built it yet
    if current_network_name and current_network_data and not current_connection:
        current_connection = build_current_connection(
            current_network_name, current_network_data
        )

    return current_connection, other_networks


def build_current_connection(name: str, data: dict) -> Optional[CurrentConnection]:
    """Build CurrentConnection from parsed data."""
    try:
        channel_str = data.get("Channel", "0")
        channel, band, bandwidth = parse_channel_info(channel_str)

        signal_str = data.get("Signal / Noise", "-70 dBm / -90 dBm")
        rssi, noise = parse_signal_noise(signal_str)

        tx_rate = int(data.get("Transmit Rate", "0"))
        mcs_str = data.get("MCS Index")
        mcs = int(mcs_str) if mcs_str else None

        return CurrentConnection(
            ssid=name,
            channel=channel,
            band=band,
            band_width=bandwidth,
            phy_mode=data.get("PHY Mode", "Unknown"),
            security=data.get("Security", "Unknown"),
            rssi=rssi or -70,
            noise=noise or -90,
            tx_rate=tx_rate,
            mcs_index=mcs
        )
    except Exception as e:
        print(f"Error building current connection: {e}")
        return None


def build_network_info(name: str, data: dict) -> Optional[NetworkInfo]:
    """Build NetworkInfo from parsed data."""
    try:
        channel_str = data.get("Channel", "0")
        channel, band, bandwidth = parse_channel_info(channel_str)

        rssi, noise = None, None
        signal_str = data.get("Signal / Noise")
        if signal_str:
            rssi, noise = parse_signal_noise(signal_str)

        return NetworkInfo(
            ssid=name,
            channel=channel,
            band=band,
            band_width=bandwidth,
            phy_mode=data.get("PHY Mode", "Unknown"),
            security=data.get("Security", "Unknown"),
            rssi=rssi,
            noise=noise
        )
    except Exception as e:
        print(f"Error building network info for {name}: {e}")
        return None


def scan_networks() -> tuple[Optional[CurrentConnection], list[NetworkInfo]]:
    """
    Scan for WiFi networks and get current connection info.
    Returns: (current_connection, list_of_other_networks)
    """
    data = get_wifi_data()
    if "error" in data:
        print(f"Error: {data['error']}")
        return None, []

    return parse_wifi_data(data["raw"])


def measure_latency(host: str = "8.8.8.8", count: int = 5) -> Optional[dict]:
    """Measure network latency using ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), host],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {"error": "Ping failed", "host": host}

        # Parse ping statistics
        match = re.search(
            r'round-trip min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
            result.stdout
        )

        if match:
            return {
                "min_ms": float(match.group(1)),
                "avg_ms": float(match.group(2)),
                "max_ms": float(match.group(3)),
                "stddev_ms": float(match.group(4)),
                "host": host
            }

        return {"error": "Could not parse ping output", "host": host}

    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "host": host}
    except Exception as e:
        return {"error": str(e), "host": host}


def calculate_score(network: NetworkInfo, is_current: bool = False,
                   latency: Optional[dict] = None,
                   current_rssi: Optional[int] = None) -> dict:
    """
    Calculate a recommendation score for a network.
    Score is 0-100 where higher is better.
    """
    score = 0
    factors = {}

    # Use RSSI if available
    rssi = network.rssi if network.rssi else current_rssi

    # Signal strength (40 points max)
    if rssi:
        signal_pct = network.signal_percentage() if network.rssi else (
            min(100, max(0, int((rssi + 90) * 100 / 60)))
        )
        signal_score = signal_pct * 0.4
        score += signal_score
        factors["signal"] = {"score": round(signal_score, 1), "max": 40}
    else:
        factors["signal"] = {"score": 0, "max": 40, "note": "No signal data"}

    # Band & bandwidth preference (25 points max)
    band_score = 0
    if network.band == "5GHz":
        band_score += 15
        if network.band_width in ["80MHz", "160MHz"]:
            band_score += 10
        elif network.band_width == "40MHz":
            band_score += 5
    else:  # 2.4GHz
        band_score += 8  # Good for range/penetration
        if network.band_width == "40MHz":
            band_score += 5
    score += band_score
    factors["band"] = {"score": band_score, "max": 25}

    # PHY mode preference (15 points max)
    phy_score = 0
    if "ax" in network.phy_mode:  # WiFi 6
        phy_score = 15
    elif "ac" in network.phy_mode:  # WiFi 5
        phy_score = 12
    elif "n" in network.phy_mode:  # WiFi 4
        phy_score = 8
    else:
        phy_score = 4
    score += phy_score
    factors["phy_mode"] = {"score": phy_score, "max": 15}

    # Latency (20 points max) - only for current connection
    if is_current and latency and "avg_ms" in latency:
        avg = latency["avg_ms"]
        if avg < 20:
            lat_score = 20
        elif avg < 50:
            lat_score = 15
        elif avg < 100:
            lat_score = 10
        else:
            lat_score = 5
        score += lat_score
        factors["latency"] = {"score": lat_score, "max": 20, "avg_ms": avg}
    else:
        factors["latency"] = {"score": 0, "max": 20, "note": "N/A" if not is_current else "Not measured"}

    return {
        "total": round(score, 1),
        "max_possible": 100,
        "grade": get_grade(score),
        "factors": factors,
        "recommendation": get_recommendation(score, is_current, rssi)
    }


def get_grade(score: float) -> str:
    """Convert score to letter grade."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def get_recommendation(score: float, is_current: bool, rssi: Optional[int]) -> str:
    """Get recommendation text based on score."""
    if is_current:
        if score >= 80:
            return "Excellent connection - optimal for this location"
        elif score >= 60:
            return "Good connection - suitable for most tasks"
        elif score >= 40:
            return "Fair connection - may experience slowdowns"
        else:
            return "Poor connection - consider switching networks"
    else:
        if rssi is None:
            return "Signal strength unknown - try connecting to test"
        elif score >= 50:
            return "Good candidate for this location"
        elif score >= 30:
            return "Acceptable - may work for basic tasks"
        else:
            return "Weak signal - not recommended for this location"


if __name__ == "__main__":
    print("Scanning WiFi networks...\n")

    current, networks = scan_networks()

    if current:
        print("=" * 60)
        print("CURRENT CONNECTION")
        print("=" * 60)
        print(f"  Network: {current.ssid}")
        print(f"  Band: {current.band} | Channel: {current.channel} | Width: {current.band_width}")
        print(f"  PHY Mode: {current.phy_mode}")
        print(f"  Signal: {current.rssi} dBm ({current.signal_quality()}) | {current.signal_percentage()}%")
        print(f"  Noise: {current.noise} dBm | SNR: {current.signal_to_noise()} dB")
        print(f"  TX Rate: {current.tx_rate} Mbps")
        print(f"  Security: {current.security}")

        print("\n  Measuring latency...")
        latency = measure_latency()
        if latency and "avg_ms" in latency:
            print(f"  Latency: {latency['avg_ms']:.1f} ms (min: {latency['min_ms']:.1f}, max: {latency['max_ms']:.1f})")

        # Calculate score for current connection
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
        print(f"\n  Score: {score['total']}/100 (Grade: {score['grade']})")
        print(f"  {score['recommendation']}")
    else:
        print("Not connected to any WiFi network")

    if networks:
        print("\n" + "=" * 60)
        print(f"OTHER AVAILABLE NETWORKS ({len(networks)})")
        print("=" * 60)

        # Sort by signal strength (networks with signal first, then by rssi)
        networks_sorted = sorted(
            networks,
            key=lambda n: (n.rssi is not None, n.rssi or -100),
            reverse=True
        )

        for net in networks_sorted:
            signal_info = f"{net.rssi} dBm ({net.signal_quality()})" if net.rssi else "Signal: N/A"
            print(f"\n  {net.ssid}")
            print(f"    {net.band} | Ch {net.channel} | {net.band_width} | {net.phy_mode}")
            print(f"    {signal_info}")
            print(f"    Security: {net.security}")
