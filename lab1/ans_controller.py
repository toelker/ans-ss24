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
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ethernet, packet, ipv6
from ryu.ofproto import ofproto_v1_3
from ipaddress import IPv4Address


class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)

        self.mac_to_port = {}

        # Here you can initialize the data structures you want to keep at the controller

    
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

        print("Switch connected: ", datapath.id)

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    # Handle the packet_in event
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg    #openflow message between controller and switch
        datapath = msg.datapath #datapath of openflow message
        ofproto = msg.datapath.ofproto  #Openflow protocol for the switch
        parser = msg.datapath.ofproto_parser    # Parser for the openflow protocol message
        in_port = msg.match['in_port']  # input port from the packet message
        pkt = packet.Packet(msg.data)   #parse packet data from openflow message
        eth = pkt.get_protocol(ethernet.ethernet)   #ethernet protocol header

        # Drop IPv6 packets (we use only ipv4 packages)
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            print("Dropped IPv6 Packet")
            return

        src_mac = eth.src   #source MAC
        dst_mac = eth.dst   #Destination MAC

        print("Source: ", src_mac)
        print("Destination: ", dst_mac)

        self.mac_to_port[datapath.id][src_mac] = in_port


        print("Got Packages")
        print("")
        self.package_flooding(datapath, msg, in_port)


    def package_flooding(self, datapath, msg, in_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port) for port in self.mac_to_port[datapath.id].values()
                   if port != in_port]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)