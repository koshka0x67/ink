#!/usr/bin/env python3
"""
Input validation utilities for E-Paper Display Web Interface
"""

import os
import re
from typing import Any, Dict, List, Optional, Union
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class InputValidator:
    """Input validation class"""
    
    # Allowed image formats
    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp'}
    
    # Valid temperature units
    VALID_UNITS = {'c', 'f', 'celsius', 'fahrenheit'}
    
    # Valid rotation angles
    VALID_ROTATIONS = {0, 90, 180, 270}
    
    # Min/max values
    MIN_INTERVAL = 30
    MAX_INTERVAL = 86400  # 24 hours
    MIN_SCALE = 0.1
    MAX_SCALE = 10.0
    MIN_CROP = 0
    MAX_CROP = 10000
    
    @classmethod
    def validate_image_file(cls, file) -> bool:
        """Validate uploaded image file"""
        if not file or not hasattr(file, 'filename'):
            raise ValidationError("No file provided")
        
        if not file.filename:
            raise ValidationError("No filename provided")
        
        # Check file extension
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            raise ValidationError("Invalid file type. Only JPG, PNG, GIF, BMP are allowed")
        
        # Check MIME type
        if hasattr(file, 'content_type') and file.content_type not in cls.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid MIME type: {file.content_type}")
        
        return True
    
    @classmethod
    def validate_image_data(cls, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate image processing parameters"""
        validated = {}
        
        # Scale validation
        scale = image_data.get('scale', 1.0)
        try:
            scale = float(scale)
            if not (cls.MIN_SCALE <= scale <= cls.MAX_SCALE):
                raise ValidationError(f"Scale must be between {cls.MIN_SCALE} and {cls.MAX_SCALE}")
            validated['scale'] = scale
        except (ValueError, TypeError):
            raise ValidationError("Invalid scale value")
        
        # Offset validation
        for param in ['offset_x', 'offset_y']:
            value = image_data.get(param, 0)
            try:
                value = float(value)
                if not (-cls.MAX_CROP <= value <= cls.MAX_CROP):
                    raise ValidationError(f"{param} must be between {-cls.MAX_CROP} and {cls.MAX_CROP}")
                validated[param] = value
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid {param} value")
        
        # Crop validation
        for param in ['crop_x', 'crop_y', 'crop_w', 'crop_h']:
            value = image_data.get(param, 0)
            try:
                value = int(value)
                if not (cls.MIN_CROP <= value <= cls.MAX_CROP):
                    raise ValidationError(f"{param} must be between {cls.MIN_CROP} and {cls.MAX_CROP}")
                validated[param] = value
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid {param} value")
        
        # Rotation validation
        rotation = image_data.get('rotation', 90)
        try:
            rotation = int(rotation)
            if rotation not in cls.VALID_ROTATIONS:
                raise ValidationError("Rotation must be 0, 90, 180, or 270 degrees")
            validated['rotation'] = rotation
        except (ValueError, TypeError):
            raise ValidationError("Invalid rotation value")
        
        return validated
    
    @classmethod
    def validate_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate settings data"""
        validated = {}
        
        # Mode validation
        mode = settings.get('mode', 'image')
        if mode not in {'image', 'dashboard'}:
            raise ValidationError("Mode must be 'image' or 'dashboard'")
        validated['mode'] = mode
        
        # City validation
        city = settings.get('city', '')
        if not isinstance(city, str):
            raise ValidationError("City must be a string")
        city = city.strip()
        if len(city) > 100:
            raise ValidationError("City name too long")
        validated['city'] = city
        
        # Units validation
        units = settings.get('units', 'c')
        if units.lower() not in cls.VALID_UNITS:
            raise ValidationError("Invalid temperature units")
        validated['units'] = units.lower()[:1]  # Normalize to 'c' or 'f'
        
        # Interval validation
        interval = settings.get('interval', 300)
        try:
            interval = int(interval)
            if not (cls.MIN_INTERVAL <= interval <= cls.MAX_INTERVAL):
                raise ValidationError(f"Interval must be between {cls.MIN_INTERVAL} and {cls.MAX_INTERVAL} seconds")
            validated['interval'] = interval
        except (ValueError, TypeError):
            raise ValidationError("Invalid interval value")
        
        # Boolean validations
        for param in ['show_humidity', 'show_wind', 'show_sun', 'flip_h', 'flip_v']:
            value = settings.get(param, False)
            validated[param] = bool(value)
        
        # Rotation validation
        rotation = settings.get('rotation', 0)
        try:
            rotation = int(rotation)
            if rotation not in cls.VALID_ROTATIONS:
                raise ValidationError("Rotation must be 0, 90, 180, or 270 degrees")
            validated['rotation'] = rotation
        except (ValueError, TypeError):
            raise ValidationError("Invalid rotation value")
        
        return validated
    
    @classmethod
    def validate_rotation_data(cls, data: Dict[str, Any]) -> int:
        """Validate rotation data"""
        degrees = data.get('degrees', 0)
        try:
            degrees = int(degrees)
            if degrees not in cls.VALID_ROTATIONS:
                raise ValidationError("Degrees must be 0, 90, 180, or 270")
            return degrees
        except (ValueError, TypeError):
            raise ValidationError("Invalid degrees value")
    
    @classmethod
    def validate_auto_action(cls, data: Dict[str, Any]) -> str:
        """Validate auto action"""
        action = data.get('action', '').lower()
        if action not in {'start', 'stop'}:
            raise ValidationError("Action must be 'start' or 'stop'")
        return action
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for security"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Limit length
        filename = filename[:100]
        
        return filename or 'untitled'
    
    @classmethod
    def validate_image_dimensions(cls, image: Image.Image) -> bool:
        """Validate image dimensions are reasonable"""
        width, height = image.size
        
        # Check for reasonable dimensions
        if width <= 0 or height <= 0:
            raise ValidationError("Image dimensions must be positive")
        
        if width > 10000 or height > 10000:
            raise ValidationError("Image dimensions too large")
        
        return True

def validate_request_data(data: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
    """Validate request data with required fields"""
    if not isinstance(data, dict):
        raise ValidationError("Request data must be a dictionary")
    
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return data

def safe_int(value: Any, default: int = 0, min_val: int = None, max_val: int = None) -> int:
    """Safely convert value to int with constraints"""
    try:
        result = int(value)
        if min_val is not None and result < min_val:
            return min_val
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0, min_val: float = None, max_val: float = None) -> float:
    """Safely convert value to float with constraints"""
    try:
        result = float(value)
        if min_val is not None and result < min_val:
            return min_val
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (ValueError, TypeError):
        return default

def safe_bool(value: Any, default: bool = False) -> bool:
    """Safely convert value to bool"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {'true', '1', 'yes', 'on'}
    if isinstance(value, (int, float)):
        return bool(value)
    return default
