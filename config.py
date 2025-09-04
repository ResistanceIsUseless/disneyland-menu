import os
from datetime import datetime, timedelta

class Config:
    """Configuration settings for Disneyland Menu app"""
    
    # API Settings
    BASE_URL = os.environ.get('DISNEY_BASE_URL', 'https://disneyland.disney.go.com')
    
    # Date for API queries - uses current date by default
    API_DATE = os.environ.get('DISNEY_API_DATE', 
                              datetime.now().strftime('%Y-%m-%d'))
    
    # Cache Settings
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_HOURS = int(os.environ.get('CACHE_HOURS', '6'))
    CACHE_DIR = os.environ.get('CACHE_DIR', 'disney_responses')
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.environ.get('PORT', '5000'))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Logging Settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', None)
    
    # Request Settings
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
    
    # UI Settings
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', '100'))
    
    # Feature Flags
    ENABLE_REFRESH_BUTTON = os.environ.get('ENABLE_REFRESH_BUTTON', 'true').lower() == 'true'
    ENABLE_FAVORITES = os.environ.get('ENABLE_FAVORITES', 'false').lower() == 'true'
    ENABLE_DATE_SELECTOR = os.environ.get('ENABLE_DATE_SELECTOR', 'true').lower() == 'true'
    MAX_DAYS_AHEAD = int(os.environ.get('MAX_DAYS_AHEAD', '7'))  # How many days ahead user can view
    
    # User Agent for requests
    USER_AGENT = os.environ.get('USER_AGENT', 
                                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    @classmethod
    def get_headers(cls):
        """Get headers for API requests"""
        return {
            "Host": "disneyland.disney.go.com",
            "Accept": "application/json",
            "Accept-Language": "en_US",
            "Content-Type": "application/json",
            "Origin": cls.BASE_URL,
            "Referer": f"{cls.BASE_URL}/dining/",
            "User-Agent": cls.USER_AGENT,
            "Sec-Ch-Ua": '"Chromium";v="133", "Not(A:Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "macOS",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty"
        }
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        errors = []
        
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production' and not cls.DEBUG:
            errors.append("SECRET_KEY must be changed for production")
        
        if cls.CACHE_HOURS < 0:
            errors.append("CACHE_HOURS must be non-negative")
        
        if cls.REQUEST_TIMEOUT < 1:
            errors.append("REQUEST_TIMEOUT must be at least 1 second")
        
        if cls.MAX_RETRIES < 0:
            errors.append("MAX_RETRIES must be non-negative")
        
        if cls.ITEMS_PER_PAGE < 1:
            errors.append("ITEMS_PER_PAGE must be at least 1")
        
        return errors

class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    CACHE_HOURS = 1  # Shorter cache for development

class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    CACHE_HOURS = 12  # Longer cache for production
    
    @classmethod
    def validate(cls):
        errors = super().validate()
        
        # Additional production validations
        if not os.environ.get('SECRET_KEY'):
            errors.append("SECRET_KEY environment variable must be set in production")
        
        return errors

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig
    else:
        return DevelopmentConfig