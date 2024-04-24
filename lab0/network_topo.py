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

#!/usr/bin/python

from mininet.topo import Topo

class SingleSwitchTopo(Topo):
    "Single Switch Topology"
    def build(self, count=1):
        hosts = [self.addHost('h%d' % i)
        for i in range(1, count + 1)]
        s1 = self.addSwitch('s1')
        for h in hosts:
        self.addLink(h, s1)

class BridgeTopo(Topo):
    "Creat a bridge-like customized network topology according to Figure 1 in the lab0 description."

    def __init__(self):

        Topo.__init__(self)

        # TODO: add nodes and links to construct the topology; remember to specify the link properties

        # Add nodes
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        c1 = self.addController('c1')
        # Add links
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        # Opeartions
        self.start()
        CLI(net)
        net.stop()
        # Performance modeling
        net = Mininet(link=TCLink, host=cpuLimitedHost)
        net.addLink(h2, s1, bw=10, delay='50ms')
        net.addHost('h1', cpu=.2)

topos = {'bridge': (lambda: BridgeTopo())}
