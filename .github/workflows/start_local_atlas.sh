#!/bin/bash
set -eu

echo "Starting the container"

IMAGE=${1:-mongodb/mongodb-atlas-local:latest}
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

# Sleep for a bit to let all services start.
sleep 5
