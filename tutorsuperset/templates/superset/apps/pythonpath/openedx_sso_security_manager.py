from collections import namedtuple
import logging
import MySQLdb

from flask import current_app, session

from superset.security import SupersetSecurityManager
from superset.utils.memoized import memoized

from flask_appbuilder.security.views import AuthOAuthView
from flask_appbuilder.views import expose
from werkzeug.wrappers import Response as WerkzeugResponse
from flask import current_app, redirect, request, session, flash
from flask_appbuilder.utils.base import get_safe_redirect
from flask_appbuilder._compat import as_unicode
from authlib.integrations.flask_client.apps import FlaskOAuth2App

import jwt
import re

from flask_login import login_user


log = logging.getLogger(__name__)


from authlib.common.urls import add_params_to_qs, add_params_to_uri


def add_to_uri(token, uri):
    """Add a Bearer Token to the request URI.
    Not recommended, use only if client can't use authorization header or body.

    http://www.example.com/path?access_token=h480djs93hd8
    """
    return add_params_to_uri(uri, [('access_token', token)])


def add_to_headers(token, headers=None):
    """Add a Bearer Token to the request URI.
    Recommended method of passing bearer tokens.

    Authorization: Bearer h480djs93hd8
    """
    headers = headers or {}
    headers['Authorization'] = 'JWT {}'.format(token)
    return headers


def add_to_body(token, body=None):
    """Add a Bearer Token to the request body.

    access_token=h480djs93hd8
    """
    if body is None:
        body = ''
    return add_params_to_qs(body, [('access_token', token)])


def add_bearer_jwt_token(token, uri, headers, body, placement='header'):
    if placement in ('uri', 'url', 'query'):
        uri = add_to_uri(token, uri)
    elif placement in ('header', 'headers'):
        headers = add_to_headers(token, headers)
    elif placement == 'body':
        body = add_to_body(token, body)
    return uri, headers, body


class FlaskOauth2OpenedxApp(FlaskOAuth2App):

    def fetch_access_token(self, url=None, token_type="jwt", **kwargs):
        """Alias for fetch_token."""
        return self.fetch_token(url, token_type=token_type, **kwargs)


class OpenedxSSOView(AuthOAuthView):

    @expose("/oauth-authorized/<provider>")
    def oauth_authorized(self, provider: str) -> WerkzeugResponse:
        log.debug("Authorized init")
        if provider not in self.appbuilder.sm.oauth_remotes:
            flash(u"Provider not supported.", "warning")
            log.warning("OAuth authorized got an unknown provider %s", provider)
            return redirect(self.appbuilder.get_url_for_login)
        try:
            resp = self.appbuilder.sm.oauth_remotes[provider].authorize_access_token(token_type="jwt")
        except Exception as e:
            log.error("Error authorizing OAuth access token: {0}".format(e))
            flash("The request to sign in was denied.", "error")
            return redirect(self.appbuilder.get_url_for_login)
        if resp is None:
            flash("You denied the request to sign in.", "warning")
            return redirect(self.appbuilder.get_url_for_login)
        log.debug("OAUTH Authorized resp: {0}".format(resp))
        # Retrieves specific user info from the provider
        try:
            self.appbuilder.sm.set_oauth_session(provider, resp)
            userinfo = self.appbuilder.sm.oauth_user_info(provider, resp)
        except Exception as e:
            log.error("Error returning OAuth user info: {0}".format(e))
            user = None
        else:
            log.debug("User info retrieved from {0}: {1}".format(provider, userinfo))
            # User email is not whitelisted
            if provider in self.appbuilder.sm.oauth_whitelists:
                whitelist = self.appbuilder.sm.oauth_whitelists[provider]
                allow = False
                for email in whitelist:
                    if "email" in userinfo and re.search(email, userinfo["email"]):
                        allow = True
                        break
                if not allow:
                    flash(u"You are not authorized.", "warning")
                    return redirect(self.appbuilder.get_url_for_login)
            else:
                log.debug("No whitelist for OAuth provider")
            user = self.appbuilder.sm.auth_user_oauth(userinfo)

        if user is None:
            flash(as_unicode(self.invalid_login_message), "warning")
            return redirect(self.appbuilder.get_url_for_login)
        else:
            login_user(user)
            try:
                state = jwt.decode(
                    request.args["state"],
                    self.appbuilder.app.config["SECRET_KEY"],
                    algorithms=["HS256"],
                )
            except jwt.InvalidTokenError:
                raise Exception("State signature is not valid!")

            next_url = self.appbuilder.get_url_for_index
            # Check if there is a next url on state
            if "next" in state and len(state["next"]) > 0:
                next_url = get_safe_redirect(state["next"][0])
            return redirect(next_url)



