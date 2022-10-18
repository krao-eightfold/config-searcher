#!/bin/bash -ex

CON_NAME='config_searcher'

docker rm -f ${CON_NAME} || true

docker build . -t ${CON_NAME}_img:latest

docker run \
    -p 0.0.0.0:5250:5000 \
    --name ${CON_NAME} \
    --restart=unless-stopped \
    --detach \
    --add-host=host.docker.internal:host-gateway \
    ${CON_NAME}_img:latest

docker logs -f ${CON_NAME}
