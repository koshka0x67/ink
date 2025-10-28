#!/usr/bin/env python3
"""
Display management for E-Paper Display Web Interface
"""

import os
import sys
from typing import Optional, Tuple
from PIL import Image, ImageOps, ImageDraw, ImageFont
import logging

from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisplayManager:
    """Manages E-Paper display operations"""
    
    def __init__(self):
        self.epd_instance = None
        self.rotation_degrees = 90
        self._init_epd_library()
    
    def _init_epd_library(self) -> bool:
        """Initialize the E-Paper library"""
        if not Config.is_epd_available():
            logger.warning("Waveshare library not found. Running in demo mode.")
            return False
        
        try:
            sys.path.append(Config.get_epd_path())
            from waveshare_epd import epd2in13_V4
            self.epd_class = epd2in13_V4.EPD
            return True
        except ImportError as e:
            logger.warning(f"Could not import Waveshare library: {e}")
            return False
    
    def init_display(self) -> Optional[object]:
        """Initialize the e-Paper display"""
        if not hasattr(self, 'epd_class'):
            logger.warning("E-Paper library not available")
            return None
        
        try:
            if self.epd_instance is None:
                epd = self.epd_class()
                epd.init()
                epd.Clear(0xFF)
                logger.info(f"EPD initialized. width={epd.width}, height={epd.height}")
                self.epd_instance = epd
            return self.epd_instance
        except Exception as e:
            logger.error(f"Error initializing display: {e}")
            return None
    
    def process_image(self, image_file, scale: float = 1.0, offset_x: float = 0, offset_y: float = 0,
                     crop_x: int = 0, crop_y: int = 0, crop_w: Optional[int] = None, 
                     crop_h: Optional[int] = None, rotation: int = 90) -> Image.Image:
        """Convert and resize image for e-Paper display with optional scaling, offset, cropping, and rotation"""
        try:
            img = Image.open(image_file)
            img = img.convert('RGB')
            
            # Apply rotation first
            if rotation != 0:
                img = img.rotate(rotation, expand=True)
            
            # Apply scaling
            if scale != 1.0:
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Set default crop dimensions if not provided
            if crop_w is None:
                crop_w = Config.DISPLAY_WIDTH
            if crop_h is None:
                crop_h = Config.DISPLAY_HEIGHT
            
            # Apply offset (move the image)
            if offset_x != 0 or offset_y != 0:
                # Create a larger canvas to accommodate the offset
                offset_canvas = Image.new('RGB', 
                    (img.width + abs(int(offset_x)), img.height + abs(int(offset_y))), 'white')
                offset_canvas.paste(img, (max(0, int(offset_x)), max(0, int(offset_y))))
                img = offset_canvas
            
            # Apply cropping
            if crop_x > 0 or crop_y > 0 or crop_w < img.width or crop_h < img.height:
                # Ensure crop coordinates are within image bounds
                crop_x = max(0, min(crop_x, img.width - 1))
                crop_y = max(0, min(crop_y, img.height - 1))
                crop_w = min(crop_w, img.width - crop_x)
                crop_h = min(crop_h, img.height - crop_y)
                
                img = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
            
            # Create final image with proper dimensions
            new_img = Image.new('RGB', (Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT), 'white')
            
            # Center the processed image
            x = (Config.DISPLAY_WIDTH - img.width) // 2
            y = (Config.DISPLAY_HEIGHT - img.height) // 2
            new_img.paste(img, (x, y))
            
            # Convert to black and white
            gray_img = new_img.convert('L')
            bw_img = gray_img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            # Save debug and base images
            bw_img.save('/tmp/debug_processed.bmp')
            bw_img.save(Config.CURRENT_IMAGE_BASE)
            
            return bw_img
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def display_image(self, img: Image.Image, settings: dict) -> bool:
        """Display image on e-Paper"""
        try:
            # Build transformed image for both preview and device
            transformed = img.rotate(settings.get('rotation', 0), expand=True) if settings.get('rotation', 0) % 360 != 0 else img
            
            # Apply flips
            if settings.get('flip_h'):
                transformed = ImageOps.mirror(transformed)
            if settings.get('flip_v'):
                transformed = ImageOps.flip(transformed)

            if not hasattr(self, 'epd_class'):
                logger.info("Display not available - saving image only")
                transformed.save(Config.CURRENT_IMAGE)
                img.save(Config.CURRENT_IMAGE_BASE)
                return True
            
            epd = self.init_display()
            if epd is None:
                logger.warning("Could not initialize display")
                return False
            
            try:
                base_img = transformed
                target_size = (getattr(epd, 'width', Config.DISPLAY_WIDTH), 
                             getattr(epd, 'height', Config.DISPLAY_HEIGHT))

                if base_img.size != target_size:
                    candidate_imgs = [base_img, base_img.rotate(90, expand=True), base_img.rotate(270, expand=True)]
                else:
                    candidate_imgs = [base_img]

                displayed = False
                last_error = None
                for candidate in candidate_imgs:
                    try:
                        if candidate.size != target_size:
                            candidate = candidate.resize(target_size)
                        buffer = epd.getbuffer(candidate)
                        epd.display(buffer)
                        candidate.save(Config.CURRENT_IMAGE)
                        img.save(Config.CURRENT_IMAGE_BASE)
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
                logger.error(f"Error displaying image: {e}")
                return False
        except Exception as e:
            logger.error(f"Error in display_image: {e}")
            return False
    
    def clear_display(self) -> bool:
        """Clear the e-Paper display"""
        if not hasattr(self, 'epd_class'):
            logger.info("Display not available - cannot clear")
            return True
        
        try:
            epd = self.init_display()
            if epd is None:
                return False
            epd.Clear(0xFF)
            return True
        except Exception as e:
            logger.error(f"Error clearing display: {e}")
            return False
    
    def set_rotation(self, degrees: int):
        """Set the rotation degrees"""
        self.rotation_degrees = degrees % 360
    
    def get_rotation(self) -> int:
        """Get the current rotation degrees"""
        return self.rotation_degrees
