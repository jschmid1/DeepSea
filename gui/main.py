import urwid
import logging
import salt.client
logging.basicConfig(filename='example.log',level=logging.DEBUG)

""" 
TODO:

Create a Config() class that implements a .save()
and .load() functions for diverse config options

Options may parsed out of files located in different locations

/srv/pillar/ceph/
/srv/pillar/ceph/cluster/
/srv/pillar/ceph/cluster/stack/global.cfg
/srv/pillar/ceph/cluster/stack/ceph/
/srv/pillar/ceph/cluster/stack/ceph/cluster.yml
/srv/pillar/ceph/cluster/stack/default/ceph/cluster.yml

Maybe we should add pre-loaded options for init.sls I need
to parse all dirs under /srv/salt/ceph/

Global 'Host' configurations might be set for.

/etc/sysctl.conf

"""

class Settings(object):
    """
    Common settings
    """

    def __init__(self):
        """
        Assign root_dir, salt __opts__ and stack configuration.  (Stack
        configuration is not used currently.)
        """
        __opts__ = salt.config.client_config('/etc/salt/master')
        self.__opts__ = __opts__

        for ext in __opts__['ext_pillar']:
            if 'stack' in ext:
                self.stack = ext['stack']
        self.root_dir = "/srv/pillar/ceph/proposals"

class SaltWriter(object):
    """
    All salt files are essentially yaml files in the pillar by default.  The
    pillar uses sls extensions and stack.py uses yml.
    """

    def __init__(self, **kwargs):
        """
        Keep yaml human readable/editable.  Disable yaml references.
        """
        self.dumper = yaml.SafeDumper
        self.dumper.ignore_aliases = lambda self, data: True

        if 'overwrite' in kwargs:
            self.overwrite = kwargs['overwrite']
        else:
            self.overwrite = False

    def write(self, filename, contents):
        """
        Write a yaml file in the conventional way
        """
        if self.overwrite or not os.path.isfile(filename):
            log.info("Writing {}".format(filename))
            with open(filename, "w") as yml:
                yml.write(yaml.dump(contents, Dumper=self.dumper,
                          default_flow_style=False))

class Config(object):

    def __init__(self):
        self.settings = Settings()
        self.local = salt.client.LocalClient()
        self.master_minion = self.get_master()
        self.deepsea_minions = self.deepsea_minions()
        # get from pillar
        self.pre_check()

    def pre_check(self):
       if not self.master_minion:
           raise ImportError("There is no minion with the master role.")
       if not self.deepsea_minions:
           self.deepsea_minions = '*'

    def deepsea_minions(self):
        return self.local.cmd(self.master_minion, 'pillar.get', ['deepsea_minions'], expr_form="compound").values()[0]

    def get_master(self):
        # Thats not very nice. Parse the file and check for the pillar data to be set..
        # this is TODO
        return self.local.cmd('*', 'pillar.get', ['master_minion'], expr_form="compound").values()[0]

    def get_roles(self):
        return self.local.cmd('*', 'pillar.get', ['roles'], expr_form="compound")

    def get_hosts(self):
        # make this more lightweight
        return self.get_roles().keys()

    def get_available_roles(self):
        return self.local.cmd(self.master_minion, 'pillar.get', ['available_roles'], expr_form="compound").values()[0]

    def get_clusters(self):
        return self.local.cmd(self.master_minion, 'pillar.get', ['cluster'], expr_form="compound").values()


class Cluster(object):
    
    def __init__(self):
        self._selected_node = None
        # load existing cluster
        self._layout = {}
        self.settings = Settings()
        self.cfg = Config()
        self.local = salt.client.LocalClient()
        self._selections = []
        self._hosts = []
        self._roles = []
        self._clusters = []
        self._conf_options = {}

    @property
    def hosts(self):
        return self._hosts

    @hosts.setter
    def hosts(self, hosts):
        self._hosts = hosts

    @property
    def config_options(self):
        # later with salt
        return self._conf_options

    @config_options.setter
    def config_options(self, opts):
        # later with salt
        self._conf_options = opts

    @property
    def roles(self):
        return self._roles

    @roles.setter
    def roles(self, roles):
        self._roles = roles

    @property
    def selections(self):
        return self._selections

    @selections.deleter
    def selections(self):
        del self._selections

    def add_to_selections(self, selections):
        self._selections.append(selections)

    def pop_from_selection(self):
        if len(self._selections) >= 1:
            self._selections.pop()

    @property
    def clusters(self):
        return self._clusters

    @clusters.setter
    def clusters(self, clusters):
        self._clusters = clusters
        
    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, new_layout):
        self._layout = new_layout

    def find_node_name(self):
        # a 'bit' hacky..
        node_name = set(self.hosts).intersection(self.selections).pop()
        logging.debug('Operating on node: {}'.format(node_name))
        # raise if None
        return node_name

    def find_role_name(self):
        # a 'bit' hacky..
        role_name = set(self.roles).intersection(self.selections).pop()
        logging.debug('Operating on role: {}'.format(role_name))
        # raise if None
        return role_name

    def layout_diff(self):
        pass

    def reverse_view(self):
        # show roles that list nodes
        nodes = []
        role = self.find_role_name()
        logging.info('Found role: {}'.format(role))
        for node, roles in self.layout.iteritems():
            logging.info("Node: {}".format(node))
            logging.info("with roles: {}".format(roles))
            if role in roles:
                nodes.append(node)
        return nodes


