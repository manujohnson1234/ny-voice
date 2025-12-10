"""External API client functions."""
from typing import Dict, Any, Optional
import requests
import json
from datetime import datetime, timedelta, timezone
from loguru import logger

from config import APIConfig


class DriverInfoClient:
    """Client for driver information API."""
    
    @staticmethod
    def get_driver_info(mobile_number: str, time_till_not_getting_rides: Optional[int] = None, time_quantity: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch driver information by mobile number.
        
        Args:
            mobile_number: Driver's mobile number
            
        Returns:
            Dictionary containing driver information
        """
        headers = {
            "token": APIConfig.DRIVER_INFO_API_KEY,
            "Content-Type": APIConfig.CONTENT_TYPE_JSON,
        }
        
        url = f"{APIConfig.DRIVER_INFO_API_URL}?mobileNumber={mobile_number}"
        logger.info(f"Fetching driver info from: {url}")
        
        try:
            resp = requests.get(url, headers=headers)
            logger.info(f"Driver info API responded: {resp.status_code}")
            
            if resp.status_code != 200:
                body = resp.text
                logger.error(f"Driver info API failed: status {resp.status_code}, body: {body}")
                return {
                    "success": False,
                    "error": f"Driver info API request failed with status {resp.status_code}",
                    "body": body
                }
            
            return {"success": True, "data": resp.json()}
        except Exception as e:
            error_msg = f"Driver info request failed: {str(e)}"
            logger.error(f"Driver info exception: {error_msg}")
            return {"success": False, "error": error_msg}


class SearchRequestClient:
    """Client for search request API."""
    
    @staticmethod
    def get_search_requests(
        driver_id: str,
        minutes_back: int = 40,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Fetch search requests for a driver.
        
        Args:
            driver_id: Driver ID
            minutes_back: Number of minutes to look back
            limit: Maximum number of results
            
        Returns:
            Dictionary containing search requests
        """
        headers = {
            "token": APIConfig.DASHBOARD_TOKEN,
            "Content-Type": APIConfig.CONTENT_TYPE_JSON,
        }
        
        now = datetime.now(timezone.utc)
        time_from = now - timedelta(minutes=minutes_back)
        
        to_date = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        from_date = time_from.isoformat(timespec="seconds").replace("+00:00", "Z")
        
        params = {
            "limit": limit,
            "driverId": driver_id,
            "fromDate": from_date,
            "toDate": to_date,
            "offset": 0,
        }
        
        logger.info(f"Fetching search requests for driverId: {driver_id}")
        
        try:
            resp = requests.get(APIConfig.SEARCH_REQUEST_API_URL, params=params, headers=headers)
            logger.info(f"Search request API responded: {resp.status_code}")
            
            if resp.status_code != 200:
                logger.warning(f"Search request failed for driverId {driver_id}: {resp.status_code}")
                return {"success": False, "error": f"Search request API failed with status {resp.status_code}"}

            
            search_data = resp.json()

            search_requests = search_data.get('searchrequests', [])

            
            count = 0
            if isinstance(search_requests, list):
                count = len(search_requests)
            elif isinstance(search_requests, dict) and 'count' in search_requests:
                count = search_requests.get('count', 0)
            
            return {"success": True, "count": count, "data": search_requests}
        except Exception as e:
            error_msg = f"Search request failed: {str(e)}"
            logger.error(f"Search request exception: {error_msg}")
            return {"success": False, "error": error_msg}


class NotificationClient:
    """Client for notification APIs."""
    
    @staticmethod
    def send_dummy_notification(driver_id: str) -> Dict[str, Any]:
        """
        Send dummy notification to a driver.
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Dictionary containing API response
        """
        headers = {
            "token": APIConfig.DASHBOARD_TOKEN,
            "Content-Type": APIConfig.CONTENT_TYPE_JSON,
        }
        
        url = APIConfig.DUMMY_NOTIFICATION_API_URL.format(driver_id)
        logger.info(f"Sending dummy notification to: {url}")
        
        try:
            resp = requests.post(url, headers=headers)
            logger.info(f"Dummy notification API responded: {resp.status_code}")
            
            if resp.status_code not in [200, 201, 202]:
                body = resp.text
                logger.error(f"Notification API failed: status {resp.status_code}, body: {body}")
                return {
                    "success": False,
                    "error": f"Dummy notification API failed with status {resp.status_code}",
                    "body": body
                }
            
            try:
                result = resp.json()
                return {"success": True, "result": result}
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "result": {"text": resp.text, "status_code": resp.status_code}
                }
        except Exception as e:
            error_msg = f"Dummy notification request failed: {str(e)}"
            logger.error(f"Dummy notification exception: {error_msg}")
            return {"success": False, "error": error_msg}
    
    @staticmethod
    def send_overlay_sms(driver_id: str) -> Dict[str, Any]:
        """
        Send overlay SMS notification to a driver.
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Dictionary containing API response
        """
        headers = {
            "token": APIConfig.DASHBOARD_TOKEN,
            "Content-Type": APIConfig.CONTENT_TYPE_JSON,
        }
        
        request_body = {
            "channel": "OVERLAY",
            "messageKey": "SMS_HOW_IT_WORKS_MESSAGE",
            "overlayKey": "DASHBOARD_CLEAR_DUES_TO_BE_BLOCKED_DRIVERS_OVERLAY"
        }
        
        url = APIConfig.OVERLAY_API_URL.format(driver_id)
        logger.info(f"Sending overlay SMS to: {url}")
        
        try:
            resp = requests.post(url, headers=headers, json=request_body)
            logger.info(f"Overlay SMS API responded: {resp.status_code}")
            
            if resp.status_code not in [200, 201, 202]:
                body = resp.text
                logger.error(f"Overlay SMS API failed: status {resp.status_code}, body: {body}")
                return {
                    "success": False,
                    "error": f"Overlay SMS API failed with status {resp.status_code}",
                    "body": body
                }
            
            try:
                result = resp.json()
                return {"success": True, "result": result}
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "result": {"text": resp.text, "status_code": resp.status_code}
                }
        except Exception as e:
            error_msg = f"Overlay SMS request failed: {str(e)}"
            logger.error(f"Overlay SMS exception: {error_msg}")
            return {"success": False, "error": error_msg}


