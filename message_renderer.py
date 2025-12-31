#!/usr/bin/env python3
"""
Message Board Renderer
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
from config import Config
import logging

logger = logging.getLogger(__name__)

class MessageRenderer:
    def __init__(self):
        self.fonts = self._load_fonts()
        
    def _load_fonts(self):
        fonts = {}
        defaults = [
            Config.FONT_PATHS[0],
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf'
        ]
        
        path = None
        for p in defaults:
            try:
                if (import_os := __import__('os')).path.exists(p):
                    path = p
                    break
            except: continue
            
        if path:
            fonts['small'] = ImageFont.truetype(path, 16)
            fonts['medium'] = ImageFont.truetype(path, 20)
            fonts['large'] = ImageFont.truetype(path, 32)
        else:
            default = ImageFont.load_default()
            fonts = {'small': default, 'medium': default, 'large': default}
        return fonts

    def render_message(self, message: str, settings: dict):
        """Render a custom message"""
        img = Image.new('1', (Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT), 1)
        draw = ImageDraw.Draw(img)
        
        # Get settings
        font_size = settings.get('font_size', 'medium') # small, medium, large
        font = self.fonts.get(font_size, self.fonts['medium'])
        
        # Wrap text
        # Approx chars per line logic
        char_width = 12 if font_size == 'medium' else (18 if font_size == 'large' else 10)
        cols = Config.DISPLAY_WIDTH // char_width
        
        lines = textwrap.wrap(message, width=cols)
        
        # Calculate total height to center vertically
        # Valid property for PIL >= 9.2.0 is font.getbbox or draw.textbbox
        # Fallback to getsize if needed
        line_heights = []
        try:
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_heights.append(bbox[3] - bbox[1] + 4) # + padding
        except:
             # Fallback for old PIL
             line_heights = [24] * len(lines)

        total_h = sum(line_heights)
        start_y = (Config.DISPLAY_HEIGHT - total_h) // 2
        
        y = start_y
        for line in lines:
            # Center horizontally
            try:
                 bbox = draw.textbbox((0, 0), line, font=font)
                 w = bbox[2] - bbox[0]
            except:
                 w = len(line) * char_width

            x = (Config.DISPLAY_WIDTH - w) // 2
            draw.text((x, y), line, font=font, fill=0)
            y += line_heights[lines.index(line)]
            
        # Add border
        draw.rectangle((0, 0, Config.DISPLAY_WIDTH-1, Config.DISPLAY_HEIGHT-1), outline=0)
        
        return img
