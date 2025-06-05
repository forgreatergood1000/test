# SAML Azure AD Authentication with Cognito Integration

A comprehensive Flask web application that demonstrates secure authentication using SAML 2.0 with Azure Active Directory, automatic group claims mapping to Amazon Cognito custom attributes, and robust session management with group-based access control.

## 🚀 Features

### Authentication & Security
- **SAML 2.0 SSO** with Azure Active Directory
- **Secure session management** with configurable timeouts
- **Group-based access control** and authorization
- **CSRF protection** and security headers
- **Input validation** and sanitization
- **Error handling** without information disclosure

### Azure AD Integration
- **SAML assertion processing** and validation
- **Group claims extraction** from Azure AD
- **User attribute mapping** (email, name, groups)
- **Single Sign-On (SSO)** and Single Logout (SLO)
- **Metadata generation** for SP configuration

### Amazon Cognito Integration
- **Automatic user creation/update** in Cognito User Pools
- **Group mapping** to custom Cognito attributes
- **Attribute synchronization** between SAML and Cognito
- **Flexible mapping configuration** via environment variables

### User Interface
- **Responsive design** with Bootstrap 5
- **Real-time session monitoring** and warnings
- **Comprehensive user dashboard** with profile information
- **Group membership display** and access control indicators
- **Session information** and management tools

## 📋 Prerequisites

- Python 3.8+
- Azure Active Directory tenant with SAML app registration
- Amazon Cognito User Pool (optional)
- SSL certificate for production deployment

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd saml-azure-ad-auth
```

### 2. Install Dependencies

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y libxmlsec1-dev libxmlsec1-openssl pkg-config

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# SAML Configuration
SAML_SP_ENTITY_ID=https://your-app.example.com
SAML_SP_ACS_URL=https://your-app.example.com/saml/acs
SAML_SP_SLS_URL=https://your-app.example.com/saml/sls
SAML_IDP_ENTITY_ID=https://sts.windows.net/your-tenant-id/
SAML_IDP_SSO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_IDP_SLS_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_IDP_X509_CERT=your-azure-ad-certificate

# AWS Cognito Configuration (Optional)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
COGNITO_USER_POOL_ID=your-user-pool-id
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret

# Group Mapping Configuration
GROUP_MAPPING={"azure_group_1": "cognito_attribute_1", "azure_group_2": "cognito_attribute_2"}
```

## 🔧 Azure AD Configuration

### 1. Create Enterprise Application

1. Go to Azure Portal → Azure Active Directory → Enterprise Applications
2. Click "New application" → "Create your own application"
3. Choose "Integrate any other application you don't find in the gallery"

### 2. Configure SAML

1. Go to Single sign-on → SAML
2. Configure the following:

**Basic SAML Configuration:**
- Identifier (Entity ID): `https://your-app.example.com`
- Reply URL (ACS): `https://your-app.example.com/saml/acs`
- Sign on URL: `https://your-app.example.com`
- Logout URL: `https://your-app.example.com/saml/sls`

**Attributes & Claims:**
- Add group claims: Security groups or All groups
- Configure name identifier format: Email address

### 3. Download Certificate

Download the Base64 certificate and add it to your `.env` file as `SAML_IDP_X509_CERT`.

### 4. Assign Users

Assign users and groups to the application in the "Users and groups" section.

## ☁️ AWS Cognito Configuration

### 1. Create User Pool

1. Go to AWS Console → Cognito → User Pools
2. Create a new user pool with the following settings:
   - Sign-in options: Email
   - Password policy: As required
   - MFA: Optional
   - User account recovery: Email only

### 2. Configure Custom Attributes

Add custom attributes for group mappings:
- `saml_groups` (String)
- `saml_nameid` (String)
- Add any custom attributes for your group mappings

### 3. Create App Client

1. Create an app client with the following settings:
   - App type: Confidential client
   - Authentication flows: ALLOW_ADMIN_USER_PASSWORD_AUTH
   - Generate client secret: Yes

### 4. Configure IAM

