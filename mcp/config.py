"""Configuration settings for the MCP server."""
import os
from typing import Optional


class APIConfig:
    """API endpoint and authentication configuration."""
    
    # Base URLs
    DRIVER_INFO_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/info"
    SEARCH_REQUEST_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/searchRequest/list"
    DUMMY_NOTIFICATION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/{}/sendDummyNotification"
    SUBSCRIPTION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/plan/{}/\"YATRI_SUBSCRIPTION\""
    OVERLAY_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/driver/{}/sendSms"
    
    # API Keys
    DRIVER_INFO_API_KEY = os.getenv("DRIVER_INFO_API_KEY", "add9b7b9-4a84-4abb-abf5-189469c7df3d")
    SEARCH_REQUEST_API_KEY = os.getenv("SEARCH_REQUEST_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
    DUMMY_NOTIFICATION_API_KEY = os.getenv("DUMMY_NOTIFICATION_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
    SUBSCRIPTION_API_KEY = os.getenv("SUBSCRIPTION_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
    OVERLAY_API_KEY = os.getenv("OVERLAY_API_URL_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
    
    # Constants
    CONTENT_TYPE_JSON = "application/json"


class ClickHouseConfig:
    """ClickHouse database configuration."""
    
    HOST = os.getenv("CLICKHOUSE_HOST", "10.6.155.14")
    USER = os.getenv("CLICKHOUSE_USER", "juspay_ro")
    PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "hARCGXR9lFsDMWhS")
    PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))


class AppConfig:
    """Application configuration."""
    
    TITLE = "Namma Yatri MCP Server"
    VERSION = "1.0.0"
    HOST = "0.0.0.0"
    PORT = 8000

