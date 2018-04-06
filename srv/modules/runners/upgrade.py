# -*- coding: utf-8 -*-
# pylint: disable=modernize-parse-error
"""
Verify that an automated upgrade is possible
"""
from __future__ import absolute_import
from __future__ import print_function
# pylint: disable=import-error,3rd-party-module-not-gated,redefined-builtin
import salt.client
import salt.utils.error
from glob import glob
import logging
from printer import PrettyPrinter
from exceptions import InvalidConfigKV

log = logging.getLogger(__name__)


class UpgradeValidation(object):
    """
    Due to the current situation you have to upgrade
    all monitors before ceph allows you to start any OSD
    Our current implementation of maintenance upgrades
    triggers this behavior if you happen to have
    Monitors and Storage roles assigned on the same node
    (And more then one monitor)
    To avoid this, before actually providing a proper solution,
    we stop users to execute the upgade in the first place.
    """

    def __init__(self, cluster='ceph'):
        """
        Initialize Salt client, cluster
        """
        self.local = salt.client.LocalClient()
        self.cluster = cluster
        self.printer = PrettyPrinter()

    def colocated_services(self):
        """
        Check for shared monitor and storage roles
        """
        search = "I@cluster:{}".format(self.cluster)
        pillar_data = self.local.cmd(search, 'pillar.items', [], tgt_type="compound")
        for host in pillar_data:
            if 'roles' in pillar_data[host]:
                if ('storage' in pillar_data[host]['roles']
                   and 'mon' in pillar_data[host]['roles']):
                    msg = """
                         ************** PLEASE READ ***************
                         We currently do not support upgrading when
                         you have a monitor and a storage role
                         assigned on the same node.
                         ******************************************"""
                    return False, msg
        return True, ""

    def is_master_standalone(self):
        """
        Check for shared master and storage role
        """
        search = "I@roles:master"
        pillar_data = self.local.cmd(search, 'pillar.items', [], tgt_type="compound")
        # in case of multimaster
        for host in pillar_data:
            if 'roles'in pillar_data[host]:
                if 'storage' in pillar_data[host]:
                    msg = """
                         ************** PLEASE READ ***************
                         Detected a storage role on your master.
                         This is not supported. Please migrate all
                         OSDs off the master in order to continue.
                         ******************************************"""
                    return False, msg
        return True, ""

    def check_deprecated_conf_val(self):
        """
        Checks for deprecated/renamed config values
        #TODO: find a curated list of those
        """
        depr_conf = {'dummy': 'value',
                     'foo': 'bar',
                     'lala': 'bar',
                     'lala': 'mlala'}
        conf_path = '/srv/salt/ceph/configuration/files/ceph.conf.d'
        suffix = '*.conf'
        files = glob("{path}/{suffix}".format(path=conf_path, suffix=suffix))
        matches = {}
        for fn in files:
            with open(fn, 'r') as _fd:
                matches[fn] = {}
                for line in _fd:
                    if not len(line.split('=')) == 2:
                        raise InvalidConfigKV
                    k, v = line.split('=')
                    k = k.strip()
                    if k in depr_conf:
                        logging.info('found {} in list of deprecated configs'.format(k))
                        v = v.strip()
                        if depr_conf[k] == v:
                            logging.info('found key: {} for value: {} in list of deprecated configs'.format(k, v))
                            matches[fn][k] = v
            if not matches[fn]:
                logging.info('{fn} did not contain any depricated or dangerous configs'.format(fn=fn))
                matches.pop(fn, None)

        
        return (False, matches) if matches else (True, 'success')


def check_deprecated_conf_val():
    uvo = UpgradeValidation()
    return uvo.check_deprecated_conf_val()
    

def help_():
    """
    Usage
    """
    usage = ('salt-run upgrade.check:\n\n'
             '    Performs a series of checks to verify that upgrades are possible\n'
             '\n\n')
    print(usage)
    return ""


def check():
    """
    Run upgrade checks
    """
    uvo = UpgradeValidation()
    checks = [uvo.is_master_standalone, check_deprecated_conf_val]  # , uvo.colocated_services]
    for chk in checks:
        ret, msg = chk()
        if not ret:
            uvo.printer.add('check_drep', {}, msg, {})
            return ret
    return ret

__func_alias__ = {
                 'help_': 'help',
                 }
