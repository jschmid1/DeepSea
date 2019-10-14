#!/usr/bin/env python3

PODMAN_PREFERENCE = ['podman', 'docker']  # prefer podman to docker
"""
You can invoke ceph-daemon in two ways:

1. The normal way, at the command line.

2. By piping the script to the python3 binary.  In this latter case, you should
   prepend one or more lines to the beginning of the script.

   For arguments,

       injected_argv = [...]

   e.g.,

       injected_argv = ['ls']

   For reading stdin from the '--config-and-json -' argument,

       injected_stdin = '...'
"""

import configparser
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import time

from argparser import cmdline_args
from container import CephContainer
from utils import make_fsid, get_hostname, create_daemon_dirs, get_data_dir, get_log_dir, get_daemon_args, get_container_mounts, get_unit_name, extract_uid_gid
from config import Config
from keyrings import Keyring

try:
    from StringIO import StringIO
except ImportError:
    pass
try:
    from io import StringIO
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)

podman_path = None

##################################


def get_legacy_daemon_fsid(cluster_name, daemon_type, daemon_id):
    # TODO: args
    fsid = None
    if daemon_type == 'osd':
        try:
            with open(
                    os.path.join(args.data_dir, daemon_type,
                                 'ceph-%s' % daemon_id, 'ceph_fsid'),
                    'r') as f:
                fsid = f.read().strip()
        except IOError:
            pass
    if not fsid:
        fsid = get_legacy_config_fsid(cluster)
    return fsid


def get_config_and_keyring():
    # TODO: args
    if args.config_and_keyring:
        if args.config_and_keyring == '-':
            try:
                j = injected_stdin
            except NameError:
                j = sys.stdin.read()
        else:
            with open(args.config_and_keyring, 'r') as f:
                j = f.read()
        d = json.loads(j)
        config = d.get('config')
        keyring = d.get('keyring')
    else:
        if args.key:
            keyring = '[%s]\n\tkey = %s\n' % (args.name, args.key)
        elif args.keyring:
            with open(args.keyring, 'r') as f:
                keyring = f.read()
        else:
            raise RuntimeError('no keyring')
        with open(args.config, 'r') as f:
            config = f.read()
    return (config, keyring)


def get_container(fsid,
                  daemon_type,
                  daemon_id,
                  privileged=False,
                  data_dir=None,
                  log_dir=None):
    # TODO: args
    podman_args = []

    if daemon_type == 'osd' or privileged:
        podman_args += ['--privileged']
    return CephContainer(
        image=args.image,
        entrypoint='/usr/bin/ceph-' + daemon_type,
        args=[
            '-n',
            '%s.%s' % (daemon_type, daemon_id),
            '-f',  # foreground
        ] + get_daemon_args(fsid, daemon_type, daemon_id),
        podman_args=podman_args,
        volume_mounts=get_container_mounts(
            fsid, daemon_type, daemon_id, data_dir=data_dir, log_dir=log_dir),
        cname='ceph-%s-%s.%s' % (fsid, daemon_type, daemon_id),
    )


