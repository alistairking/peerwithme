#!/usr/bin/env python3

import subprocess
import sys
import pybgpstream
import time


def gobgp_do(args):
    args = ["/root/gobgp"] + args
    sys.stderr.write(" ".join(args) + "\n")
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

stream = pybgpstream.BGPStream(
    from_time=last_rib,
    until_time=0,
    collectors=["route-views.sg"],
    filter="peer 7713",
)

for elem in stream:
    if elem.type == "A":
        gobgp_add(elem.fields['prefix'], elem.fields['as-path'],
                  elem.fields['next-hop'], ",".join(elem.fields['communities']))
    elif elem.type == "W":
        gobgp_del(elem.fields['prefix'])

