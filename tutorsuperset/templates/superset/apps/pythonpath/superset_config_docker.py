import os
from urllib.parse import urljoin
from flask_appbuilder.security.manager import AUTH_OAUTH

# Application secret key

SECRET_KEY = os.environ["SECRET_KEY"]

# Don't limit the number of rows that can be used in queries
ROW_LIMIT = int({{ SUPERSET_ROW_LIMIT }})
SQL_MAX_ROW = ROW_LIMIT

# Credentials for connecting to the Open edX MySQL database
OPENEDX_DATABASE = {
    'host': os.environ["OPENEDX_MYSQL_HOST"],
    'port': int(os.environ["OPENEDX_MYSQL_PORT"]),
    'database': os.environ["OPENEDX_MYSQL_DATABASE"],
    'user': os.environ["OPENEDX_MYSQL_USERNAME"],
    'password': os.environ["OPENEDX_MYSQL_PASSWORD"],
}

OPENEDX_LMS_ROOT_URL = os.environ["OPENEDX_LMS_ROOT_URL"]
OPENEDX_API_URLS = {
    "get_username": urljoin(OPENEDX_LMS_ROOT_URL, os.environ["OPENEDX_USERNAME_PATH"]),
    "get_profile": urljoin(OPENEDX_LMS_ROOT_URL, os.environ["OPENEDX_USER_PROFILE_PATH"]),
    "get_courses": urljoin(OPENEDX_LMS_ROOT_URL, os.environ["OPENEDX_COURSES_LIST_PATH"]),
}

# Set the authentication type to OAuth
AUTH_TYPE = AUTH_OAUTH

OAUTH_PROVIDERS = [
    {   'name':'openedxsso',
        'token_key':'access_token', # Name of the token in the response of access_token_url
        'icon':'fa-address-card',   # Icon for the provider
        'remote_app': {
            'client_id': os.environ["SSO_CLIENT_ID"],
            'client_secret': os.environ["SSO_CLIENT_SECRET"],
            'client_kwargs':{
                'scope': 'read'               # Scope for the Authorization
            },
            'access_token_method':'POST',    # HTTP Method to call access_token_url
            'access_token_params':{        # Additional parameters for calls to access_token_url
                'client_id': os.environ["SSO_CLIENT_ID"],
            },
            'access_token_headers':{    # Additional headers for calls to access_token_url
                'Authorization': 'Basic Base64EncodedClientIdAndSecret'
            },
            'api_base_url': OPENEDX_LMS_ROOT_URL,
            'access_token_url': urljoin(OPENEDX_LMS_ROOT_URL, os.environ["OAUTH2_ACCESS_TOKEN_PATH"]),
            'authorize_url': urljoin(OPENEDX_LMS_ROOT_URL, os.environ["OAUTH2_AUTHORIZE_PATH"]),
        }
    }
]

# Will allow user self registration, allowing to create Flask users from Authorized User
AUTH_USER_REGISTRATION = True

# The default user self registration role
AUTH_USER_REGISTRATION_ROLE = "Gamma"

# Should we replace ALL the user's roles each login, or only on registration?
AUTH_ROLES_SYNC_AT_LOGIN = True

# map from the values of `userinfo["role_keys"]` to a list of Superset roles
# cf https://superset.apache.org/docs/security/#roles
AUTH_ROLES_MAPPING = {
    "admin": ["Admin"],      # Superusers
    "alpha": ["Alpha"],      # Global staff
    "gamma": ["Gamma"],      # Course staff
    "openedx": ["{{SUPERSET_OPENEDX_ROLE_NAME}}"], # All Open edX users
    "public": ["Public"],    # AKA anonymous users
}

from openedx_sso_security_manager import OpenEdxSsoSecurityManager
CUSTOM_SECURITY_MANAGER = OpenEdxSsoSecurityManager


# Enable use of variables in datasets/queries
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    # Can't enable this until we can add roles to dashboards
    # cf https://github.com/opus-42/superset-api-client/pull/31
    #"DASHBOARD_RBAC": True,
}

# Add this custom template processor which returns the list of courses the current user can access
from openedx_jinja_filters import can_view_courses
JINJA_CONTEXT_ADDONS = {
    'can_view_courses': can_view_courses,
}
