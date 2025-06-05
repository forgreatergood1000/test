# Deployment Guide

This document provides comprehensive instructions for deploying the SAML Azure AD Authentication application to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Azure AD Configuration](#azure-ad-configuration)
3. [AWS Cognito Setup](#aws-cognito-setup)
4. [Application Configuration](#application-configuration)
5. [Production Deployment](#production-deployment)
6. [Security Considerations](#security-considerations)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Python 3.8 or higher
- Linux/Unix-based operating system
- SSL/TLS certificate for HTTPS
- Domain name for the application

### Required Services

- Azure Active Directory tenant
- AWS account (for Cognito integration)
- Web server (nginx, Apache, or similar)
- WSGI server (Gunicorn, uWSGI, or similar)

### Dependencies

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv xmlsec1 libxmlsec1-dev pkg-config

# CentOS/RHEL
sudo yum install -y python3-pip xmlsec1 xmlsec1-devel pkgconfig

# macOS
brew install xmlsec1 pkg-config
```

## Azure AD Configuration

### Step 1: Create Enterprise Application

1. Sign in to the Azure portal (https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **Enterprise applications**
3. Click **New application** > **Create your own application**
4. Choose **Integrate any other application you don't find in the gallery**
5. Name your application (e.g., "SAML Auth App")

### Step 2: Configure SAML Single Sign-On

1. In your enterprise application, go to **Single sign-on**
2. Select **SAML** as the single sign-on method
3. Configure the following settings:

#### Basic SAML Configuration

- **Identifier (Entity ID)**: `https://your-domain.com/saml/metadata`
- **Reply URL (Assertion Consumer Service URL)**: `https://your-domain.com/saml/acs`
- **Sign on URL**: `https://your-domain.com/auth/login`
- **Logout URL**: `https://your-domain.com/auth/logout`

#### User Attributes & Claims

Configure the following claims:

| Claim Name | Source | Source Attribute |
|------------|--------|------------------|
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | Attribute | user.mail |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` | Attribute | user.givenname |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` | Attribute | user.surname |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name` | Attribute | user.userprincipalname |
| `groups` | Attribute | user.groups |

### Step 3: Download Certificates

1. In the **SAML Signing Certificate** section
2. Download the **Certificate (Base64)** file
3. Save it as `azure_ad_cert.pem` in your application directory

### Step 4: Get Azure AD Metadata

1. Copy the **App Federation Metadata Url**
2. Download the metadata XML file
3. Extract the following information:
   - **Entity ID**: Found in `<EntityDescriptor entityID="...">`
   - **SSO URL**: Found in `<SingleSignOnService Location="...">`
   - **SLO URL**: Found in `<SingleLogoutService Location="...">`

## AWS Cognito Setup

### Step 1: Create User Pool

1. Sign in to the AWS Console
2. Navigate to **Amazon Cognito**
3. Click **Create user pool**
4. Configure the following settings:

#### Authentication providers
- **Cognito user pool sign-in options**: Email

#### Security requirements
- **Password policy**: Custom (set according to your requirements)
- **Multi-factor authentication**: Optional or Required

#### Sign-up experience
- **Self-service sign-up**: Disabled (users will be created via SAML)
- **Attribute verification and user account confirmation**: Email

#### Message delivery
- **Email provider**: Amazon SES or Cognito default

#### App integration
- **User pool name**: `saml-auth-user-pool`
- **App client name**: `saml-auth-client`
- **Client secret**: Generate a client secret

### Step 2: Configure Custom Attributes

Add the following custom attributes to store group information:

1. Go to **User pool properties** > **Attributes**
2. Add custom attributes:
   - `custom:azure_groups` (String, Mutable)
   - `custom:primary_group` (String, Mutable)
   - `custom:access_level` (String, Mutable)

### Step 3: Get Cognito Configuration

Note down the following values:
- **User Pool ID**: Found in the user pool overview
- **App Client ID**: Found in app integration settings
- **App Client Secret**: Found in app client settings
- **Region**: AWS region where the user pool is created

## Application Configuration

### Step 1: Environment Variables

Create a `.env` file in your application root:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here-change-this-in-production
SESSION_TIMEOUT=3600

# SAML Configuration
SAML_ENTITY_ID=https://your-domain.com/saml/metadata
SAML_ACS_URL=https://your-domain.com/saml/acs
SAML_SLS_URL=https://your-domain.com/saml/sls
SAML_SSO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_SLO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
SAML_IDP_ENTITY_ID=https://sts.windows.net/your-tenant-id/
SAML_X509_CERT_PATH=/path/to/azure_ad_cert.pem

# AWS Cognito Configuration (Optional)
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/saml-auth/app.log
```

### Step 2: SSL Certificates

Ensure you have valid SSL certificates:

```bash
# Create certificates directory
sudo mkdir -p /etc/ssl/saml-auth

# Copy your certificates
sudo cp your-domain.crt /etc/ssl/saml-auth/
sudo cp your-domain.key /etc/ssl/saml-auth/
sudo cp azure_ad_cert.pem /etc/ssl/saml-auth/

# Set proper permissions
sudo chmod 600 /etc/ssl/saml-auth/*
sudo chown www-data:www-data /etc/ssl/saml-auth/*
```

## Production Deployment

### Step 1: Application Setup

```bash
# Create application directory
sudo mkdir -p /opt/saml-auth
cd /opt/saml-auth

# Clone or copy your application
git clone <your-repository> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set proper permissions
sudo chown -R www-data:www-data /opt/saml-auth
sudo chmod +x app.py
```

### Step 2: Gunicorn Configuration

Create `/opt/saml-auth/gunicorn.conf.py`:

```python
# Gunicorn configuration file
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
user = "www-data"
group = "www-data"
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
forwarded_allow_ips = '*'
```

### Step 3: Systemd Service

Create `/etc/systemd/system/saml-auth.service`:

```ini
[Unit]
Description=SAML Auth Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/saml-auth
Environment=PATH=/opt/saml-auth/venv/bin
ExecStart=/opt/saml-auth/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable saml-auth
sudo systemctl start saml-auth
sudo systemctl status saml-auth
```

### Step 4: Nginx Configuration

Create `/etc/nginx/sites-available/saml-auth`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/saml-auth/your-domain.crt;
    ssl_certificate_key /etc/ssl/saml-auth/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Protocol $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_redirect off;
    }

    location /static/ {
        alias /opt/saml-auth/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/saml-auth /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Security Considerations

### 1. Environment Variables

- Store sensitive configuration in environment variables
- Use a secrets management system in production
- Never commit secrets to version control

### 2. SSL/TLS Configuration

- Use strong SSL/TLS configuration
- Implement HSTS headers
- Use secure cipher suites
- Regularly update certificates

### 3. Session Security

- Use secure session cookies
- Implement session timeout
- Use CSRF protection
- Validate session integrity

### 4. Input Validation

- Validate all SAML assertions
- Sanitize user inputs
- Implement proper error handling
- Log security events

### 5. Access Control

- Implement role-based access control
- Validate group memberships
- Use principle of least privilege
- Regular access reviews

## Monitoring and Logging

### Application Logs

Configure structured logging in `/opt/saml-auth/logging.conf`:

```ini
[loggers]
keys=root,saml_auth

[handlers]
keys=fileHandler,consoleHandler

[formatters]
keys=jsonFormatter

[logger_root]
level=INFO
handlers=fileHandler,consoleHandler

[logger_saml_auth]
level=DEBUG
handlers=fileHandler
qualname=saml_auth
propagate=0

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=jsonFormatter
args=('/var/log/saml-auth/app.log',)

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=jsonFormatter
args=(sys.stdout,)

[formatter_jsonFormatter]
format={"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}
```

### Health Monitoring

Set up monitoring for:

- Application health endpoint (`/health`)
- Response times
- Error rates
- Authentication success/failure rates
- Session metrics

### Log Analysis

Monitor logs for:

- Failed authentication attempts
- Unusual access patterns
- Error conditions
- Performance issues

## Troubleshooting

### Common Issues

#### 1. SAML Configuration Errors

**Problem**: "Invalid dict settings: idp_cert_or_fingerprint_not_found_and_required"

**Solution**: 
- Verify Azure AD certificate is properly configured
- Check certificate file permissions
- Ensure certificate path is correct in environment variables

#### 2. Authentication Failures

**Problem**: Users cannot authenticate

**Solution**:
- Check Azure AD application configuration
- Verify SAML URLs match exactly
- Review Azure AD logs for errors
- Check application logs for SAML assertion issues

#### 3. Group Mapping Issues

**Problem**: Groups not appearing in user session

**Solution**:
- Verify group claims are configured in Azure AD
- Check group claim name mapping
- Review SAML assertion content
- Validate Cognito attribute mapping

#### 4. Session Issues

**Problem**: Users getting logged out unexpectedly

**Solution**:
- Check session timeout configuration
- Verify session storage configuration
- Review session cookie settings
- Check for session conflicts

### Debug Mode

For troubleshooting, temporarily enable debug mode:

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
```

**Warning**: Never use debug mode in production!

### Log Analysis Commands

```bash
# View application logs
sudo tail -f /var/log/saml-auth/app.log

# Check authentication events
sudo grep "authentication" /var/log/saml-auth/app.log

# Monitor error rates
sudo grep "ERROR" /var/log/saml-auth/app.log | tail -20

# Check service status
sudo systemctl status saml-auth
sudo systemctl status nginx
```

## Support

For additional support:

1. Check the application logs
2. Review Azure AD sign-in logs
3. Verify network connectivity
4. Test with SAML debugging tools
5. Consult the README.md for additional information

---

**Note**: This deployment guide assumes a Linux-based production environment. Adjust configurations as needed for your specific infrastructure and requirements.