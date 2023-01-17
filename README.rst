superset plugin for `Tutor <https://docs.tutor.overhang.io>`__
===================================================================================

Installation
------------

::

    pip install git+https://github.com/open-craft/tutor-contrib-superset

Usage
-----

::

    # Enable this plugin
    tutor plugins enable superset
    tutor config save

    # Set up SSO with Open edX
    tutor [dev|local] do init --limit superset


Connect to Superset's UI on the configured port (default is `:8088`):

  http://local.overhang.io:8088


License
-------

This software is licensed under the terms of the AGPLv3.