def deploy_daemon(fsid,
                  daemon_type,
                  daemon_id,
                  c,
                  uid,
                  gid,
                  config=None,
                  keyring=None):
    # TODO: args
    if daemon_type == 'mon':
        # tmp keyring file
        tmp_keyring = tempfile.NamedTemporaryFile(mode='w')
        os.fchmod(tmp_keyring.fileno(), 0o600)
        os.fchown(tmp_keyring.fileno(), uid, gid)
        tmp_keyring.write(keyring)
        tmp_keyring.flush()

        # tmp config file
        tmp_config = tempfile.NamedTemporaryFile(mode='w')
        os.fchmod(tmp_config.fileno(), 0o600)
        os.fchown(tmp_config.fileno(), uid, gid)
        tmp_config.write(config)
        tmp_config.flush()

        # --mkfs
        create_daemon_dirs(fsid, daemon_type, daemon_id, uid, gid)
        mon_dir = get_data_dir(fsid, 'mon', daemon_id)
        log_dir = get_log_dir(fsid)
        out = CephContainer(
            image=args.image,
            entrypoint='/usr/bin/ceph-mon',
            args=[
                '--mkfs',
                '-i',
                daemon_id,
                '--fsid',
                fsid,
                '-c',
                '/tmp/config',
                '--keyring',
                '/tmp/keyring',
            ] + get_daemon_args(fsid, 'mon', daemon_id),
            volume_mounts={
                log_dir: '/var/log/ceph:z',
                mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (daemon_id),
                tmp_keyring.name: '/tmp/keyring:z',
                tmp_config.name: '/tmp/config:z',
            },
        ).run()

        # write conf
        with open(mon_dir + '/config', 'w') as f:
            os.fchown(f.fileno(), uid, gid)
            os.fchmod(f.fileno(), 0o600)
            f.write(config)
    else:
        # dirs, conf, keyring
        create_daemon_dirs(fsid, daemon_type, daemon_id, uid, gid, config,
                           keyring)

    if daemon_type == 'osd' and args.osd_fsid:
        pc = CephContainer(
            image=args.image,
            entrypoint='/usr/sbin/ceph-volume',
            args=['lvm', 'activate', daemon_id, args.osd_fsid, '--no-systemd'],
            podman_args=['--privileged'],
            volume_mounts=get_container_mounts(fsid, daemon_type, daemon_id),
            cname='ceph-%s-activate-%s.%s' % (fsid, daemon_type, daemon_id),
        )
        pc.run()

    deploy_daemon_units(fsid, daemon_type, daemon_id, c)


def deploy_daemon_units(fsid,
                        daemon_type,
                        daemon_id,
                        c,
                        data_dir=None,
                        log_dir=None,
                        unit_dir=None,
                        enable=True,
                        start=True):
    # cmd
    data_dir = get_data_dir(fsid, daemon_type, daemon_id, data_dir)
    with open(data_dir + '/cmd', 'w') as f:
        f.write('#!/bin/sh\n' + ' '.join(c.run_cmd()) + '\n')
        os.fchmod(f.fileno(), 0o700)

    # systemd
    install_base_units(fsid)

    unit = get_unit_file(fsid)
    unit_file = 'ceph-%s@.service' % (fsid)
    with open(unit_dir + '/' + unit_file + '.new', 'w') as f:
        f.write(unit)
        os.rename(unit_dir + '/' + unit_file + '.new',
                  unit_dir + '/' + unit_file)
    subprocess.check_output(['systemctl', 'daemon-reload'])

    unit_name = get_unit_name(fsid, daemon_type, daemon_id)
    if enable:
        subprocess.check_output(['systemctl', 'enable', unit_name])
    if start:
        subprocess.check_output(['systemctl', 'start', unit_name])


def install_base_units(fsid):
    """
    Set up ceph.target and ceph-$fsid.target units.
    """
    # TODO: args
    existed = os.path.exists(args.unit_dir + '/ceph.target')
    with open(args.unit_dir + '/ceph.target.new', 'w') as f:
        f.write('[Unit]\n'
                'Description=all ceph service\n'
                '[Install]\n'
                'WantedBy=multi-user.target\n')
        os.rename(args.unit_dir + '/ceph.target.new',
                  args.unit_dir + '/ceph.target')
    if not existed:
        subprocess.check_output(['systemctl', 'enable', 'ceph.target'])
        subprocess.check_output(['systemctl', 'start', 'ceph.target'])

    existed = os.path.exists(args.unit_dir + '/ceph-%s.target' % fsid)
    with open(args.unit_dir + '/ceph-%s.target.new' % fsid, 'w') as f:
        f.write('[Unit]\n'
                'Description=ceph cluster {fsid}\n'
                'PartOf=ceph.target\n'
                'Before=ceph.target\n'
                '[Install]\n'
                'WantedBy=multi-user.target ceph.target\n'.format(fsid=fsid))
        os.rename(args.unit_dir + '/ceph-%s.target.new' % fsid,
                  args.unit_dir + '/ceph-%s.target' % fsid)
    if not existed:
        subprocess.check_output(
            ['systemctl', 'enable',
             'ceph-%s.target' % fsid])
        subprocess.check_output(
            ['systemctl', 'start',
             'ceph-%s.target' % fsid])


