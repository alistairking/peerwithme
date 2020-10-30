#!/bin/sh
set -e
set -x

GOBGP="docker exec -it peerwithme gobgp"

# Normal IPv4 route
$GOBGP global rib add 192.172.226.0/24 origin egp aspath "3356 1909" nexthop 192.168.1.1 community "33:44,12:21"

# Normal IPv6 route
$GOBGP global rib add -a ipv6 2002:c000:0204::/48 origin igp aspath "335 446" nexthop 2002::2

# VRF-V4 Route
$GOBGP vrf princess rib add 10.20.30.0/24 origin igp aspath "777 888 999" nexthop 1.2.3.4

# VRF-V6 Route
$GOBGP vrf princess rib add -a ipv6 2020:1010::/48 origin igp aspath "123 234 345 456" nexthop ::1

# MPLS-V4 Route
$GOBGP global rib add -a ipv4-mpls 10.20.30.0/24 100/200 origin igp nexthop 44.3.2.1 aspath "414 616 818"

# MPLS-V6 Route
$GOBGP global rib add -a ipv6-mpls 2002:2233::/48 111/222 origin igp nexthop ::2 aspath "313 525 737"
