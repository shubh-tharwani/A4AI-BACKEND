"""
Centralized DAO Error Handling Utilities

This module provides consistent error handling patterns for all DAO operations
across the application. It ensures that database failures are properly handled
and appropriate exceptions are raised.
"""

import logging
from typing import Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class DAOError(Exception):
    """Base exception for DAO-related errors"""
    def __init__(self, operation: str, details: str, original_error: Optional[Exception] = None):
        self.operation = operation
        self.details = details
        self.original_error = original_error
        super().__init__(f"DAO {operation} failed: {details}")

class DAOConnectionError(DAOError):
    """Exception for database connection issues"""
    pass

class DAOValidationError(DAOError):
    """Exception for data validation issues"""
    pass

class DAOOperationError(DAOError):
    """Exception for general operation failures"""
    pass

def handle_dao_errors(operation_name: str):
    """
    Decorator to handle common DAO errors and convert them to appropriate exceptions
    
    Args:
        operation_name: Name of the operation being performed (e.g., "save_assessment", "get_user")
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Handle None results for operations that should return data
                if result is None and operation_name.startswith('get_'):
                    logger.warning(f"DAO operation '{operation_name}' returned None")
                    return None  # Allow None for get operations
                
                # Handle False results for operations that should return boolean success
                if result is False and any(operation_name.startswith(prefix) for prefix in ['save_', 'update_', 'delete_', 'create_']):
                    raise DAOOperationError(
                        operation=operation_name,
                        details="Operation returned False indicating failure"
                    )
                
                return result
                
            except DAOError:
                # Re-raise our custom DAO errors
                raise
            except Exception as e:
                error_message = str(e)
                
                # Categorize common error types
                if "permission" in error_message.lower() or "403" in error_message:
                    raise DAOConnectionError(
                        operation=operation_name,
                        details="Insufficient database permissions",
                        original_error=e
                    )
                elif "connection" in error_message.lower() or "timeout" in error_message.lower():
                    raise DAOConnectionError(
                        operation=operation_name,
                        details="Database connection failed",
                        original_error=e
                    )
                elif "validation" in error_message.lower() or "invalid" in error_message.lower():
                    raise DAOValidationError(
                        operation=operation_name,
                        details=f"Data validation failed: {error_message}",
                        original_error=e
                    )
                else:
                    # Generic operation error
                    raise DAOOperationError(
                        operation=operation_name,
                        details=error_message,
                        original_error=e
                    )
        
        return wrapper
    return decorator

def validate_dao_result(result: Any, operation_name: str, expected_type: Optional[type] = None) -> Any:
    """
    Validate DAO operation results and raise appropriate exceptions
    
    Args:
        result: The result from the DAO operation
        operation_name: Name of the operation
        expected_type: Expected type of the result (optional)
    
    Returns:
        The validated result
    
    Raises:
        DAOOperationError: If the result is invalid
    """
    # Check for None results where data is expected
    if result is None and operation_name.startswith(('get_', 'save_', 'update_')):
        if operation_name.startswith('get_'):
            # get_ operations can legitimately return None
            return None
        else:
            # save_ and update_ operations should not return None
            raise DAOOperationError(
                operation=operation_name,
                details="Operation returned None instead of expected result"
            )
    
    # Check for False results in boolean operations
    if result is False and any(operation_name.startswith(prefix) for prefix in ['save_', 'update_', 'delete_', 'create_']):
        raise DAOOperationError(
            operation=operation_name,
            details="Operation returned False indicating failure"
        )
    
    # Type checking if expected_type is provided
    if expected_type is not None and result is not None and not isinstance(result, expected_type):
        raise DAOValidationError(
            operation=operation_name,
            details=f"Expected {expected_type.__name__} but got {type(result).__name__}"
        )
    
    return result

# Utility functions for common patterns
def ensure_document_id(document_id: Optional[str], operation_name: str) -> str:
    """Ensure a document ID is valid and not None"""
    if not document_id:
        raise DAOOperationError(
            operation=operation_name,
            details="Document ID is required but was not provided or is empty"
        )
    return document_id

def ensure_collection_exists(collection_check_func: Callable, collection_name: str) -> bool:
    """Ensure a collection exists before performing operations"""
    try:
        exists = collection_check_func()
        if not exists:
            logger.warning(f"Collection '{collection_name}' does not exist or is empty")
            return False
        return True
    except Exception as e:
        raise DAOConnectionError(
            operation=f"check_collection_{collection_name}",
            details=f"Failed to verify collection existence: {str(e)}",
            original_error=e
        )

# Service-level error handlers
def handle_service_dao_errors(service_operation: str):
    """
    Decorator specifically for service functions that call DAOs
    Converts DAO errors to service-level exceptions with better context
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except DAOError as dao_error:
                # Convert DAO error to service error with additional context
                raise Exception(f"Service '{service_operation}' failed: {str(dao_error)}")
            except Exception as e:
                # Handle any other errors
                raise Exception(f"Service '{service_operation}' encountered an error: {str(e)}")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DAOError as dao_error:
                # Convert DAO error to service error with additional context  
                raise Exception(f"Service '{service_operation}' failed: {str(dao_error)}")
            except Exception as e:
                # Handle any other errors
                raise Exception(f"Service '{service_operation}' encountered an error: {str(e)}")
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
