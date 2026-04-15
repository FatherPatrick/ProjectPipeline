"""
Base collector class with common functionality for all data collectors.
Provides retry logic, error handling, and logging.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time
from loguru import logger
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class BaseCollector(ABC):
    """
    Abstract base class for data collectors.
    Provides common functionality like retry logic and error handling.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize collector.

        Args:
            max_retries: Number of times to retry failed requests
            retry_delay: Base delay in seconds between retries (exponential backoff)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate that the collector is properly configured.
        Must be implemented by subclasses.

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        Main collection method. Must be implemented by subclasses.

        Returns:
            Dictionary of collected data
        """
        pass

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            params: Query parameters
            json: JSON body
            timeout: Request timeout in seconds

        Returns:
            Response object

        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            RequestException: If request fails after all retries
        """
        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                logger.debug(f"Request attempt {attempt + 1}/{self.max_retries + 1}: {method} {url}")

                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=timeout,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.retry_delay))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")

                # Handle authentication errors
                if response.status_code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed: {response.status_code} {response.reason}"
                    )

                # Raise for other HTTP errors
                response.raise_for_status()

                logger.debug(f"Request successful: {url}")
                return response

            except (ConnectionError, Timeout) as e:
                last_exception = e
                attempt += 1
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.warning(
                        f"Connection error: {str(e)}. Retrying in {wait_time}s... "
                        f"(attempt {attempt}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {str(e)}")
                    raise

            except (RateLimitError, AuthenticationError) as e:
                raise

            except requests.HTTPError as e:
                last_exception = e
                logger.error(f"HTTP error: {str(e)}")
                raise

            except Exception as e:
                logger.error(f"Unexpected error during request: {str(e)}")
                raise

        # Should not reach here, but raise last exception if somehow we do
        if last_exception:
            raise last_exception
        raise RequestException("Request failed for unknown reason")

    def _validate_data(self, data: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that required keys exist in data.

        Args:
            data: Data dictionary to validate
            required_keys: List of required keys

        Returns:
            True if valid

        Raises:
            DataValidationError: If validation fails
        """
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise DataValidationError(f"Missing required keys: {missing_keys}")
        return True

    def close(self):
        """Close the requests session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
