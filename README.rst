=====================================================
``gordon-janitor``: Reconciliation Service for Gordon
=====================================================

.. desc-begin

Cloud DNS reconciliation - a service that checks cloud DNS records against a source of truth and submits corrections to `gordon`_.

.. desc-end

**NOTICE**: This is still in the planning phase and under active development. Gordon-Janitor should not be used in production, yet.

.. intro-begin

Requirements
============

* Python 3.6

Support for other Python versions may be added in the future.

Development
===========

For development and running tests, your system must have all supported versions of Python installed. We suggest using `pyenv`_.

Setup
-----

.. code-block:: bash

    $ git clone git@github.com:spotify/gordon-janitor.git && cd gordon-janitor
    # make a virtualenv
    (env) $ pip install -r dev-requirements.txt

Running tests
-------------

To run the entire test suite:

.. code-block:: bash

    # outside of the virtualenv
    # if tox is not yet installed
    $ pip install tox
    $ tox

If you want to run the test suite for a specific version of Python:

.. code-block:: bash

    # outside of the virtualenv
    $ tox -e py36

To run an individual test, call ``pytest`` directly:

.. code-block:: bash

    # inside virtualenv
    (env) $ pytest tests/test_foo.py


Build docs
----------

To generate documentation:


.. code-block:: bash

    (env) $ pip install -r docs-requirements.txt
    (env) $ cd docs && make html  # builds HTML files into _build/html/
    (env) $ cd _build/html
    (env) $ python -m http.server $PORT


Then navigate to ``localhost:$PORT``!

To watch for changes and automatically reload in the browser:

.. code-block:: bash

    (env) $ cd docs
    (env) $ make livehtml  # default port 8888
    # to change port
    (env) $ make livehtml PORT=8080


Code of Conduct
===============

This project adheres to the `Open Code of Conduct`_. By participating, you are expected to honor this code.

.. _`pyenv`: https://github.com/yyuu/pyenv
.. _`Open Code of Conduct`: https://github.com/spotify/code-of-conduct/blob/master/code-of-conduct.md
.. _`gordon`: https://github.com/spotify/gordon
