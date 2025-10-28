#!/usr/bin/env python3
"""
Weather service for E-Paper Display Web Interface
"""

import urllib.parse
import urllib.request
import json
import datetime as dt
from typing import Dict, Any, Optional, Tuple
import logging

from config import Config

logger = logging.getLogger(__name__)

class WeatherService:
    """Handles weather data fetching and processing"""
    
    def __init__(self):
        self.timeout = Config.WEATHER_API_TIMEOUT
        self.user_agent = Config.WEATHER_API_USER_AGENT
    
    def _http_get_json(self, url: str) -> Dict[str, Any]:
        """Make HTTP GET request and return JSON response"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise
    
    def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:
        """Get coordinates and display name for a city"""
        try:
            qs = urllib.parse.urlencode({"name": city, "count": 1})
            data = self._http_get_json(f"https://geocoding-api.open-meteo.com/v1/search?{qs}")
            results = data.get('results') or []
            if not results:
                logger.warning(f"No results found for city: {city}")
                return None
            
            r0 = results[0]
            lat, lon = float(r0['latitude']), float(r0['longitude'])
            name = str(r0.get('name') or city)
            admin1, country = r0.get('admin1'), r0.get('country')
            display = ", ".join([x for x in [name, admin1, country] if x])
            return lat, lon, display
        except Exception as e:
            logger.error(f"Geocoding failed for city {city}: {e}")
            return None
    
    def fetch_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch weather data for given coordinates"""
        try:
            qs = urllib.parse.urlencode({
                'latitude': lat, 'longitude': lon,
                'current': ','.join(['temperature_2m','relative_humidity_2m','wind_speed_10m','weather_code']),
                'daily': ','.join(['sunrise','sunset']),
                'timezone': 'auto'
            })
            return self._http_get_json(f"https://api.open-meteo.com/v1/forecast?{qs}")
        except Exception as e:
            logger.error(f"Weather fetch failed for lat={lat}, lon={lon}: {e}")
            raise
    
    def get_weather_code_text(self, code: int) -> str:
        """Convert WMO weather code to text"""
        mapping = {
            0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
            45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle',
            55: 'Heavy drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
            71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 80: 'Rain showers',
            95: 'Thunder'
        }
        return mapping.get(int(code), '')
    
    def format_time(self, iso_string: str) -> Optional[str]:
        """Format ISO time string to HH:MM format"""
        if not iso_string:
            return None
        try:
            return dt.datetime.fromisoformat(str(iso_string)).strftime('%H:%M')
        except Exception as e:
            logger.warning(f"Time formatting failed for {iso_string}: {e}")
            return None
    
    def get_weather_data(self, city: str) -> Dict[str, Any]:
        """Get complete weather data for a city"""
        try:
            coords = self.geocode_city(city)
            if not coords:
                return {'error': 'City not found'}
            
            lat, lon, city_display = coords
            weather = self.fetch_weather(lat, lon)
            
            current = weather.get('current') or {}
            daily = weather.get('daily') or {}
            
            return {
                'city_display': city_display,
                'temperature': current.get('temperature_2m'),
                'humidity': current.get('relative_humidity_2m'),
                'wind_speed': current.get('wind_speed_10m'),
                'weather_code': current.get('weather_code'),
                'sunrise': (daily.get('sunrise') or [None])[0],
                'sunset': (daily.get('sunset') or [None])[0],
                'error': None
            }
        except Exception as e:
            logger.error(f"Weather data fetch failed for {city}: {e}")
            return {'error': str(e)}