Create an IAM user with the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminUpdateUserAttributes",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminDeleteUser",
                "cognito-idp:ListUsers",
                "cognito-idp:DescribeUserPool"
            ],
            "Resource": "arn:aws:cognito-idp:region:account:userpool/your-user-pool-id"
        }
    ]
}
```

## 🚀 Running the Application

### Development Mode

```bash
python app.py
```

The application will be available at:
- https://work-1-poevxxzbytddmxlz.prod-runtime.all-hands.dev (port 12000)
- https://work-2-poevxxzbytddmxlz.prod-runtime.all-hands.dev (port 12001)

### Production Mode

```bash
# Set environment
export FLASK_ENV=production
export FLASK_DEBUG=False

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:12000 app:app
```

## 📁 Project Structure

```
saml-azure-ad-auth/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── saml_auth.py          # SAML authentication logic
│   │   └── session_manager.py    # Session management and access control
│   ├── cognito/
│   │   ├── __init__.py
│   │   └── cognito_client.py     # Amazon Cognito integration
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css         # Custom styles
│   │   └── js/
│   │       └── app.js            # Client-side functionality
│   ├── templates/
│   │   ├── errors/               # Error pages
│   │   ├── base.html             # Base template
│   │   ├── index.html            # Home page
│   │   ├── dashboard.html        # User dashboard
│   │   ├── profile.html          # User profile
│   │   └── session_info.html     # Session information
│   └── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py               # Configuration management
├── certs/                        # SSL certificates (production)
├── app.py                        # Main Flask application
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
└── README.md                     # This file
```

## 🔒 Security Features

### Authentication Security
- **SAML assertion validation** with signature verification
- **Session timeout** with configurable duration
- **Secure session storage** with signed cookies
- **CSRF protection** on all forms
- **Input validation** and sanitization

### Transport Security
- **HTTPS enforcement** in production
- **Security headers** (HSTS, X-Frame-Options, etc.)
- **Secure cookie settings** with HttpOnly and Secure flags

### Access Control
- **Group-based authorization** with decorators
- **Role-based access control** for different features
- **Session monitoring** with automatic logout
- **Permission checking** for sensitive operations

## 🎯 Usage Examples

### Basic Authentication Flow

1. User visits the application
2. Clicks "Sign In with Azure AD"
3. Redirected to Azure AD for authentication
4. Azure AD sends SAML assertion with user info and groups
5. Application processes assertion and creates/updates Cognito user
6. User is logged in with appropriate permissions

### Group-Based Access Control

```python
from app.auth.session_manager import group_required

@app.route('/admin')
@group_required(['admin', 'administrators'])
def admin_panel():
    return render_template('admin.html')

@app.route('/reports')
@group_required(['managers', 'analysts'], require_all=False)
def reports():
    return render_template('reports.html')
```

### Session Management

```python
from app.auth.session_manager import SessionManager

session_manager = SessionManager()

# Check authentication
if session_manager.is_authenticated():
    user_info = session_manager.get_user_info()
    user_groups = session_manager.get_user_groups()

# Check specific permissions
if session_manager.has_group('admin'):
    # Admin functionality
    pass
```

## 🔧 Customization

### Group Mapping

Configure group mappings in your `.env` file:

```env
GROUP_MAPPING={"Azure_Admins": "admin_access", "Azure_Users": "user_access", "Azure_Managers": "manager_access"}
```

### Session Timeout

Adjust session timeout in configuration:

```env
SESSION_TIMEOUT=7200  # 2 hours in seconds
```

### Custom Attributes

Add custom SAML attribute mappings in `app/auth/saml_auth.py`:

```python
def _extract_user_attributes(self, auth):
    # Add custom attribute extraction logic
    custom_attr = self._get_attribute_value(attributes, ['custom:department'])
    user_data['department'] = custom_attr
```

## 🐛 Troubleshooting

### Common Issues

1. **SAML Certificate Issues**
   - Ensure certificate is properly formatted (no spaces, correct line breaks)
   - Verify certificate is not expired
   - Check certificate matches Azure AD configuration

2. **Cognito Integration Failures**
   - Verify AWS credentials and permissions
   - Check User Pool ID and Client ID
   - Ensure custom attributes are created in Cognito

3. **Session Issues**
   - Check Flask secret key configuration
   - Verify session storage permissions
   - Monitor session timeout settings

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Check

Monitor application health:

```bash
curl https://your-app.example.com/health
```

## 📊 Monitoring and Logging

The application includes comprehensive logging for:
- Authentication events
- Session management
- Cognito integration
- Error conditions
- Security events

Logs are structured and include:
- Timestamp
- Log level
- Component name
- Event details
- User context (when available)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the logs for error details
- Open an issue on GitHub
- Contact the development team

## 🔄 Updates and Maintenance

Regular maintenance tasks:
- Update dependencies for security patches
- Rotate certificates before expiration
- Monitor session and authentication logs
- Review and update group mappings
- Test backup and recovery procedures