from collections import namedtuple
import logging
import MySQLdb

from flask import current_app, session

from superset.security import SupersetSecurityManager
from superset.utils.memoized import memoized


class OpenEdxSsoSecurityManager(SupersetSecurityManager):

    def set_oauth_session(self, provider, oauth_response):
        """
        Store the oauth token in the session for later retrieval.
        """
        res = super().set_oauth_session(provider, oauth_response)

        if provider == "openedxsso":
            session["oauth_token"] = oauth_response
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
            return ["admin", "alpha", "openedx"]
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
