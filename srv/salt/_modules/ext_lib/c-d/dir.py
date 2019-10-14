import os


class Directory(object):
    def __init__(self, config):
        self.config = config
        self.daemon_type = None
        self.daemon_id = None

    def __getattr__(self, attr):
        # Inheritance vs Composition..
        return getattr(self.config, attr)

    def create_daemon_dirs(self, daemon_type=None daemon_id=None, config=None, keyring=None):
        self.daemon_type = daemon_type
        self.daemon_id = daemon_id
        data_dir = self.make_data_dir()
        log_dir = self.make_log_dir()

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

    def get_log_dir(self):
        return os.path.join(self.log_dir, self.fsid)


    def get_data_dir(self):
        return os.path.join(self.data_dir, self.fsid, '%s.%s' % (self.daemon_type, self.daemon_id))


    def make_data_dir(self):
        self.make_data_dir_base()
        data_dir = self.get_data_dir()
        makedirs(data_dir, uid, gid, DATA_DIR_MODE)
        return data_dir


    def make_data_dir_base(self, fsid, uid, gid, data_dir):

        data_dir_base = os.path.join(data_dir, fsid)
        makedirs(data_dir_base, uid, gid, DATA_DIR_MODE)
        return data_dir_base


    def make_log_dir(self, fsid, uid=None, gid=None, log_dir=None):
        log_dir = get_log_dir(fsid, log_dir)
        makedirs(log_dir, uid, gid, LOG_DIR_MODE)
        return log_dir
