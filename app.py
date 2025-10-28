#!/usr/bin/env python3
"""
Main Flask application for E-Paper Display Web Interface
"""

import os
import sys
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image

from config import Config
from display_manager import DisplayManager
from dashboard_renderer import DashboardRenderer
from utils.logger import setup_logging, get_logger, ErrorHandler
from utils.validators import InputValidator, ValidationError, validate_request_data

# Set up logging
logger = setup_logging('INFO', '/tmp/epaper_display.log')
error_handler = ErrorHandler(logger)

# Set up global exception handler
sys.excepthook = error_handler.handle_exception

app = Flask(__name__)

# Initialize components
display_manager = DisplayManager()
dashboard_renderer = DashboardRenderer()

# Global state
settings = Config.load_settings()
auto_thread = None
auto_running = False

def save_preview(img: Image.Image):
    """Save dashboard preview image"""
    try:
        img.save(Config.LAST_DASHBOARD_PREVIEW)
    except Exception as e:
        logger.error(f"Preview save failed: {e}")

def apply_settings(new_data: dict):
    """Apply new settings and save to file"""
    global settings
    settings.update({
        'mode': new_data.get('mode', settings['mode']),
        'city': new_data.get('city', settings['city']),
        'units': new_data.get('units', settings['units']),
        'interval': int(new_data.get('interval', settings['interval'])),
        'show_humidity': bool(new_data.get('show_humidity', settings['show_humidity'])),
        'show_wind': bool(new_data.get('show_wind', settings['show_wind'])),
        'show_sun': bool(new_data.get('show_sun', settings['show_sun'])),
        'rotation': int(new_data.get('rotation', settings.get('rotation', 0))),
        'flip_h': bool(new_data.get('flip_h', settings.get('flip_h', False))),
        'flip_v': bool(new_data.get('flip_v', settings.get('flip_v', False)))
    })
    
    display_manager.set_rotation(settings.get('rotation', 0))
    Config.save_settings(settings)

def auto_loop():
    """Auto-update loop for dashboard mode"""
    global auto_running
    while auto_running:
        try:
            if settings.get('mode') == 'dashboard':
                frame = dashboard_renderer.render_dashboard(settings)
                save_preview(frame)
                display_manager.display_image(frame, settings)
                logger.info("[AUTO] Dashboard frame displayed")
        except Exception as e:
            logger.error(f"[AUTO] error: {e}")
        
        delay = max(30, int(settings.get('interval', 300)))
        for _ in range(delay):
            if not auto_running:
                break
            time.sleep(1)

def start_auto():
    """Start auto-update thread"""
    global auto_thread, auto_running
    if auto_running:
        return
    auto_running = True
    auto_thread = threading.Thread(target=auto_loop, daemon=True)
    auto_thread.start()

def stop_auto():
    """Stop auto-update thread"""
    global auto_running
    auto_running = False