def get_unit_file(fsid):
    u = """[Unit]
Description=Ceph daemon for {fsid}

# According to:
#   http://www.freedesktop.org/wiki/Software/systemd/NetworkTarget
# these can be removed once ceph-mon will dynamically change network
# configuration.
After=network-online.target local-fs.target time-sync.target
Wants=network-online.target local-fs.target time-sync.target

PartOf=ceph-{fsid}.target
Before=ceph-{fsid}.target

[Service]
LimitNOFILE=1048576
LimitNPROC=1048576
EnvironmentFile=-/etc/environment
ExecStartPre=-{podman_path} rm ceph-{fsid}-%i
ExecStartPre=-mkdir -p /var/run/ceph
ExecStart={data_dir}/{fsid}/%i/cmd
ExecStop=-{podman_path} stop ceph-{fsid}-%i
ExecStopPost=-/bin/rm -f /var/run/ceph/{fsid}-%i.asok
Restart=on-failure
RestartSec=10s
TimeoutStartSec=120
TimeoutStopSec=15
StartLimitInterval=30min
StartLimitBurst=5

[Install]
WantedBy=ceph-{fsid}.target
""".format(
        podman_path=podman_path, fsid=fsid, data_dir=args.data_dir)
    return u


def gen_ssh_key(fsid):
    tmp_dir = tempfile.TemporaryDirectory()
    path = tmp_dir.name + '/key'
    subprocess.check_output(
        ['ssh-keygen', '-C',
         'ceph-%s' % fsid, '-N', '', '-f', path])
    with open(path, 'r') as f:
        secret = f.read()
    with open(path + '.pub', 'r') as f:
        pub = f.read()
    os.unlink(path)
    os.unlink(path + '.pub')
    tmp_dir.cleanup()
    return (secret, pub)


##################################

##################################

##################################

##################################


def command_deploy():
    (daemon_type, daemon_id) = args.name.split('.')
    if daemon_type not in ['mon', 'mgr', 'mds', 'osd', 'rgw']:
        raise RuntimeError('daemon type %s not recognized' % daemon_type)
    (config, keyring) = get_config_and_keyring()
    if daemon_type == 'mon':
        if args.mon_ip:
            config += '[mon.%s]\n\tpublic_addr = %s\n' % (daemon_id,
                                                          args.mon_ip)
        elif args.mon_network:
            config += '[mon.%s]\n\tpublic_network = %s\n' % (daemon_id,
                                                             args.mon_network)
        else:
            raise RuntimeError('must specify --mon-ip or --mon-network')
    (uid, gid) = extract_uid_gid()
    c = get_container(args.fsid, daemon_type, daemon_id)
    deploy_daemon(args.fsid, daemon_type, daemon_id, c, uid, gid, config,
                  keyring)


##################################


def command_run():
    (daemon_type, daemon_id) = args.name.split('.')
    c = get_container(args.fsid, daemon_type, daemon_id)
    subprocess.call(c.run_cmd())


##################################


def command_shell():
    if args.fsid:
        make_log_dir(args.fsid)
    if args.name:
        if '.' in args.name:
            (daemon_type, daemon_id) = args.name.split('.')
        else:
            daemon_type = args.name
            daemon_id = None
    else:
        daemon_type = 'osd'  # get the most mounts
        daemon_id = None
    mounts = get_container_mounts(args.fsid, daemon_type, daemon_id)
    if args.config:
        mounts[pathify(args.config)] = '/etc/ceph/ceph.conf:z'
    if args.keyring:
        mounts[pathify(args.keyring)] = '/etc/ceph/ceph.keyring:z'
    c = CephContainer(
        image=args.image,
        entrypoint='doesnotmatter',
        args=[],
        podman_args=['--privileged'],
        volume_mounts=mounts)
    subprocess.call(c.shell_cmd())


##################################


def command_enter():
    (daemon_type, daemon_id) = args.name.split('.')
    c = get_container(args.fsid, daemon_type, daemon_id)
    subprocess.call(c.exec_cmd(['bash']))


