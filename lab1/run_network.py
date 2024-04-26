"""
 Copyright 2024 Computer Networks Group @ UPB

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """

#!/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


class NetworkTopo(Topo):

    def __init__(self):

        Topo.__init__(self)

        h1 = self.addHost(name="h1", ip="10.0.1.2/24", defaultRoute="via 10.0.1.1")
        h2 = self.addHost(name="h2", ip="10.0.1.2/24", defaultRoute="via 10.0.1.1")
        ser = self.addHost(name="ser", ip="10.0.2.2/24", defaultRoute="via 10.0.2.1")
        ext = self.addHost(name="ext", intf="ext_eth0", ip="192.168.1.123/24", defaultRoute="via 192.168.1.1")

        s1 = self.addSwitch("s1", inft="s1_eth1")
        s2 = self.addSwitch("s2", intf="s2_eth2")
        s3 = self.addSwitch("s3", intf="s3_eth0") #Router
                   
        self.addLink(h1, s1, bw=15, delay='10ms')    #Host1, Switch1
        self.addLink(h2, s1, bw=15, delay='10ms')    #Host2, Switch1

        self.addLink(node1=s3, node2=s1, bw=15, delay='10ms', intf1="s3_eth1", intf2="s1_eth1", params1={"ip":"10.0.1.1/24"})    #Switch1, Router
        self.addLink(s3, s2, bw=15, delay='10ms', intf1="s3_eth2", intf2="s2_eth2", params1={"ip":"10.0.2.1/24"})    #Router, Switch2
        self.addLink(s3, ext, bw=15, delay='10ms', intf1="s3_eth3", intf2="ext_eth0", params1={"ip":"192.168.1.1/24"})   #Router, Internet Host

        self.addLink(s2, ser, bw=15, delay='10ms')  # Switch2, Data center server

        # Build the specified network topology here

def run():
    topo = NetworkTopo()
    net = Mininet(topo=topo,
                  switch=OVSKernelSwitch,
                  link=TCLink,
                  controller=None)
    net.addController(
        'c1',
        controller=RemoteController,
        ip="127.0.0.1",
        port=6653)
    net.get("s3").intf("s3-eth1").setMAC("00:00:00:00:01:01")
    net.get("s3").intf("s3-eth2").setMAC("00:00:00:00:01:02")  # setmac
    net.get("s3").intf("s3-eth3").setMAC("00:00:00:00:01:03")  # setmac

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()