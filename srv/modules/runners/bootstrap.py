from ext_lib.utils import runner

# We have to take care of the one-time operations that need to be done before a deployment


"""

TODO: Make the time-server thing separate

* Update the host system
* Populate the proposals (salt-run populate.proposals)
* Scan for the networks (maybe ask the user this time?)
* SSL-certificates


"""


def ceph():
    qrunner = runner(__opts__)
    print("Print a basic help thing explaining the steps and asking for a timeserver")

    print("If policty.cfg and proposals dir is not present")
    print("qrunner.cmd('host.update')")
    print("qrunner.cmd('populate.proposals')")
    print("Ask the user to create(adapt) a policy.cfg. Exit and ask to re-run this command")
    print("This is now the entry point for the second invocation")
    print("Use salt-run advise-networks to ask user if that's the right networks")
    print("Tell user where mon and mgrs will be deployed")
    print("Do it with interactive mode")
    print("After successful deploy. Guide towards osd.deploy and drivegroups (wiki)")
    print("From there on every command (mon/osd/mgr) should be selfcontained and doesn't require an additional step")
    print("I.e. adding a MON. 1) Adapt the policy.cfg 2) Run mon.deploy")

    print(""" Open questions:

    When to update the /srv/pillar/ struct. Previously we did that in every stage.1 invocation
    We may keep track of the salt-key -L ('inventory')
""")


def cluster():
    ceph()
