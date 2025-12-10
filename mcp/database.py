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
                port=ClickHouseConfig.PORT,
                send_receive_timeout=10,  # 5 second timeout for all queries
                settings={'max_execution_time': 10}  # Server-side query timeout
            )
            logger.info("ClickHouse client initialized successfully")
            return self._client
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse client: {str(e)}")
            self._client = None
            return None
    
    def query_search_requests_batch(
        self, 
        driver_id: str, 
        interval: int = 2,
        time_quantity: str = "HOUR"
    ) -> int:
        """
        Query search requests from ClickHouse for a specific driver.
        
        Args:
            driver_id: The driver ID to search for
            minutes_back: Number of minutes to look back (default: 40)
        
        Returns:
            List of search request records (as lists for JSON serialization)
        """
        client = self.get_client()
        if client is None:
            logger.warning("ClickHouse client is not available, returning empty results")
            return 0
        
        if not driver_id:
            logger.error("driver_id is required for ClickHouse query")
            return 0
        
        try:
            # Escape single quotes in driver_id to prevent SQL injection
            escaped_driver_id = driver_id.replace("'", "''")
            
            # Use ClickHouse's now() function (UTC) with INTERVAL for time range
            rows = client.execute(f"""
                SELECT COUNT(*)
                FROM atlas_kafka.search_request_batch
                WHERE has(driverIds, '{escaped_driver_id}')
                  AND date BETWEEN now() - INTERVAL {interval} {time_quantity} AND now()
                  AND filterStage = 'ActualDistance';
            """)
            
            logger.debug(f"ClickHouse query returned {len(rows)} rows for driver_id: {driver_id}")
            
            # Convert tuples to lists for JSON serialization
            return rows
        except Exception as e:
            logger.error(f"ClickHouse query failed: {str(e)}")
            return 0

    def query_search_requests_for_driver(self, driver_id: str, interval: int = 2, time_quantity: str = "HOUR") -> int: 
        """
        Query search requests from ClickHouse for a specific driver.
        
        Args:
            driver_id: The driver ID to search for
            internal: Number of internal search requests to look back (default: 2)
        """
        client = self.get_client()
        if client is None:
            logger.warning("ClickHouse client is not available, returning empty results")
            return 0
        
        if not driver_id:
            logger.error("driver_id is required for ClickHouse query")
            return 0
        logger.info(f"interval: {interval}, time_quantity: {time_quantity}")
        try:
            row = client.execute(f"""
                SELECT COUNT(*) from atlas_driver_offer_bpp.search_request_for_driver
                WHERE driver_id = '{driver_id}'
                AND created_at BETWEEN now() - INTERVAL {interval} {time_quantity} AND now();
            """)

            logger.info(f"Search requests for driver: {len(row)}")
            return row
        except Exception as e:
            logger.error(f"Error querying search requests for driver: {str(e)}")
            return 0


    def query_driver_locations(self, driver_id: str, interval: int = 2) -> int:
        """
        Query driver locations from ClickHouse for a specific driver.
        
        Args:
            driver_id: The driver ID to search for
            minutes_back: Number of minutes to look back (default: 1)
        """
        
        client = self.get_client()
        if client is None:
            logger.warning("ClickHouse client is not available, returning empty results")
            return 0
        
        if not driver_id:
            logger.error("driver_id is required for ClickHouse query")
            return 0
        
        try:
            rows = client.execute(f"""
                SELECT COUNT(*)
                FROM atlas_kafka.driver_eda_kafka
                WHERE driver_id = '{driver_id}'
                AND partition_date = toDate(now()) AND ts BETWEEN now() - INTERVAL {interval} MINUTE AND now();
            """)

            return rows
        except Exception as e:
            logger.error(f"Error querying driver locations: {str(e)}")
            return 0
        
# Global instance
clickhouse_client = ClickHouseClient()