# Routes
@app.route('/')
def index():
    """Main page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template error: {e}")
        return "<!DOCTYPE html><html><body>Template missing. Please ensure templates/index.html exists.</body></html>"

@app.route('/upload', methods=['POST'])
def upload():
    """Upload and display image"""
    try:
        # Validate file upload
        if 'image' not in request.files:
            raise ValidationError('No image provided')
        
        file = request.files['image']
        if file.filename == '':
            raise ValidationError('No image selected')
        
        # Validate image file
        InputValidator.validate_image_file(file)
        
        logger.info(f"Processing upload: {file.filename}")
        
        # Validate and get resize/crop parameters
        image_data = {
            'scale': request.form.get('scale', 1.0),
            'crop_x': request.form.get('crop_x', 0),
            'crop_y': request.form.get('crop_y', 0),
            'crop_w': request.form.get('crop_w', Config.DISPLAY_WIDTH),
            'crop_h': request.form.get('crop_h', Config.DISPLAY_HEIGHT)
        }
        
        validated_data = InputValidator.validate_image_data(image_data)
        
        # Process and display image
        img = display_manager.process_image(
            file, 
            scale=validated_data['scale'],
            crop_x=validated_data['crop_x'],
            crop_y=validated_data['crop_y'],
            crop_w=validated_data['crop_w'],
            crop_h=validated_data['crop_h']
        )
        
        success = display_manager.display_image(img, settings)
        
        if success:
            logger.info(f"Successfully uploaded and displayed: {file.filename}")
            return jsonify({'success': True, 'rotation': settings.get('rotation', 0)})
        else:
            raise Exception('Failed to display image')
    
    except ValidationError as e:
        logger.warning(f"Validation error in upload: {e}")
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Upload failed'})

@app.route('/clear', methods=['POST'])
def clear():
    """Clear display"""
    try:
        success = display_manager.clear_display()
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Clear error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/refresh', methods=['POST'])
def refresh():
    """Refresh display with current image"""
    try:
        source_path = Config.CURRENT_IMAGE_BASE if os.path.exists(Config.CURRENT_IMAGE_BASE) else Config.CURRENT_IMAGE
        if not os.path.exists(source_path):
            return jsonify({'success': False, 'error': 'No image to refresh'})

        img = Image.open(source_path)
        if img.mode != '1':
            img = img.convert('1')

        success = display_manager.display_image(img, settings)
        return jsonify({'success': bool(success)})
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rotate', methods=['POST'])
def rotate():
    """Rotate display"""
    try:
        data = request.get_json(silent=True) or {}
        deg = int(data.get('degrees', 0))

        current_rotation = settings.get('rotation', 0)
        new_rotation = (current_rotation + deg) % 360
        settings['rotation'] = new_rotation
        display_manager.set_rotation(new_rotation)
        
        Config.save_settings(settings)

        # Auto-refresh on rotate
        try:
            if settings.get('mode') == 'dashboard':
                img = dashboard_renderer.render_dashboard(settings)
            else:
                source_path = Config.CURRENT_IMAGE_BASE if os.path.exists(Config.CURRENT_IMAGE_BASE) else Config.CURRENT_IMAGE
                img = Image.open(source_path) if os.path.exists(source_path) else None
                if img and img.mode != '1':
                    img = img.convert('1')
            if img is not None:
                save_preview(img)
                display_manager.display_image(img, settings)
        except Exception as e:
            logger.warning(f"Auto-refresh on rotate failed: {e}")

        return jsonify({'success': True, 'rotation': new_rotation})
    except Exception as e:
        logger.error(f"Rotate error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings', methods=['GET', 'POST'])
def settings_route():
    """Get or update settings"""
    if request.method == 'GET':
        return jsonify(settings)
    
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate settings data
        validated_settings = InputValidator.validate_settings(data)
        
        # Apply validated settings
        apply_settings(validated_settings)
        
        logger.info(f"Settings updated: {list(validated_settings.keys())}")
        
        # Auto-refresh on settings changes
        try:
            if settings.get('mode') == 'dashboard':
                img = dashboard_renderer.render_dashboard(settings)
            else:
                source_path = Config.CURRENT_IMAGE_BASE if os.path.exists(Config.CURRENT_IMAGE_BASE) else Config.CURRENT_IMAGE
                img = Image.open(source_path) if os.path.exists(source_path) else None
                if img and img.mode != '1':
                    img = img.convert('1')
            if img is not None:
                save_preview(img)
                display_manager.display_image(img, settings)
        except Exception as e:
            logger.warning(f"Auto-refresh on settings change failed: {e}")
        
        return jsonify({'success': True, 'settings': settings})
    
    except ValidationError as e:
        logger.warning(f"Settings validation error: {e}")
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        logger.error(f"Settings error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Settings update failed'})

@app.route('/render_dashboard', methods=['POST'])
def render_dashboard_route():
    """Render and display dashboard"""
    try:
        img = dashboard_renderer.render_dashboard(settings)
        save_preview(img)
        success = display_manager.display_image(img, settings)
        return jsonify({'success': bool(success)})
    except Exception as e:
        logger.error(f"Render error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview')
def preview_route():
    """Serve preview image"""
    try:
        source_path = None
        if settings.get('mode') == 'dashboard' and os.path.exists(Config.LAST_DASHBOARD_PREVIEW):
            source_path = Config.LAST_DASHBOARD_PREVIEW
        elif os.path.exists(Config.CURRENT_IMAGE):
            source_path = Config.CURRENT_IMAGE
        elif os.path.exists(Config.CURRENT_IMAGE_BASE):
            source_path = Config.CURRENT_IMAGE_BASE
        
        if not source_path:
            return jsonify({'success': False, 'error': 'No preview available'})
        
        return send_file(source_path, mimetype='image/bmp')
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview_resize', methods=['POST'])
def preview_resize():
    """Preview resized/cropped image without displaying on device"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image selected'})
    
    try:
        # Get resize/crop parameters
        scale = float(request.form.get('scale', 1.0))
        crop_x = int(request.form.get('crop_x', 0))
        crop_y = int(request.form.get('crop_y', 0))
        crop_w = int(request.form.get('crop_w', Config.DISPLAY_WIDTH))
        crop_h = int(request.form.get('crop_h', Config.DISPLAY_HEIGHT))
        
        # Process image for preview
        img = display_manager.process_image(file, scale=scale, crop_x=crop_x, 
                                          crop_y=crop_y, crop_w=crop_w, crop_h=crop_h)
        
        # Save preview
        preview_path = '/tmp/resize_preview.bmp'
        img.save(preview_path)
        
        return jsonify({'success': True, 'preview_url': '/preview_resize_image'})
        
    except Exception as e:
        logger.error(f"Preview resize error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview_resize_image')
def preview_resize_image():
    """Serve the resize preview image"""
    try:
        preview_path = '/tmp/resize_preview.bmp'
        if os.path.exists(preview_path):
            return send_file(preview_path, mimetype='image/bmp')
        else:
            return "No preview available", 404
    except Exception as e:
        logger.error(f"Preview resize image error: {e}")
        return f"Preview error: {e}", 500

@app.route('/auto', methods=['POST'])
def auto_route():
    """Control auto-update functionality"""
    try:
        data = request.get_json(silent=True) or {}
        action = (data.get('action') or '').lower()
        
        if action == 'start':
            start_auto()
        elif action == 'stop':
            stop_auto()
        else:
            return jsonify({'success': False, 'error': 'action must be start or stop'})
        
        return jsonify({'success': True, 'running': auto_running})
    except Exception as e:
        logger.error(f"Auto route error: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    logger.info("Starting E-Paper Display Web Interface...")
    logger.info("Access at http://raspberrypi.local:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
