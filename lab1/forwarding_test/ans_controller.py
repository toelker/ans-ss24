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

from ryu.base import app_manager
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet, ethernet, ipv6, arp
from ryu.ofproto import ofproto_v1_3, ether


class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
        'dpset': dpset.DPSet,
    }

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)

        # Here you can initialize the data structures you want to keep at the controller
        self.mac_to_port = {}
        self.datapaths = {}

        # Router port MACs assumed by the controller
        self.port_to_own_mac = {
            1: "00:00:00:00:01:01",
            2: "00:00:00:00:01:02",
            3: "00:00:00:00:01:03"
        }
        # Router port (gateways) IP addresses assumed by the controller
        self.port_to_own_ip = {
            1: "10.0.1.1",
            2: "10.0.2.1",
            3: "192.168.1.1"
        }
        self.dpset = kwargs['dpset']
        print(self.dpset)

    def _get_hwaddr(self, dpid, port_no):
        return self.dpset.get_port(dpid, port_no).hw_addr

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)


    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Initial flow entry for matching misses
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        self.mac_to_port[datapath.id] = {}
        self.datapaths[datapath.id] = {datapath}

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flow_mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                     match=match, instructions=inst)
        datapath.send_msg(flow_mod)

    # Handle the packet_in event
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg  # openflow message between controller and switch
        datapath = msg.datapath  # datapath of openflow message
        ofproto = msg.datapath.ofproto  # Openflow protocol for the switch
        parser = msg.datapath.ofproto_parser  # Parser for the openflow protocol message
        in_port = msg.match['in_port']  # input port from the packet message
        pkt = packet.Packet(msg.data)  # parse packet data from openflow message
        ether_frame = pkt.get_protocol(ethernet.ethernet)  # ethernet protocol header
        src_mac = ether_frame.src  # source MAC
        dst_mac = ether_frame.dst  # Destination MAC
        arp_pkt = pkt.get_protocol(arp.arp)
        print("ARP: ", arp_pkt)

        # Drop IPv6 packets (we use only ipv4 packages)
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=ether_frame.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            print("Dropped IPv6 Packet")
            return

        print("Source: ", src_mac)
        print("Destination: ", dst_mac)
        print("__________")
        print("SwitchID: ", datapath.id)
        print(self.mac_to_port)
        print("__________")

        print("************************************************")
        print(pkt)
        print("************************************************")

        self.mac_to_port[datapath.id][src_mac] = in_port

        if dst_mac == 'ff:ff:ff:ff:ff:ff':
            out_port = ofproto.OFPP_FLOOD
        elif dst_mac in self.mac_to_port[datapath.id]:
            out_port = self.mac_to_port[datapath.id][datapath.id]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, dst_mac, src_mac, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        datapath.send_msg(out)
