from collections import namedtuple
import logging
import MySQLdb

from flask import current_app, session
from superset.security import SupersetSecurityManager
from superset.extensions import security_manager
from superset.utils.core import get_username
from superset.utils.memoized import memoized


class OpenEdxSsoSecurityManager(SupersetSecurityManager):

    def set_oauth_session(self, provider, oauth_response):
        """
        Store the oauth token in the session for later retrieval.
        """
        res = super().set_oauth_session(provider, oauth_response)

        # TODO: better to save to a database
        if provider == "openedxsso":
            _set_oauth_token(oauth_response)
        return res

    def oauth_user_info(self, provider, response=None):
        openedx_apis = current_app.config['OPENEDX_API_URLS']
        if provider == 'openedxsso':
            oauth_remote = self.appbuilder.sm.oauth_remotes[provider]
            username_url = openedx_apis['get_username']
            me = oauth_remote.get(username_url).json()
            logging.debug(f"{username_url}: {me}")
            username = me['username']

            user_profile_url = openedx_apis['get_profile'].format(username=username)
            user_profile = oauth_remote.get(user_profile_url).json()
            logging.debug(f"{user_profile_url}: {user_profile}")

            user_roles = _get_user_roles(username)
            logging.debug(f"user_roles: {user_roles}")

            return {
                'name': user_profile['name'],
                'email': user_profile['email'],
                'id': user_profile['username'],
                'username': user_profile['username'],
                'first_name': '',
                'last_name': '',
                'role_keys': user_roles,
            }


def _set_oauth_token(token):
    """
    Stores the oauth token in the session.
    """
    # TODO: is it better to store this in the database?
    session["oauth_token"] = token


def _get_oauth_token():
    """
    Retrieves the oauth token from the session.

    Returns an empty hash if there is no session.
    """
    # TODO: handle refreshing expired tokens?
    return session.get("oauth_token", {})


def _get_user_roles(username):
    """
    Returns the Superset roles that should be associated with the given user.
    """
    user_access = _fetch_user_access(username)
    logging.debug(f"user access: {user_access}")

    if user_access.is_superuser:
        return ["admin", "alpha", "openedx"]
    elif user_access.is_staff:
        return ["alpha", "openedx"]
    else:
        # User has to have staff access to one or more courses to view any content here.
        courses = _get_courses(username)
        if courses:
            return ["gamma", "openedx"]
        return []


ALL_COURSES = "1 = 1"
NO_COURSES = "1 = 0"

def can_view_courses(username, field_name='course_id'):
    """
    Returns SQL WHERE clause which restricts access to the courses the current user has staff access to.
    """
    user = security_manager.get_user_by_username(username)
    if user:
        user_roles = security_manager.get_user_roles(user)
    else:
        user_roles = []
    logging.debug(f"can_view_courses: {username} roles: {user_roles}")

    # Users with no roles don't get to see any courses
    if not user_roles:
        return NO_COURSES

    # Superusers and global staff have access to all courses
    if ("Admin" in user_roles) or ("Alpha" in user_roles):
        return ALL_COURSES

    # Everyone else only has access if they're staff on a course.
    courses = _get_courses(username)
    logging.debug(f"{username} is course staff on {courses}")

    # FIXME: what happens when the list of courses grows beyond what the query will handle?
    if courses:
        course_id_list = ", ".join(
            f'"{course_id}"' for course_id in courses
        )
        return f"{field_name} in ({course_id_list})"
    else:
        # If you're not course staff on any courses, you don't get to see any.
        return NO_COURSES


UserAccess = namedtuple(
    "UserAccess", ["username", "is_superuser", "is_staff"]
)


def _fetch_user_access(username):
    """
    Fetches the given user's access details from the Open edX User database
    (since Open edX doesn't have an API for this).
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


@memoized
def _get_courses(username, permission="staff", next_url=None):
    """
    Returns the list of courses the current user has access to.
    """
    courses = []

    provider = session.get("oauth_provider")
    oauth_remote = security_manager.oauth_remotes.get(provider)
    if not oauth_remote:
        logging.error("No OAuth2 provider? expected openedx")
        return courses

    token = _get_oauth_token()
    if not token:
        logging.error("No access_token? expected one provided by openedx")
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
        next_courses = _get_courses(username, permission=permission, next_url=response['next'])
        for course_id in next_courses:
            courses.append(course_id)

    logging.debug(f"{username} has {permission} access to {courses}")
    return courses
