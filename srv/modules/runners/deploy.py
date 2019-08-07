from ext_lib.hash_dir import pillar_questioneer

def mon():
    pillar_questioneer()
    # 'target' <- roles with 'role' foo.
    # call podman module targeting 'target'
    # podman modules figures out if we need to re-deploy/newly create
    # NOTE:
    # stage.5 sort of things need to go away.
    # only allow to specifically target nodes/hosts/services etc.
    # salt-run mon.remove <host>



""" Interface

# mon
#allows to share code, follows the osd.remove/replace
salt-run mon.deploy <reads from pillar/policy.cfg>
salt-run mon.remove <either delta or specify mon host>
salt-run mon.update <id..range(n), default is all>

# osd
salt-run osd.deploy <reads from drivegroups>
salt-run osd.remove <id..range(n)>
salt-run osd.replace <id..range(n)>
salt-run osd.update <id..range(n), default is all>

# host
salt-run host.update

# services (better name)
salt-run services.update (calls mon/mgr/osd.update internally)

# monitoring
salt-run monitoring.deploy
what else is here necessary?

# dashboard
salt-run dashboard.deploy
salt-run dashboard.configure

# combined
salt-run ceph.deploy (combines all modes in the right order) demo=True/False
demo=True/False creates pools and makes things ready for a POC



######## DREAMLAND ############

Wrap all runner in a deepsea> REPL type shell, that makes help messages, autocomplete, audit, history, suggestions etc

deepsea> osd.deploy

# prompt opens with ceph-volume foo.. --report output


deepsea> help osd.deploy

# prompt(pager) opens with manpage of drivegroups and options osd.deploy provides



"""
