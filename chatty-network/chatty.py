#!/usr/bin/python

import sys
import os
import subprocess

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg
from mininet.node import Node
from mininet.topolib import TreeTopo
from mininet.util import waitListening

def TreeNet(depth=1, fanout=2, **kwargs):
    topo = TreeTopo(depth, fanout)
    return Mininet(topo, **kwargs)

def connectToRootNS(network, switch, ip, routes):
    root = Node('root', inNamespace=False)
    intf = network.addLink(root, switch).intf1
    root.setIP(ip, intf=intf)
    network.start()
    for route in routes:
        root.cmd('route add -net {} dev {} '.format(route, intf)) 

def chatserver(host, cwd, hostname, port, cmd='{}webserver.py --addr {} --port {}'):
    cmd = '{} &'.format(cmd.format(cwd, hostname, port))
    host.cmd(cmd)
    print "*** Starting webserver ***"
    print cmd
#    waitListening(server=hostname, port=port, timeout=5)

def client(host, cwd, hostname, port, cmd='{}client.py --host {} --port {}'):
    print "**** Running Client ****"
    host.cmd('{}'.format(cmd.format(cwd, hostname, port)))

def run_cmd(cmd, cwd):
    subprocess.check_call([cmd], shell=True, cwd=cwd)

def getcwd():
    return os.path.join(os.getcwd(), 'bin/greenlet-chatserver-example/')

def get_ip(host):
    '''
    Gets the ip on eth0
    '''
    return host.intfs[0].ip

 
def run():
    network = TreeNet(depth=1, fanout=4)
    webserver,clients = (network.hosts[0], network.hosts[1:])
    port = 80
    chatserver(webserver, getcwd(), get_ip(webserver), port)
    for host in clients:
        client(host, getcwd(), get_ip(webserver), port)
    webserver.cmd('pkill -9 -f {}'.format('webserver.py'))
    network.stop()
    

def install():
    '''
    Setup test env
    '''

    code_root = os.environ.get('NM_TESTS_ROOT', os.getcwd())
    code_bin = os.path.join(code_root, 'bin')
    if not os.path.exists(code_bin):
        os.makedirs(code_bin)
    
    #Install mininet
    cmds = [
        'git clone git://github.com/mininet/mininet',
        'mininet/util/install.sh -s {}'.format(code_bin)
    ]

    #Install chatserver
    cmds += [
        'git clone git@github.com:amwelch/greenlet-chatserver-example.git',
        'pip install -r {}/greenlet-chatserver-example/requirements.txt'.format(code_bin)
    ]

    for cmd in cmds:
        run_cmd(cmd, cwd = code_bin)

if __name__ == '__main__':
    run()
