"""External API Integration Subsystem.

Demonstrates:
- HTTP requests using Python `requests` library
- Handling of all required external network states:
  1. Successful response (200 OK)
  2. Invalid response (Malformed JSON / schema mismatch)
  3. Timeout (requests.exceptions.Timeout)
  4. Connection error (requests.exceptions.ConnectionError)
  5. HTTP error (requests.exceptions.HTTPError / 4xx, 5xx)
"""

from typing import Any, Dict, Optional
import requests
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger()


class ExternalAPIService:
    """Consumes external REST web APIs with resilient error handling."""

    def __init__(self, base_url: Optional[str] = None, timeout_seconds: float = 4.0) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.EXTERNAL_API_URL
        self.timeout = timeout_seconds

    def fetch_time_sync(self, endpoint_url: Optional[str] = None) -> Dict[str, Any]:
        """Queries the external time API to synchronize enterprise clock state.

        Demonstrates:
        - 200 Success
        - Timeout handling
        - Connection error handling
        - HTTP 4xx/5xx status handling
        - Non-JSON / malformed response handling
        """
        url = endpoint_url or self.base_url
        logger.info("Initiating external HTTP GET request to: %s", url)

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "IT-Asset-Manager/1.0"},
            )

            # Check for HTTP status error (4xx, 5xx)
            response.raise_for_status()

            # Attempt JSON parsing (guards against invalid/malformed response)
            try:
                data = response.json()
            except ValueError as json_err:
                logger.error("External API returned invalid JSON: %s", json_err)
                return {
                    "status": "INVALID_RESPONSE",
                    "success": False,
                    "error_message": "Response body could not be parsed as valid JSON.",
                    "status_code": response.status_code,
                    "raw_text": response.text[:200],
                }

            logger.info("External API request succeeded with status %d", response.status_code)
            return {
                "status": "SUCCESS",
                "success": True,
                "status_code": response.status_code,
                "data": data,
            }

        except requests.exceptions.Timeout as timeout_err:
            logger.error("External API timed out after %.1f seconds: %s", self.timeout, timeout_err)
            return {
                "status": "TIMEOUT",
                "success": False,
                "error_message": f"Connection timed out after {self.timeout} seconds.",
                "details": str(timeout_err),
            }

        except requests.exceptions.ConnectionError as conn_err:
            logger.error("External API connection failed: %s", conn_err)
            return {
                "status": "CONNECTION_ERROR",
                "success": False,
                "error_message": "Failed to establish network connection to external endpoint.",
                "details": str(conn_err),
            }

        except requests.exceptions.HTTPError as http_err:
            status_code = response.status_code if "response" in locals() else None
            logger.error("External API HTTP error (%s): %s", status_code, http_err)
            return {
                "status": "HTTP_ERROR",
                "success": False,
                "status_code": status_code,
                "error_message": f"External endpoint returned HTTP status {status_code}.",
                "details": str(http_err),
            }

        except Exception as generic_err:
            logger.error("Unexpected error during external API request: %s", generic_err)
            return {
                "status": "UNEXPECTED_ERROR",
                "success": False,
                "error_message": "An unexpected error occurred during external communication.",
                "details": str(generic_err),
            }
