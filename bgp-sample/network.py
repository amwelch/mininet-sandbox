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

import os
import sys

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
        self.addLink('R1', 'R2')
        self.addLink('R2', 'R4')
        self.addLink('R1', 'R3')
        self.addLink('R3', 'R4')

        for asn in range(num_ases):
            for j in range(num_hosts_per_as):
                hostname = 'h{}-{}'.format(asn, j)
                host = self.addNode(hostname)
                hosts.append(host)
                self.addLink('R{}'.format(asn+1), hostname)
        return

def get_host_id(hostname):
    return int(hostname.split('-')[1])

def get_host_asn(hostname):
    asn = int(hostname.split('-')[0].replace('h', ''))
    return asn

def getIP(hostname):
    asn = get_host_asn(hostname)
    num = get_host_id(hostname)
    ip = '%s.0.%s.1/24' % (10+asn, num)
    return ip

def getGateway(hostname):
    asn = get_host_asn(hostname)
    num = get_host_id(hostname)
    gw = '%s.0.%s.254' % (10+asn, num)
    return gw

def main():
    os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 bird > /dev/null 2>&1")

    net = Mininet(topo=SimpleTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    sleep_time = 10
    print "Waiting {} seconds for sysctl changes to take effect...".format(sleep_time)
    sleep(sleep_time)

    for router in net.switches:
        router.cmd("bird 2>&1", shell=True)
        router.waitOutput()
        print "Starting bird on %s" % router.name

    for host in net.hosts:
        host.cmd("ifconfig %s-eth0 %s" % (host.name, getIP(host.name)))
        host.cmd("route add default gw %s" % (getGateway(host.name)))

    CLI(net)
    net.stop()
    os.system("killall -9 bird")


if __name__ == "__main__":
    main()
