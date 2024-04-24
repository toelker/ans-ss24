
from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__(self):
        Topo.__init__(self)

        # Add hosts and switches
        leftHost = self.addHost(name='h1', ip='10.0.1.2/24')
        rightHost = self.addHost(name='h1', ip='10.0.1.2/24')
        leftSwitch = self.addSwitch( 's3' )
        rightSwitch = self.addSwitch( 's4' )

        # Add links
        self.addLink( leftHost, leftSwitch )
        self.addLink( leftSwitch, rightSwitch )
        self.addLink( rightSwitch, rightHost )



topos = { 'mytopo': ( lambda: MyTopo() ) }
