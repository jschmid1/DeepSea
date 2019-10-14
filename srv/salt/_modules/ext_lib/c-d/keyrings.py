import logging
from container import CephContainer

class Keyring(object):

    def __init__(self):
        self.config = Config()

def create_mon_key(image):
    # create some initial keys
    logging.info('Creating initial mon key..')
    mon_key = CephContainer(
        image=image,
        entrypoint='/usr/bin/ceph-authtool',
        args=['--gen-print-key'],
    ).run().stdout
    return mon_key
