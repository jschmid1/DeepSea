from ext_lib.utils import runner


# Downside of calling runners from runners and that every runner is selfcontained (in terms of module/pillar sync) is that we now check the dir checksums for every call here

def deploy_core():
    print("may check for updates before")
    foo = runner(__opts__)
    foo.cmd('mon.deploy')
    foo.cmd('mgr.deploy')
    foo.cmd('disks.deploy')

def deploy_services(demo=False):
    print("may check for updates before")
    print("Call to ceph-iscsi")
    print("Call to mds")
    print("Call to nfs-ganesha")
    print("Call to rgw")

def deploy(demo=False):
    deploy_core()
    foo = runner(__opts__)
    foo.cmd('services.deploy')
