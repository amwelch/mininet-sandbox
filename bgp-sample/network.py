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
        for i in range(1, num_ases+1):
            router = self.addSwitch('R%d' % (i))
            routers.append(router)
        hosts = []
        for i in range(1, num_ases+1):
            router = 'R%d' % (i)
            for j in range(num_hosts_per_as):
                hostname = 'h%d_%d' % (i, j)
                host = self.addNode(hostname)
                hosts.append(host)
                self.addLink(router, host)
  
        #AS2 has a 1 MBPS link while AS3 has 10 MBPS
        self.addLink('R1', 'R2')
        self.addLink('R2', 'R4')
        self.addLink('R1', 'R3')
        self.addLink('R3', 'R4')

        return

def get_host_id(hostname):
    return int(hostname.split('_')[1])

def get_host_asn(hostname):
    asn = int(hostname.split('_')[0].replace('h', ''))
    return asn

def get_router_asn(hostname):
    return int(hostname.replace('R', ''))

def get_router_ip(hostname):
    asn = get_router_asn(hostname)
    ip = '{}.0.1.254'.format(10+asn)
    return ip

def getIP(hostname):
    asn = get_host_asn(hostname)
    num = get_host_id(hostname)
    ip = '%s.0.%s.1' % (10+asn, num)
    return ip

def getGateway(hostname):
    asn = get_host_asn(hostname)
    gw = '%s.0.1.254' % (10+asn)
    return gw

bird_template = '''
log syslog all;

router id {local_ip};

protocol kernel {{
   import all;
   export all;
}}
{neighbors}
'''
neighbor_template = '''
protocol bgp as{remote_as} {{
    import all;
    export all;
    local as {local_as};
    source address {local_ip};
    neighbor {neighbor_ip} as {remote_as};
}}
'''

def make_directories(d):
    try:
        os.makedirs(os.path.dirname(d))
    except OSError:
        pass
    return

def get_bird_conf(hostname):
    return '/usr/local/etc/bird.{}.conf'.format(hostname)

def write_bgp_conf(hostname, neighbors):
    local_asn = get_router_asn(hostname)
    local_ip = get_router_ip(hostname)

    neighbor_buf = ''
    for neighbor in neighbors:
        asn = get_router_asn(neighbor)
        ip = get_router_ip(neighbor)
        neighbor_buf += neighbor_template.format(remote_as=asn, 
            local_as=local_asn, local_ip=local_ip, neighbor_ip=ip)

    buf = bird_template.format(local_ip=ip, neighbors=neighbor_buf)
    ofn = get_bird_conf(hostname)
    make_directories(ofn)
    with open(ofn, 'w') as fp:
        fp.write(buf)

def main():
    os.system("rm -f /tmp/R*.log /tmp/R*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 bird > /dev/null 2>&1")

    net = Mininet(topo=SimpleTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    sleep_time = 1
    print "Waiting {} seconds for sysctl changes to take effect...".format(sleep_time)
    sleep(sleep_time)

    #Write the bird config files
    write_bgp_conf('R1', ['R2', 'R3'])
    write_bgp_conf('R2', ['R1', 'R4'])
    write_bgp_conf('R3', ['R1', 'R4'])
    write_bgp_conf('R4', ['R2', 'R3'])

    os.system("killall -9 bird")
    for router in net.switches:

        router.cmd("ifconfig {}-eth1 {}".format(router.name, get_router_ip(router.name)))

        conf = get_bird_conf(router.name)
        cmd = "bird -c {} 2>&1".format(conf)
        print "Starting bird on %s" % router.name
        print cmd
        router.cmd(cmd, shell=True)
        router.waitOutput()

    for host in net.hosts:
        host.cmd("ifconfig %s-eth0 %s" % (host.name, getIP(host.name)))
        host.cmd("route add default gw %s" % (getGateway(host.name)))

    CLI(net)
    net.stop()
    os.system("killall -9 bird")


if __name__ == "__main__":
    main()
