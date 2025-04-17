#!/bin/bash
set -eu

echo "Starting the container"

IMAGE=mongodb/mongodb-atlas-local:latest
DOCKER=$(which docker || which podman)

$DOCKER pull $IMAGE

$DOCKER kill mongodb_atlas_local || true

CONTAINER_ID=$($DOCKER run --rm -d --name mongodb_atlas_local -p 27017:27017 $IMAGE)

function wait() {
  CONTAINER_ID=$1
  echo "waiting for container to become healthy..."
  $DOCKER logs mongodb_atlas_local
}

wait "$CONTAINER_ID"

# EXPOSED_PORT=$($DOCKER inspect --format='{{ (index (index .NetworkSettings.Ports "27017/tcp") 0).HostPort }}' "$CONTAINER_ID")
# export MONGODB_URI="mongodb://127.0.0.1:$EXPOSED_PORT/?directConnection=true"
# SCRIPT_DIR=$(realpath "$(dirname ${BASH_SOURCE[0]})")
# ROOT_DIR=$(dirname $SCRIPT_DIR)
# echo "MONGODB_URI=$MONGODB_URI" > $ROOT_DIR/.local_atlas_uri

# Sleep for a bit to let all services start.
sleep 5
