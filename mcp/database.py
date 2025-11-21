"""ClickHouse database operations."""
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from clickhouse_driver import Client
from loguru import logger

from config import ClickHouseConfig


class ClickHouseClient:
    """ClickHouse database client with lazy initialization."""
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    def get_client(self) -> Optional[Client]:
        """Get or initialize ClickHouse client (lazy initialization)."""
        if self._client is not None:
            return self._client
        
        try:
            logger.info(
                f"Initializing ClickHouse client "
                f"(host={ClickHouseConfig.HOST}, "
                f"port={ClickHouseConfig.PORT}, "
                f"user={ClickHouseConfig.USER})"
            )
            self._client = Client(
                host=ClickHouseConfig.HOST,
                user=ClickHouseConfig.USER,
                password=ClickHouseConfig.PASSWORD,
                port=ClickHouseConfig.PORT
            )
            logger.info("ClickHouse client initialized successfully")
            return self._client
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse client: {str(e)}")
            self._client = None
            return None
    
    def query_search_requests(
        self, 
        driver_id: str, 
        minutes_back: int = 10
    ) -> List[List]:
        """
        Query search requests from ClickHouse for a specific driver.
        
        Args:
            driver_id: The driver ID to search for
            minutes_back: Number of minutes to look back (default: 10)
        
        Returns:
            List of search request records (as lists for JSON serialization)
        """
        client = self.get_client()
        if client is None:
            logger.warning("ClickHouse client is not available, returning empty results")
            return []
        
        if not driver_id:
            logger.error("driver_id is required for ClickHouse query")
            return []
        
        # Use Indian Standard Time (IST = UTC+5:30)
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        time_from = now - timedelta(minutes=minutes_back)
        
        # ClickHouse-compatible timestamp format (NO "Z")
        to_time = now.strftime("%Y-%m-%d %H:%M:%S")
        from_time = time_from.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.debug(f"Querying ClickHouse: FROM={from_time}, TO={to_time}")
        
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
            
            logger.debug(f"ClickHouse query returned {len(rows)} rows for driver_id: {driver_id}")
            
            # Convert tuples to lists for JSON serialization
            return [list(row) for row in rows]
        except Exception as e:
            logger.error(f"ClickHouse query failed: {str(e)}")
            return []


# Global instance
clickhouse_client = ClickHouseClient()

