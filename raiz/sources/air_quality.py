"""Air Quality — real-time and hyperlocal monitoring.

Two sources:
  AirNow — official EPA monitors (sparse, reliable)
  PurpleAir — community sensors (dense, noisier)

The gap between them IS the environmental justice story.
EPA monitors are sparse in low-income neighborhoods.
PurpleAir sensors are placed by people who can afford $250.
The communities with the worst air often have the least data.

Raíz combines both to see the full picture.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AirReading:
    """A single air quality reading."""
    timestamp: datetime
    source: str  # "airnow", "purpleair", "openaq"
    latitude: float
    longitude: float
    aqi: int = 0
    pm25: float = 0.0
    pm10: float = 0.0
    ozone: float = 0.0
    no2: float = 0.0
    so2: float = 0.0
    co: float = 0.0
    category: str = ""  # "Good", "Moderate", "Unhealthy for Sensitive Groups", etc.
    station_name: str = ""
    distance_miles: float = 0.0

    @property
    def is_unhealthy(self) -> bool:
        return self.aqi >= 101

    @property
    def is_hazardous(self) -> bool:
        return self.aqi >= 301


@dataclass
class AirQualityReport:
    """Air quality summary for an area."""
    zip_code: str
    timestamp: datetime
    readings: list[AirReading]
    nearest_epa_monitor: AirReading | None = None
    nearest_community_sensor: AirReading | None = None
    monitoring_gap: bool = False  # True if nearest EPA monitor is >5 miles away

    def summarize(self) -> str:
        parts = [f"Air Quality Report for {self.zip_code}:"]

        if self.nearest_epa_monitor:
            m = self.nearest_epa_monitor
            parts.append(
                f"  EPA monitor ({m.station_name}, {m.distance_miles:.1f} mi): "
                f"AQI {m.aqi} ({m.category})"
            )
        else:
            parts.append("  No EPA monitor within 10 miles — monitoring gap")

        if self.nearest_community_sensor:
            s = self.nearest_community_sensor
            parts.append(
                f"  Community sensor ({s.distance_miles:.1f} mi): "
                f"PM2.5 {s.pm25:.1f} µg/m³"
            )

        if self.monitoring_gap:
            parts.append(
                "  ⚠ MONITORING GAP: Nearest EPA monitor is far from this community. "
                "Air quality data may not reflect local conditions."
            )

        unhealthy = [r for r in self.readings if r.is_unhealthy]
        if unhealthy:
            parts.append(f"  {len(unhealthy)} readings at Unhealthy levels or worse")

        return "\n".join(parts)


class AirNowSource:
    """Query AirNow for official EPA air quality data.

    Requires free API key from docs.airnowapi.org
    """

    API_BASE = "https://www.airnowapi.org/aq"

    def __init__(self, api_key: str = "", dry_run: bool = False) -> None:
        self._api_key = api_key
        self._dry_run = dry_run

    async def current_by_zip(self, zip_code: str) -> list[AirReading]:
        if self._dry_run:
            return self._mock_readings(zip_code)

        if not self._api_key:
            logger.warning("AirNow API key not set")
            return []

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required")
            return []

        url = f"{self.API_BASE}/observation/zipCode/current/"
        params = {
            "format": "application/json",
            "zipCode": zip_code,
            "API_KEY": self._api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

            readings = []
            for obs in data if isinstance(data, list) else []:
                readings.append(AirReading(
                    timestamp=datetime.now(timezone.utc),
                    source="airnow",
                    latitude=float(obs.get("Latitude", 0)),
                    longitude=float(obs.get("Longitude", 0)),
                    aqi=int(obs.get("AQI", 0)),
                    category=obs.get("Category", {}).get("Name", ""),
                    station_name=obs.get("ReportingArea", ""),
                ))
            return readings
        except Exception as e:
            logger.error("AirNow query failed: %s", e)
            return []

    def _mock_readings(self, zip_code: str) -> list[AirReading]:
        return [AirReading(
            timestamp=datetime.now(timezone.utc),
            source="airnow",
            latitude=39.78, longitude=-89.65,
            aqi=72, pm25=22.1, category="Moderate",
            station_name="Springfield-EPA", distance_miles=2.3,
        )]


class PurpleAirSource:
    """Query PurpleAir for community sensor data.

    API key required (free for research).
    These sensors fill the gaps where EPA monitors don't exist —
    which is exactly where environmental justice communities live.
    """

    API_BASE = "https://api.purpleair.com/v1"

    def __init__(self, api_key: str = "", dry_run: bool = False) -> None:
        self._api_key = api_key
        self._dry_run = dry_run

    async def sensors_near(
        self, lat: float, lon: float, radius_km: float = 5.0,
    ) -> list[AirReading]:
        if self._dry_run:
            return self._mock_sensors(lat, lon)

        if not self._api_key:
            logger.warning("PurpleAir API key not set")
            return []

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required")
            return []

        nwlat = lat + radius_km / 111
        nwlng = lon - radius_km / 85
        selat = lat - radius_km / 111
        selng = lon + radius_km / 85

        url = f"{self.API_BASE}/sensors"
        params = {
            "fields": "pm2.5,pm2.5_10minute,latitude,longitude,name",
            "nwlat": nwlat, "nwlng": nwlng,
            "selat": selat, "selng": selng,
        }
        headers = {"X-API-Key": self._api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    data = await resp.json()

            readings = []
            fields = data.get("fields", [])
            for row in data.get("data", []):
                sensor = dict(zip(fields, row))
                readings.append(AirReading(
                    timestamp=datetime.now(timezone.utc),
                    source="purpleair",
                    latitude=float(sensor.get("latitude", 0)),
                    longitude=float(sensor.get("longitude", 0)),
                    pm25=float(sensor.get("pm2.5", 0) or 0),
                    station_name=sensor.get("name", ""),
                ))
            return readings
        except Exception as e:
            logger.error("PurpleAir query failed: %s", e)
            return []

    def _mock_sensors(self, lat: float, lon: float) -> list[AirReading]:
        return [
            AirReading(
                timestamp=datetime.now(timezone.utc),
                source="purpleair",
                latitude=lat + 0.005, longitude=lon + 0.003,
                pm25=31.4, station_name="Elm Street Sensor",
                distance_miles=0.4,
            ),
            AirReading(
                timestamp=datetime.now(timezone.utc),
                source="purpleair",
                latitude=lat - 0.008, longitude=lon - 0.002,
                pm25=18.7, station_name="River Road Monitor",
                distance_miles=0.7,
            ),
        ]