cl = Cluster()
clcl = cl
cfg = Config()
cl.layout = cfg.get_roles()
cl.clusters = cfg.get_clusters()
cl.roles = cfg.get_available_roles()
cl.hosts = cfg.get_hosts()
cl.config_options = {'config1': 'val1', 'config2': 'val2', 'config3': 'val3'}

import pdb;pdb.set_trace()

def register_position(widget_obj):
    logging.info(widget_obj.label)
    cl.add_to_selections(widget_obj.label)

def menu_button(caption, callback):
    button = urwid.Button(caption)
    urwid.connect_signal(button, 'click', callback)
    urwid.connect_signal(button, 'click', register_position)
    return urwid.AttrMap(button, None, focus_map='reversed')

def sub_menu(caption, choices):
    contents = menu(caption, choices)
    def open_menu(button):
        return top.open_box(contents)
    return menu_button([caption], open_menu)

def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    body.extend(choices)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))

def host_selector_callback(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    logging.info(cl.layout)
    hosts = cl.reverse_view()
    if not hosts:
        response = urwid.Text([u'There are no hosts assigned to this Role'])
        # FIXME: Q,ESC does not work here
    arg_to_open_box = [response]
    for host in hosts:
        user_data = button.label
        check_box_host = urwid.CheckBox(unicode(host))
        # being at that stage, all nodes have that role and are checked therefore
        check_box_host.set_state(True)
        urwid.connect_signal(check_box_host, 'change', register_host_change, user_data)
        arg_to_open_box.append(check_box_host)
    top.open_box(urwid.Filler(urwid.Pile(arg_to_open_box)))

    logging.info("Hosts with selected Role {}".format(hosts))

def role_selector_callback(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    args_to_open_box = [response]
    node_name = cl.find_node_name()
    for role in cl.roles:
        check_box_role = urwid.CheckBox(u"{}".format(role))
        if role in cl.layout[node_name]:
            check_box_role.set_state(True)
        user_data = button.label
        urwid.connect_signal(check_box_role, 'change', register_change, user_data)
        args_to_open_box.append(check_box_role)
    top.open_box(urwid.Filler(urwid.Pile(args_to_open_box)))

def conf_selector_callback(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    top.open_box(urwid.Filler(urwid.Pile([response])))

def cluster_selector_callback(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    top.open_box(urwid.Filler(urwid.Pile([response])))

def register_conf_change(obj, dunno):
    logging.info("Current layout: {}".format(layout))

def item_chosen(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    done = menu_button(u'Ok', exit_program)
    top.open_box(urwid.Filler(urwid.Pile([response, done])))

def item_edit(button):
    config_option = button.label
    text_edit_cap1 = ('editcp', u"{}: ".format(button.label))
    config_value = cl.config_options[button.label]
    text_edit_text1 = u"{}".format(config_value)
    #ask = urwid.AttrWrap(urwid.Edit(text_edit_cap1, text_edit_text1), 'editbx', 'editfc')
    ask = urwid.Edit(text_edit_cap1, text_edit_text1)
    button = urwid.Button(u'Save')
    reply = urwid.Text(u'')
    div = urwid.Divider()
    pile = urwid.Pile([ask, div, reply, div, button])
    #
    def on_ask_change(edit, new_edit_text):
        reply.set_text(new_edit_text)
    # Decorations of Edit -> AttrWrap can not be connected to signals

    urwid.connect_signal(ask, 'change', on_ask_change)
    user_data = {'key': config_option, 'value': reply}
    urwid.connect_signal(button, 'click', save_config_option, user_data)
    topo = urwid.Filler(pile, valign='top')

    top.open_box(topo)

def save_config_option(obj, user_data):
    if user_data['value'].text != '':
        if user_data['key'] in cl.config_options:
            cl.config_options[user_data['key']] = user_data['value'].text
        else:
            logging.info('handle this case')
        logging.info('user_data: {}'.format(user_data))
        logging.info('Saved config option successfully. new value: {}'.format(user_data['value'].text))
        logging.info(cl.config_options)
    else:
        logging.info('No Change in configuration. Not saving.')

# rename register_role_change
def register_change(obj, dunno, node_name):
    # True seems to be unchecked
    layout = cl.layout
    logging.info("Current layout: {}".format(layout))
    node_name = cl.find_node_name()
    if obj.get_state() is False:
        logging.info("Selected role {}".format(obj.label))
        cl.layout[node_name].append(obj.label)
    if obj.get_state() is True:
        logging.info("Deselected role {}".format(obj.label))
        cl.layout[node_name].remove(obj.label)

# rename register_role_change
def register_host_change(obj, dunno, node_name):
    # True seems to be unchecked
    layout = cl.layout
    logging.info("Current layout: {}".format(layout))
    role_name = cl.find_role_name()
    if obj.get_state() is False:
        logging.info("Slected role {}".format(obj.label))
        cl.layout[obj.label].append(role_name)
    if obj.get_state() is True:
        logging.info("Deselected role {}".format(obj.label))
        cl.layout[obj.label].remove(role_name)

def exit_program(button):
    raise urwid.ExitMainLoop()


menu_top = menu(u'Main Menu', [ sub_menu(u'Cluster', 
                                         [ 
                                          sub_menu(u'{}'.format(cluster_name), [ 
                                              sub_menu(u'Roles', [ 
                                                      sub_menu(u'{}'.format(role), [ 
                                                          menu_button(u'Assigned Hosts', host_selector_callback),
                                                          sub_menu(u'Config for Role', [ 
                                                              menu_button(u'config1', item_edit), 
                                                              menu_button(u'config2', item_edit)
                                                                 ]), 
                                                              ]) for role in cl.roles ]), 
                                              sub_menu(u'Cluster Config', [
                                                  menu_button(u'config1', item_edit), 
                                                  menu_button(u'config2', item_edit)]), 
                                              sub_menu(u'Hosts', [ 
                                                  sub_menu(u'{}'.format(host), [ 
                                                      sub_menu(u'Host options', [ 
                                                          menu_button(u'{}'.format(config_option), item_edit) for config_option in cl.config_options ]), 
                                                      menu_button(u'Role Selector', role_selector_callback)
                                                          ]) for host in cl.hosts ]),
                                                 ]) for cluster_name in cl.clusters
                                          ]), 
                                sub_menu(u'Global Configs', 
                                        [ sub_menu(u'Preferences', [ 
                                            menu_button(u'Dummy', item_chosen), ]), 
                                            menu_button(u'Dummy', item_chosen), ]), 
                                        ]) 

class CascadingBoxes(urwid.WidgetPlaceholder):
    max_box_levels = 7

    def __init__(self, box):
        super(CascadingBoxes, self).__init__(urwid.SolidFill(u' '))
        self.box_level = 0
        self.open_box(box)

    def open_box(self, box):
        self.original_widget = urwid.Overlay(urwid.LineBox(box),
            self.original_widget,
            align='center', width=('relative', 100),
            valign='middle', height=('relative', 100),
            min_width=24, min_height=8,
            left=self.box_level * 3,
            right=(self.max_box_levels - self.box_level - 1) * 3,
            top=self.box_level * 2,
            bottom=(self.max_box_levels - self.box_level - 1) * 2)
        self.box_level += 1

    def keypress(self, size, key):
        if key == 'esc' and self.box_level > 1:
            self.original_widget = self.original_widget[0]
            self.box_level -= 1
            cl.pop_from_selection()
        else:
            return super(CascadingBoxes, self).keypress(size, key)

#import pdb;pdb.set_trace()
top = CascadingBoxes(menu_top)
def main():
    urwid.command_map['h'] = urwid.CURSOR_LEFT
    urwid.command_map['j'] = urwid.CURSOR_DOWN
    urwid.command_map['k'] = urwid.CURSOR_UP
    urwid.command_map['l'] = urwid.CURSOR_RIGHT
    palette = [
        ('body','black','dark cyan', 'standout'),
        ('foot','light gray', 'black'),
        ('key','light cyan', 'black', 'underline'),
        ('title', 'white', 'black',),
        ('editfc','white', 'dark blue', 'bold'),
        ('editbx','light gray', 'dark blue'),
        ('editcp','black','light gray', 'standout'),
        ]

    footer_text = [
        ('title', "SES Configurator"), "    ",
        ('key', "UP, j"), ", ", ('key', "DOWN, k"), ", ",
        ('key', "PAGE UP"), " and ", ('key', "PAGE DOWN"),
        " move view  ",
        ('key', "Q"), " exits or moves one layer down",
        ]
    header_text = ('title', "SES Configurator")

    footer = urwid.AttrMap(urwid.Text(footer_text), 'foot')
    header = urwid.AttrMap(urwid.Text(header_text), 'header')
    view = urwid.Frame(top, footer=footer, header=header)
    loop = urwid.MainLoop(view, palette)
    loop.run()

main()
