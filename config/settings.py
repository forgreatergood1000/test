"""
Application configuration settings.

This module handles all configuration settings for the Flask application,
including SAML, AWS Cognito, and security configurations.
"""

import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class with common settings."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'saml_app:'
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))
    
    # Security Settings
    REQUIRE_HTTPS = os.getenv('REQUIRE_HTTPS', 'False').lower() == 'true'
    
    # SAML Configuration
    SAML_SP_ENTITY_ID = os.getenv('SAML_SP_ENTITY_ID', 'https://localhost:12000')
    SAML_SP_ACS_URL = os.getenv('SAML_SP_ACS_URL', 'https://localhost:12000/saml/acs')
    SAML_SP_SLS_URL = os.getenv('SAML_SP_SLS_URL', 'https://localhost:12000/saml/sls')
    
    # Azure AD IdP Configuration
    SAML_IDP_ENTITY_ID = os.getenv('SAML_IDP_ENTITY_ID', '')
    SAML_IDP_SSO_URL = os.getenv('SAML_IDP_SSO_URL', '')
    SAML_IDP_SLS_URL = os.getenv('SAML_IDP_SLS_URL', '')
    SAML_IDP_X509_CERT = os.getenv('SAML_IDP_X509_CERT', '')
    
    # AWS Cognito Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', '')
    COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', '')
    COGNITO_CLIENT_SECRET = os.getenv('COGNITO_CLIENT_SECRET', '')
    
    # Group Mapping Configuration
    _group_mapping_str = os.getenv('GROUP_MAPPING', '{}')
    try:
        GROUP_MAPPING = json.loads(_group_mapping_str)
    except json.JSONDecodeError:
        GROUP_MAPPING = {}
    
    @classmethod
    def get_saml_settings(cls) -> Dict[str, Any]:
        """
        Generate SAML settings dictionary for python3-saml library.
        
        Returns:
            Dict containing SAML configuration settings
        """
        return {
            "sp": {
                "entityId": cls.SAML_SP_ENTITY_ID,
                "assertionConsumerService": {
                    "url": cls.SAML_SP_ACS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": cls.SAML_SP_SLS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": "",
                "privateKey": ""
            },
            "idp": {
                "entityId": cls.SAML_IDP_ENTITY_ID,
                "singleSignOnService": {
                    "url": cls.SAML_IDP_SSO_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": cls.SAML_IDP_SLS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": cls.SAML_IDP_X509_CERT
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantAssertionsSigned": True,
                "wantNameId": True,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "signatureAlgorithm": "http://www.w3.org/2000/09/xmldsig#rsa-sha1",
                "digestAlgorithm": "http://www.w3.org/2000/09/xmldsig#sha1",
            }
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that all required configuration values are present.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_fields = [
            'SECRET_KEY',
            'SAML_SP_ENTITY_ID',
            'SAML_SP_ACS_URL',
            'SAML_SP_SLS_URL'
        ]
        
        for field in required_fields:
            if not getattr(cls, field):
                print(f"Missing required configuration: {field}")
                return False
        
        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    REQUIRE_HTTPS = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    REQUIRE_HTTPS = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    REQUIRE_HTTPS = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}