##################################


def command_exec():
    (daemon_type, daemon_id) = args.name.split('.')
    c = get_container(
        args.fsid, daemon_type, daemon_id, privileged=args.privileged)
    subprocess.call(c.exec_cmd(args.command))


##################################


def command_ceph_volume():
    make_log_dir(args.fsid)

    mounts = get_container_mounts(args.fsid, 'osd', None)

    tmp_config = None
    tmp_keyring = None

    if args.config_and_keyring:
        # note: this will always pull from args.config_and_keyring (we
        # require it) and never args.config or args.keyring.
        (config, keyring) = get_config_and_keyring()

        # tmp keyring file
        tmp_keyring = tempfile.NamedTemporaryFile(mode='w')
        os.fchmod(tmp_keyring.fileno(), 0o600)
        tmp_keyring.write(keyring)
        tmp_keyring.flush()

        # tmp config file
        tmp_config = tempfile.NamedTemporaryFile(mode='w')
        os.fchmod(tmp_config.fileno(), 0o600)
        tmp_config.write(config)
        tmp_config.flush()

        mounts[tmp_config.name] = '/etc/ceph/ceph.conf:z'
        mounts[tmp_keyring.name] = '/var/lib/ceph/bootstrap-osd/ceph.keyring:z'

    c = CephContainer(
        image=args.image,
        entrypoint='/usr/sbin/ceph-volume',
        args=args.command,
        podman_args=['--privileged'],
        volume_mounts=mounts,
    )
    subprocess.call(c.run_cmd())


##################################


def command_unit():
    (daemon_type, daemon_id) = args.name.split('.')
    unit_name = get_unit_name(args.fsid, daemon_type, daemon_id)
    subprocess.call(['systemctl', args.command, unit_name])


##################################


def command_ls():
    ls = []

    # /var/lib/ceph
    if os.path.exists(args.data_dir):
        for i in os.listdir(args.data_dir):
            if i in ['mon', 'osd', 'mds', 'mgr']:
                daemon_type = i
                for j in os.listdir(os.path.join(args.data_dir, i)):
                    if '-' not in j:
                        continue
                    (cluster, daemon_id) = j.split('-', 1)
                    fsid = get_legacy_daemon_fsid(cluster, daemon_type,
                                                  daemon_id) or 'unknown'
                    (enabled, active) = check_unit(
                        'ceph-%s@%s' % (daemon_type, daemon_id))
                    ls.append({
                        'style': 'legacy',
                        'name': '%s.%s' % (daemon_type, daemon_id),
                        'fsid': fsid,
                        'enabled': enabled,
                        'active': active,
                    })
            elif is_fsid(i):
                fsid = i
                for j in os.listdir(os.path.join(args.data_dir, i)):
                    (daemon_type, daemon_id) = j.split('.', 1)
                    (enabled, active) = check_unit(
                        get_unit_name(fsid, daemon_type, daemon_id))
                    ls.append({
                        'style': 'ceph-daemon:v1',
                        'name': '%s.%s' % (daemon_type, daemon_id),
                        'fsid': fsid,
                        'enabled': enabled,
                        'active': active,
                    })

    # /var/lib/rook
    # WRITE ME

    print(json.dumps(ls, indent=4))


##################################


