# -*- coding: utf-8 -*-
#
# Copyright 2017 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Interface definitions for Gordon Janitor Plugins.

Please see :doc:`plugins` for more information on writing a plugin for
the Gordon Janitor service.
"""

from zope.interface import Interface


class IGenericPlugin(Interface):
    """**Do not** implement this interface directly.

    Use :py:class:`IAuthority`, :py:class:`IReconciler`, or
    :py:class:`IPublisher` instead.

    Args:
        config (dict): Plugin-specific configuration.
        plugin_kwargs (dict): Plugin-specific keyword arguments. See
            specific interface declarations.
    """
    def __init__(config, **plugin_kwargs):
        """Initialize a Janitor Plugin client."""

    async def run():
        """Start plugin in the main event loop.

        Once required work is all processed, :py:meth:`cleanup` needs to
        be called.
        """

    async def cleanup():
        """Cleanup once plugin-specific work is cleanup.

        Cleanup work might include allowing outstanding asynchronous
        Python tasks to finish, cancelling them if they extend beyond a
        desired timeout, and/or closing HTTP sessions.
        """


class IAuthority(IGenericPlugin):
    """Scan source of truth(s) of hosts and emit messages to Reconciler.

    The purpose of this client is to consult a source of truth, for
    example, the list instances APIs in Google Compute Engine or AWS
    EC2, or consulting one's own database of hosts. A message per DNS
    zone with every instance record (per service owner's own
    requirements) will then be put onto the ``rrset_channel`` queue for
    a Reconciler to - you guessed it - reconcile.

    Args:
        config (dict): Authority-specific configuration.
        rrset_channel (asyncio.Queue): queue to put record set messages
            for later validation.
        metrics (obj): Optional object to emit Authority-specific
            metrics.
    """
    def __init__(config, rrset_channel, metrics=None):
        """Initialize an Authority Plugin client."""


class IReconciler(IGenericPlugin):
    """Validate current records in DNS against desired Authority.

    Clients that implement :py:class:`IReconciler` will create a change
    message for the configured :py:class:`IPublisher` client plugin to
    consume if there is a discrepancy between records in DNS and the
    desired state.

    Once validation is done, the :py:class:`IReconciler` client will
    need to emit a ``None`` message to the :py:attr:`changes_channel`
    queue, signalling to an :py:class:`IPublisher` client to publish the
    message to a pub/sub to which `Gordon
    <https://github.com/spotify/gordon>`_ subscribes.

    Args:
        config (dict): Reconciler-specific configuration.
        rrset_channel (asyncio.Queue): queue from which to consume
            record set messages to validate.
        changes_channel (asyncio.Queue): queue to publish corrective
            messages to be published.
        metrics (obj): Optional object to emit Reconciler-specific
            metrics.
    """
    def __init__(config, rrset_channel, changes_channel, metrics=None):
        """Initialize a Reconciler Plugin client."""


class IPublisher(IGenericPlugin):
    """Publish change messages to the pub/sub Gordon consumes.

    Clients that implement :py:class:`IPublisher` will consume from the
    :py:attr:`changes_channel` queue and publish the message to the
    configured pub/sub for which `Gordon
    <https://github.com/spotify/gordon>`_ subscribes.

    Args:
        config (dict): Publisher-specific configuration.
        changes_channel (asyncio.Queue): queue to consume the
             corrective messages needing to be published.
        metrics (obj): Optional object to emit Publisher-specific
            metrics.
    """
    def __init__(config, changes_channel, metrics=None):
        """Initialize a Publisher Plugin client."""
