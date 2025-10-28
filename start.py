#!/usr/bin/env python3
"""
Startup script for E-Paper Display Web Interface
"""

import os
import sys
import argparse
from config import Config

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description='E-Paper Display Web Interface')
    parser.add_argument('--host', default=Config.HOST, help='Host to bind to')
    parser.add_argument('--port', type=int, default=Config.PORT, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', default=Config.DEBUG, help='Enable debug mode')
    parser.add_argument('--log-level', default=Config.LOG_LEVEL, help='Log level')
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['EPAPER_HOST'] = args.host
    os.environ['EPAPER_PORT'] = str(args.port)
    os.environ['EPAPER_DEBUG'] = str(args.debug).lower()
    os.environ['EPAPER_LOG_LEVEL'] = args.log_level
    
    # Import and run the app
    from app import app, logger
    
    logger.info(f"Starting E-Paper Display Web Interface on {args.host}:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    logger.info(f"Log level: {args.log_level}")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