def command_adopt():
    (daemon_type, daemon_id) = args.name.split('.')
    (uid, gid) = extract_uid_gid()
    if args.style == 'legacy':
        fsid = get_legacy_daemon_fsid(args.cluster, daemon_type, daemon_id)
        if not fsid:
            raise RuntimeError(
                'could not detect fsid; add fsid = to ceph.conf')

        # NOTE: implicit assumption here that the units correspond to the
        # cluster we are adopting based on the /etc/{defaults,sysconfig}/ceph
        # CLUSTER field.
        unit_name = 'ceph-%s@%s' % (daemon_type, daemon_id)
        (enabled, active) = check_unit(unit_name)

        if active:
            logging.info('Stopping old systemd unit %s...' % unit_name)
            subprocess.check_output(['systemctl', 'stop', unit_name])
        if enabled:
            logging.info('Disabling old systemd unit %s...' % unit_name)
            subprocess.check_output(['systemctl', 'disable', unit_name])

        logging.info('Moving data...')
        make_data_dir_base(fsid, uid, gid)
        data_dir = get_data_dir(fsid, daemon_type, daemon_id)
        subprocess.check_output([
            'mv',
            '/var/lib/ceph/%s/%s-%s' % (daemon_type, args.cluster, daemon_id),
            data_dir
        ])
        subprocess.check_output([
            'cp',
            '/etc/ceph/%s.conf' % args.cluster,
            os.path.join(data_dir, 'config')
        ])
        os.chmod(data_dir, DATA_DIR_MODE)
        os.chown(data_dir, uid, gid)

        logging.info('Moving logs...')
        log_dir = make_log_dir(fsid, uid=uid, gid=gid)
        try:
            subprocess.check_output([
                'mv',
                '/var/log/ceph/%s-%s.%s.log*' %
                (args.cluster, daemon_type, daemon_id),
                os.path.join(log_dir)
            ],
                                    shell=True)
        except Exception as e:
            logging.warning('unable to move log file: %s' % e)
            pass

        logging.info('Creating new units...')
        c = get_container(fsid, daemon_type, daemon_id)
        deploy_daemon_units(
            fsid,
            daemon_type,
            daemon_id,
            c,
            enable=True,  # unconditionally enable the new unit
            start=active)
    else:
        raise RuntimeError('adoption of style %s not implemented' % args.style)


##################################


def command_rm_daemon():
    (daemon_type, daemon_id) = args.name.split('.')
    if daemon_type in ['mon', 'osd'] and not args.force:
        raise RuntimeError('must pass --force to proceed: '
                           'this command may destroy precious data!')
    unit_name = get_unit_name(args.fsid, daemon_type, daemon_id)
    subprocess.check_output(['systemctl', 'stop', unit_name])
    subprocess.check_output(['systemctl', 'disable', unit_name])
    data_dir = get_data_dir(args.fsid, daemon_type, daemon_id)
    subprocess.check_output(['rm', '-rf', data_dir])


##################################


def command_rm_cluster():
    if not args.force:
        raise RuntimeError('must pass --force to proceed: '
                           'this command may destroy precious data!')

    unit_name = 'ceph-%s.target' % args.fsid
    try:
        subprocess.check_output(['systemctl', 'stop', unit_name])
        subprocess.check_output(['systemctl', 'disable', unit_name])
    except subprocess.CalledProcessError:
        pass

    slice_name = 'system-%s.slice' % (
        ('ceph-%s' % args.fsid).replace('-', '\\x2d'))
    try:
        subprocess.check_output(['systemctl', 'stop', slice_name])
    except subprocess.CalledProcessError:
        pass

    # FIXME: stop + disable individual daemon units, too?

    # rm units
    subprocess.check_output(
        ['rm', '-f', args.unit_dir + '/ceph-%s@.service' % args.fsid])
    subprocess.check_output(
        ['rm', '-f', args.unit_dir + '/ceph-%s.target' % args.fsid])
    subprocess.check_output(
        ['rm', '-rf', args.unit_dir + '/ceph-%s.target.wants' % args.fsid])
    # rm data
    subprocess.check_output(['rm', '-rf', args.data_dir + '/' + args.fsid])
    # rm logs
    subprocess.check_output(['rm', '-rf', args.log_dir + '/' + args.fsid])
    subprocess.check_output(
        ['rm', '-rf', args.log_dir + '/*.wants/ceph-%s@*' % args.fsid])




##################################


class Version(object):
    def __init__(self, config):
        self.image = config.image
        self.version = self.command_version()
        self.report()

    def command_version(self):
        ret = CephContainer(self.image, 'ceph', ['--version']).run()
        return ret.stdout

    def report(self):
        # consider __call__()
        print(self.version)


class Deploy(object):
    pass



