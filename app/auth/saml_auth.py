"""
SAML 2.0 Authentication Module.

This module handles SAML authentication with Azure Active Directory,
including processing SAML assertions and extracting user information
and group claims.
"""

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from flask import request, session, redirect, url_for

logger = logging.getLogger(__name__)


class SAMLAuthenticator:
    """
    Handles SAML 2.0 authentication with Azure Active Directory.
    
    This class provides methods for initiating SAML authentication,
    processing SAML responses, and extracting user information and
    group claims from SAML assertions.
    """
    
    def __init__(self, saml_settings: Dict):
        """
        Initialize the SAML authenticator.
        
        Args:
            saml_settings: Dictionary containing SAML configuration
        """
        self.saml_settings = saml_settings
        self._validate_settings()
    
    def _validate_settings(self) -> None:
        """Validate SAML settings configuration."""
        required_sp_fields = ['entityId', 'assertionConsumerService', 'singleLogoutService']
        required_idp_fields = ['entityId', 'singleSignOnService', 'x509cert']
        
        sp_config = self.saml_settings.get('sp', {})
        idp_config = self.saml_settings.get('idp', {})
        
        for field in required_sp_fields:
            if field not in sp_config:
                raise ValueError(f"Missing required SP configuration: {field}")
        
        for field in required_idp_fields:
            if field not in idp_config:
                raise ValueError(f"Missing required IdP configuration: {field}")
    
    def _init_saml_auth(self, req: Dict) -> OneLogin_Saml2_Auth:
        """
        Initialize SAML Auth object.
        
        Args:
            req: Request information dictionary
            
        Returns:
            OneLogin_Saml2_Auth: Configured SAML auth object
        """
        return OneLogin_Saml2_Auth(req, self.saml_settings)
    
    def _prepare_flask_request(self, request_obj) -> Dict:
        """
        Prepare Flask request object for SAML library.
        
        Args:
            request_obj: Flask request object
            
        Returns:
            Dict: Request information formatted for SAML library
        """
        url_data = urlparse(request_obj.url)
        return {
            'https': 'on' if request_obj.scheme == 'https' else 'off',
            'http_host': request_obj.headers.get('Host', ''),
            'server_port': url_data.port or (443 if request_obj.scheme == 'https' else 80),
            'script_name': request_obj.path,
            'get_data': request_obj.args.copy(),
            'post_data': request_obj.form.copy()
        }
    
    def initiate_login(self) -> str:
        """
        Initiate SAML login process.
        
        Returns:
            str: Redirect URL for SAML authentication
            
        Raises:
            Exception: If SAML authentication initialization fails
        """
        try:
            req = self._prepare_flask_request(request)
            auth = self._init_saml_auth(req)
            
            # Clear any existing session data
            session.clear()
            
            # Generate and return SSO URL
            sso_url = auth.login()
            logger.info("SAML login initiated")
            return sso_url
            
        except Exception as e:
            logger.error(f"Failed to initiate SAML login: {str(e)}")
            raise Exception(f"SAML login initialization failed: {str(e)}")
    
    def process_response(self) -> Tuple[bool, Optional[Dict], List[str]]:
        """
        Process SAML response from Azure AD.
        
        Returns:
            Tuple containing:
            - bool: True if authentication successful, False otherwise
            - Optional[Dict]: User attributes if successful, None otherwise
            - List[str]: List of error messages if any
            
        Raises:
            Exception: If SAML response processing fails
        """
        try:
            req = self._prepare_flask_request(request)
            auth = self._init_saml_auth(req)
            
            # Process the SAML response
            auth.process_response()
            
            errors = auth.get_errors()
            if errors:
                logger.error(f"SAML authentication errors: {errors}")
                return False, None, errors
            
            if not auth.is_authenticated():
                logger.warning("SAML authentication failed - user not authenticated")
                return False, None, ["Authentication failed"]
            
            # Extract user attributes
            user_attributes = self._extract_user_attributes(auth)
            
            # Store authentication info in session
            session['saml_authenticated'] = True
            session['saml_nameid'] = auth.get_nameid()
            session['saml_nameid_format'] = auth.get_nameid_format()
            session['saml_session_index'] = auth.get_session_index()
            session['user_attributes'] = user_attributes
            
            logger.info(f"SAML authentication successful for user: {user_attributes.get('email', 'unknown')}")
            return True, user_attributes, []
            
        except Exception as e:
            logger.error(f"Failed to process SAML response: {str(e)}")
            raise Exception(f"SAML response processing failed: {str(e)}")
    
    def _extract_user_attributes(self, auth: OneLogin_Saml2_Auth) -> Dict:
        """
        Extract user attributes from SAML assertion.
        
        Args:
            auth: Authenticated SAML auth object
            
        Returns:
            Dict: User attributes including groups
        """
        attributes = auth.get_attributes()
        
        # Common Azure AD attribute mappings
        user_data = {
            'nameid': auth.get_nameid(),
            'email': self._get_attribute_value(attributes, [
                'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
                'email',
                'mail'
            ]),
            'first_name': self._get_attribute_value(attributes, [
                'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
                'givenname',
                'firstname'
            ]),
            'last_name': self._get_attribute_value(attributes, [
                'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
                'surname',
                'lastname'
            ]),
            'display_name': self._get_attribute_value(attributes, [
                'http://schemas.microsoft.com/identity/claims/displayname',
                'displayname',
                'name'
            ]),
            'groups': self._extract_groups(attributes),
            'raw_attributes': attributes
        }
        
        # Use email as fallback for display name
        if not user_data['display_name']:
            user_data['display_name'] = user_data['email']
        
        return user_data
    
    def _get_attribute_value(self, attributes: Dict, possible_keys: List[str]) -> Optional[str]:
        """
        Get attribute value by trying multiple possible keys.
        
        Args:
            attributes: SAML attributes dictionary
            possible_keys: List of possible attribute keys to try
            
        Returns:
            Optional[str]: Attribute value if found, None otherwise
        """
        for key in possible_keys:
            if key in attributes and attributes[key]:
                value = attributes[key]
                return value[0] if isinstance(value, list) else value
        return None
    
    def _extract_groups(self, attributes: Dict) -> List[str]:
        """
        Extract group memberships from SAML attributes.
        
        Args:
            attributes: SAML attributes dictionary
            
        Returns:
            List[str]: List of group names/IDs
        """
        group_attributes = [
            'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
            'http://schemas.xmlsoap.org/claims/Group',
            'groups',
            'memberOf'
        ]
        
        groups = []
        for attr_name in group_attributes:
            if attr_name in attributes:
                attr_value = attributes[attr_name]
                if isinstance(attr_value, list):
                    groups.extend(attr_value)
                else:
                    groups.append(attr_value)
        
        # Remove duplicates and empty values
        return list(set(filter(None, groups)))
    
    def initiate_logout(self) -> str:
        """
        Initiate SAML logout process.
        
        Returns:
            str: Redirect URL for SAML logout
            
        Raises:
            Exception: If SAML logout initialization fails
        """
        try:
            req = self._prepare_flask_request(request)
            auth = self._init_saml_auth(req)
            
            # Get session info for logout
            name_id = session.get('saml_nameid')
            session_index = session.get('saml_session_index')
            name_id_format = session.get('saml_nameid_format')
            
            # Clear session
            session.clear()
            
            # Generate logout URL
            logout_url = auth.logout(
                name_id=name_id,
                session_index=session_index,
                name_id_format=name_id_format
            )
            
            logger.info("SAML logout initiated")
            return logout_url
            
        except Exception as e:
            logger.error(f"Failed to initiate SAML logout: {str(e)}")
            raise Exception(f"SAML logout initialization failed: {str(e)}")
    
    def process_logout_response(self) -> Tuple[bool, List[str]]:
        """
        Process SAML logout response.
        
        Returns:
            Tuple containing:
            - bool: True if logout successful, False otherwise
            - List[str]: List of error messages if any
        """
        try:
            req = self._prepare_flask_request(request)
            auth = self._init_saml_auth(req)
            
            # Process logout response
            url = auth.process_slo(delete_session_cb=lambda: session.clear())
            errors = auth.get_errors()
            
            if errors:
                logger.error(f"SAML logout errors: {errors}")
                return False, errors
            
            logger.info("SAML logout completed successfully")
            return True, []
            
        except Exception as e:
            logger.error(f"Failed to process SAML logout response: {str(e)}")
            return False, [f"Logout processing failed: {str(e)}"]
    
    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated via SAML.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return session.get('saml_authenticated', False)
    
    def get_user_info(self) -> Optional[Dict]:
        """
        Get current user information from session.
        
        Returns:
            Optional[Dict]: User attributes if authenticated, None otherwise
        """
        if self.is_authenticated():
            return session.get('user_attributes')
        return None
    
    def get_metadata(self) -> str:
        """
        Generate SAML metadata for the service provider.
        
        Returns:
            str: XML metadata string
        """
        try:
            settings = OneLogin_Saml2_Settings(self.saml_settings)
            metadata = settings.get_sp_metadata()
            errors = settings.check_sp_metadata(metadata)
            
            if errors:
                logger.error(f"SAML metadata errors: {errors}")
                raise Exception(f"Invalid metadata: {errors}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to generate SAML metadata: {str(e)}")
            raise Exception(f"Metadata generation failed: {str(e)}")