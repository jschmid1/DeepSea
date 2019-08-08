from ext_lib.hash_dir import pillar_questioneer
import salt.client

def mon():
    pillar_questioneer()
    # 'target' <- roles with 'role' foo.
    # call podman module targeting 'target'
    # podman modules figures out if we need to re-deploy/newly create
    # NOTE:
    # stage.5 sort of things need to go away.
    # only allow to specifically target nodes/hosts/services etc.
    # salt-run mon.remove <host>
    local_client = salt.client.LocalClient()
    ret: str = local_client.cmd("cluster:ceph", 'podman.create_mon', ['registry.suse.de/devel/storage/6.0/images/ses/6/ceph/ceph', 'foo'], tgt_type='pillar')


def mon_remove():
    local_client = salt.client.LocalClient()
    ret: str = local_client.cmd("cluster:ceph", 'podman.remove_mon', ['registry.suse.de/devel/storage/6.0/images/ses/6/ceph/ceph', 'foo'], tgt_type='pillar')
