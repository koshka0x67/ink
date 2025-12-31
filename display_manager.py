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
    
    def process_image(self, image_file, scale: float = 1.0, 
                     offset_x: int = 0, offset_y: int = 0, 
                     rotation: float = 0,
                     # Legacy params kept for compatibility but ignored if new ones present
                     crop_x: int = 0, crop_y: int = 0, 
                     crop_w: Optional[int] = None, crop_h: Optional[int] = None) -> Image.Image:
        """
        Process image with Affine Transformation (Scale -> Rotate -> Translate)
        Matches the HTML5 Canvas logic in the frontend.
        """
        try:
            img = Image.open(image_file)
            img = img.convert('RGB')
            
            # 1. Scale
            if scale != 1.0:
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                # Prevent zero size
                new_w = max(1, new_w)
                new_h = max(1, new_h)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 2. Rotate (Content Rotation)
            # PIL rotates counter-clockwise, Canvas rotates clockwise. 
            # So we invert the angle. expand=True matches drawing full rotated image.
            if rotation != 0:
                img = img.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
            
            # 3. Create Canvas (Viewport)
            target_w = Config.DISPLAY_WIDTH
            target_h = Config.DISPLAY_HEIGHT
            canvas = Image.new('RGB', (target_w, target_h), 'black') # Fill black (off) or white? User interface is black bg.
            
            # Note: E-Paper usually treats White as "Empty/Background" and Black as "Ink".
            # If the user pans the image away, the background should be White (Clear) or Black?
            # Index.html css has background #1a1a1a (dark).
            # Let's use White as the "Canvas Color" so empty space is clean.
            canvas = Image.new('RGB', (target_w, target_h), 'white')
            
            # 4. Paste (Translate)
            # Center of canvas is (target_w/2, target_h/2)
            # User offset is (offset_x, offset_y) applied to the center.
            # Center of image should be at (target_w/2 + offset_x, target_h/2 + offset_y)
            
            center_x = target_w // 2 + offset_x
            center_y = target_h // 2 + offset_y
            
            paste_x = int(center_x - img.width / 2)
            paste_y = int(center_y - img.height / 2)
            
            # Paste with mask if transparent (though we converted to RGB above, 
            # if original was RGBA we might want to keep alpha for compositing? 
            # For now RGB is fine, assuming rectangular images).
            canvas.paste(img, (paste_x, paste_y))
            
            # 5. Convert to 1-bit Dithered
            gray_img = canvas.convert('L')
            bw_img = gray_img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            # Save debug
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

    def save_to_gallery(self, file_storage, filename: str) -> bool:
        """Save an uploaded file to the gallery"""
        try:
            if not os.path.exists(Config.GALLERY_PATH):
                os.makedirs(Config.GALLERY_PATH)
            
            # Secure filename (basic check)
            filename = os.path.basename(filename)
            file_path = os.path.join(Config.GALLERY_PATH, filename)
            
            # Save original
            file_storage.save(file_path)
            return True
        except Exception as e:
            logger.error(f"Error saving to gallery: {e}")
            return False

    def get_gallery_images(self) -> list:
        """Get list of images in gallery"""
        images = []
        if not os.path.exists(Config.GALLERY_PATH):
            return images
            
        try:
            for filename in os.listdir(Config.GALLERY_PATH):
                if any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS):
                    file_path = os.path.join(Config.GALLERY_PATH, filename)
                    stat = os.stat(file_path)
                    images.append({
                        'name': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
            # Sort by modified time (newest first)
            images.sort(key=lambda x: x['modified'], reverse=True)
            return images
        except Exception as e:
            logger.error(f"Error listing gallery: {e}")
            return []

    def delete_gallery_image(self, filename: str) -> bool:
        """Delete an image from the gallery"""
        try:
            file_path = os.path.join(Config.GALLERY_PATH, os.path.basename(filename))
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting from gallery: {e}")
            return False

    def get_gallery_image_path(self, filename: str) -> Optional[str]:
        """Get full path to a gallery image if it exists"""
        file_path = os.path.join(Config.GALLERY_PATH, os.path.basename(filename))
        if os.path.exists(file_path):
            return file_path
        return None
