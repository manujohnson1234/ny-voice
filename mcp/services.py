"""Business logic services that orchestrate API calls and database queries."""
from typing import Dict, Any, Optional
from loguru import logger

from api_clients import (
    DriverInfoClient,
    SearchRequestClient,
    NotificationClient,
    SubscriptionClient,
    RideFareBreakupClient,
    RideInfoClient,
    DocStatusClient
)
from database import clickhouse_client
from block_messages import get_blocked_reason_message

from config import APIConfig






class DriverService:
    """Service for driver-related operations."""
    
    def __init__(self):
        self.driver_info_client = DriverInfoClient()
        self.search_request_client = SearchRequestClient()
        self.subscription_client = SubscriptionClient()
        self.ride_info_client = RideInfoClient()
        self.fare_breakup_client = RideFareBreakupClient()
    
    def get_driver_info(self, mobile_number: str, time_till_not_getting_rides: Optional[int] = None, time_quantity: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive driver information including status, dues, and search requests.
        
        Args:
            mobile_number: Driver's mobile number
            
        Returns:
            Dictionary containing driver information and status
        """
        logger.info(f"Getting driver info for mobile number: {mobile_number}")
        
        # Validate mobile number
        if not mobile_number or not mobile_number.isdigit():
            error_msg = "mobileNumber must be a valid numeric string."
            logger.error(f"Validation failed: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Fetch driver info
        driver_info_response = self.driver_info_client.get_driver_info(mobile_number)
        if not driver_info_response.get("success"):
            return driver_info_response
        
        driver_info = driver_info_response.get("data", {})
        
        # Extract driver details
        driver_id = (
            driver_info.get('driverId') or 
            driver_info.get('driver_id') or 
            driver_info.get('id')
        )
        
        if not driver_id:
            logger.warning("driverId not found in driver info response")
            return {
                "success": False,
                "error": "driverId not found in driver info response",
                "driver_info": driver_info
            }
        
        # Check if driver is blocked
        blocked = driver_info.get('blocked', False) or driver_info.get('isBlocked', False)
        blocked_reason = driver_info.get('blockedReason')
        
        if blocked:
            blocked_reason_message = get_blocked_reason_message(blocked_reason)
            return {
                "success": True,
                "blocked": True,
                "blockedReason": blocked_reason_message
            }
        
        # Check RC verification status
        rc_list = driver_info.get('vehicleRegistrationDetails', [])
        is_rc_verified = False
        
        for rc in rc_list:
            if rc.get('isRcActive'):
                is_rc_verified = True
                break
        
        if not is_rc_verified:
            return {"success": True, "isRCDeActivated": True}
        
        # Check subscription dues
        dues_details = self.subscription_client.get_subscription_plan(driver_id)
        
        if isinstance(dues_details, dict) and dues_details.get('success'):
            has_dues = dues_details.get('hasDues')
            if has_dues:
                dues_details["driverId"] = driver_id
                return dues_details

        # offline check
        if isinstance(driver_info, dict) :
            mode = driver_info.get('driverMode')
            logger.info(f"Driver mode: {mode}")
            if mode == 'OFFLINE':
                return {"success": True, "driver_mode": mode}

        


        search_requests_count = 0

        if APIConfig.ENVIRONMENT == "master":
        # Fetch search requests from API
            search_response = self.search_request_client.get_search_requests(
                driver_id,
                minutes_back=40,
                limit=20
            )
            if search_response.get("success"):
                search_requests_count = search_response.get("count", 0)
        
        # Query ClickHouse for search requests
        clickhouse_results_count = 0
        driver_locations_count = 0

        if time_quantity:
            if time_quantity in ["minutes", "Minutes", "MINUTES", "minute", "Minute", "MINUTE"]:
                time_quantity = "MINUTE"
            else:
                time_quantity = "HOUR"

        if APIConfig.ENVIRONMENT != "master":
            if time_till_not_getting_rides and time_quantity:
                clickhouse_results_count = clickhouse_client.query_search_requests_batch(driver_id, interval=time_till_not_getting_rides, time_quantity=time_quantity)
                search_requests_count = clickhouse_client.query_search_requests_for_driver(driver_id, interval=time_till_not_getting_rides, time_quantity=time_quantity)
            else:
                clickhouse_results_count = clickhouse_client.query_search_requests_batch(driver_id, interval=int(APIConfig.TIME_INTERVAL), time_quantity="HOUR")
                search_requests_count = clickhouse_client.query_search_requests_for_driver(driver_id, interval=int(APIConfig.TIME_INTERVAL), time_quantity="HOUR")

        driver_locations_count = clickhouse_client.query_driver_locations(driver_id, interval=int(APIConfig.TIME_INTERVAL_FOR_LOCATIONS))
        
        
        
        # logger.info(f"Driver locations count: {driver_locations_count}")
        # Combine results
        if APIConfig.ENVIRONMENT != "master":
            combined_response = {
                "success": True,
                "no_search_requests": search_requests_count,
                "driverId": driver_id,
                "driver_considered_for_nearby_search_request_count": clickhouse_results_count,
                "driver_locations_count": driver_locations_count,
                "hasDues": False,
            }
        else:
            combined_response = {
                "success": True,
                "no_search_requests": search_requests_count,
                "driverId": driver_id
            }
        
        logger.info(f"Driver info retrieved successfully for driverId: {driver_id}")
        return combined_response


class NotificationService:
    """Service for notification operations."""
    
    def __init__(self):
        self.notification_client = NotificationClient()
    
    def send_dummy_notification(
        self, 
        driver_id: str, 
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send dummy notification to a driver.
        
        Args:
            driver_id: Driver ID
            extra: Optional extra parameters (for prerequisite errors)
            
        Returns:
            Dictionary containing API response
        """
        logger.info(f"Sending dummy notification to driver_id: {driver_id}")
        
        # Check for prerequisite errors
        if extra and "_prerequisite_error" in extra:
            error = extra["_prerequisite_error"]
            logger.warning(f"Returning prerequisite error: {error}")
            return {"success": False, "error": error}
        
        # Validate driver_id
        if not driver_id:
            error_msg = "driver_id must be a valid string."
            logger.error(f"Validation failed: {error_msg}")
            return {"success": False, "error": error_msg}
        
        return self.notification_client.send_dummy_notification(driver_id)
    
    def send_overlay_sms(self, driver_id: str) -> Dict[str, Any]:
        """
        Send overlay SMS notification to a driver.
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Dictionary containing API response
        """
        logger.info(f"Sending overlay SMS to driver_id: {driver_id}")
        
        # Validate driver_id
        if not driver_id:
            error_msg = "driver_id must be a valid string."
            logger.error(f"Validation failed: {error_msg}")
            return {"success": False, "error": error_msg}
        
        return self.notification_client.send_overlay_sms(driver_id)



class RideDetailsService:
    """Service for ride details operations."""
    def __init__(self):
        self.fare_breakup_client = RideFareBreakupClient()
        self.ride_info_client = RideInfoClient()
    
    def get_ride_details(self, ride_id: str, issue_type: str) -> Dict[str, Any]:
        """
        Get ride details by ride ID and process based on issue type.
        
        Args:
            ride_id: Ride ID
            issue_type: Issue type ('TOLL_CHARGES' or 'FARE')
            
        Returns:
            Dictionary containing processed ride details based on issue type
        """
        logger.info(f"Getting ride details for ride_id: {ride_id}, issue_type: {issue_type}")
        
        # Fetch data from both APIs
        fare_breakup_response = self.fare_breakup_client.get_fare_breakup(ride_id)
        if not fare_breakup_response.get("success"):
            return fare_breakup_response
            
        ride_info_response = self.ride_info_client.get_ride_info(ride_id)
        if not ride_info_response.get("success"):
            return ride_info_response
        
        # Extract the data
        ride_fare = fare_breakup_response.get("data", {})
        ride_info = ride_info_response.get("data", {})
        
        actual_charges = ride_fare.get('actualFareBreakUp', {})
        estimated_charges = ride_fare.get('estimatedFareBreakUp', {})

        if issue_type == "TOLL_CHARGES":
            actual_toll_charges = actual_charges.get('tollCharges', None)
            estimated_toll_charges = estimated_charges.get('tollCharges', None)
            logger.info(f"Toll charges retrieved - Estimated: {estimated_toll_charges}, Actual: {actual_toll_charges}")

            return {
                "success": True,
                "actual_toll_charges": actual_toll_charges,
                "estimated_toll_charges": estimated_toll_charges
            }
            
        elif issue_type == "FARE":
            estimated_fare = ride_info.get('estimatedFare', None)
            actual_fare = ride_info.get('actualFare', None)

            # If fares match, return simplified response
            if estimated_fare and actual_fare and estimated_fare == actual_fare:
                logger.info(f"Fares match - Estimated: {estimated_fare}, Actual: {actual_fare}")
                return {
                    "success": True,
                    "estimated_fare": estimated_fare,
                    "actual_fare": actual_fare
                }

            # Extract detailed fare breakdown
            estimated_baseFare = estimated_charges.get('baseFare', None)
            actual_baseFare = actual_charges.get('baseFare', None)
            
            # Extract extra km fare from nested fareParametersDetails
            estimated_fare_params = estimated_charges.get('fareParametersDetails', {}).get('contents', {})
            actual_fare_params = actual_charges.get('fareParametersDetails', {}).get('contents', {})
            
            estimated_extraKmFare = estimated_fare_params.get('extraKmFare', None)
            actual_extraKmFare = actual_fare_params.get('extraKmFare', None)
            
            estimated_deadKmFare = estimated_fare_params.get('deadKmFare', None)
            actual_deadKmFare = actual_fare_params.get('deadKmFare', None)

            # Extract driver selected fare
            estimated_driverSelectedFare = estimated_charges.get('driverSelectedFare', None)
            actual_driverSelectedFare = actual_charges.get('driverSelectedFare', None)

            logger.info(f"Fare breakdown retrieved - Estimated Fare: {estimated_fare}, Actual Fare: {actual_fare}")
            return {
                "success": True,
                "estimated_fare": estimated_fare,
                "actual_fare": actual_fare,
                "estimated_baseFare": estimated_baseFare,
                "actual_baseFare": actual_baseFare,
                "estimated_extraKmFare": estimated_extraKmFare,
                "actual_extraKmFare": actual_extraKmFare,
                "estimated_deadKmFare": estimated_deadKmFare,
                "actual_deadKmFare": actual_deadKmFare,
                "estimated_driverSelectedFare": estimated_driverSelectedFare,
                "actual_driverSelectedFare": actual_driverSelectedFare
            }
        else:
            error_msg = f"Invalid issue_type: {issue_type}. Must be 'TOLL_CHARGES' or 'FARE'"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}



