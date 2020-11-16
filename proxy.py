#!/usr/bin/env python3

import subprocess
import sys
import pybgpstream
from pygobgp import *
import time
from google.protobuf.any_pb2 import Any

# TODO: make this easier to change (at run time)
CONFIG = {
    "project": "routeviews",
    "collector": "route-views.sg",
    "peer_asn": 7713,
    "peer_addresses": {"27.111.228.155", "2001:de8:4::7713:1"},
}

def log(msg):
    sys.stderr.write(msg + "\n")


def gobgp_do(args):
    args = ["/root/gobgp", "--port", "50090"] + args
    # log(" ".join(args))
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
    communities = Any()
    comms = []
    for c in community:
        x = c.split(":")
        comms.append(int(x[0])<<16|int(x[1]))
    communities.Pack(attribute_pb2.CommunitiesAttribute(
        communities=comms,
    ))
    attributes = [origin, as_path, next_hop, communities]

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
last_rib = int(now/28800)*28800

log("Starting PyBGPStream: from_time=%d, config: %s" % (last_rib, CONFIG))
stream = pybgpstream.BGPStream(
    from_time=last_rib,
    until_time=0,
    project=CONFIG["project"],
    collector=CONFIG["collector"],
    filter="peer %d" % CONFIG["peer_asn"],
)
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
    if elem.peer_address not in CONFIG["peer_addresses"]:
        continue
    bgp_time = elem.time
    if elem.type in {"A", "R"}:
        gobgp_add(elem.fields['prefix'], elem.fields['as-path'],
                  elem.fields['next-hop'], ",".join(elem.fields['communities']))
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

