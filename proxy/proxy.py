#!/usr/bin/env python3

import argparse
import subprocess
import sys
import pybgpstream
from pygobgp import *
import time
from google.protobuf.any_pb2 import Any

parser = argparse.ArgumentParser("""
Proxy BGP data from a RV peer into a GoBGPd instance.
""")
# all args are optional
parser.add_argument("--ribs", action="store_true", default=False,
                    help="Start with a RIB dump to ensure a full table")

parser.add_argument("--projects", default="routeviews",
                    help="BGPStream collection projects")
parser.add_argument("--collectors", default="route-views.sg",
                    help="BGPStream collectors")
parser.add_argument("--peer-asn", type=int, default="24482",
                    help="BGPStream collector peer ASN")
parser.add_argument("--peer-ips", default="27.111.228.159,2001:de8:4::2:4482:1",
                    help="BGPStream collector peer IPs (comma-separated)")

CONFIG = vars(parser.parse_args())
CONFIG["projects"] = CONFIG["projects"].split(",")
CONFIG["collectors"] = CONFIG["collectors"].split(",")
CONFIG["peer_ips"] = CONFIG["peer_ips"].split(",")

def log(msg):
    sys.stdout.write(msg + "\n")


def gobgp_do(args):
    args = ["gobgp"] + args
    subprocess.run(args)

gobgp = PyGoBGP(address="127.0.0.1", port=50090)


def build_aspath(path):
    # XXX: super quickly written AS path parser...
    hops = path.split(" ")
    segs = []
    cur_type = 2
    cur_nbrs = []

    def reset(ntype):
        nonlocal segs
        nonlocal cur_type
        nonlocal cur_nbrs
        seg = attribute_pb2.AsSegment(
            numbers = [int(x) for x in cur_nbrs]
        )
        seg.type = cur_type
        if len(cur_nbrs) > 0:
            segs.append(seg)
        cur_type = ntype
        cur_nbrs = []

    for hop in hops:
        if "{" in hop:
            if cur_type != 1:
                reset(1)
            cur_nbrs += hop.replace("{","").replace("}", "").split(",")
        else:
            if cur_type != 2:
                reset(2)
            cur_nbrs += [hop]
    reset(0)
    as_path = Any()
    as_path.Pack(attribute_pb2.AsPathAttribute(
        segments=segs,
    ))
    return as_path


# TODO: move this into the pygobgp package
def gobgp_add(pfx, path, nexthop, community):
    afi = gobgp_pb2.Family.AFI_IP
    if ":" in pfx:
        afi = gobgp_pb2.Family.AFI_IP6

    nlri = Any()
    pfxaddr, pfxlen = pfx.split("/")
    nlri.Pack(attribute_pb2.IPAddressPrefix(
        prefix_len=int(pfxlen),
        prefix=pfxaddr,
    ))
    origin = Any()
    origin.Pack(attribute_pb2.OriginAttribute(
        origin = 0 # IGP?
    ))
    as_path = build_aspath(path)
    next_hop = Any()
    next_hop.Pack(attribute_pb2.NextHopAttribute(
        next_hop=nexthop,
    ))
    attributes = [origin, as_path, next_hop]
    if len(community) > 0:
        communities = Any()
        comms = []
        for c in community:
            x = c.split(":")
            comms.append(int(x[0])<<16|int(x[1]))
        communities.Pack(attribute_pb2.CommunitiesAttribute(
            communities=comms,
        ))
        attributes.append(communities)

    gobgp.stub.AddPath(
        gobgp_pb2.AddPathRequest(
            table_type=gobgp_pb2.GLOBAL,
            path=gobgp_pb2.Path(
                nlri=nlri,
                pattrs=attributes,
                family=gobgp_pb2.Family(afi=afi, safi=gobgp_pb2.Family.SAFI_UNICAST),
            )
        )
    )


# TODO: switch to using grpc for this too
def gobgp_del(pfx):
    args = ["global", "rib", "del"]
    if ":" in pfx:
        args += ["-a", "ipv6"]
    args += [pfx]
    gobgp_do(args)


# dump the current neighbors out:
gobgp_do(["neighbor"])

now = time.time()
record_types=["updates"]
if CONFIG["ribs"]:
    record_types.append("ribs")
    from_time = int(now/28800)*28800
else:
    # grab updates from 15 mins ago
    from_time = int(now-900)

log("Starting PyBGPStream: from_time=%d, config: %s" % (from_time, CONFIG))
stream = pybgpstream.BGPStream(
    record_types=record_types,
    from_time=from_time,
    until_time=0,
    projects=CONFIG["projects"],
    collectors=CONFIG["collectors"],
    filter="peer %d" % CONFIG["peer_asn"],
)
if CONFIG["ribs"]:
    stream.add_rib_period_filter(-1)

stats = [
    {
        "*": 0,
        "A": 0,
        "R": 0,
        "W": 0,
        "S": 0, # unused
    },
    {
        "*": 0,
        "A": 0,
        "R": 0,
        "W": 0,
        "S": 0, # unused
    },
]
bgp_time = 0
elem_cnt = 0

for elem in stream:
    # peer ip isn't a filter?? sigh
    if elem.peer_address not in CONFIG["peer_ips"]:
        continue
    bgp_time = elem.time
    if elem.type in {"A", "R"}:
        gobgp_add(elem.fields['prefix'], elem.fields['as-path'],
                  elem.fields['next-hop'], elem.fields['communities'])
    elif elem.type == "W":
        gobgp_del(elem.fields['prefix'])
    if ":" in elem.peer_address:
        stats[1][elem.type] += 1
        stats[1]["*"] += 1
    else:
        stats[0][elem.type] += 1
        stats[0]["*"] += 1

    elem_cnt += 1
    if elem_cnt % 1000 == 0:
        s = stats[0]
        log("IPv4: *: %d, R: %d, A: %d, W: %d" % (s["*"], s["R"], s["A"], s["W"]))
        s = stats[1]
        log("IPv6: *: %d, R: %d, A: %d, W: %d" % (s["*"], s["R"], s["A"], s["W"]))
        now = time.time()
        log("RT Delay: %ds, Now: %d, BGP: %d" % ((now-bgp_time), now, bgp_time))
        log("")
    if elem_cnt % 100000 == 0:
        gobgp_do(["neighbor"])
        log("")

