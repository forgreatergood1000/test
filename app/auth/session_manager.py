"""
Session Management Module.

This module handles secure session management, including session
validation, timeout handling, and access control based on user
groups and attributes.
"""

import logging
import time
from typing import Dict, List, Optional, Callable
from functools import wraps
from flask import session, request, redirect, url_for, flash, current_app

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Handles secure session management and access control.
    
    This class provides methods for session validation, timeout handling,
    and group-based access control for protected resources.
    """
    
    def __init__(self, session_timeout: int = 3600):
        """
        Initialize the session manager.
        
        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
        """
        self.session_timeout = session_timeout
    
    def is_authenticated(self) -> bool:
        """
        Check if the current session is authenticated.
        
        Returns:
            bool: True if authenticated and session is valid, False otherwise
        """
        if not session.get('saml_authenticated', False):
            return False
        
        # Check session timeout
        if self._is_session_expired():
            self.clear_session()
            return False
        
        # Update last activity timestamp
        self._update_last_activity()
        return True
    
    def _is_session_expired(self) -> bool:
        """
        Check if the current session has expired.
        
        Returns:
            bool: True if session has expired, False otherwise
        """
        last_activity = session.get('last_activity')
        if not last_activity:
            return True
        
        current_time = time.time()
        return (current_time - last_activity) > self.session_timeout
    
    def _update_last_activity(self) -> None:
        """Update the last activity timestamp in the session."""
        session['last_activity'] = time.time()
    
    def clear_session(self) -> None:
        """Clear all session data."""
        session.clear()
        logger.info("Session cleared")
    
    def get_user_info(self) -> Optional[Dict]:
        """
        Get current user information from session.
        
        Returns:
            Optional[Dict]: User attributes if authenticated, None otherwise
        """
        if self.is_authenticated():
            return session.get('user_attributes')
        return None
    
    def get_user_groups(self) -> List[str]:
        """
        Get current user's groups from session.
        
        Returns:
            List[str]: List of user groups
        """
        user_info = self.get_user_info()
        if user_info:
            return user_info.get('groups', [])
        return []
    
    def has_group(self, required_group: str) -> bool:
        """
        Check if the current user belongs to a specific group.
        
        Args:
            required_group: Group name to check
            
        Returns:
            bool: True if user belongs to the group, False otherwise
        """
        user_groups = self.get_user_groups()
        return required_group in user_groups
    
    def has_any_group(self, required_groups: List[str]) -> bool:
        """
        Check if the current user belongs to any of the specified groups.
        
        Args:
            required_groups: List of group names to check
            
        Returns:
            bool: True if user belongs to any of the groups, False otherwise
        """
        user_groups = self.get_user_groups()
        return any(group in user_groups for group in required_groups)
    
    def has_all_groups(self, required_groups: List[str]) -> bool:
        """
        Check if the current user belongs to all of the specified groups.
        
        Args:
            required_groups: List of group names to check
            
        Returns:
            bool: True if user belongs to all groups, False otherwise
        """
        user_groups = self.get_user_groups()
        return all(group in user_groups for group in required_groups)
    
    def get_session_info(self) -> Dict:
        """
        Get comprehensive session information.
        
        Returns:
            Dict: Session information including user data and timing
        """
        if not self.is_authenticated():
            return {'authenticated': False}
        
        last_activity = session.get('last_activity', 0)
        time_remaining = max(0, self.session_timeout - (time.time() - last_activity))
        
        return {
            'authenticated': True,
            'user_info': self.get_user_info(),
            'groups': self.get_user_groups(),
            'session_timeout': self.session_timeout,
            'time_remaining': int(time_remaining),
            'last_activity': last_activity,
            'nameid': session.get('saml_nameid'),
            'session_index': session.get('saml_session_index')
        }


def login_required(f: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Args:
        f: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_manager = SessionManager(
            session_timeout=current_app.config.get('SESSION_TIMEOUT', 3600)
        )
        
        if not session_manager.is_authenticated():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def group_required(required_groups: List[str], require_all: bool = False):
    """
    Decorator to require specific group membership for a route.
    
    Args:
        required_groups: List of required group names
        require_all: If True, user must belong to ALL groups; if False, ANY group
        
    Returns:
        Callable: Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_manager = SessionManager(
                session_timeout=current_app.config.get('SESSION_TIMEOUT', 3600)
            )
            
            if not session_manager.is_authenticated():
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            # Check group membership
            if require_all:
                has_access = session_manager.has_all_groups(required_groups)
            else:
                has_access = session_manager.has_any_group(required_groups)
            
            if not has_access:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


class AccessControl:
    """
    Handles access control and authorization logic.
    
    This class provides methods for checking permissions and
    managing access to different parts of the application.
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize access control.
        
        Args:
            session_manager: SessionManager instance
        """
        self.session_manager = session_manager
    
    def can_access_admin(self) -> bool:
        """
        Check if user can access admin features.
        
        Returns:
            bool: True if user has admin access, False otherwise
        """
        admin_groups = ['admin', 'administrators', 'Admin']
        return self.session_manager.has_any_group(admin_groups)
    
    def can_access_user_management(self) -> bool:
        """
        Check if user can access user management features.
        
        Returns:
            bool: True if user has user management access, False otherwise
        """
        user_mgmt_groups = ['admin', 'user_managers', 'hr']
        return self.session_manager.has_any_group(user_mgmt_groups)
    
    def can_view_reports(self) -> bool:
        """
        Check if user can view reports.
        
        Returns:
            bool: True if user can view reports, False otherwise
        """
        report_groups = ['admin', 'managers', 'analysts', 'reports_viewers']
        return self.session_manager.has_any_group(report_groups)
    
    def can_edit_profile(self, target_user_email: str = None) -> bool:
        """
        Check if user can edit a profile.
        
        Args:
            target_user_email: Email of the user whose profile is being edited
            
        Returns:
            bool: True if user can edit the profile, False otherwise
        """
        user_info = self.session_manager.get_user_info()
        if not user_info:
            return False
        
        # Users can always edit their own profile
        if not target_user_email or user_info.get('email') == target_user_email:
            return True
        
        # Admins can edit any profile
        return self.can_access_admin()
    
    def get_accessible_features(self) -> List[str]:
        """
        Get list of features accessible to the current user.
        
        Returns:
            List[str]: List of accessible feature names
        """
        features = ['dashboard', 'profile']
        
        if self.can_access_admin():
            features.extend(['admin', 'user_management', 'system_settings'])
        
        if self.can_access_user_management():
            features.append('user_management')
        
        if self.can_view_reports():
            features.append('reports')
        
        return list(set(features))  # Remove duplicates
    
    def get_user_permissions(self) -> Dict:
        """
        Get comprehensive user permissions.
        
        Returns:
            Dict: User permissions and capabilities
        """
        return {
            'can_access_admin': self.can_access_admin(),
            'can_access_user_management': self.can_access_user_management(),
            'can_view_reports': self.can_view_reports(),
            'accessible_features': self.get_accessible_features(),
            'groups': self.session_manager.get_user_groups()
        }