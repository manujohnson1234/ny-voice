#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Request
from typing import Dict, Any, Optional
import uvicorn
import requests
import json
import os
from datetime import datetime, timedelta, timezone, date
from loguru import logger
from clickhouse_driver import Client

from block_messages import get_blocked_reason_message

app = FastAPI(title="Namma Yatri MCP Server", version="1.0.0")

# API Configuration
DRIVER_INFO_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/info"
SEARCH_REQUEST_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/searchRequest/list"
DUMMY_NOTIFICATION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/driver/{}/sendDummyNotification"
SUBSCRIPTION_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/Bangalore/plan/{}/\"YATRI_SUBSCRIPTION\""
OVERLAY_API_URL = "https://dashboard.beckn.juspay.in/api/bpp/driver-offer/NAMMA_YATRI_PARTNER/driver/{}/sendSms" 
DRIVER_INFO_API_KEY = os.getenv("DRIVER_INFO_API_KEY", "add9b7b9-4a84-4abb-abf5-189469c7df3d")
SEARCH_REQUEST_API_KEY = os.getenv("SEARCH_REQUEST_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
DUMMY_NOTIFICATION_API_KEY = os.getenv("DUMMY_NOTIFICATION_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
SUBSCRIPTION_API_KEY = os.getenv("SUBSCRIPTION_API_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")
OVERLAY_API_URL_KEY = os.getenv("OVERLAY_API_URL_KEY", "5931f977-8a9c-4ad1-81f3-ccfa14f3db22")



# Constants
CONTENT_TYPE_JSON = "application/json"

# ClickHouse Configuration
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "10.6.155.14")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "juspay_ro")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "hARCGXR9lFsDMWhS")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))

# Global ClickHouse client instance (lazy initialization)
clickhouse_client: Optional[Client] = None

def get_clickhouse_client() -> Optional[Client]:
    """Get or initialize ClickHouse client (lazy initialization)."""
    global clickhouse_client
    if clickhouse_client is not None:
        return clickhouse_client
    
    try:
        logger.info(f"Initializing ClickHouse client (host={CLICKHOUSE_HOST}, port={CLICKHOUSE_PORT}, user={CLICKHOUSE_USER})")
        clickhouse_client = Client(
            host=CLICKHOUSE_HOST,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            port=CLICKHOUSE_PORT
        )
        logger.info("ClickHouse client initialized successfully")
        return clickhouse_client
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse client: {str(e)}")
        clickhouse_client = None
        return None

# Still use Pydantic for request validation of tool calls, if desired
# But we drop response_model so we can return raw JSON

