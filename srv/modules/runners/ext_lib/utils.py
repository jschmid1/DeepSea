import salt.client
import salt.runner

def runner(opts):
    runner = salt.runner.RunnerClient(opts)
    __master_opts__ = salt.config.client_config("/etc/salt/master")
    __master_opts__['quiet'] = False
    qrunner = salt.runner.RunnerClient(__master_opts__)
    return qrunner
