from utils import extract_uid_gid, get_hostname, make_fsid

class Config(object):

    def __init__(self, config):
        self.image = config.image
        self.mon_ip = config.mon_ip
        self.mon_addrv = config.mon_addrv
        self.output_config = config.output_config
        self.output_keyring = config.output_keyring
        self.ceph_conf = config.config
        self.ceph_uid, self.ceph_gid = extract_uid_gid(self.image)
        self.data_dir = config.data_dir
        self.log_dir = config.log_dir
        self.unit_dir = config.unit_dir
        self.fsid = config.fsid or make_fsid()
        self.mon_id = config.mon_id or get_hostname()
        self.mgr_id = config.mgr_id or get_hostname()
