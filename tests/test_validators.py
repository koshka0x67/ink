#!/usr/bin/env python3
"""
Tests for input validation
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, MagicMock
from PIL import Image

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.validators import InputValidator, ValidationError, safe_int, safe_float, safe_bool

class TestInputValidator(unittest.TestCase):
    """Test input validation functionality"""
    
    def test_validate_image_file_valid(self):
        """Test validation of valid image file"""
        mock_file = Mock()
        mock_file.filename = 'test.jpg'
        mock_file.content_type = 'image/jpeg'
        
        # Should not raise exception
        InputValidator.validate_image_file(mock_file)
    
    def test_validate_image_file_no_file(self):
        """Test validation with no file"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_file(None)
    
    def test_validate_image_file_no_filename(self):
        """Test validation with no filename"""
        mock_file = Mock()
        mock_file.filename = ''
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_file(mock_file)
    
    def test_validate_image_file_invalid_extension(self):
        """Test validation with invalid file extension"""
        mock_file = Mock()
        mock_file.filename = 'test.txt'
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_file(mock_file)
    
    def test_validate_image_file_invalid_mime_type(self):
        """Test validation with invalid MIME type"""
        mock_file = Mock()
        mock_file.filename = 'test.jpg'
        mock_file.content_type = 'text/plain'
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_file(mock_file)
    
    def test_validate_image_data_valid(self):
        """Test validation of valid image data"""
        image_data = {
            'scale': 1.5,
            'crop_x': 10,
            'crop_y': 20,
            'crop_w': 100,
            'crop_h': 80
        }
        
        result = InputValidator.validate_image_data(image_data)
        self.assertEqual(result['scale'], 1.5)
        self.assertEqual(result['crop_x'], 10)
        self.assertEqual(result['crop_y'], 20)
        self.assertEqual(result['crop_w'], 100)
        self.assertEqual(result['crop_h'], 80)
    
    def test_validate_image_data_invalid_scale(self):
        """Test validation with invalid scale"""
        image_data = {'scale': 15.0}  # Too large
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_data(image_data)
    
    def test_validate_image_data_invalid_crop(self):
        """Test validation with invalid crop values"""
        image_data = {'crop_x': -10}  # Negative value
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_data(image_data)
    
    def test_validate_settings_valid(self):
        """Test validation of valid settings"""
        settings = {
            'mode': 'dashboard',
            'city': 'Test City',
            'units': 'c',
            'interval': 300,
            'show_humidity': True,
            'show_wind': False,
            'show_sun': True,
            'rotation': 90,
            'flip_h': False,
            'flip_v': True
        }
        
        result = InputValidator.validate_settings(settings)
        self.assertEqual(result['mode'], 'dashboard')
        self.assertEqual(result['city'], 'Test City')
        self.assertEqual(result['units'], 'c')
        self.assertEqual(result['interval'], 300)
        self.assertTrue(result['show_humidity'])
        self.assertFalse(result['show_wind'])
        self.assertTrue(result['show_sun'])
        self.assertEqual(result['rotation'], 90)
        self.assertFalse(result['flip_h'])
        self.assertTrue(result['flip_v'])
    
    def test_validate_settings_invalid_mode(self):
        """Test validation with invalid mode"""
        settings = {'mode': 'invalid'}
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_settings(settings)
    
    def test_validate_settings_invalid_units(self):
        """Test validation with invalid units"""
        settings = {'units': 'kelvin'}
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_settings(settings)
    
    def test_validate_settings_invalid_interval(self):
        """Test validation with invalid interval"""
        settings = {'interval': 10}  # Too small
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_settings(settings)
    
    def test_validate_settings_invalid_rotation(self):
        """Test validation with invalid rotation"""
        settings = {'rotation': 45}  # Not valid rotation angle
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_settings(settings)
    
    def test_validate_rotation_data_valid(self):
        """Test validation of valid rotation data"""
        data = {'degrees': 90}
        result = InputValidator.validate_rotation_data(data)
        self.assertEqual(result, 90)
    
    def test_validate_rotation_data_invalid(self):
        """Test validation of invalid rotation data"""
        data = {'degrees': 45}
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_rotation_data(data)
    
    def test_validate_auto_action_valid(self):
        """Test validation of valid auto action"""
        data = {'action': 'start'}
        result = InputValidator.validate_auto_action(data)
        self.assertEqual(result, 'start')
    
    def test_validate_auto_action_invalid(self):
        """Test validation of invalid auto action"""
        data = {'action': 'invalid'}
        
        with self.assertRaises(ValidationError):
            InputValidator.validate_auto_action(data)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test dangerous characters
        result = InputValidator.sanitize_filename('test<>:"/\\|?*.jpg')
        self.assertEqual(result, 'test.jpg')
        
        # Test path traversal
        result = InputValidator.sanitize_filename('../../../etc/passwd')
        self.assertEqual(result, 'etcpasswd')
        
        # Test empty filename
        result = InputValidator.sanitize_filename('')
        self.assertEqual(result, 'untitled')
    
    def test_validate_image_dimensions(self):
        """Test image dimension validation"""
        # Valid image
        img = Image.new('RGB', (100, 100))
        InputValidator.validate_image_dimensions(img)
        
        # Invalid dimensions
        img = Image.new('RGB', (0, 100))
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_dimensions(img)
        
        # Too large
        img = Image.new('RGB', (20000, 20000))
        with self.assertRaises(ValidationError):
            InputValidator.validate_image_dimensions(img)

class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_safe_int(self):
        """Test safe integer conversion"""
        self.assertEqual(safe_int('123'), 123)
        self.assertEqual(safe_int('abc', default=0), 0)
        self.assertEqual(safe_int('5', min_val=10, max_val=20), 10)
        self.assertEqual(safe_int('25', min_val=10, max_val=20), 20)
    
    def test_safe_float(self):
        """Test safe float conversion"""
        self.assertEqual(safe_float('123.45'), 123.45)
        self.assertEqual(safe_float('abc', default=0.0), 0.0)
        self.assertEqual(safe_float('5.0', min_val=10.0, max_val=20.0), 10.0)
        self.assertEqual(safe_float('25.0', min_val=10.0, max_val=20.0), 20.0)
    
    def test_safe_bool(self):
        """Test safe boolean conversion"""
        self.assertTrue(safe_bool(True))
        self.assertTrue(safe_bool('true'))
        self.assertTrue(safe_bool('1'))
        self.assertTrue(safe_bool('yes'))
        self.assertTrue(safe_bool('on'))
        self.assertTrue(safe_bool(1))
        
        self.assertFalse(safe_bool(False))
        self.assertFalse(safe_bool('false'))
        self.assertFalse(safe_bool('0'))
        self.assertFalse(safe_bool('no'))
        self.assertFalse(safe_bool('off'))
        self.assertFalse(safe_bool(0))
        self.assertFalse(safe_bool('invalid'))

if __name__ == '__main__':
    unittest.main()