class SubscriptionClient:
    """Client for subscription API."""
    
    @staticmethod
    def get_subscription_plan(driver_id: str) -> Dict[str, Any]:
        """
        Get subscription plan details for a driver.
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Dictionary containing subscription information
        """
        headers = {
            "token": APIConfig.DASHBOARD_TOKEN,
            "Content-Type": APIConfig.CONTENT_TYPE_JSON,
        }
        
        url = APIConfig.SUBSCRIPTION_API_URL.format(driver_id)
        logger.info(f"Fetching subscription plan from: {url}")
        
        try:
            resp = requests.get(url, headers=headers)
            logger.info(f"Subscription API responded: {resp.status_code}")
            
            if resp.status_code != 200:
                body = resp.text
                logger.error(f"Subscription API failed: status {resp.status_code}, body: {body}")
                return {
                    "success": False,
                    "error": f"Subscription API request failed with status {resp.status_code}",
                    "body": body
                }
            
            subscription_data = resp.json()
            current_dues = 0
            total_plan_credit_limit = 0
            
            if isinstance(subscription_data, dict):
                current_plan_details = subscription_data.get('currentPlanDetails', {})
                current_dues = current_plan_details.get('currentDues', 0)
                total_plan_credit_limit = current_plan_details.get('totalPlanCreditLimit', 0)
            
            return {
                "success": True,
                "hasDues": current_dues > total_plan_credit_limit,
                "currentDues": current_dues
            }
        except Exception as e:
            error_msg = f"Subscription request failed: {str(e)}"
            logger.error(f"Subscription exception: {error_msg}")
            return {"success": False, "error": error_msg}

