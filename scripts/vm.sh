#!/usr/bin/env bash
# Oregon on-demand VM lifecycle (i-0d9504316bb8cd248, c7a.8xlarge, us-west-2).
# The instance has NO elastic IP: the public IP changes on every start, so
# 'start' fetches the fresh IP and rewrites the openfoam-server ssh alias.
#
#   scripts/vm.sh start    # start + wait + update ~/.ssh/config + ssh check
#   scripts/vm.sh stop     # stop + verify 'stopped' (never 'terminated')
#   scripts/vm.sh status   # state + current IP
set -euo pipefail

ID=i-0d9504316bb8cd248
REGION=us-west-2

case "${1:?usage: vm.sh start|stop|status}" in
  start)
    aws ec2 start-instances --region $REGION --instance-ids $ID \
        --output text --query 'StartingInstances[0].CurrentState.Name'
    aws ec2 wait instance-running --region $REGION --instance-ids $ID
    IP=$(aws ec2 describe-instances --region $REGION --instance-ids $ID \
         --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    # rewrite ONLY the HostName line inside the openfoam-server block
    sed -i '' "/^Host openfoam-server\$/,/^Host /{s/^    HostName .*/    HostName $IP/;}" \
        ~/.ssh/config
    echo "running at $IP (ssh config updated)"
    for i in 1 2 3 4 5 6; do
        ssh -o ConnectTimeout=10 openfoam-server 'echo "ssh OK: $(hostname)"' \
            && exit 0 || sleep 10
    done
    echo "instance running but ssh not up yet — retry shortly"; exit 1 ;;
  stop)
    aws ec2 stop-instances --region $REGION --instance-ids $ID \
        --output text --query 'StoppingInstances[0].CurrentState.Name'
    aws ec2 wait instance-stopped --region $REGION --instance-ids $ID
    STATE=$(aws ec2 describe-instances --region $REGION --instance-ids $ID \
            --query 'Reservations[0].Instances[0].State.Name' --output text)
    echo "state: $STATE"
    [ "$STATE" = stopped ] || { echo "WARNING: expected 'stopped'"; exit 1; } ;;
  status)
    aws ec2 describe-instances --region $REGION --instance-ids $ID \
        --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress]' \
        --output text ;;
  *) echo "usage: vm.sh start|stop|status"; exit 1 ;;
esac
