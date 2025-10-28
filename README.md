# E-Paper Display Web Interface

A modern, responsive web interface for controlling Waveshare 2.13" V4 E-Paper displays. Features image upload with visual editing, weather dashboard, and comprehensive display controls.

## Features

### 🖼️ Image Management
- **Visual Image Editor**: Interactive drag, zoom, and crop functionality
- **Multiple Format Support**: JPG, PNG, GIF, BMP
- **Real-time Preview**: See exactly how your image will look on the display
- **Smart Processing**: Automatic black & white conversion optimized for e-ink

### 🌤️ Weather Dashboard
- **Live Weather Data**: Real-time weather information from Open-Meteo API
- **Customizable Display**: Choose what information to show (temperature, humidity, wind, sunrise/sunset)
- **Multiple Cities**: Support for any city worldwide
- **Auto-update**: Configurable refresh intervals

### 🔄 Display Controls
- **Orientation Control**: 0°, 90°, 180°, 270° rotation
- **Flip Options**: Horizontal and vertical mirroring
- **Display Management**: Clear, refresh, and preview functions
- **Settings Persistence**: All settings saved automatically

### 🎨 Modern UI
- **Mobile-First Design**: Optimized for phones and tablets
- **Dark Theme**: Easy on the eyes with beautiful gradients
- **Tabbed Interface**: Organized, intuitive navigation
- **Real-time Feedback**: Status messages and progress indicators

## Installation

### Prerequisites
- Python 3.8 or higher
- Raspberry Pi (recommended) or Linux system
- Waveshare 2.13" V4 E-Paper display (optional - runs in demo mode without hardware)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd epaper-display
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (optional)
   ```bash
   cp env.example .env
   # Edit .env with your preferred settings
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the web interface**
   Open your browser to `http://localhost:5000` (or your Pi's IP address)

### Hardware Setup

For Raspberry Pi with Waveshare display:

1. **Install Waveshare library**
   ```bash
   git clone https://github.com/waveshare/e-Paper.git
   cd e-Paper/RaspberryPi_JetsonNano/python
   sudo python3 setup.py install
   ```

2. **Enable SPI** (if not already enabled)
   ```bash
   sudo raspi-config
   # Navigate to Interfacing Options > SPI > Enable
   ```

3. **Set environment variable**
   ```bash
   export EPAPER_LIB_PATH=/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib
   ```

## Configuration

### Environment Variables

The application can be configured using environment variables. Copy `env.example` to `.env` and modify as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `EPAPER_WIDTH` | 250 | Display width in pixels |
| `EPAPER_HEIGHT` | 122 | Display height in pixels |
| `EPAPER_HOST` | 0.0.0.0 | Web server host |
| `EPAPER_PORT` | 5000 | Web server port |
| `EPAPER_DEBUG` | false | Enable debug mode |
| `EPAPER_LOG_LEVEL` | INFO | Logging level |
| `EPAPER_DEFAULT_CITY` | San Francisco | Default weather city |
| `EPAPER_DEFAULT_UNITS` | c | Temperature units (c/f) |
| `EPAPER_DEFAULT_INTERVAL` | 300 | Auto-refresh interval (seconds) |

### Settings File

User settings are automatically saved to `/tmp/epaper_settings.json` and include:
- Display mode (image/dashboard)
- Weather city and units
- Display options (humidity, wind, sun times)
- Rotation and flip settings
- Auto-update preferences

## API Reference

### Endpoints

#### `GET /`
Main web interface

#### `POST /upload`
Upload and display an image
- **Parameters**: `image` (file), `scale`, `crop_x`, `crop_y`, `crop_w`, `crop_h`
- **Returns**: JSON with success status and rotation

#### `POST /clear`
Clear the display
- **Returns**: JSON with success status

#### `POST /refresh`
Refresh display with current image
- **Returns**: JSON with success status

#### `POST /rotate`
Rotate display
- **Parameters**: `degrees` (JSON)
- **Returns**: JSON with success status and new rotation

#### `GET /settings`
Get current settings
- **Returns**: JSON with all settings

#### `POST /settings`
Update settings
- **Parameters**: Settings object (JSON)
- **Returns**: JSON with success status and updated settings

#### `POST /render_dashboard`
Render and display weather dashboard
- **Returns**: JSON with success status

#### `GET /preview`
Get current preview image
- **Returns**: BMP image file

#### `POST /auto`
Control auto-update functionality
- **Parameters**: `action` (start/stop)
- **Returns**: JSON with success status and running state

## Architecture

### Modular Design

The application is built with a clean, modular architecture:

- **`app.py`**: Main Flask application and route handlers
- **`config.py`**: Configuration management with environment variables
- **`display_manager.py`**: E-Paper display operations and image processing
- **`weather_service.py`**: Weather data fetching and processing
- **`dashboard_renderer.py`**: Weather dashboard layout and rendering
- **`utils/logger.py`**: Logging utilities and error handling
- **`utils/validators.py`**: Input validation and sanitization

### Key Features

- **Error Handling**: Comprehensive error handling with detailed logging
- **Input Validation**: All inputs validated and sanitized
- **Configuration Management**: Environment-based configuration
- **Modular Design**: Clean separation of concerns
- **Type Hints**: Full type annotation for better code quality

## Development

### Running in Development Mode

```bash
export EPAPER_DEBUG=true
export EPAPER_LOG_LEVEL=DEBUG
python app.py
```

### Code Style

The project follows Python best practices:
- Type hints throughout
- Comprehensive error handling
- Modular architecture
- Clear documentation
- Consistent naming conventions

### Testing

```bash
# Run tests (when implemented)
python -m pytest tests/
```

## Troubleshooting

### Common Issues

1. **Display not working**
   - Check SPI is enabled on Raspberry Pi
   - Verify Waveshare library installation
   - Check wiring connections

2. **Weather data not loading**
   - Check internet connection
   - Verify city name is correct
   - Check API timeout settings

3. **Images not displaying**
   - Verify image format is supported
   - Check file size limits
   - Ensure image dimensions are reasonable

### Logs

Check the log file for detailed error information:
```bash
tail -f /tmp/epaper_display.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Open an issue on GitHub

## Changelog

### Version 2.0.0
- Complete rewrite with modular architecture
- Enhanced error handling and logging
- Environment-based configuration
- Improved input validation
- Better mobile UI
- Comprehensive documentation

### Version 1.0.0
- Initial release
- Basic image upload and display
- Weather dashboard
- Orientation controls
