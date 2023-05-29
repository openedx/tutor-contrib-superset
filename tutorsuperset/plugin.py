import os
from glob import glob

import pkg_resources
from tutor import hooks

from .__about__ import __version__

########################################
# CONFIGURATION
########################################

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        # Prefix your setting names with 'SUPERSET_'.
        ("SUPERSET_VERSION", __version__),
        ("SUPERSET_TAG", "2.0.1"),
        ("SUPERSET_HOST", "superset.{{ LMS_HOST }}"),
        ("SUPERSET_PORT", "8088"),
        ("SUPERSET_DB_DIALECT", "mysql"),
        ("SUPERSET_DB_HOST", "{{ MYSQL_HOST }}"),
        ("SUPERSET_DB_PORT", "{{ MYSQL_PORT }}"),
        ("SUPERSET_DB_NAME", "superset"),
        ("SUPERSET_DB_USERNAME", "superset"),
        ("SUPERSET_OAUTH2_ACCESS_TOKEN_PATH", "/oauth2/access_token/"),
        ("SUPERSET_OAUTH2_AUTHORIZE_PATH", "/oauth2/authorize/"),
        (
            "SUPERSET_OPENEDX_COURSES_LIST_PATH",
            "/api/courses/v1/courses/?permissions={permission}&username={username}",
        ),
        ("SUPERSET_OPENEDX_ROLE_NAME", "Open edX"),
        ("SUPERSET_ADMIN_EMAIL", "admin@openedx.org"),
        # Set to 0 to have no row limit.
        ("SUPERSET_ROW_LIMIT", 100_000),
        ("SUPERSET_SENTRY_DSN", ""),
    ]
)

hooks.Filters.CONFIG_UNIQUE.add_items(
    [
        # Add settings that don't have a reasonable default for all users here.
        # For instance: passwords, secret keys, etc.
        # Each new setting is a pair: (setting_name, unique_generated_value).
        # Prefix your setting names with 'SUPERSET_'.
        # For example:
        ("SUPERSET_SECRET_KEY", "{{ 24|random_string }}"),
        ("SUPERSET_DB_PASSWORD", "{{ 24|random_string }}"),
        ("SUPERSET_OAUTH2_CLIENT_ID", "{{ 16|random_string }}"),
        ("SUPERSET_OAUTH2_CLIENT_SECRET", "{{ 16|random_string }}"),
        ("SUPERSET_ADMIN_USERNAME", "{{ 12|random_string }}"),
        ("SUPERSET_ADMIN_PASSWORD", "{{ 24|random_string }}"),
        ("RUN_SUPERSET", True),
        (
            "SUPERSET_TALISMAN_CONFIG",
            {
                "content_security_policy": {
                    "default-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
                    "img-src": ["'self'", "data:"],
                    "worker-src": ["'self'", "blob:"],
                    "connect-src": [
                        "'self'",
                        "https://api.mapbox.com",
                        "https://events.mapbox.com",
                    ],
                    "object-src": "'none'",
                }
            },
        ),
        ("SUPERSET_TALISMAN_ENABLED", True),
    ]
)

hooks.Filters.CONFIG_OVERRIDES.add_items(
    [
        # Danger zone!
        # Add values to override settings from Tutor core or other plugins here.
        # Each override is a pair: (setting_name, new_value). For example:
        # ("PLATFORM_NAME", "My platform"),
    ]
)


########################################
# INITIALIZATION TASKS
########################################

# To add a custom initialization task, create a bash script template under:
# tutorsuperset/templates/superset/jobs/init/
# and then add it to the MY_INIT_TASKS list. Each task is in the format:
# ("<service>", ("<path>", "<to>", "<script>", "<template>"))
MY_INIT_TASKS = [
    # For example, to add LMS initialization steps, you could add the script template at:
    # tutorsuperset/templates/superset/jobs/init/lms.sh
    # And then add the line:
    ### ("lms", ("superset", "jobs", "init", "lms.sh")),
    ("mysql", ("superset", "jobs", "init", "init-mysql.sh")),
    ("superset", ("superset", "jobs", "init", "init-superset.sh")),
    ("lms", ("superset", "jobs", "init", "init-openedx.sh")),
]

# For each task added to MY_INIT_TASKS, we load the task template
# and add it to the CLI_DO_INIT_TASKS filter, which tells Tutor to
# run it as part of the `init` job.
for service, template_path in MY_INIT_TASKS:
    full_path: str = pkg_resources.resource_filename(
        "tutorsuperset", os.path.join("templates", *template_path)
    )
    with open(full_path, encoding="utf-8") as init_task_file:
        init_task: str = init_task_file.read()
    hooks.Filters.CLI_DO_INIT_TASKS.add_item((service, init_task))


########################################
# DOCKER IMAGE MANAGEMENT
########################################

# To build an image with `tutor images build myimage`, add a Dockerfile to templates/superset/build/myimage and write:
# hooks.Filters.IMAGES_BUILD.add_item((
#     "myimage",
#     ("plugins", "superset", "build", "myimage"),
#     "docker.io/myimage:{{ SUPERSET_VERSION }}",
#     (),
# )

# To pull/push an image with `tutor images pull myimage` and `tutor images push myimage`, write:
# hooks.Filters.IMAGES_PULL.add_item((
#     "myimage",
#     "docker.io/myimage:{{ SUPERSET_VERSION }}",
# )
# hooks.Filters.IMAGES_PUSH.add_item((
#     "myimage",
#     "docker.io/myimage:{{ SUPERSET_VERSION }}",
# )


########################################
# TEMPLATE RENDERING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

hooks.Filters.ENV_TEMPLATE_ROOTS.add_items(
    # Root paths for template files, relative to the project root.
    [
        pkg_resources.resource_filename("tutorsuperset", "templates"),
    ]
)

hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    # For each pair (source_path, destination_path):
    # templates at ``source_path`` (relative to your ENV_TEMPLATE_ROOTS) will be
    # rendered to ``source_path/destination_path`` (relative to your Tutor environment).
    # For example, ``tutorsuperset/templates/superset/build``
    # will be rendered to ``$(tutor config printroot)/env/plugins/superset/build``.
    [
        ("superset/build", "plugins"),
        ("superset/apps", "plugins"),
    ],
)

########################################
# PATCH LOADING
# (It is safe & recommended to leave
#  this section as-is :)
########################################

# For each file in tutorsuperset/patches,
# apply a patch based on the file's name and contents.
for path in glob(
    os.path.join(
        pkg_resources.resource_filename("tutorsuperset", "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))
