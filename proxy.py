#!/usr/bin/env python3

import subprocess
import sys
import pybgpstream
import time


def log(msg):
    sys.stderr.write(msg + "\n")


def gobgp_do(args):
    args = ["/root/gobgp", "--port", "50090"] + args
    # log(" ".join(args))
    subprocess.run(args)


def gobgp_add(pfx, path, nexthop, community):
    args = ["global", "rib", "add"]
    if ":" in pfx:
        args += ["-a", "ipv6"]
    args += [pfx, "aspath", path, "nexthop", nexthop]
    if community != "":
        args += ["community", community]
    gobgp_do(args)


def gobgp_del(pfx):
    args = ["global", "rib", "del"]
    if ":" in pfx:
        args += ["-a", "ipv6"]
    args += [pfx]
    gobgp_do(args)


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

stats = {
    "A": 0,
    "R": 0,
    "W": 0,
    "S": 0, # unused
}
elem_cnt = 0

for elem in stream:
    # peer ip isn't a filter?? sigh
    if elem.peer_address != "27.111.228.155":
        continue
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

