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
    qrunner = runner()
    print("Print a basic help thing explaining the steps and asking for a timeserver")

    print("If policty.cfg and proposals dir is not present")
    qrunner.cmd('host.update')
    qrunner.cmd('populate.proposals')
    print("Ask the user to create(adapt) a policy.cfg. Exit and ask to re-run this command")
    print("This is now the entry point for the second invocation")
    print("Tell user where mon and mgrs will be deployed")
    print("Do it with interactive mode")
    print("After successful deploy. Guide towards osd.deploy and drivegroups (wiki)")
