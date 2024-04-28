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
from ryu.lib.packet import packet, ethernet, ipv6, arp
from ryu.ofproto import ofproto_v1_3, ether


class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.arp_table = {}
        self.datapaths = {}

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
        self.datapaths[datapath.id] = {datapath}


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
        msg = ev.msg  # openflow message between controller and switch
        datapath = msg.datapath  # datapath of openflow message
        ofproto = msg.datapath.ofproto  # Openflow protocol for the switch
        parser = msg.datapath.ofproto_parser  # Parser for the openflow protocol message
        in_port = msg.match['in_port']  # input port from the packet message
        pkt = packet.Packet(msg.data)  # parse packet data from openflow message
        ether_frame = pkt.get_protocol(ethernet.ethernet)  # ethernet protocol header

        # Drop IPv6 packets (we use only ipv4 packages)
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=ether_frame.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            print("Dropped IPv6 Packet")
            return


        arp_pkt = pkt.get_protocol(arp.arp)
        print("ARP: ", arp_pkt)
        #Check if packet is ARP-request
        if arp_pkt:
            self.arp_handler(arp_pkt, ev, datapath)
            return

        src_mac = ether_frame.src  # source MAC
        dst_mac = ether_frame.dst  # Destination MAC

        print("Source: ", src_mac)
        print("Destination: ", dst_mac)
        print("__________")
        print("SwitchID: ", datapath.id)
        print(self.mac_to_port)
        print("__________")

        self.mac_to_port[datapath.id][src_mac] = in_port

        if dst_mac in self.mac_to_port[datapath.id]:
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



    def arp_handler(self, arp_pkt, ev, datapath):
        # ARP packet is received
        print("ARP handler")
        # Store the sender host information
        src_ip = arp_pkt.src_ip
        src_mac = arp_pkt.src_mac
        if src_ip not in self.arp_table:
            self.arp_table[src_ip] = src_mac

        dst_ip = arp_pkt.dst_ip

        if arp_pkt.opcode == arp.ARP_REQUEST:
            if dst_ip in self.arp_table:
                # If ARP request and destination MAC is known, send ARP reply
                print("ARP destination is in hosts, sending ARP reply")
                dst_mac = self.arp_table[dst_ip]
                self.send_arp_reply(ev.msg.datapath,
                                    dst_mac, src_mac, dst_ip, src_ip, ev.msg.match['in_port'])
            else:
                # If ARP request and destination MAC is not known, send ARP request to all hosts
                print("ARP destination is not in hosts, sending ARP request")
                dp_dict = datapath.ports
                for key in dp_dict:
                    if key != datapath.id:  # Don't send ARP request to the same Datapath
                        self.send_arp_request(datapath, src_mac, src_ip, dst_ip)

        else:
            print("ARP reply received from ", src_ip)
            # No need to do anything as we already stored the host IP, we wait for the requester to send another ARP request


    def send_arp_reply(self, datapath, src_mac, dst_mac, src_ip, dst_ip, in_port):
        self.send_arp(datapath, arp.ARP_REPLY, src_mac,
                        src_ip, dst_mac, dst_ip, in_port)

    def send_arp_request(self, datapath, src_mac, src_ip, dst_ip):
        self.send_arp(datapath, arp.ARP_REQUEST, src_mac,
                        src_ip, None, dst_ip, None)

    def send_arp(self, datapath, opcode, src_mac, src_ip, dst_mac, dst_ip, in_port):
        eth_dst_mac = dst_mac
        arp_dst_mac = dst_mac


        if opcode == arp.ARP_REQUEST:
            eth_dst_mac = 'ff:ff:ff:ff:ff:ff'
            arp_dst_mac = '00:00:00:00:00:00'
            actions = [datapath.ofproto_parser.OFPActionOutput(
                datapath.ofproto.OFPP_FLOOD)]
        else:
            actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]

        # Create Ethernet header
        eth = ethernet.ethernet(
            dst=eth_dst_mac,
            src=src_mac,
            ethertype=packet.ethernet.ether.ETH_TYPE_ARP
        )

        # Create ARP header
        arp_header = arp.arp(
            opcode=opcode,
            src_mac=src_mac,
            src_ip=src_ip,
            dst_mac=arp_dst_mac,
            dst_ip=dst_ip
        )

        # Create packet and send it
        pkt = packet.Packet()
        pkt.add_protocol(eth)
        pkt.add_protocol(arp_header)

        pkt.serialize()
        datapath.send_packet_out(
            buffer_id=datapath.ofproto.OFP_NO_BUFFER,
            in_port=datapath.ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=pkt.data
        )