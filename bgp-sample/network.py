#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, info, setLogLevel
from mininet.util import dumpNodeConnections, quietRun, moveIntf
from mininet.cli import CLI
from mininet.node import Switch, OVSKernelSwitch

from subprocess import Popen, PIPE, check_output
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

#Taken/Derived from https://bitbucket.org/jvimal/bgp/overview
#https://github.com/mininet/mininet/wiki/BGP-Path-Hijacking-Attack-Demo

setLogLevel('info')

class Router(Switch):
    """Defines a new router that is inside a network namespace so that the
    individual routing entries don't collide.

    """
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)
        Router.ID += 1
        self.switch_id = Router.ID

    @staticmethod
    def setup():
        return

    def start(self, controllers):
        pass

    def stop(self):
        self.deleteIntfs()

    def log(self, s, col="magenta"):
        print T.colored(s, col)

class SimpleTopo(Topo):
    """
    TOPOLOGY:
        AS2
       /   \ 
    AS1     AS4
       \   /
        AS3
    """

    slow_conn = {'bw': 1}
    fast_conn = {'bw': 10}
 
    def __init__(self):
        # Add default members to class.
        super(SimpleTopo, self ).__init__()
        num_hosts_per_as = 1
        num_ases = 4
        num_hosts = num_hosts_per_as * num_ases
        # The topology has one router per AS
        routers = []
        for i in xrange(num_ases):
            router = self.addSwitch('R%d' % (i+1))
	      routers.append(router)
        hosts = []
        for i in xrange(num_ases):
            router = 'R%d' % (i+1)
            for j in xrange(num_hosts_per_as):
                hostname = 'h%d-%d' % (i+1, j+1)
                host = self.addNode(hostname)
                hosts.append(host)
                self.addLink(router, host)

        #AS2 has a 1 MBPS link while AS3 has 10 MBPS
        self.addLink('R1', 'R2', **slow_conn)
        self.addLink('R2', 'R4', **slow_conn)
        self.addLink('R1', 'R3', **fast_conn)
        self.addLink('R3', 'R4', **fast_conn)

        for j in xrange(num_hosts_per_as):
            hostname = 'h%d'.format(j)
            host = self.addNode(hostname)
            hosts.append(host)
            self.addLink('R{}'.format(j), hostname)
        return

