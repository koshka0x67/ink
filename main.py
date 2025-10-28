#!/usr/bin/env python3
"""
E-Paper Display Web Interface for Waveshare 2.13" V4
Enhanced mobile-first UI with tabbed interface and orientation controls
"""

from flask import Flask, render_template, render_template_string, request, jsonify, send_file
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io
import os
import sys
import json
import threading
import time
import datetime as dt
import urllib.parse
import urllib.request

# Add Waveshare e-Paper library path
epd_path = '/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib'
if os.path.exists(epd_path):
    sys.path.append(epd_path)

try:
    from waveshare_epd import epd2in13_V4
    EPD_AVAILABLE = True
except ImportError:
    print("Warning: Waveshare library not found. Running in demo mode.")
    EPD_AVAILABLE = False

app = Flask(__name__)

# Display dimensions
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122

# Store current image path
CURRENT_IMAGE = '/tmp/current_epaper.bmp'
CURRENT_IMAGE_BASE = '/tmp/current_epaper_base.bmp'
EPD_INSTANCE = None
ROTATION_DEGREES = 90  # Default start orientation

# Dashboard state and settings
SETTINGS_PATH = '/tmp/epaper_settings.json'
LAST_DASHBOARD_PREVIEW = '/tmp/dashboard_preview.bmp'

DEFAULT_SETTINGS = {
    'mode': 'image',
    'city': 'San Francisco',
    'units': 'c',
    'interval': 300,
    'show_humidity': True,
    'show_wind': True,
    'show_sun': True,
    'rotation': 90,
    'flip_h': False,
    'flip_v': False
}

SETTINGS = DEFAULT_SETTINGS.copy()
AUTO_THREAD = None
AUTO_RUNNING = False

def init_display():
    """Initialize the e-Paper display"""
    if not EPD_AVAILABLE:
        return None
    try:
        global EPD_INSTANCE
        if EPD_INSTANCE is None:
            epd = epd2in13_V4.EPD()
            epd.init()
            epd.Clear(0xFF)
            print(f"EPD initialized. width={epd.width}, height={epd.height}")
            EPD_INSTANCE = epd
        return EPD_INSTANCE
    except Exception as e:
        print(f"Error initializing display: {e}")
        return None

def process_image(image_file, scale=1.0, crop_x=0, crop_y=0, crop_w=None, crop_h=None):
    """Convert and resize image for e-Paper display with optional scaling and cropping"""
    img = Image.open(image_file)
    img = img.convert('RGB')
    
    # Apply scaling
    if scale != 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Set default crop dimensions if not provided
    if crop_w is None:
        crop_w = DISPLAY_WIDTH
    if crop_h is None:
        crop_h = DISPLAY_HEIGHT
    
    # Apply cropping
    if crop_x > 0 or crop_y > 0 or crop_w < img.width or crop_h < img.height:
        # Ensure crop coordinates are within image bounds
        crop_x = max(0, min(crop_x, img.width - 1))
        crop_y = max(0, min(crop_y, img.height - 1))
        crop_w = min(crop_w, img.width - crop_x)
        crop_h = min(crop_h, img.height - crop_y)
        
        img = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
    
    # Create final image with proper dimensions
    new_img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), 'white')
    
    # Center the processed image
    x = (DISPLAY_WIDTH - img.width) // 2
    y = (DISPLAY_HEIGHT - img.height) // 2
    new_img.paste(img, (x, y))
    
    # Convert to black and white
    gray_img = new_img.convert('L')
    bw_img = gray_img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    bw_img.save('/tmp/debug_processed.bmp')
    bw_img.save(CURRENT_IMAGE_BASE)
    return bw_img

