#!/usr/bin/env python3
"""
Production setup and run script for Portfolio Optimizer Pro.
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """Setup basic logging for setup script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8 or higher is required")

def install_dependencies():
    """Install required dependencies."""
    logger = logging.getLogger(__name__)
    
    requirements_file = Path(__file__).parent / "requirements_production.txt"
    
    if not requirements_file.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_file}")
    
    logger.info("Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        logger.info("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        raise

def setup_environment():
    """Setup environment variables and configuration."""
    logger = logging.getLogger(__name__)
    
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        logger.info("Creating default .env file...")
        
        default_env = """# Portfolio Application Configuration
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DB_PATH=portfolio.db
DB_TIMEOUT=30

# Data Configuration
DEFAULT_PERIOD=5y
CACHE_TIMEOUT=300
MAX_RETRIES=3
RETRY_DELAY=1.0
REQUEST_TIMEOUT=30

# Strategy Configuration
MIN_WEIGHT=0.05
MAX_WEIGHT=0.4
BOLLINGER_WINDOW=20
BOLLINGER_STD=2.0
ML_LOOKBACK_DAYS=252

# Optional: API Keys (uncomment and set if needed)
# OPENAI_API_KEY=your_openai_key_here
# IB_HOST=127.0.0.1
# IB_PORT=7497
"""
        
        with open(env_file, 'w') as f:
            f.write(default_env)
        
        logger.info(f"Created {env_file}")
        logger.info("Please review and update the .env file with your settings")
    else:
        logger.info(f"Environment file already exists: {env_file}")

def run_tests():
    """Run the test suite."""
    logger = logging.getLogger(__name__)
    
    logger.info("Running test suite...")
    
    try:
        # Run our custom test suite
        result = subprocess.run([
            sys.executable, "test_production.py"
        ], check=False, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode == 0:
            logger.info("All tests passed!")
            return True
        else:
            logger.error("Some tests failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        return False

def run_application():
    """Run the Streamlit application."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Portfolio Optimizer Pro...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "main.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start application: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("Application stopped by user")

def main():
    """Main setup and run function."""
    logger = setup_logging()
    
    try:
        logger.info("Setting up Portfolio Optimizer Pro...")
        
        # Check Python version
        check_python_version()
        logger.info(f"Python version: {sys.version}")
        
        # Install dependencies
        install_dependencies()
        
        # Setup environment
        setup_environment()
        
        # Ask user what to do
        print("\nSetup complete! What would you like to do?")
        print("1. Run tests")
        print("2. Start application")
        print("3. Run tests then start application")
        print("4. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                run_tests()
                break
            elif choice == "2":
                run_application()
                break
            elif choice == "3":
                if run_tests():
                    print("\nTests passed! Starting application...")
                    run_application()
                else:
                    print("\nTests failed! Please fix issues before running the application.")
                break
            elif choice == "4":
                logger.info("Exiting...")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()