def get_driver_info(mobile_number: str) -> dict:
    logger.info(f"get_driver_info called with mobileNumber: {mobile_number}")
    if not mobile_number or not mobile_number.isdigit():
        error_msg = "mobileNumber must be a valid numeric string."
        logger.error(f"get_driver_info validation failed: {error_msg}")
        return {"success": False, "error": error_msg}

    headers = {
        "token": DRIVER_INFO_API_KEY,
        "Content-Type": CONTENT_TYPE_JSON,
    }

    url = f"{DRIVER_INFO_API_URL}?mobileNumber={mobile_number}"
    logger.info(f"Making API request to: {url}")
    
    try:
        resp = requests.get(url, headers=headers)
        logger.info(f"Driver info API request responded: {resp.status_code}")
        if resp.status_code != 200:
            body = resp.text
            logger.error(f"Driver info API failed: status {resp.status_code}, body: {body}")
            return {"success": False, "error": f"Driver info API request failed with status {resp.status_code}", "body": body}
        
        driver_info = resp.json()
        # extract driverId etc.
        driver_id = None
        blocked = False
        isRCVerified = False
        blockedReason = None
        if isinstance(driver_info, dict):
            driver_id = driver_info.get('driverId') or driver_info.get('driver_id') or driver_info.get('id')
            blocked = driver_info.get('blocked', False) or driver_info.get('isBlocked', False)
            rcList = driver_info.get('vehicleRegistrationDetails')
            
            blockedReason = driver_info.get('blockedReason')
           
            if blocked:
                blockedReasonMessage = get_blocked_reason_message(blockedReason)
                return {"success": True, "blocked": True, "blockedReason": blockedReasonMessage}

            for rc in rcList:
                if rc.get('isRcActive'):
                    isRCVerified = True
                    break
            
            if not isRCVerified:
                return {"success": True, "isRCDeActivated" : True}

        if not driver_id:
            logger.warning("driverId not found in driver info response")
            return {"success": False, "error": "driverId not found in driver info response", "driver_info": driver_info}
        
        # fetch payment details
        dues_details = get_subscription_plan(driver_id)

        if isinstance(dues_details, dict) and dues_details.get('success'):
            hasDues = dues_details.get('hasDues')
            if hasDues:
                dues_details["driverId"] = driver_id    
                return dues_details

        # Query ClickHouse for search requests
        clickhouse_results = query_search_requests_clickhouse(driver_id)
        
        # fetch search requests count
        search_headers = {
            "token": SEARCH_REQUEST_API_KEY,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        now = datetime.now(timezone.utc)
        ten_minutes_ago = now - timedelta(minutes=10)

        to_date = now.isoformat(timespec="seconds").replace("+00:00", "Z")
        from_date = ten_minutes_ago.isoformat(timespec="seconds").replace("+00:00", "Z")

        search_params = {
            "limit": 5,
            "driverId": driver_id,
            "fromDate": from_date,
            "toDate": to_date,
            "offset": 0,
        }
        logger.info(f"Making search request for driverId: {driver_id}")
        search_resp = requests.get(SEARCH_REQUEST_API_URL, params=search_params, headers=search_headers)
        logger.info(f"Search request responded: {search_resp.status_code}")
        
        search_requests_count = 0
        if search_resp.status_code == 200:
            search_data = search_resp.json()
            search_requests = search_data.get('data', search_data.get('results', search_data.get('searchRequests', [])))
            if isinstance(search_requests, list):
                search_requests_count = len(search_requests)
            elif isinstance(search_requests, dict) and 'count' in search_requests:
                search_requests_count = search_requests.get('count', 0)
        else:
            logger.warning(f"Search request failed for driverId {driver_id}")
            # you may choose to include body or error in response

        combined_response = {
            "success": True,
            "no_search_requests": search_requests_count,
            "driverId": driver_id,
            "clickhouse_search_requests": clickhouse_results,
            "clickhouse_search_requests_count": len(clickhouse_results)
        }
        logger.info(f"get_driver_info returning: {combined_response}")
        return combined_response
    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(f"get_driver_info exception: {error_msg}")
        return {"success": False, "error": error_msg}


def send_dummy_request(driver_id: str, extra: Optional[Dict[str, Any]] = None) -> dict:
    logger.info(f"send_dummy_request called with driver_id: {driver_id}, extra: {extra}")
    # You can inspect extra if passed; for example, if you want to accept injected parameters
    if extra and "_prerequisite_error" in extra:
        error = extra["_prerequisite_error"]
        logger.warning(f"Returning prerequisite error: {error}")
        return {"success": False, "error": error}
    if not driver_id:
        error_msg = "driver_id must be a valid string."
        logger.error(f"send_dummy_request validation failed: {error_msg}")
        return {"success": False, "error": error_msg}

    headers = {
        "token": DUMMY_NOTIFICATION_API_KEY,
        "Content-Type": CONTENT_TYPE_JSON,
    }
    url = DUMMY_NOTIFICATION_API_URL.format(driver_id)
    logger.info(f"Making dummy notification API call to: {url}")
    try:
        resp = requests.post(url, headers=headers)
        logger.info(f"Dummy notification API responded: {resp.status_code}")
        if resp.status_code not in [200, 201, 202]:
            body = resp.text
            logger.error(f"Notification API failed: status {resp.status_code}, body: {body}")
            return {"success": False, "error": f"Dummy notification API failed with status {resp.status_code}", "body": body}
        try:
            result = resp.json()
            logger.info("send_dummy_request got JSON response")
            return {"success": True, "result": result}
        except json.JSONDecodeError:
            text = resp.text
            logger.info("send_dummy_request got non-JSON response")
            return {"success": True, "result": {"text": text, "status_code": resp.status_code}}
    except Exception as e:
        error_msg = f"Dummy notification request failed: {str(e)}"
        logger.error(f"send_dummy_request exception: {error_msg}")
        return {"success": False, "error": error_msg}


def send_overlay_sms(driver_id: str) -> dict:
    logger.info(f"send_overlay_sms called with driver_id: {driver_id}")
    if not driver_id:
        error_msg = "driver_id must be a valid string."
        logger.error(f"send_overlay_sms validation failed: {error_msg}")
        return {"success": False, "error": error_msg}
    
    headers = {
        "token": OVERLAY_API_URL_KEY,
        "Content-Type": CONTENT_TYPE_JSON,
    }
    
    request_body = {
        "channel": "OVERLAY",
        "messageKey": "SMS_HOW_IT_WORKS_MESSAGE",
        "overlayKey": "DASHBOARD_CLEAR_DUES_TO_BE_BLOCKED_DRIVERS_OVERLAY"
    }
    
    url = OVERLAY_API_URL.format(driver_id)
    logger.info(f"Making overlay SMS API call to: {url}")
    try:
        resp = requests.post(url, headers=headers, json=request_body)
        logger.info(f"Overlay SMS API responded: {resp.status_code}")
        if resp.status_code not in [200, 201, 202]:
            body = resp.text
            logger.error(f"Overlay SMS API failed: status {resp.status_code}, body: {body}")
            return {"success": False, "error": f"Overlay SMS API failed with status {resp.status_code}", "body": body}
        try:
            result = resp.json()
            logger.info("send_overlay_sms got JSON response")
            return {"success": True, "result": result}
        except json.JSONDecodeError:
            text = resp.text
            logger.info("send_overlay_sms got non-JSON response")
            return {"success": True, "result": {"text": text, "status_code": resp.status_code}}
    except Exception as e:
        error_msg = f"Overlay SMS request failed: {str(e)}"
        logger.error(f"send_overlay_sms exception: {error_msg}")
        return {"success": False, "error": error_msg}

def get_subscription_plan(driver_id: str) -> dict:
    logger.info(f"get_subscription_plan called with driver_id: {driver_id}")
    if not driver_id:
        error_msg = "driver_id must be a valid string."
        logger.error(f"get_subscription_plan validation failed: {error_msg}")
        return {"success": False, "error": error_msg}

    headers = {
        "token": SUBSCRIPTION_API_KEY,
        "Content-Type": CONTENT_TYPE_JSON,
    }
    url = SUBSCRIPTION_API_URL.format(driver_id)
    logger.info(f"Making subscription API call to: {url}")
    try:
        resp = requests.get(url, headers=headers)
        logger.info(f"Subscription API responded: {resp.status_code}")
        if resp.status_code != 200:
            body = resp.text
            logger.error(f"Subscription API failed: status {resp.status_code}, body: {body}")
            return {"success": False, "error": f"Subscription API request failed with status {resp.status_code}", "body": body}
        
        subscription_data = resp.json()
        # logger.info(f"Subscription plan data: {subscription_data}")
        currentDues = 0
        totalPlanCreditLimit = 0
        if isinstance(subscription_data, dict):
            currentPlanDetails = subscription_data.get('currentPlanDetails')
            currentDues = currentPlanDetails.get('currentDues')
            totalPlanCreditLimit = currentPlanDetails.get('totalPlanCreditLimit')

        return  {"success": True, "hasDues" : currentDues > totalPlanCreditLimit, "currentDues" : currentDues}
    except Exception as e:
        error_msg = f"Subscription request failed: {str(e)}"
        logger.error(f"get_subscription_plan exception: {error_msg}")
        return {"success": False, "error": error_msg}


def query_search_requests_clickhouse(driver_id: str, from_date: Optional[str] = None) -> list:
    """
    Query search requests from ClickHouse for a specific driver.
    
    Args:
        driver_id: The driver ID to search for
        from_date: Optional date string in format 'YYYY-MM-DD'. Defaults to today's date.
    
    Returns:
        List of search request records (as lists for JSON serialization)
    """
    client = get_clickhouse_client()
    if client is None:
        logger.warning("ClickHouse client is not available, returning empty results")
        return []
    
    if not driver_id:
        logger.error("driver_id is required for ClickHouse query")
        return []
    
    # Use Indian Standard Time (IST = UTC+5:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist) - timedelta(minutes=5)

    # 5 minutes before now
    five_minutes_ago = now - timedelta(minutes=5)

    # ClickHouse-compatible timestamp format (NO "Z")
    to_time = now.strftime("%Y-%m-%d %H:%M:%S")
    from_time = five_minutes_ago.strftime("%Y-%m-%d %H:%M:%S")

    print("FROM:", from_time)
    print("TO:  ", to_time)
    
    try:
        # Escape single quotes in driver_id to prevent SQL injection
        escaped_driver_id = driver_id.replace("'", "''")
        
        rows = client.execute(f"""
            SELECT *
            FROM atlas_kafka.search_request_batch
            WHERE has(driverIds, '{escaped_driver_id}')
              AND date BETWEEN '{from_time}' AND '{to_time}'
            ORDER BY date
        """)
        
        # logger.info(f"ClickHouse query returned {len(rows)} rows for driver_id: {driver_id}")
        
        # Convert tuples to lists for JSON serialization
        return [list(row) for row in rows]
    except Exception as e:
        logger.error(f"ClickHouse query failed: {str(e)}")
        return []


TOOLS = {
    "get_driver_info": get_driver_info,
    "send_dummy_notification": send_dummy_request,
    "send_overlay_sms": send_overlay_sms
}

@app.post("/call-tool")
async def call_tool(request: Request):
    try:
        # Parse JSON from request body
        body = await request.json()

        logger.info(f"call_tool request body: {body}")
        tool_name = body.get("tool") or body.get("params", {}).get("tool")
        parameters = body.get("parameters", {}) or body.get("params", {}).get("parameters", {})
        
        logger.info(f"call_tool called with tool_name: {tool_name}, parameters: {parameters}")

        if not tool_name:
            return {"success": False, "error": "Tool name is required"}
            
        if tool_name not in TOOLS:
            return {"success": False, "error": f"Tool '{tool_name}' not found. Available tools: {list(TOOLS.keys())}"}
        
        tool_func = TOOLS[tool_name]
        
        # Call the tool function with parameters
        result = tool_func(**parameters)
        
        # Return raw JSON
        return {"success": True, "result": result}
        
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Error calling tool: {err_msg}")
        return {"success": False, "error": err_msg}


@app.get("/tools") 
async def list_tools():
    # Just raw JSON dictionary
    return {
        "tools": list(TOOLS.keys()),
        "descriptions": {
            "get_driver_info": "Retrieve driver information and search requests using mobile number",
            "send_dummy_notification": "Send dummy ride request notification to a driver using driver_id",
            "send_overlay_sms": "Send overlay SMS notification to a driver using driver_id"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Namma Yatri MCP Server"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
