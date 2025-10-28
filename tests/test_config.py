#!/usr/bin/env python3
"""
Tests for configuration management
"""

import os
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        """Set up test environment"""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_default_values(self):
        """Test default configuration values"""
        self.assertEqual(Config.DISPLAY_WIDTH, 250)
        self.assertEqual(Config.DISPLAY_HEIGHT, 122)
        self.assertEqual(Config.HOST, '0.0.0.0')
        self.assertEqual(Config.PORT, 5000)
        self.assertFalse(Config.DEBUG)
        self.assertEqual(Config.LOG_LEVEL, 'INFO')
    
    def test_environment_override(self):
        """Test environment variable override"""
        with patch.dict(os.environ, {
            'EPAPER_WIDTH': '300',
            'EPAPER_HEIGHT': '200',
            'EPAPER_PORT': '8080',
            'EPAPER_DEBUG': 'true',
            'EPAPER_LOG_LEVEL': 'DEBUG'
        }):
            # Reload config to pick up environment variables
            import importlib
            import config
            importlib.reload(config)
            
            self.assertEqual(config.Config.DISPLAY_WIDTH, 300)
            self.assertEqual(config.Config.DISPLAY_HEIGHT, 200)
            self.assertEqual(config.Config.PORT, 8080)
            self.assertTrue(config.Config.DEBUG)
            self.assertEqual(config.Config.LOG_LEVEL, 'DEBUG')
    
    def test_load_settings_file_exists(self):
        """Test loading settings from existing file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            test_settings = {
                'mode': 'dashboard',
                'city': 'Test City',
                'units': 'f',
                'interval': 600
            }
            import json
            json.dump(test_settings, f)
            temp_file = f.name
        
        try:
            with patch.object(Config, 'SETTINGS_PATH', temp_file):
                settings = Config.load_settings()
                self.assertEqual(settings['mode'], 'dashboard')
                self.assertEqual(settings['city'], 'Test City')
                self.assertEqual(settings['units'], 'f')
                self.assertEqual(settings['interval'], 600)
        finally:
            os.unlink(temp_file)
    
    def test_load_settings_file_not_exists(self):
        """Test loading settings when file doesn't exist"""
        with patch.object(Config, 'SETTINGS_PATH', '/nonexistent/file.json'):
            settings = Config.load_settings()
            self.assertEqual(settings, Config.DEFAULT_SETTINGS)
    
    def test_save_settings(self):
        """Test saving settings to file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            with patch.object(Config, 'SETTINGS_PATH', temp_file):
                test_settings = {'mode': 'test', 'city': 'Test City'}
                result = Config.save_settings(test_settings)
                self.assertTrue(result)
                
                # Verify file was created and contains correct data
                self.assertTrue(os.path.exists(temp_file))
                with open(temp_file, 'r') as f:
                    saved_data = json.load(f)
                self.assertEqual(saved_data['mode'], 'test')
                self.assertEqual(saved_data['city'], 'Test City')
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_is_epd_available(self):
        """Test E-Paper library availability check"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.assertTrue(Config.is_epd_available())
            
            mock_exists.return_value = False
            self.assertFalse(Config.is_epd_available())

if __name__ == '__main__':
    unittest.main()
