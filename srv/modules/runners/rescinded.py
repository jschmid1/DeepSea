#!/usr/bin/python

import salt.client
import pprint


def ids(cluster, **kwargs):
    """
    """
        
    local = salt.client.LocalClient()

    # Restrict search to this cluster
    search = "I@cluster:{}".format(cluster)

    pillar_data = local.cmd(search , 'pillar.items', [], expr_form="compound")
    ids = []
    for minion in pillar_data.keys():
        if ('roles' in pillar_data[minion] and
            'storage' in pillar_data[minion]['roles']):
                continue
        data = local.cmd(minion, 'osd.list', [], expr_form="glob")
        ids.extend(data[minion])
    return ids

