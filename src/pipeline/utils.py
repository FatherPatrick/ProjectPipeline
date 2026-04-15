"""
Pipeline utilities and helper functions.
"""
import json
from datetime import datetime, date
from typing import Any, Dict


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder for datetime objects."""
    
    def default(self, obj: Any) -> Any:
        """Encode datetime and date objects."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def serialize_data(data: Dict[str, Any]) -> str:
    """
    Serialize data to JSON string with datetime support.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        JSON string
    """
    return json.dumps(data, cls=DateTimeEncoder, indent=2)


def parse_iso_datetime(date_string: str) -> datetime:
    """
    Parse ISO format datetime string.
    
    Args:
        date_string: ISO format datetime string
        
    Returns:
        Parsed datetime object
    """
    return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