class OpenEdxSsoSecurityManager(SupersetSecurityManager):

    authoauthview = OpenedxSSOView

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oauth.oauth2_client_cls.client_cls.token_auth_class.SIGN_METHODS.update({
            "jwt": add_bearer_jwt_token,
        })
        self.oauth.oauth2_client_cls = FlaskOauth2OpenedxApp

    def set_oauth_session(self, provider, oauth_response):
        """
        Store the oauth token in the session for later retrieval.
        """
        res = super().set_oauth_session(provider, oauth_response)

        if provider == "openedxsso":
            session["oauth_token"] = oauth_response["access_token"]
        return res

    def oauth_user_info(self, provider, response=None):
        openedx_apis = current_app.config['OPENEDX_API_URLS']
        if provider == 'openedxsso':
            oauth_remote = self.appbuilder.sm.oauth_remotes[provider]
            username_url = openedx_apis['get_username']
            me = oauth_remote.get(username_url).json()
            username = me['username']

            user_profile_url = openedx_apis['get_profile'].format(username=username)
            user_profile = oauth_remote.get(user_profile_url).json()

            user_roles = self._get_user_roles(username)

            return {
                'name': user_profile['name'],
                'email': user_profile['email'],
                'id': user_profile['username'],
                'username': user_profile['username'],
                'first_name': '',
                'last_name': '',
                'role_keys': user_roles,
            }

    def get_oauth_token(self, token=None):
        """
        Retrieves the oauth token from the session.

        Returns an empty hash if there is no session.
        """
        # TODO: handle refreshing expired tokens?
        return session.get("oauth_token", {})

    @property
    def access_token(self):
        """
        Returns the string access_token portion of the current OAuth token.
        """
        return self.get_oauth_token().get('access_token')

    def _get_user_roles(self, username):
        """
        Returns the Superset roles that should be associated with the given user.
        """
        user_access = _fetch_openedx_user_access(username)
        if user_access.is_superuser:
            return ["admin", "openedx"]
        elif user_access.is_staff:
            return ["alpha", "openedx"]
        else:
            # User has to have staff access to one or more courses to view any content here.
            courses = self.get_courses(username)
            if courses:
                return ["gamma", "openedx"]
            return []

    @memoized(watch=('access_token',))
    def get_courses(self, username, permission="staff", next_url=None):
        """
        Returns the list of courses the current user has access to.
        """
        courses = []
        provider = session.get("oauth_provider")
        oauth_remote = self.oauth_remotes.get(provider)
        if not oauth_remote:
            logging.error("No OAuth2 provider? expected openedx")
            return courses

        token = self.get_oauth_token()
        if not token:
            logging.error("No oauth token? expected one provided by openedx")
            return courses

        openedx_apis = current_app.config['OPENEDX_API_URLS']
        courses_url = openedx_apis['get_courses'].format(username=username, permission=permission)
        url = next_url or courses_url
        response = oauth_remote.get(url, token=token).json()

        for course in response.get('results', []):
            course_id = course.get('course_id')
            if course_id:
                courses.append(course_id)

        # Recurse to iterate over all the pages of results
        if response.get("next"):
            next_courses = self.get_courses(username, permission=permission, next_url=response['next'])
            for course_id in next_courses:
                courses.append(course_id)

        return courses


UserAccess = namedtuple(
    "UserAccess", ["username", "is_superuser", "is_staff"]
)


def _fetch_openedx_user_access(username):
    """
    Fetches the given user's access details from the Open edX User database

    NOTE: Open edX JWT seems to provide this info with the "profile" scope.
    How do we access this via the AllAuth OAuth2?
    """
    cxn = _connect_openedx_db()
    cursor = cxn.cursor()

    query = "SELECT is_staff, is_superuser FROM auth_user WHERE username=%s"
    if cursor.execute(query, (username,)):
        (is_staff, is_superuser) = cursor.fetchone()
        user_access = UserAccess(
            username=username,
            is_superuser=is_superuser,
            is_staff=is_staff,
        )
    else:
        user_access = UserAccess(
            username=username,
            is_superuser=False,
            is_staff=False,
        )

    cursor.close()
    cxn.close()
    return user_access


def _connect_openedx_db():
    """
    Return an open connection to the Open edX MySQL database.
    """
    openedx_database = current_app.config['OPENEDX_DATABASE']
    return MySQLdb.connect(**openedx_database)