class Bootstrap(object):
    def __init__(self, args):
        self.config = Config(args)
        # TODO: this sucks
        self.config.ceph_uid, self.config.ceph_gid = extract_uid_gid(CephContainer, self.image)
        self.keyring = Keyring(self.config)
        self.directory = Directory(self.config)
        self.bootstrap()

    def __getattr__(self, attr):
        # Inheritance vs Composition..
        return getattr(self.config, attr)

    def create_initial_config(self):
        # config
        cp = configparser.ConfigParser()
        cp.add_section('global')
        cp['global']['fsid'] = self.fsid
        cp['global']['mon host'] = self.addr_arg
        with StringIO() as f:
            cp.write(f)
            config = f.getvalue()
        return config

    def create_monmap(self):
        # create initial monmap, tmp monmap file
        logging.info('Creating initial monmap...')
        tmp_monmap = tempfile.NamedTemporaryFile(mode='w')
        os.fchmod(tmp_monmap.fileno(), 0o644)
        out = CephContainer(
            image=self.image,
            entrypoint='/usr/bin/monmaptool',
            args=[
                '--create', '--clobber', '--fsid', self.fsid, '--addv',
                self.mon_id, self.addr_arg, '/tmp/monmap'
            ],
            volume_mounts={
                tmp_monmap.name: '/tmp/monmap:z',
            },
        ).run().stdout
        return out

    def bootstrap(self):
        logging.info('Cluster fsid: %s' % self.fsid)

        keyring, _, admin_key, mgr_key = self.keyring.create_initial_keyring(self.mgr_id)


        tmp_keyring = self.keyring.write_tmp_keyring(keyring)

        config = self.create_initial_config()

        # create mon
        logging.info('Creating mon...')

        self.directory.create_daemon_dirs(daemon_type='mon', daemon_id=self.mon_id)

        mon_dir = get_data_dir(self.fsid, 'mon', self.mon_id, self.data_dir)
        log_dir = get_log_dir(self.fsid, self.log_dir)
        out = CephContainer(
            image=self.image,
            entrypoint='/usr/bin/ceph-mon',
            args=[
                '--mkfs',
                '-i',
                self.mon_id,
                '--fsid',
                self.fsid,
                '-c',
                '/dev/null',
                '--monmap',
                '/tmp/monmap',
                '--keyring',
                '/tmp/keyring',
            ] + get_daemon_args(self.fsid, 'mon', self.mon_id),
            volume_mounts={
                log_dir: '/var/log/ceph:z',
                mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (self.mon_id),
                tmp_keyring.name: '/tmp/keyring:z',
                tmp_monmap.name: '/tmp/monmap:z',
            },
        ).run()

        with open(mon_dir + '/config', 'w') as f:
            os.fchown(f.fileno(), self.ceph_uid, self.ceph_gid)
            os.fchmod(f.fileno(), 0o600)
            f.write(config)

        mon_c = get_container(
            self.fsid,
            'mon',
            self.mon_id,
            data_dir=self.data_dir,
            log_dir=self.log_dir)

        deploy_daemon_units(
            self.fsid,
            'mon',
            self.mon_id,
            mon_c,
            data_dir=self.data_dir,
            log_dir=self.log_dir,
            unit_dir=self.unit_dir)

        # create mgr
        logging.info('Creating mgr...')
        mgr_keyring = '[mgr.%s]\n\tkey = %s\n' % (self.mgr_id, mgr_key)
        mgr_c = get_container(
            self.fsid,
            'mgr',
            self.mgr_id,
            data_dir=self.data_dir,
            log_dir=self.log_dir)
        deploy_daemon(self.fsid, 'mgr', self.mgr_id, mgr_c, self.ceph_uid,
                      self.ceph_gid, config, mgr_keyring)


        # output files
        if self.output_keyring:
            with open(self.output_keyring, 'w') as f:
                os.fchmod(f.fileno(), 0o600)
                f.write('[client.admin]\n' '\tkey = ' + admin_key + '\n')
            logging.info('Wrote keyring to %s' % self.output_keyring)
        if self.output_config:
            with open(self.output_config, 'w') as f:
                f.write(config)
            logging.info('Wrote config to %s' % self.output_config)

        logging.info('Waiting for mgr to start...')
        while True:
            out = CephContainer(
                image=self.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id, 'status',
                    '-f', 'json-pretty'
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                },
            ).run()
            j = json.loads(out)
            if j.get('mgrmap', {}).get('available', False):
                break
            logging.info('mgr is still not available yet, waiting...')
            time.sleep(1)

        # ssh
        if not args.skip_ssh:
            logging.info('Generating ssh key...')
            (ssh_key, ssh_pub) = gen_ssh_key(fsid)

            tmp_key = tempfile.NamedTemporaryFile(mode='w')
            os.fchmod(tmp_key.fileno(), 0o600)
            os.fchown(tmp_key.fileno(), uid, gid)
            tmp_key.write(ssh_key)
            tmp_key.flush()
            tmp_pub = tempfile.NamedTemporaryFile(mode='w')
            os.fchmod(tmp_pub.fileno(), 0o600)
            os.fchown(tmp_pub.fileno(), uid, gid)
            tmp_pub.write(ssh_pub)
            tmp_pub.flush()

            if args.output_pub_ssh_key:
                with open(args.output_put_ssh_key, 'w') as f:
                    f.write(ssh_pub)
                logging.info(
                    'Wrote public SSH key to to %s' % args.output_pub_ssh_key)

            CephContainer(
                image=args.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id, 'config-key',
                    'set', 'mgr/ssh/ssh_identity_key', '-i', '/tmp/key'
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                    tmp_key.name: '/tmp/key:z',
                },
            ).run()
            CephContainer(
                image=args.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id, 'config-key',
                    'set', 'mgr/ssh/ssh_identity_pub', '-i', '/tmp/pub'
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                    tmp_pub.name: '/tmp/pub:z',
                },
            ).run()

            logging.info('Adding key to root@localhost\'s authorized_keys...')
            with open('/root/.ssh/authorized_keys', 'a') as f:
                os.fchmod(f.fileno(), 0o600)  # just in case we created it
                f.write(ssh_pub + '\n')

            logging.info('Enabling ssh module...')
            CephContainer(
                image=args.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id, 'mgr',
                    'module', 'enable', 'ssh'
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                    tmp_pub.name: '/tmp/pub:z',
                },
            ).run()
            logging.info('Setting orchestrator backend to ssh...')
            CephContainer(
                image=args.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id,
                    'orchestrator', 'set', 'backend', 'ssh'
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                    tmp_pub.name: '/tmp/pub:z',
                },
            ).run()
            host = get_hostname()
            logging.info('Adding host %s...' % host)
            CephContainer(
                image=args.image,
                entrypoint='/usr/bin/ceph',
                args=[
                    '-n', 'mon.', '-k',
                    '/var/lib/ceph/mon/ceph-%s/keyring' % mon_id, '-c',
                    '/var/lib/ceph/mon/ceph-%s/config' % mon_id,
                    'orchestrator', 'host', 'add', host
                ],
                volume_mounts={
                    mon_dir: '/var/lib/ceph/mon/ceph-%s:z' % (mon_id),
                    tmp_pub.name: '/tmp/pub:z',
                },
            ).run()
        return 0


def main(config):
    print(config)

    mapper = {'version': Version, 'deploy': Deploy, 'bootstrap': Bootstrap}
    # No default values or exception checking needed here,
    # argparse only allows defined subcommands.
    mapper.get(config.command)(config)


def container_app():
    # TODO: args
    if args.docker:
        podman_path = find_program('docker')
    else:
        for i in PODMAN_PREFERENCE:
            try:
                podman_path = find_program(i)
                break
            except Exception as e:
                logging.debug('could not locate %s: %s' % (i, e))
        if not podman_path:
            raise RuntimeError(
                'unable to locate any of %s' % PODMAN_PREFERENCE)


if __name__ == '__main__':

    if sys.version_info < (2, 6, 0):
        sys.stderr.write("You need python 2.6 or later to run this script\n")
        sys.exit(1)

    try:
        args = cmdline_args()
        main(args)

    # TODO: No bare except
    except Exception:
        raise
