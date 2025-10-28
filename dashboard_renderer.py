#!/usr/bin/env python3
"""
Dashboard rendering for E-Paper Display Web Interface
"""

import os
import datetime as dt
from typing import Dict, Any, Tuple
from PIL import Image, ImageOps, ImageDraw, ImageFont
import logging

from config import Config
from weather_service import WeatherService

logger = logging.getLogger(__name__)

class DashboardRenderer:
    """Handles dashboard rendering and layout"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.fonts = self._load_fonts()
    
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Load available fonts"""
        fonts = {}
        for size_name, size in [('large', Config.FONT_LARGE_SIZE), 
                               ('med', Config.FONT_MED_SIZE), 
                               ('small', Config.FONT_SMALL_SIZE)]:
            fonts[size_name] = self._load_font(size)
        return fonts
    
    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load a font of specified size"""
        for path in Config.FONT_PATHS:
            try:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            except Exception as e:
                logger.warning(f"Could not load font {path}: {e}")
                continue
        return ImageFont.load_default()
    
    def _measure_text(self, draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
        """Measure text dimensions"""
        try:
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            return r - l, b - t
        except Exception as e:
            logger.warning(f"Text measurement failed: {e}")
            return (0, 0)
    
    def _ellipsis_to_fit(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
        """Truncate text with ellipsis to fit max_width"""
        w, _ = self._measure_text(draw, text, font)
        if w <= max_width:
            return text
        
        ell = '…'
        base = text
        # Binary search for optimal length
        lo, hi = 0, len(base)
        best = ''
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = base[:mid] + ell
            cw, _ = self._measure_text(draw, candidate, font)
            if cw <= max_width:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return best or ell
    
    def _choose_temp_font(self, draw: ImageDraw.ImageDraw, temp_text: str) -> ImageFont.FreeTypeFont:
        """Choose appropriate font size for temperature to fit left column"""
        for size in [Config.FONT_LARGE_SIZE, 24, 20, 18]:
            font = self._load_font(size)
            w, _ = self._measure_text(draw, temp_text, font)
            if w <= 120:  # left column width budget
                return font
        return self._load_font(18)
    
    def render_dashboard(self, settings: Dict[str, Any]) -> Image.Image:
        """Render the weather dashboard"""
        try:
            city = settings.get('city') or 'San Francisco'
            weather_data = self.weather_service.get_weather_data(city)
            
            if weather_data.get('error'):
                return self._render_error(weather_data['error'])
            
            return self._render_weather_dashboard(weather_data, settings)
        except Exception as e:
            logger.error(f"Dashboard rendering failed: {e}")
            return self._render_error(str(e))
    
    def _render_error(self, error_message: str) -> Image.Image:
        """Render error message"""
        img = Image.new('1', (Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT), 1)
        draw = ImageDraw.Draw(img)
        draw.text((8, 8), error_message, font=self.fonts['med'], fill=0)
        return img
    
    def _render_weather_dashboard(self, weather_data: Dict[str, Any], settings: Dict[str, Any]) -> Image.Image:
        """Render the weather dashboard with data"""
        img = Image.new('1', (Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT), 1)
        draw = ImageDraw.Draw(img)
        
        # Get current time and date
        now = dt.datetime.now()
        time_str = now.strftime('%I:%M %p').lstrip('0')
        date_str = now.strftime('%a %b %d')
        
        # Layout constraints
        margin = 8
        header_y = 4
        subheader_y = 40
        divider_y = 58
        left_x = 10
        right_margin = 10
        left_col_max_w = 130
        
        # Header
        draw.text((margin, header_y), time_str, font=self.fonts['large'], fill=0)
        
        # Subheader with city and date
        city_text = self._ellipsis_to_fit(draw, weather_data['city_display'], 
                                        self.fonts['med'], 
                                        Config.DISPLAY_WIDTH - 2*margin - 70)
        draw.text((left_x, subheader_y), date_str, font=self.fonts['med'], fill=0)
        w_city, _ = self._measure_text(draw, city_text, self.fonts['med'])
        draw.text((Config.DISPLAY_WIDTH - w_city - margin, subheader_y), city_text, font=self.fonts['med'], fill=0)
        draw.line((margin, divider_y, Config.DISPLAY_WIDTH - margin, divider_y), fill=0)
        
        # Temperature and condition
        temp_disp = self._format_temperature(weather_data['temperature'], settings.get('units', 'c'))
        temp_font = self._choose_temp_font(draw, temp_disp)
        draw.text((left_x, divider_y + 8), temp_disp, font=temp_font, fill=0)
        
        condition_text = self._ellipsis_to_fit(draw, 
                                             self.weather_service.get_weather_code_text(weather_data['weather_code'] or 0),
                                             self.fonts['small'], 
                                             left_col_max_w)
        draw.text((left_x, Config.DISPLAY_HEIGHT - 20), condition_text, font=self.fonts['small'], fill=0)
        
        # Right column data
        self._render_right_column(draw, weather_data, settings, divider_y, left_x, left_col_max_w, right_margin)
        
        # Apply orientation and flips
        return self._apply_transforms(img, settings)
    
    def _format_temperature(self, temp_c: float, units: str) -> str:
        """Format temperature based on units"""
        if temp_c is None:
            return '--'
        
        if units.lower() == 'f':
            return f"{(temp_c*9/5)+32:.0f}°F"
        else:
            return f"{float(temp_c):.0f}°C"
    
    def _render_right_column(self, draw: ImageDraw.ImageDraw, weather_data: Dict[str, Any], 
                           settings: Dict[str, Any], divider_y: int, left_x: int, 
                           left_col_max_w: int, right_margin: int):
        """Render the right column with weather details"""
        lines = []
        
        if settings.get('show_humidity') and weather_data['humidity'] is not None:
            lines.append(f"Hum {weather_data['humidity']:.0f}%")
        
        if settings.get('show_wind') and weather_data['wind_speed'] is not None:
            lines.append(f"Wind {weather_data['wind_speed']:.0f} km/h")
        
        if settings.get('show_sun'):
            sunrise = self.weather_service.format_time(weather_data['sunrise'])
            sunset = self.weather_service.format_time(weather_data['sunset'])
            if sunrise:
                lines.append(f"↑ {sunrise}")
            if sunset:
                lines.append(f"↓ {sunset}")
        
        y = divider_y + 8
        right_col_xmax = Config.DISPLAY_WIDTH - right_margin
        right_col_min_x = left_x + left_col_max_w + 6
        
        for line in lines:
            avail = max(10, right_col_xmax - right_col_min_x)
            txt = self._ellipsis_to_fit(draw, line, self.fonts['med'], max_width=avail)
            w, h = self._measure_text(draw, txt, self.fonts['med'])
            draw.text((right_col_xmax - w, y), txt, font=self.fonts['med'], fill=0)
            y += h + 2
    
    def _apply_transforms(self, img: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Apply rotation and flip transforms"""
        output = img
        rot = settings.get('rotation', 0)
        if rot % 360 != 0:
            output = output.rotate(rot, expand=True)
        if settings.get('flip_h'):
            output = ImageOps.mirror(output)
        if settings.get('flip_v'):
            output = ImageOps.flip(output)
        return output