def display_image(epd, img):
    """Display image on e-Paper"""
    global ROTATION_DEGREES
    # Build transformed image for both preview and device
    transformed = img.rotate(ROTATION_DEGREES, expand=True) if ROTATION_DEGREES % 360 != 0 else img
    try:
        if SETTINGS.get('flip_h'):
            transformed = ImageOps.mirror(transformed)
        if SETTINGS.get('flip_v'):
            transformed = ImageOps.flip(transformed)
    except Exception:
        pass

    if not EPD_AVAILABLE or epd is None:
        print("Display not available - saving image only")
        transformed.save(CURRENT_IMAGE)
        img.save(CURRENT_IMAGE_BASE)
        return True
    
    try:
        base_img = transformed
        target_size = (getattr(epd, 'width', DISPLAY_WIDTH), getattr(epd, 'height', DISPLAY_HEIGHT))

        if base_img.size != target_size:
            candidate_imgs = [base_img, base_img.rotate(90, expand=True), base_img.rotate(270, expand=True)]
        else:
            candidate_imgs = [base_img]

        displayed = False
        last_error = None
        for idx, candidate in enumerate(candidate_imgs):
            try:
                if candidate.size != target_size:
                    candidate = candidate.resize(target_size)
                buffer = epd.getbuffer(candidate)
                epd.display(buffer)
                candidate.save(CURRENT_IMAGE)
                img.save(CURRENT_IMAGE_BASE)
                displayed = True
                break
            except Exception as inner_e:
                last_error = inner_e

        if not displayed:
            if last_error:
                raise last_error
            raise RuntimeError("Failed to display image")
        return True
    except Exception as e:
        print(f"Error displaying image: {e}")
        return False

# Dashboard helpers
def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "EpaperDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

def _geocode_city(city: str):
    qs = urllib.parse.urlencode({"name": city, "count": 1})
    data = _http_get_json(f"https://geocoding-api.open-meteo.com/v1/search?{qs}")
    results = data.get('results') or []
    if not results:
        return None
    r0 = results[0]
    lat, lon = float(r0['latitude']), float(r0['longitude'])
    name = str(r0.get('name') or city)
    admin1, country = r0.get('admin1'), r0.get('country')
    display = ", ".join([x for x in [name, admin1, country] if x])
    return lat, lon, display

def _fetch_weather(lat: float, lon: float) -> dict:
    qs = urllib.parse.urlencode({
        'latitude': lat, 'longitude': lon,
        'current': ','.join(['temperature_2m','relative_humidity_2m','wind_speed_10m','weather_code']),
        'daily': ','.join(['sunrise','sunset']),
        'timezone': 'auto'
    })
    return _http_get_json(f"https://api.open-meteo.com/v1/forecast?{qs}")

def _wmo_text(code: int) -> str:
    mapping = {0:'Clear',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',
               51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',
               71:'Light snow',73:'Snow',75:'Heavy snow',80:'Rain showers',95:'Thunder'}
    return mapping.get(int(code), '')

def _load_font(size: int):
    candidates = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                  '/usr/share/fonts/truetype/freefont/FreeSans.ttf']
    for p in candidates:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

FONT_LARGE = _load_font(28)
FONT_MED = _load_font(14)
FONT_SMALL = _load_font(12)

def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    try:
        l,t,r,b = draw.textbbox((0,0), text, font=font)
        return r-l, b-t
    except:
        return (0,0)

