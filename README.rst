THIS REPOSITORY IS DEPRECATED
=============================

This functionality now lives in `tutor-contrib-oars <https://github.com/openedx/tutor-contrib-oars>`__ as we work to consolidate the Open edX analytics functionality into one place.

This repository was experimental as we worked on OARS and will be archived soon.

Apache Superset plugin for `Tutor <https://docs.tutor.overhang.io>`__
===================================================================================

Runs `Apache Superset <https://superset.apache.org>`__ in the Tutor environment.

This plugin is speculative and being used to test new Open edX analytics features.
It is not configured for production use at this time, use at your own risk!

See https://github.com/openedx/openedx-oars for more details.

Installation
------------

::

    pip install git+https://github.com/openedx/tutor-contrib-superset


Compatibility
-------------

This plugin is compatible with Tutor 15.0.0 and later.

Usage
-----

::

    # Enable this plugin
    tutor plugins enable superset
    tutor config save

    # Set up SSO with Open edX
    tutor [dev|local] do init --limit superset


Connect to Superset's UI on the configured port (default is `:8088`):

  http://superset.local.overhang.io:8088


Access and Permissions
----------------------

Superset is configured to use Open edX SSO for authentication,
and the global Open edX user permissions and course access for authorization.

* Users who are "superusers" in Open edX are made members of the built-in Superset `Admin`_ role, and the custom `Open edX` role.
* Users who are global "staff" in Open edX are made members of the built-in Superset `Alpha`_ role, and the custom `Open edX` role.
* Users who have staff access to any courses in Open edX are made members of the Superset custom `Open edX` role.
* All other users, including anonymous users, are not made members of any roles, and so cannot see or change any data in Superset.

There is also an `Admin`_ user with a randomly-generated username and password which can access the Superset API, but cannot login to the GUI.

Open edX role
^^^^^^^^^^^^^

The custom ``Open edX`` role controls access to course data using `Row Level Security Filters`_ managed by the `OARS`_ plugin.

`Admin`_ and `Alpha`_ users can see data from any course, but `Open edX` users can only see data from courses they have staff access to.


.. _Admin: https://superset.apache.org/docs/security/#admin
.. _Alpha: https://superset.apache.org/docs/security/#alpha
.. _Gamma: https://superset.apache.org/docs/security/#gamma
.. _Row Level Security Filters: https://superset.apache.org/docs/security/#row-level-security
.. _OARS: https://github.com/openedx/tutor-contrib-oars

License
-------

This software is licensed under the terms of the AGPLv3.
