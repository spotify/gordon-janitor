Configuring the Gordon Janitor Service
======================================


Example Configuration
---------------------

An example of a ``gordon-janitor.toml`` file:

.. literalinclude:: ../gordon-janitor.toml.example
    :language: ini


You may choose to have a ``gordon-janitor-user.toml`` file for development. Any top-level key will override what's found in ``gordon-janitor.toml``.

.. code-block:: ini

    [core]
    debug = true

    [core.logging]
    level = "debug"
    handlers = ["stream"]


Supported Configuration
-----------------------

The following sections are supported:

core
~~~~

.. option:: plugins=LIST-OF-STRINGS

    Plugins that the Gordon Janitor service needs to load. If a plugin is not listed, the Janitor will skip it even if there's configuration.

    The strings must match the plugin's config key. See the plugin's documentation for config key names.

.. option:: debug=true|false

    Whether or not to run the Gordon Janitor service in ``debug`` mode.

    If ``true``, the  Janitor will continue running even if installed & configured plugins can not be loaded. Plugin exceptions will be logged as warnings with tracebacks.

    If ``false``, the Janitor will exit out if it can't load one or more plugins.


core.logging
~~~~~~~~~~~~

.. option:: level=info(default)|debug|warning|error|critical

    Any log level that is supported by the Python standard :py:mod:`logging` library.

.. option:: handlers=LIST-OF-STRINGS

    ``handlers`` support any of the following handlers: ``stream``, ``syslog``, and ``stackdriver``. Multiple handlers are supported. Defaults to ``syslog`` if none are defined.

    .. note::

        If ``stackdriver`` is selected, ``ulogger[stackdriver]`` needs to be installed as its dependencies are not installed by default.
