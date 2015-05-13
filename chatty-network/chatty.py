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

SERVER_PORT = 8080

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

def chatserver(network, cmd='webserver.py', hosts=None, routes=None, switch=None):
    if not switch:
        switch = network['s1']
    if not routes:
        routes = ['10.0.0.0/24']
    connectToRootNS(network, switch, ip, routes)
    for host in network.hosts:
        host.cmd('{} &'.format(cmd))
    print "*** Starting webserver ***"
    for server in hosts:
        waitListening(server=server, port=SERVER_PORT, timeout=5)

def run_cmd(cmd, cwd):
    subprocess.check_call([cmd], shell=True, cwd=cwd)

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
    install()