def _ellipsis_to_fit(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """Truncate with ellipsis to fit max_width."""
    w, _ = _measure(draw, text, font)
    if w <= max_width:
        return text
    ell = '…'
    base = text
    # Quick binary-like reduction
    lo, hi = 0, len(base)
    best = ''
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = base[:mid] + ell
        cw, _ = _measure(draw, candidate, font)
        if cw <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best or ell

def _choose_temp_font(draw: ImageDraw.ImageDraw, temp_text: str):
    """Choose a font for temperature so it fits left column without overlap."""
    # Try large → medium → small
    for f in (FONT_LARGE, _load_font(24), _load_font(20)):
        w, _ = _measure(draw, temp_text, f)
        if w <= 120:  # left column width budget
            return f
    return _load_font(18)

def render_dashboard_image(settings: dict) -> Image.Image:
    city = settings.get('city') or 'San Francisco'
    coords = _geocode_city(city)
    if not coords:
        img = Image.new('1', (DISPLAY_WIDTH, DISPLAY_HEIGHT), 1)
        d = ImageDraw.Draw(img)
        d.text((8, 8), 'City not found', font=FONT_MED, fill=0)
        return img
    
    lat, lon, city_disp = coords
    weather = _fetch_weather(lat, lon)
    img = Image.new('1', (DISPLAY_WIDTH, DISPLAY_HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    
    now = dt.datetime.now()
    time_str = now.strftime('%I:%M %p').lstrip('0')
    date_str = now.strftime('%a %b %d')
    
    current = weather.get('current') or {}
    daily = weather.get('daily') or {}
    temp_c = current.get('temperature_2m')
    humidity = current.get('relative_humidity_2m')
    wind_kmh = current.get('wind_speed_10m')
    wcode = current.get('weather_code')
    sunrise = (daily.get('sunrise') or [None])[0]
    sunset = (daily.get('sunset') or [None])[0]
    
    units_f = (settings.get('units','c').lower() == 'f')
    temp_disp = '--'
    if isinstance(temp_c, (int,float)):
        if units_f:
            temp_disp = f"{(temp_c*9/5)+32:.0f}°F"
        else:
            temp_disp = f"{float(temp_c):.0f}°C"
    
    # Layout constraints to avoid overlap
    margin = 8
    header_y = 4
    subheader_y = 40
    divider_y = 58
    left_x = 10
    right_margin = 10
    left_col_max_w = 130

    # Header
    draw.text((margin, header_y), time_str, font=FONT_LARGE, fill=0)

    # Subheader with truncation for city
    city_text = _ellipsis_to_fit(draw, city_disp, FONT_MED, max_width=DISPLAY_WIDTH - 2*margin - 70)
    draw.text((left_x, subheader_y), date_str, font=FONT_MED, fill=0)
    w_city, _ = _measure(draw, city_text, FONT_MED)
    draw.text((DISPLAY_WIDTH - w_city - margin, subheader_y), city_text, font=FONT_MED, fill=0)
    draw.line((margin, divider_y, DISPLAY_WIDTH - margin, divider_y), fill=0)

    # Left column temperature with dynamic font, and condition truncated
    temp_font = _choose_temp_font(draw, temp_disp)
    draw.text((left_x, divider_y + 8), temp_disp, font=temp_font, fill=0)
    cond_text = _ellipsis_to_fit(draw, _wmo_text(wcode or 0), FONT_SMALL, max_width=left_col_max_w)
    draw.text((left_x, DISPLAY_HEIGHT - 20), cond_text, font=FONT_SMALL, fill=0)

    # Right column, truncated
    lines = []
    if settings.get('show_humidity') and isinstance(humidity,(int,float)):
        lines.append(f"Hum {humidity:.0f}%")
    if settings.get('show_wind') and isinstance(wind_kmh,(int,float)):
        lines.append(f"Wind {wind_kmh:.0f} km/h")
    if settings.get('show_sun'):
        def fmt(iso):
            if not iso: return None
            try:
                return dt.datetime.fromisoformat(str(iso)).strftime('%H:%M')
            except:
                return None
        sr, ss = fmt(sunrise), fmt(sunset)
        if sr: lines.append(f"↑ {sr}")
        if ss: lines.append(f"↓ {ss}")
    
    y = divider_y + 8
    right_col_xmax = DISPLAY_WIDTH - right_margin
    right_col_min_x = left_x + left_col_max_w + 6
    for ln in lines:
        avail = max(10, right_col_xmax - right_col_min_x)
        txt = _ellipsis_to_fit(draw, ln, FONT_MED, max_width=avail)
        w,h = _measure(draw, txt, FONT_MED)
        draw.text((right_col_xmax - w, y), txt, font=FONT_MED, fill=0)
        y += h + 2

    # Apply orientation after rendering to keep text direction correct
    output = img
    rot = settings.get('rotation', 0)
    if rot % 360 != 0:
        output = output.rotate(rot, expand=True)
    if settings.get('flip_h'):
        output = ImageOps.mirror(output)
    if settings.get('flip_v'):
        output = ImageOps.flip(output)
    return output

def save_preview(img: Image.Image):
    try:
        img.save(LAST_DASHBOARD_PREVIEW)
    except Exception as e:
        print(f"Preview save failed: {e}")

def apply_settings(new_data: dict):
    global SETTINGS, ROTATION_DEGREES
    SETTINGS.update({
        'mode': new_data.get('mode', SETTINGS['mode']),
        'city': new_data.get('city', SETTINGS['city']),
        'units': new_data.get('units', SETTINGS['units']),
        'interval': int(new_data.get('interval', SETTINGS['interval'])),
        'show_humidity': bool(new_data.get('show_humidity', SETTINGS['show_humidity'])),
        'show_wind': bool(new_data.get('show_wind', SETTINGS['show_wind'])),
        'show_sun': bool(new_data.get('show_sun', SETTINGS['show_sun'])),
        'rotation': int(new_data.get('rotation', SETTINGS.get('rotation', 0))),
        'flip_h': bool(new_data.get('flip_h', SETTINGS.get('flip_h', False))),
        'flip_v': bool(new_data.get('flip_v', SETTINGS.get('flip_v', False)))
    })
    ROTATION_DEGREES = SETTINGS.get('rotation', 0)
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(SETTINGS, f)
    except:
        pass

def load_settings():
    global SETTINGS, ROTATION_DEGREES
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r') as f:
                data = json.load(f)
                SETTINGS.update(data)
                ROTATION_DEGREES = SETTINGS.get('rotation', 0)
        except:
            pass

def auto_loop():
    global AUTO_RUNNING
    while AUTO_RUNNING:
        try:
            if SETTINGS.get('mode') == 'dashboard':
                epd = init_display()
                frame = render_dashboard_image(SETTINGS)
                save_preview(frame)
                display_image(epd, frame)
                print("[AUTO] Dashboard frame displayed")
        except Exception as e:
            print(f"[AUTO] error: {e}")
        delay = max(30, int(SETTINGS.get('interval', 300)))
        for _ in range(delay):
            if not AUTO_RUNNING:
                break
            time.sleep(1)

def start_auto():
    global AUTO_THREAD, AUTO_RUNNING
    if AUTO_RUNNING:
        return
    AUTO_RUNNING = True
    AUTO_THREAD = threading.Thread(target=auto_loop, daemon=True)
    AUTO_THREAD.start()

def stop_auto():
    global AUTO_RUNNING
    AUTO_RUNNING = False

HTML_TEMPLATE = """<!DOCTYPE html><html><body>Template missing. Please ensure templates/index.html exists.</body></html>"""

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception:
        # Fallback to inline template if external template missing
        return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image selected'})
    
    try:
        print(f"\n=== Processing upload: {file.filename} ===")
        
        # Get resize/crop parameters
        scale = float(request.form.get('scale', 1.0))
        crop_x = int(request.form.get('crop_x', 0))
        crop_y = int(request.form.get('crop_y', 0))
        crop_w = int(request.form.get('crop_w', DISPLAY_WIDTH))
        crop_h = int(request.form.get('crop_h', DISPLAY_HEIGHT))
        
        img = process_image(file, scale=scale, crop_x=crop_x, crop_y=crop_y, crop_w=crop_w, crop_h=crop_h)
        epd = init_display()
        success = display_image(epd, img)
        
        if success:
            return jsonify({'success': True, 'rotation': ROTATION_DEGREES})
        else:
            return jsonify({'success': False, 'error': 'Failed to display image'})
    
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear', methods=['POST'])
def clear():
    if not EPD_AVAILABLE:
        return jsonify({'success': True})
    
    try:
        epd = init_display()
        epd.Clear(0xFF)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Clear error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/refresh', methods=['POST'])
def refresh():
    try:
        source_path = CURRENT_IMAGE_BASE if os.path.exists(CURRENT_IMAGE_BASE) else CURRENT_IMAGE
        if not os.path.exists(source_path):
            return jsonify({'success': False, 'error': 'No image to refresh'})

        img = Image.open(source_path)
        if img.mode != '1':
            img = img.convert('1')

        epd = init_display()
        success = display_image(epd, img)
        return jsonify({'success': bool(success)})
    except Exception as e:
        print(f"Refresh error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rotate', methods=['POST'])
def rotate():
    try:
        data = request.get_json(silent=True) or {}
        deg = int(data.get('degrees', 0))

        global ROTATION_DEGREES
        ROTATION_DEGREES = (ROTATION_DEGREES + deg) % 360

        # Update settings with new rotation
        SETTINGS['rotation'] = ROTATION_DEGREES
        try:
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(SETTINGS, f)
        except:
            pass

        # Auto-refresh on rotate: re-display last image/dashboard and refresh preview
        try:
            if SETTINGS.get('mode') == 'dashboard':
                img = render_dashboard_image(SETTINGS)
            else:
                source_path = CURRENT_IMAGE_BASE if os.path.exists(CURRENT_IMAGE_BASE) else CURRENT_IMAGE
                img = Image.open(source_path) if os.path.exists(source_path) else None
                if img and img.mode != '1':
                    img = img.convert('1')
            if img is not None:
                save_preview(img)
                epd = init_display()
                display_image(epd, img)
        except Exception as _e:
            pass

        return jsonify({'success': True, 'rotation': ROTATION_DEGREES})
    except Exception as e:
        print(f"Rotate error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings', methods=['GET', 'POST'])
def settings_route():
    if request.method == 'GET':
        load_settings()
        return jsonify(SETTINGS)
    try:
        data = request.get_json(silent=True) or {}
        apply_settings(data)
        # Auto-refresh on settings changes
        try:
            if SETTINGS.get('mode') == 'dashboard':
                img = render_dashboard_image(SETTINGS)
            else:
                source_path = CURRENT_IMAGE_BASE if os.path.exists(CURRENT_IMAGE_BASE) else CURRENT_IMAGE
                img = Image.open(source_path) if os.path.exists(source_path) else None
                if img and img.mode != '1':
                    img = img.convert('1')
            if img is not None:
                save_preview(img)
                epd = init_display()
                display_image(epd, img)
        except Exception:
            pass
        return jsonify({'success': True, 'settings': SETTINGS})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/render_dashboard', methods=['POST'])
def render_dashboard_route():
    try:
        img = render_dashboard_image(SETTINGS)
        save_preview(img)
        epd = init_display()
        ok = display_image(epd, img)
        return jsonify({'success': bool(ok)})
    except Exception as e:
        print(f"Render error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview')
def preview_route():
    try:
        # Always serve the latest transformed image for accurate preview
        source_path = None
        if SETTINGS.get('mode') == 'dashboard' and os.path.exists(LAST_DASHBOARD_PREVIEW):
            source_path = LAST_DASHBOARD_PREVIEW
        elif os.path.exists(CURRENT_IMAGE):
            source_path = CURRENT_IMAGE
        elif os.path.exists(CURRENT_IMAGE_BASE):
            source_path = CURRENT_IMAGE_BASE
        if not source_path:
            return jsonify({'success': False, 'error': 'No preview available'})
        return send_file(source_path, mimetype='image/bmp')
    except Exception as e:
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
        crop_w = int(request.form.get('crop_w', DISPLAY_WIDTH))
        crop_h = int(request.form.get('crop_h', DISPLAY_HEIGHT))
        
        # Process image for preview
        img = process_image(file, scale=scale, crop_x=crop_x, crop_y=crop_y, crop_w=crop_w, crop_h=crop_h)
        
        # Save preview
        preview_path = '/tmp/resize_preview.bmp'
        img.save(preview_path)
        
        return jsonify({'success': True, 'preview_url': '/preview_resize_image'})
        
    except Exception as e:
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
        return f"Preview error: {e}", 500

@app.route('/auto', methods=['POST'])
def auto_route():
    try:
        data = request.get_json(silent=True) or {}
        action = (data.get('action') or '').lower()
        if action == 'start':
            start_auto()
        elif action == 'stop':
            stop_auto()
        else:
            return jsonify({'success': False, 'error': 'action must be start or stop'})
        return jsonify({'success': True, 'running': AUTO_RUNNING})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("Starting E-Paper Display Web Interface...")
    print("Access at http://raspberrypi.local:5000")
    load_settings()
    app.run(host='0.0.0.0', port=5000, debug=False)
