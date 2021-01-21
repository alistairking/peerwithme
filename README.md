# peerwithme

Trivial Docker(GoBGP + BGPStream) setup that makes it easy (well, at
least easier) to send some routes to a BGP peer.

## Get Started

```
cp gobgpd.yaml.example gobgpd.yaml
make restart
```

This will build the docker image and start gobgpd running using the
config in [gobgpd.yaml.example](/gobgpd.yaml.example).

In the current config, gobgpd listens on 17917 on the host's interface
which allows it to be run on a machine with a "real" BGPd running on
179.

Note that `make restart` will also `stop` and `rm` an existing
`peerwithme` container, so it can be used to update config etc.

## Gobgp Client

To use the gobgp CLI:
```
docker exec -it peerwithme gobgp [cmd]
```

E.g.,
```
docker exec -it peerwithme gobgp neighbor
```

And to add a route:
```
docker exec -it peerwithme gobgp \
  global rib add 192.172.226.0/24 \
  origin igp \
  aspath "3356 1909" \
  nexthop 10.250.100.1
```

To talk to a different gobgpd instance:
```
docker exec -it peerwithme gobgp --port=50099 [cmd]
```

## BGPStream "Proxy"

There's a simple PyBGPStream script that consumes a RIB and then
updates from one peer of route-views.sg, and then uses the gobgp CLI
to add/del them from the global RIB (and thus advertises them to any
configured peers).

```
docker exec -it peerwithme proxy.py
```

This runs in the foreground (it probably should be turned into its own
Docker container at some point), so run it in screen to watch its
progress.
