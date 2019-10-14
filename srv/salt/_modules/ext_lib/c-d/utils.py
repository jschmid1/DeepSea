from distutils.spawn import find_executable
import socket
import os
import uuid
import socket
from distutils.spawn import find_executable
LOG_DIR_MODE = 0o770
DATA_DIR_MODE = 0o700


def pathify(p):
    if '/' not in p:
        return './' + p
    return p


def get_hostname():
    return socket.gethostname()


def make_fsid():
    return str(uuid.uuid1())


def is_fsid(s):
    try:
        uuid.UUID(s)
    except ValueError:
        return False
    return True


def makedirs(dir, uid, gid, mode):
    os.makedirs(dir, exist_ok=True, mode=mode)
    os.chown(dir, uid, gid)
    os.chmod(dir, mode)  # the above is masked by umask...


def find_program(filename):
    name = find_executable(filename)
    if name is None:
        raise ValueError(f'{filename} not found')
    return name


def get_unit_name(fsid, daemon_type, daemon_id):
    return 'ceph-%s@%s.%s' % (fsid, daemon_type, daemon_id)


def get_daemon_args(fsid, daemon_type, daemon_id):
    r = [
        '--default-log-to-file=false',
        '--default-log-to-stderr=true',
    ]
    if fsid and daemon_id:
        r += [
            '--default-admin-socket', '/var/run/ceph/' + fsid + '-' +
            daemon_type + '.' + daemon_id + '.asok'
        ]
    r += ['--setuser', 'ceph']
    r += ['--setgroup', 'ceph']
    return r


def get_legacy_config_fsid(cluster):
    try:
        config = configparser.ConfigParser()
        config.read('/etc/ceph/%s.conf' % cluster)
        # TODO: use dict.getter
        if 'global' in config and 'fsid' in config['global']:
            return config['global']['fsid']
    # TODO: bare exception
    except Exception as e:
        logging.warning(
            'unable to parse \'fsid\' from \'[global]\' section of /etc/ceph/ceph.conf: %s'
            % e)
        return None
    return None


def create_daemon_dirs(fsid,
                       daemon_type,
                       daemon_id,
                       uid,
                       gid,
                       config=None,
                       data_dir=None,
                       log_dir=None,
                       keyring=None):
    data_dir = make_data_dir(
        fsid, daemon_type, daemon_id, uid=uid, gid=gid, data_dir=data_dir)
    make_log_dir(fsid, uid=uid, gid=gid, log_dir=log_dir)

    if config:
        with open(data_dir + '/config', 'w') as f:
            os.fchown(f.fileno(), uid, gid)
            os.fchmod(f.fileno(), 0o600)
            f.write(config)
    if keyring:
        with open(data_dir + '/keyring', 'w') as f:
            os.fchmod(f.fileno(), 0o600)
            os.fchown(f.fileno(), uid, gid)
            f.write(keyring)


def check_unit(unit_name):
    try:
        # TODO: generalize check_output and decoding
        out = subprocess.check_output(['systemctl', 'is-enabled', unit_name])
        enabled = out.decode('utf-8').strip() == 'enabled'
    # TODO: bare exceptions
    except Exception as e:
        logging.warning('unable to run systemctl' % e)
        enabled = False
    try:
        out = subprocess.check_output(['systemctl', 'is-active', unit_name])
        active = out.decode('utf-8').strip() == 'active'
    # TODO: bare exceptions
    except Exception as e:
        logging.warning('unable to run systemctl: %s' % e)
        active = False
    return (enabled, active)



def get_container_mounts(fsid,
                         daemon_type,
                         daemon_id,
                         data_dir=None,
                         log_dir=None):
    mounts = {}

    if fsid:
        log_dir = get_log_dir(fsid, log_dir=log_dir)
        mounts[log_dir] = '/var/log/ceph:z'

    if daemon_id:
        data_dir = get_data_dir(
            fsid, daemon_type, daemon_id, data_dir=data_dir)
        cdata_dir = '/var/lib/ceph/%s/ceph-%s' % (daemon_type, daemon_id)
        mounts[data_dir] = cdata_dir + ':z'
        mounts[data_dir + '/config'] = '/etc/ceph/ceph.conf:z'

    if daemon_type in ['mon', 'osd']:
        mounts['/dev'] = '/dev:z'  # FIXME: narrow this down?
        mounts['/run/udev'] = '/run/udev:z'
    if daemon_type == 'osd':
        mounts['/sys'] = '/sys:z'  # for numa.cc, pick_address, cgroups, ...
        mounts['/run/lvm'] = '/run/lvm:z'
        mounts['/run/lock/lvm'] = '/run/lock/lvm:z'

    return mounts


def get_log_dir(fsid, log_dir):

    return os.path.join(log_dir, fsid)


def get_data_dir(fsid, t, n, data_dir):
    return os.path.join(data_dir, fsid, '%s.%s' % (t, n))


def make_data_dir(fsid,
                  daemon_type,
                  daemon_id,
                  uid=None,
                  gid=None,
                  data_dir=None):
    make_data_dir_base(fsid, uid, gid, data_dir)
    data_dir = get_data_dir(fsid, daemon_type, daemon_id, data_dir)
    makedirs(data_dir, uid, gid, DATA_DIR_MODE)
    return data_dir


def make_data_dir_base(fsid, uid, gid, data_dir):

    data_dir_base = os.path.join(data_dir, fsid)
    makedirs(data_dir_base, uid, gid, DATA_DIR_MODE)
    return data_dir_base


def make_log_dir(fsid, uid=None, gid=None, log_dir=None):
    log_dir = get_log_dir(fsid, log_dir)
    makedirs(log_dir, uid, gid, LOG_DIR_MODE)
    return log_dir
