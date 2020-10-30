#!/usr/bin/env python3

import subprocess
import sys
import pybgpstream
from pygobgp import *
import time
from google.protobuf.any_pb2 import Any

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

# TODO: make these params customizable
log("Starting PyBGPStream: from_time=%d, collectors=route-views.sg, " \
    "peer: 7713/27.111.228.155" % last_rib)
stream = pybgpstream.BGPStream(
    from_time=last_rib,
    until_time=0,
    projects=["routeviews"],
    collectors=["route-views.sg"],
    filter="peer 7713",
)
stream.add_rib_period_filter(-1)

stats = {
    "A": 0,
    "R": 0,
    "W": 0,
    "S": 0, # unused
}
elem_cnt = 0
bgp_time = 0

for elem in stream:
    # peer ip isn't a filter?? sigh
    if elem.peer_address != "27.111.228.155":
        continue
    bgp_time = elem.time
    if elem.type in ["A", "R"]:
        gobgp_add(elem.fields['prefix'], elem.fields['as-path'],
                  elem.fields['next-hop'], ",".join(elem.fields['communities']))
    elif elem.type == "W":
        gobgp_del(elem.fields['prefix'])
    stats[elem.type] += 1

    elem_cnt += 1
    if elem_cnt % 1000 == 0:
        log("Proxy Stats: *: %d, R: %d, A: %d, W: %d" %
            (elem_cnt, stats["R"], stats["A"], stats["W"]))
        now = time.time()
        log("RT Delay: %ds, Now: %d, BGP: %d" % ((now-bgp_time), now, bgp_time))

