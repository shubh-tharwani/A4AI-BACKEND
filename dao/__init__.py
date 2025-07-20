"""
Data Access Object (DAO) Layer
This package contains data access objects for each service

Available DAOs:
- AuthDAO: Handles supplementary user authentication data
- AssessmentDAO: Handles assessment and performance data
- VoiceAssistantDAO: Handles voice conversation data  
- ContentDAO: Handles activity and visual aid data
- PlanningDAO: Handles lesson plan and curriculum data
- UserDAO: Handles user profile and session data
"""

from .auth_dao import AuthDAO, auth_dao
from .assessment_dao import AssessmentDAO, assessment_dao
from .voice_assistant_dao import VoiceAssistantDAO, voice_assistant_dao
from .content_dao import ContentDAO, content_dao
from .planning_dao import PlanningDAO, planning_dao
from .user_dao import UserDAO, user_dao

__all__ = [
    'AuthDAO', 'auth_dao',
    'AssessmentDAO', 'assessment_dao',
    'VoiceAssistantDAO', 'voice_assistant_dao', 
    'ContentDAO', 'content_dao',
    'PlanningDAO', 'planning_dao',
    'UserDAO', 'user_dao'
]
