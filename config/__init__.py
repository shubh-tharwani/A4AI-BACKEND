"""
Configuration module for AI Education Platform.

This module centralizes all configuration settings, API credentials,
and middleware components for the application.
"""

from .config import Config
from .firebase_config import *
from .firestore_config import *
from .vertex_ai import *
from .auth_middleware import *

__all__ = [
    'Config',
]
