"""
Amazon Cognito Integration Module.

This module handles integration with Amazon Cognito User Pools,
including user creation, attribute mapping, and group management
based on SAML group claims.
"""

import logging
import json
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class CognitoClient:
    """
    Handles integration with Amazon Cognito User Pools.
    
    This class provides methods for creating and updating users,
    mapping SAML group claims to Cognito custom attributes,
    and managing user attributes based on SAML assertions.
    """
    
    def __init__(self, region: str, user_pool_id: str, client_id: str, 
                 client_secret: str, access_key_id: str = None, 
                 secret_access_key: str = None):
        """
        Initialize the Cognito client.
        
        Args:
            region: AWS region
            user_pool_id: Cognito User Pool ID
            client_id: Cognito App Client ID
            client_secret: Cognito App Client Secret
            access_key_id: AWS Access Key ID (optional if using IAM roles)
            secret_access_key: AWS Secret Access Key (optional if using IAM roles)
        """
        self.region = region
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Initialize Cognito client
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        self.cognito_client = session.client('cognito-idp')
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate Cognito configuration."""
        if not all([self.region, self.user_pool_id, self.client_id]):
            raise ValueError("Missing required Cognito configuration parameters")
        
        try:
            # Test connection by describing user pool
            self.cognito_client.describe_user_pool(UserPoolId=self.user_pool_id)
            logger.info("Cognito client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to validate Cognito configuration: {str(e)}")
            raise ValueError(f"Invalid Cognito configuration: {str(e)}")
    
    def create_or_update_user(self, user_attributes: Dict, group_mapping: Dict) -> Dict:
        """
        Create or update a user in Cognito based on SAML attributes.
        
        Args:
            user_attributes: User attributes from SAML assertion
            group_mapping: Mapping of SAML groups to Cognito attributes
            
        Returns:
            Dict: Result of user creation/update operation
            
        Raises:
            Exception: If user creation/update fails
        """
        try:
            email = user_attributes.get('email')
            if not email:
                raise ValueError("Email is required for user creation")
            
            # Check if user exists
            user_exists = self._user_exists(email)
            
            if user_exists:
                result = self._update_user(user_attributes, group_mapping)
                logger.info(f"Updated existing user: {email}")
            else:
                result = self._create_user(user_attributes, group_mapping)
                logger.info(f"Created new user: {email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create/update user: {str(e)}")
            raise Exception(f"User operation failed: {str(e)}")
    
    def _user_exists(self, email: str) -> bool:
        """
        Check if a user exists in the Cognito User Pool.
        
        Args:
            email: User email address
            
        Returns:
            bool: True if user exists, False otherwise
        """
        try:
            self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return False
            raise
    
    def _create_user(self, user_attributes: Dict, group_mapping: Dict) -> Dict:
        """
        Create a new user in Cognito.
        
        Args:
            user_attributes: User attributes from SAML assertion
            group_mapping: Mapping of SAML groups to Cognito attributes
            
        Returns:
            Dict: Result of user creation operation
        """
        try:
            email = user_attributes['email']
            
            # Prepare user attributes for Cognito
            cognito_attributes = self._prepare_cognito_attributes(user_attributes, group_mapping)
            
            # Create user
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=cognito_attributes,
                MessageAction='SUPPRESS',  # Don't send welcome email
                TemporaryPassword=self._generate_temporary_password(),
                ForceAliasCreation=False
            )
            
            # Set permanent password (user won't need to change it)
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=self._generate_temporary_password(),
                Permanent=True
            )
            
            return {
                'action': 'created',
                'user_id': response['User']['Username'],
                'attributes': cognito_attributes
            }
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    def _update_user(self, user_attributes: Dict, group_mapping: Dict) -> Dict:
        """
        Update an existing user in Cognito.
        
        Args:
            user_attributes: User attributes from SAML assertion
            group_mapping: Mapping of SAML groups to Cognito attributes
            
        Returns:
            Dict: Result of user update operation
        """
        try:
            email = user_attributes['email']
            
            # Prepare user attributes for Cognito
            cognito_attributes = self._prepare_cognito_attributes(user_attributes, group_mapping)
            
            # Update user attributes
            self.cognito_client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=cognito_attributes
            )
            
            return {
                'action': 'updated',
                'user_id': email,
                'attributes': cognito_attributes
            }
            
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise
    
    def _prepare_cognito_attributes(self, user_attributes: Dict, group_mapping: Dict) -> List[Dict]:
        """
        Prepare user attributes for Cognito format.
        
        Args:
            user_attributes: User attributes from SAML assertion
            group_mapping: Mapping of SAML groups to Cognito attributes
            
        Returns:
            List[Dict]: Cognito-formatted user attributes
        """
        attributes = []
        
        # Standard attributes
        if user_attributes.get('email'):
            attributes.append({'Name': 'email', 'Value': user_attributes['email']})
            attributes.append({'Name': 'email_verified', 'Value': 'true'})
        
        if user_attributes.get('first_name'):
            attributes.append({'Name': 'given_name', 'Value': user_attributes['first_name']})
        
        if user_attributes.get('last_name'):
            attributes.append({'Name': 'family_name', 'Value': user_attributes['last_name']})
        
        if user_attributes.get('display_name'):
            attributes.append({'Name': 'name', 'Value': user_attributes['display_name']})
        
        # Map SAML groups to custom attributes
        user_groups = user_attributes.get('groups', [])
        mapped_attributes = self._map_groups_to_attributes(user_groups, group_mapping)
        
        for attr_name, attr_value in mapped_attributes.items():
            attributes.append({'Name': f'custom:{attr_name}', 'Value': attr_value})
        
        # Store original SAML groups as JSON
        if user_groups:
            attributes.append({
                'Name': 'custom:saml_groups',
                'Value': json.dumps(user_groups)
            })
        
        # Store SAML NameID
        if user_attributes.get('nameid'):
            attributes.append({
                'Name': 'custom:saml_nameid',
                'Value': user_attributes['nameid']
            })
        
        return attributes
    
    def _map_groups_to_attributes(self, user_groups: List[str], group_mapping: Dict) -> Dict[str, str]:
        """
        Map SAML groups to Cognito custom attributes.
        
        Args:
            user_groups: List of user's SAML groups
            group_mapping: Mapping configuration
            
        Returns:
            Dict[str, str]: Mapped attributes
        """
        mapped_attributes = {}
        
        for group in user_groups:
            if group in group_mapping:
                attr_name = group_mapping[group]
                # Set attribute to 'true' to indicate membership
                mapped_attributes[attr_name] = 'true'
        
        # Add a general groups attribute with all groups
        if user_groups:
            mapped_attributes['groups'] = ','.join(user_groups)
        
        return mapped_attributes
    
    def _generate_temporary_password(self) -> str:
        """
        Generate a temporary password for new users.
        
        Returns:
            str: Temporary password
        """
        import secrets
        import string
        
        # Generate a secure random password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Ensure password meets Cognito requirements
        if not any(c.isupper() for c in password):
            password = password[:-1] + 'A'
        if not any(c.islower() for c in password):
            password = password[:-1] + 'a'
        if not any(c.isdigit() for c in password):
            password = password[:-1] + '1'
        if not any(c in "!@#$%^&*" for c in password):
            password = password[:-1] + '!'
        
        return password
    
    def get_user_attributes(self, email: str) -> Optional[Dict]:
        """
        Get user attributes from Cognito.
        
        Args:
            email: User email address
            
        Returns:
            Optional[Dict]: User attributes if found, None otherwise
        """
        try:
            response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            
            # Convert Cognito attributes to dictionary
            attributes = {}
            for attr in response.get('UserAttributes', []):
                name = attr['Name']
                value = attr['Value']
                
                # Handle custom attributes
                if name.startswith('custom:'):
                    name = name[7:]  # Remove 'custom:' prefix
                
                attributes[name] = value
            
            return attributes
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return None
            logger.error(f"Failed to get user attributes: {str(e)}")
            raise
    
    def delete_user(self, email: str) -> bool:
        """
        Delete a user from Cognito.
        
        Args:
            email: User email address
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            logger.info(f"Deleted user: {email}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                logger.warning(f"User not found for deletion: {email}")
                return False
            logger.error(f"Failed to delete user: {str(e)}")
            raise
    
    def list_users(self, limit: int = 60) -> List[Dict]:
        """
        List users in the Cognito User Pool.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List[Dict]: List of user information
        """
        try:
            response = self.cognito_client.list_users(
                UserPoolId=self.user_pool_id,
                Limit=limit
            )
            
            users = []
            for user in response.get('Users', []):
                user_info = {
                    'username': user['Username'],
                    'status': user['UserStatus'],
                    'created': user['UserCreateDate'],
                    'modified': user['UserLastModifiedDate'],
                    'attributes': {}
                }
                
                # Extract attributes
                for attr in user.get('Attributes', []):
                    name = attr['Name']
                    value = attr['Value']
                    
                    if name.startswith('custom:'):
                        name = name[7:]  # Remove 'custom:' prefix
                    
                    user_info['attributes'][name] = value
                
                users.append(user_info)
            
            return users
            
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            raise
    
    def validate_group_mapping(self, group_mapping: Dict) -> bool:
        """
        Validate group mapping configuration.
        
        Args:
            group_mapping: Group mapping dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(group_mapping, dict):
            logger.error("Group mapping must be a dictionary")
            return False
        
        for saml_group, cognito_attr in group_mapping.items():
            if not isinstance(saml_group, str) or not isinstance(cognito_attr, str):
                logger.error("Group mapping keys and values must be strings")
                return False
            
            # Validate Cognito attribute name
            if not cognito_attr.replace('_', '').isalnum():
                logger.error(f"Invalid Cognito attribute name: {cognito_attr}")
                return False
        
        return True