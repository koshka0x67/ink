#!/usr/bin/env python3
"""
Configuration management for E-Paper Display Web Interface
"""

import os
import json
from typing import Dict, Any, Optional

class Config:
    """Configuration class for the E-Paper Display application"""
    
    # Display settings
    DISPLAY_WIDTH = int(os.getenv('EPAPER_WIDTH', '250'))
    DISPLAY_HEIGHT = int(os.getenv('EPAPER_HEIGHT', '122'))
    
    # File paths
    CURRENT_IMAGE = os.getenv('EPAPER_CURRENT_IMAGE', '/tmp/current_epaper.bmp')
    CURRENT_IMAGE_BASE = os.getenv('EPAPER_CURRENT_IMAGE_BASE', '/tmp/current_epaper_base.bmp')
    SETTINGS_PATH = os.getenv('EPAPER_SETTINGS_PATH', '/tmp/epaper_settings.json')
    LAST_DASHBOARD_PREVIEW = os.getenv('EPAPER_DASHBOARD_PREVIEW', '/tmp/dashboard_preview.bmp')
    LOG_FILE = os.getenv('EPAPER_LOG_FILE', '/tmp/epaper_display.log')
    
    # E-Paper library path
    EPD_PATH = os.getenv('EPAPER_LIB_PATH', '/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib')
    
    # Server settings
    HOST = os.getenv('EPAPER_HOST', '0.0.0.0')
    PORT = int(os.getenv('EPAPER_PORT', '5000'))
    DEBUG = os.getenv('EPAPER_DEBUG', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('EPAPER_LOG_LEVEL', 'INFO')
    
    # Default settings
    DEFAULT_SETTINGS = {
        'mode': os.getenv('EPAPER_DEFAULT_MODE', 'image'),
        'city': os.getenv('EPAPER_DEFAULT_CITY', 'San Francisco'),
        'units': os.getenv('EPAPER_DEFAULT_UNITS', 'c'),
        'interval': int(os.getenv('EPAPER_DEFAULT_INTERVAL', '300')),
        'show_humidity': os.getenv('EPAPER_SHOW_HUMIDITY', 'true').lower() == 'true',
        'show_wind': os.getenv('EPAPER_SHOW_WIND', 'true').lower() == 'true',
        'show_sun': os.getenv('EPAPER_SHOW_SUN', 'true').lower() == 'true',
        'rotation': int(os.getenv('EPAPER_DEFAULT_ROTATION', '90')),
        'flip_h': os.getenv('EPAPER_FLIP_H', 'false').lower() == 'true',
        'flip_v': os.getenv('EPAPER_FLIP_V', 'false').lower() == 'true'
    }
    
    # Weather API settings
    WEATHER_API_TIMEOUT = int(os.getenv('EPAPER_WEATHER_TIMEOUT', '15'))
    WEATHER_API_USER_AGENT = os.getenv('EPAPER_USER_AGENT', 'EpaperDashboard/1.0')
    
    # Font paths
    FONT_PATHS = [
        os.getenv('EPAPER_FONT_PATH_1', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        os.getenv('EPAPER_FONT_PATH_2', '/usr/share/fonts/truetype/freefont/FreeSans.ttf')
    ]
    
    # Font sizes
    FONT_LARGE_SIZE = int(os.getenv('EPAPER_FONT_LARGE_SIZE', '28'))
    FONT_MED_SIZE = int(os.getenv('EPAPER_FONT_MED_SIZE', '14'))
    FONT_SMALL_SIZE = int(os.getenv('EPAPER_FONT_SMALL_SIZE', '12'))
    
    # Security settings
    MAX_FILE_SIZE = int(os.getenv('EPAPER_MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_EXTENSIONS = os.getenv('EPAPER_ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,bmp').split(',')
    
    # Performance settings
    IMAGE_CACHE_SIZE = int(os.getenv('EPAPER_CACHE_SIZE', '5'))
    THREAD_POOL_SIZE = int(os.getenv('EPAPER_THREAD_POOL_SIZE', '4'))
    
    @classmethod
    def load_settings(cls) -> Dict[str, Any]:
        """Load settings from file or return defaults"""
        if os.path.exists(cls.SETTINGS_PATH):
            try:
                with open(cls.SETTINGS_PATH, 'r') as f:
                    data = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    settings = cls.DEFAULT_SETTINGS.copy()
                    settings.update(data)
                    return settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")
        
        return cls.DEFAULT_SETTINGS.copy()
    
    @classmethod
    def save_settings(cls, settings: Dict[str, Any]) -> bool:
        """Save settings to file"""
        try:
            with open(cls.SETTINGS_PATH, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False
    
    @classmethod
    def get_epd_path(cls) -> str:
        """Get the E-Paper library path"""
        return cls.EPD_PATH
    
    @classmethod
    def is_epd_available(cls) -> bool:
        """Check if E-Paper library is available"""
        return os.path.exists(cls.EPD_PATH)
