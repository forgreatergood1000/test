"""
Main Flask Application for SAML Azure AD Authentication.

This application demonstrates secure authentication using SAML 2.0 with Azure Active Directory,
group claims mapping to Amazon Cognito, and comprehensive session management.

Features:
- SAML 2.0 authentication with Azure AD
- Group claims extraction and mapping
- Amazon Cognito integration
- Secure session management
- Access control based on group memberships
- Comprehensive user interface

Security considerations:
- Secure session management with timeout
- SAML assertion validation
- Input sanitization and validation
- Error handling without information disclosure
- HTTPS enforcement in production
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our custom modules
from config.settings import config
from app.auth.saml_auth import SAMLAuthenticator
from app.auth.session_manager import SessionManager, login_required, AccessControl
from app.cognito.cognito_client import CognitoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """
    Application factory function.
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Validate configuration
    if not config[config_name].validate_config():
        logger.error("Invalid configuration. Please check your settings.")
        raise ValueError("Invalid configuration")
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize components
    saml_settings = config[config_name].get_saml_settings()
    saml_authenticator = SAMLAuthenticator(saml_settings)
    session_manager = SessionManager(app.config['SESSION_TIMEOUT'])
    
    # Initialize Cognito client (if configured)
    cognito_client = None
    if all([
        app.config.get('AWS_ACCESS_KEY_ID'),
        app.config.get('AWS_SECRET_ACCESS_KEY'),
        app.config.get('COGNITO_USER_POOL_ID'),
        app.config.get('COGNITO_CLIENT_ID')
    ]):
        try:
            cognito_client = CognitoClient(
                region=app.config['AWS_REGION'],
                user_pool_id=app.config['COGNITO_USER_POOL_ID'],
                client_id=app.config['COGNITO_CLIENT_ID'],
                client_secret=app.config['COGNITO_CLIENT_SECRET'],
                access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
            )
            logger.info("Cognito client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Cognito client: {str(e)}")
            cognito_client = None
    else:
        logger.info("Cognito configuration not provided - running without Cognito integration")
    
    # Template context processors
    @app.context_processor
    def inject_template_vars():
        """Inject common template variables."""
        return {
            'get_session_info': lambda: session_manager.get_session_info(),
            'get_user_permissions': lambda: AccessControl(session_manager).get_user_permissions(),
            'moment': datetime,
            'from_json': json.loads
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(error)}")
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        return render_template('errors/403.html'), 403
    
    # Main routes
    @app.route('/')
    def index():
        """Home page."""
        return render_template('index.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """User dashboard."""
        return render_template('dashboard.html')
    
    @app.route('/profile')
    @login_required
    def profile():
        """User profile page."""
        user_info = session_manager.get_user_info()
        cognito_user = None
        
        # Get Cognito user data if available
        if cognito_client and user_info and user_info.get('email'):
            try:
                cognito_user = cognito_client.get_user_attributes(user_info['email'])
            except Exception as e:
                logger.warning(f"Failed to get Cognito user data: {str(e)}")
        
        return render_template('profile.html', cognito_user=cognito_user)
    
    @app.route('/session-info', methods=['GET', 'POST'])
    @login_required
    def session_info():
        """Session information page."""
        if request.method == 'POST':
            # Handle session extension request
            data = request.get_json()
            if data and data.get('action') == 'extend':
                # Update last activity to extend session
                session['last_activity'] = time.time()
                session_info = session_manager.get_session_info()
                return jsonify({
                    'success': True,
                    'time_remaining': session_info.get('time_remaining', 0)
                })
        
        return render_template('session_info.html')
    
    # Authentication routes
    @app.route('/auth/login')
    def login():
        """Initiate SAML login."""
        try:
            sso_url = saml_authenticator.initiate_login()
            return redirect(sso_url)
        except Exception as e:
            logger.error(f"Login initiation failed: {str(e)}")
            flash('Failed to initiate login. Please try again.', 'error')
            return redirect(url_for('index'))
    
    @app.route('/auth/logout')
    def logout():
        """Initiate SAML logout."""
        if session_manager.is_authenticated():
            try:
                logout_url = saml_authenticator.initiate_logout()
                return redirect(logout_url)
            except Exception as e:
                logger.error(f"Logout initiation failed: {str(e)}")
                session_manager.clear_session()
                flash('Logged out successfully.', 'success')
        
        return redirect(url_for('index'))
    
    @app.route('/saml/acs', methods=['POST'])
    def saml_acs():
        """SAML Assertion Consumer Service."""
        try:
            success, user_attributes, errors = saml_authenticator.process_response()
            
            if success and user_attributes:
                # Process Cognito integration if available
                if cognito_client:
                    try:
                        cognito_result = cognito_client.create_or_update_user(
                            user_attributes, 
                            app.config['GROUP_MAPPING']
                        )
                        logger.info(f"Cognito operation: {cognito_result['action']} for user {user_attributes['email']}")
                    except Exception as e:
                        logger.error(f"Cognito integration failed: {str(e)}")
                        # Continue without Cognito integration
                
                flash(f"Welcome, {user_attributes.get('display_name', 'User')}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"SAML authentication failed: {errors}")
                flash('Authentication failed. Please try again.', 'error')
                return redirect(url_for('index'))
                
        except Exception as e:
            logger.error(f"SAML ACS processing failed: {str(e)}")
            flash('Authentication error. Please try again.', 'error')
            return redirect(url_for('index'))
    
    @app.route('/saml/sls', methods=['GET', 'POST'])
    def saml_sls():
        """SAML Single Logout Service."""
        try:
            success, errors = saml_authenticator.process_logout_response()
            
            if success:
                flash('Logged out successfully.', 'success')
            else:
                logger.warning(f"SAML logout failed: {errors}")
                flash('Logout completed with warnings.', 'warning')
            
        except Exception as e:
            logger.error(f"SAML SLS processing failed: {str(e)}")
            flash('Logout completed.', 'info')
        
        return redirect(url_for('index'))
    
    @app.route('/saml/metadata')
    def saml_metadata():
        """SAML Service Provider metadata."""
        try:
            metadata = saml_authenticator.get_metadata()
            response = app.response_class(
                response=metadata,
                status=200,
                mimetype='application/xml'
            )
            return response
        except Exception as e:
            logger.error(f"Metadata generation failed: {str(e)}")
            return "Metadata generation failed", 500
    
    # API routes
    @app.route('/api/session/status')
    @login_required
    def api_session_status():
        """API endpoint for session status."""
        session_info = session_manager.get_session_info()
        return jsonify(session_info)
    
    @app.route('/api/session/extend', methods=['POST'])
    @login_required
    def api_session_extend():
        """API endpoint to extend session."""
        import time
        session['last_activity'] = time.time()
        session_info = session_manager.get_session_info()
        return jsonify({
            'success': True,
            'time_remaining': session_info.get('time_remaining', 0)
        })
    
    @app.route('/api/user/info')
    @login_required
    def api_user_info():
        """API endpoint for user information."""
        user_info = session_manager.get_user_info()
        return jsonify(user_info)
    
    # Health check
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        """Set security headers."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if app.config.get('REQUIRE_HTTPS', False):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    # Development server configuration
    import time
    
    # Add time module to globals for session extension
    app.jinja_env.globals['time'] = time
    
    # Run the application
    port = int(os.getenv('PORT', 12000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting Flask application on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Configuration: {os.getenv('FLASK_ENV', 'development')}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )