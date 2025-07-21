"""
Firestore Serialization Utilities
Handles conversion of Firestore types to JSON-serializable formats
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Union

def convert_firestore_datetime(obj: Any) -> Any:
    """
    Convert DatetimeWithNanoseconds to ISO format string
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object with datetime strings
    """
    # Check if object is a Firestore DatetimeWithNanoseconds
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'DatetimeWithNanoseconds':
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_firestore_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_firestore_datetime(item) for item in obj]
    else:
        return obj

def firestore_to_json(data: Union[Dict, List]) -> Union[Dict, List]:
    """
    Convert Firestore document data to JSON-serializable format
    
    Args:
        data: Firestore document data
        
    Returns:
        JSON-serializable data
    """
    return convert_firestore_datetime(data)

def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON, converting Firestore types
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string
    """
    converted_data = convert_firestore_datetime(data)
    return json.dumps(converted_data, **kwargs)
