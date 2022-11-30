import os
from flask_appbuilder.security.manager import AUTH_OAUTH

# Application secret key

SECRET_KEY = os.environ["SECRET_KEY"]

# Credentials for connecting to the Open edX MySQL database
OPENEDX_DATABASE = {
    'host': os.environ["OPENEDX_MYSQL_HOST"],
    'port': int(os.environ["OPENEDX_MYSQL_PORT"]),
    'database': os.environ["OPENEDX_MYSQL_DATABASE"],
    'user': os.environ["OPENEDX_MYSQL_USERNAME"],
    'password': os.environ["OPENEDX_MYSQL_PASSWORD"],
}

OPENEDX_API_URLS = {
    "get_username": os.environ["OPENEDX_USERNAME_URL"],
    "get_profile": os.environ["OPENEDX_USER_PROFILE_URL"],
    "get_courses": os.environ["OPENEDX_COURSES_LIST_URL"],
}

# Set the authentication type to OAuth
AUTH_TYPE = AUTH_OAUTH

OAUTH_PROVIDERS = [
    {   'name':'openedxsso',
        'token_key':'access_token', # Name of the token in the response of access_token_url
        'icon':'fa-address-card',   # Icon for the provider
        'remote_app': {
            'client_id': os.environ["OAUTH2_CLIENT_ID"],
            'client_secret': os.environ["OAUTH2_CLIENT_SECRET"],
            'client_kwargs':{
                'scope': 'read'               # Scope for the Authorization
            },
            'access_token_method':'POST',    # HTTP Method to call access_token_url
            'access_token_params':{        # Additional parameters for calls to access_token_url
                'client_id': os.environ["OAUTH2_CLIENT_ID"],
            },
            'access_token_headers':{    # Additional headers for calls to access_token_url
                'Authorization': 'Basic Base64EncodedClientIdAndSecret'
            },
            'api_base_url': os.environ["OAUTH2_BASE_URL"],
            'access_token_url': os.environ["OAUTH2_ACCESS_TOKEN_URL"],
            'authorize_url': os.environ["OAUTH2_AUTHORIZE_URL"],
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
    "openedx": ["Open edX"], # Open edX datastore, manually created
    "public": ["Public"],    # AKA anonymous users
}

from openedx_sso_security_manager import OpenEdxSsoSecurityManager, can_view_courses
CUSTOM_SECURITY_MANAGER = OpenEdxSsoSecurityManager


# Enable use of variables in datasets/queries
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Add this custom template processor which returns the list of courses the current user can access
JINJA_CONTEXT_ADDONS = {
    'can_view_courses': can_view_courses
}
