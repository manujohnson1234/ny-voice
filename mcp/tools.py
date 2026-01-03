"""MCP tool functions that expose services via the MCP interface."""
from typing import Dict, Any, Optional

from services import driver_service, notification_service, ride_details_service, doc_status_service


def get_driver_info(mobile_number: str, time_till_not_getting_rides: Optional[int] = None, time_quantity: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve driver information and search requests using mobile number.
    
    This tool fetches comprehensive driver information including:
    - Driver status (blocked, RC verification)
    - Subscription dues
    - Search request counts from both API and ClickHouse
    
    Args:
        mobile_number: Driver's mobile number (numeric string)
        
    Returns:
        Dictionary containing driver information and status
    """
    return driver_service.get_driver_info(mobile_number, time_till_not_getting_rides, time_quantity)


def send_dummy_notification(
    driver_id: str, 
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send dummy ride request notification to a driver using driver_id.
    
    Args:
        driver_id: Driver ID
        extra: Optional extra parameters (for prerequisite errors)
        
    Returns:
        Dictionary containing API response
    """
    return notification_service.send_dummy_notification(driver_id, extra)


def send_overlay_sms(driver_id: str) -> Dict[str, Any]:
    """
    Send overlay SMS notification to a driver using driver_id.
    
    Args:
        driver_id: Driver ID
        
    Returns:
        Dictionary containing API response
    """
    return notification_service.send_overlay_sms(driver_id)


def get_ride_details(ride_id: str, issue_type: str) -> Dict[str, Any]:
    """
    Get ride details by ride ID.
    
    Args:
        ride_id: Ride ID
        issue_type: Issue type
    """
    return ride_details_service.get_ride_details(ride_id, issue_type)



def get_doc_status(mobile_number: str) -> Dict[str, Any]:
    """
    Get the status of the driver's documents (RC/DL).
    
    Args:
        mobile_number: Driver's mobile number
    """
    return doc_status_service.get_doc_status(mobile_number)

# Tool registry
TOOLS = {
    "get_driver_info": get_driver_info,
    "send_dummy_notification": send_dummy_notification,
    "send_overlay_sms": send_overlay_sms,
    "get_ride_details": get_ride_details,
    "get_doc_status": get_doc_status
}


# Tool descriptions for API documentation
TOOL_DESCRIPTIONS = {
    "get_driver_info": "Retrieve driver information and search requests using mobile number",
    "send_dummy_notification": "Send dummy ride request notification to a driver using driver_id",
    "send_overlay_sms": "Send overlay SMS notification to a driver using driver_id",
    "get_ride_details": "Get ride details by ride ID",
    "get_doc_status": "Get the status of the driver's documents (RC/DL)",
}

