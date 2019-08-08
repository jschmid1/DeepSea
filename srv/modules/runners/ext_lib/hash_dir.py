import hashlib
import os
from pathlib import Path
import salt.client
import logging
from .pillar import proposal


def update_pillar():
    local_client = salt.client.LocalClient()
    print('Updating the pillar')
    proposal()
    ret: str = local_client.cmd(
        "cluster:ceph", 'state.apply', ['ceph.refresh'], tgt_type='pillar')
    # if (accumulated)ret == 0:
    # update md5()
    # TODO catch errors here
    print("Updating the directory's checksum")
    update_md5()
    print("The pillar should be in sync now")


directory = '/srv/pillar/ceph/'
checksum_path = f'{directory}/.md5.save'


def md5_update_from_dir(directory, hash):
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir()):
        hash.update(path.name.encode())
        if path.is_file():
            # hack, due to file permissions of /srv/pillar/ceph
            # Ideally the checksum_file would live in /srv/pillar/
            # but this belongs to root:root and due to SUSE's salt-master
            # permission policy it can only can operate with salt:salt.
            if path.match('.md5.save'):
                continue
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash.update(chunk)
        elif path.is_dir():
            hash = md5_update_from_dir(path, hash)
    return hash


def md5_dir(directory):
    return md5_update_from_dir(directory, hashlib.md5()).hexdigest()


def save_md5(md5):
    with open(checksum_path, 'w') as _fd:
        _fd.write(md5)


def update_md5():
    save_md5(md5_dir(directory))


def read_old_md5(directory):
    if not os.path.exists(checksum_path):
        update_md5()
        return '0'
    with open(checksum_path, 'r') as _fd:
        return _fd.read()


def pillar_has_changes():
    if md5_dir(directory) != read_old_md5(directory):
        return True
    return False


def pillar_questioneer():
    if pillar_has_changes():
        print("You have pending changes in the pillar that needs to be synced to the minions. Would you like to sync now?")
        answer = input("(y/n)")
        if answer.lower() == 'y':
            update_pillar()
        else:
            print("\nNot updating the pillar, please keep in mind that lalalalala")