class DocStatusService:

    def __init__(self):
        self.driver_info_client = DriverInfoClient()
        self.doc_status_client = DocStatusClient()

    def get_doc_status(self, mobile_number: str) -> Dict[str, any]:

        if not mobile_number or not mobile_number.isdigit():
            error_msg = "mobileNumber must be a valid numeric string."
            logger.error(f"Validation failed: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Fetch driver info
        driver_info_response = self.driver_info_client.get_driver_info(mobile_number)
        if not driver_info_response.get("success"):
            return driver_info_response
        
        driver_info = driver_info_response.get("data", {})
        
        # Extract driver details
        driver_id = (
            driver_info.get('driverId') or 
            driver_info.get('driver_id') or 
            driver_info.get('id')
        )
        
        if not driver_id:
            logger.warning("driverId not found in driver info response")
            return {
                "success": False,
                "error": "driverId not found in driver info response",
                "driver_info": driver_info
            }
        
        doc_status_response = self.doc_status_client.get_doc_status(driver_id)
        if not doc_status_response.get("success"):
            return doc_status_response
        
        doc_status = doc_status_response.get("data", {})
        
        return {
            "success": True,
            "doc_status": doc_status
        }




# Global service instances
driver_service = DriverService()
notification_service = NotificationService()
ride_details_service = RideDetailsService()
doc_status_service = DocStatusService()

