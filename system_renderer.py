#!/usr/bin/env python3
"""
System Monitor Renderer (Pwn-Style)
"""

import psutil
import time
import socket
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import Config
import logging

logger = logging.getLogger(__name__)

class SystemRenderer:
    def __init__(self):
        self.fonts = self._load_fonts()
        self.start_time = time.time()
        
    def _load_fonts(self):
        fonts = {}
        # Try to find a monospace font for terminal look
        mono_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
            '/usr/share/fonts/truetype/freefont/FreeMono.ttf',
            Config.FONT_PATHS[0] # Fallback
        ]
        
        for path in mono_paths:
            try:
                if (import_os := __import__('os')).path.exists(path):
                    fonts['main'] = ImageFont.truetype(path, 12)
                    fonts['header'] = ImageFont.truetype(path, 14)
                    fonts['big'] = ImageFont.truetype(path, 20)
                    return fonts
            except: continue
            
        default = ImageFont.load_default()
        return {'main': default, 'header': default, 'big': default}

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_uptime(self):
        uptime = time.time() - psutil.boot_time()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{hours}h {minutes}m"

    def get_face(self, cpu_percent):
        if cpu_percent > 80:
            return "(>_<)", "High Load"
        elif cpu_percent > 50:
            return "(o_o)", "Working"
        else:
            return "(^-^)", "Online"

    def render_system(self, settings):
        """Render system stats Pwnagotchi style"""
        img = Image.new('1', (Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT), 1)
        draw = ImageDraw.Draw(img)
        
        # Stats
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        ip = self.get_ip()
        uptime = self.get_uptime()
        
        # Layout
        margin = 6
        line_h = 16
        
        # Header bar
        draw.rectangle((0, 0, Config.DISPLAY_WIDTH, 18), fill=0)
        draw.text((margin, 2), f"SYSTEM MON // {ip}", font=self.fonts['header'], fill=1)
        
        # Stats Column (Left)
        y = 24
        draw.text((margin, y), f"CPU: {cpu}%", font=self.fonts['main'], fill=0)
        y += line_h
        draw.text((margin, y), f"RAM: {ram.percent}%", font=self.fonts['main'], fill=0)
        y += line_h
        draw.text((margin, y), f"DSK: {disk.percent}%", font=self.fonts['main'], fill=0)
        y += line_h
        draw.text((margin, y), f"UP:  {uptime}", font=self.fonts['main'], fill=0)
        
        # Face Column (Right)
        # Draw a box for the face
        face_str, status = self.get_face(cpu)
        
        face_x = 140
        face_y = 35
        
        # Face text
        draw.text((face_x, face_y), face_str, font=self.fonts['big'], fill=0)
        
        # Status text below face
        status_w = draw.textlength(status, font=self.fonts['main'])
        draw.text((face_x + 10, face_y + 30), status, font=self.fonts['main'], fill=0)
        
        # Decorative bracket
        draw.line((130, 24, 130, 100), fill=0)
        draw.line((130, 24, 135, 24), fill=0)
        draw.line((130, 100, 135, 100), fill=0)

        # Footer
        dt_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.line((0, 110, Config.DISPLAY_WIDTH, 110), fill=0)
        draw.text((margin, 110), dt_str, font=self.fonts['main'], fill=0)
        
        return img
