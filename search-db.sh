#!/bin/bash -ex

docker rm -f sonic-search || true

docker run \
    -p 0.0.0.0:1491:1491 \
    -v /home/ec2-user/tools-ef/sonic.cfg:/etc/sonic.cfg:ro \
    -v /home/ec2-user/tools-ef/data/sonic:/var/lib/sonic/store/ \
    --name sonic-search \
    --restart=unless-stopped \
    --detach \
    valeriansaliou/sonic:v1.3.2