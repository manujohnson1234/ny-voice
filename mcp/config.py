"""Configuration settings for the MCP server."""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class APIConfig:
    """API endpoint and authentication configuration."""
    
    # Base URLs
    DRIVER_INFO_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/info"
    SEARCH_REQUEST_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/searchRequest/list"
    DUMMY_NOTIFICATION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/{}/sendDummyNotification"
    SUBSCRIPTION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/plan/{}/\"YATRI_SUBSCRIPTION\""
    OVERLAY_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/driver/{}/sendSms"
    RIDE_DETAILS_FARE_BREAKUP_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/ride/{}/fareBreakUp"
    RIDE_DETAILS_INFO_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/ride/{}/info"
    DOC_STATUS_API_URL = ""
    
    # API Keys
    DRIVER_INFO_API_KEY = os.getenv("DRIVER_INFO_API_KEY", "")
    DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
    
    # Constants
    CONTENT_TYPE_JSON = "application/json"

    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

    TIME_INTERVAL = os.getenv("TIME_INTERVAL", "40")

    TIME_INTERVAL_FOR_LOCATIONS = os.getenv("TIME_INTERVAL_FOR_LOCATIONS", "10")

class ClickHouseConfig:
    """ClickHouse database configuration."""
    
    HOST = os.getenv("CLICKHOUSE_HOST")
    USER = os.getenv("CLICKHOUSE_USER")
    PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
    PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))


class AppConfig:
    """Application configuration."""
    
    TITLE = "Namma Yatri MCP Server"
    VERSION = "1.0.0"
    HOST = "0.0.0.0"
    PORT = 8000

