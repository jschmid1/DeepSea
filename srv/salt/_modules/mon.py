# -*- coding: utf-8 -*-

"""
The need for this module is that the roles show the intended state and not
the current state.  Once the admin unassigns the monitor role, the pillar
reflects that configuration.
"""

from __future__ import absolute_import
import json
import logging
# pylint: disable=import-error,3rd-party-module-not-gated
import salt.ext.six as six
from subprocess import check_output, CalledProcessError
import rados
# pylint: disable=incompatible-py3-code
log = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Monitors(object):
    """
    Connect to ceph to determine the monitors
    """

    def __init__(self, **kwargs):
        """
        Default settings can be overridden
        """

        self.settings = {
            'conf': "/etc/ceph/ceph.conf",
            'timeout': 300,
            'check': 2,
            'delay': 6,
            'negate': False
        }
        self.settings.update(kwargs)
        log.debug("settings: {}".format(_skip_dunder(self.settings)))
        self._connect()

    def _connect(self):
        """
        Connect to Ceph cluster
        """
        self.cluster = rados.Rados(conffile=self.settings['conf'])
        self.cluster.connect()

    def list(self):
        """
        Returns the keys
        """
        return [entry['name'] for entry in self._dump()]

    def _dump(self):
        """
        Call ceph mon dump
        """
        cmd = json.dumps({"prefix": "mon dump", "format": "json"})
        # pylint: disable=unused-variable
        ret, output, err = self.cluster.mon_command(cmd, b'', timeout=6)
        dump = json.loads(output)['mons']
        log.debug("status: {}".format(dump))
        return dump


def already_running():
    # check if a container is already running.
    # Check the higher-level instance - systemd.

    ## there needs to be a second check for existence..
    ## we might have the case where a mon is down, but still exists
    ## check for directory existence? or for podman image existance?

    # TODO: refine the logic when to return false/true..


    # is /host/ fine?
    mon_name = __grains__.get('host', '')
    if not mon_name:
        log.error("Could not retrieve host grain. Aborting")
        return False
    try:
        status = check_output(
            ['systemctl', 'is-active',
            f'ceph-mon@{mon_name}.service']).decode('utf-8').strip()
    except CalledProcessError as e:
        log.info(f'{e}')
        return False
    if status == 'active':
        return True
    elif status == 'inactive' or os.path.exists(f'/var/lib/ceph/mon/ceph-{mon_name}'):
        return False
    else:
        log.error(f"Could not determine state of {mon_name}")
        return False



def list_(**kwargs):
    """
    List the monitors
    """
    mons = Monitors(**kwargs)
    return mons.list()


def _skip_dunder(settings):
    """
    Skip double underscore keys
    """
    return {k: v for k, v in six.iteritems(settings) if not k.startswith('__')}

__func_alias__ = {
                 'list_': 'list',
                 }
