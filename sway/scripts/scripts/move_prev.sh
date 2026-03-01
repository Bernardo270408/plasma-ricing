#!/bin/bash

current=$(swaymsg -t get_workspaces | jq '.[] | select(.focused).num')
prev=$((current - 1))

if [ "$prev" -ge 1 ]; then
  swaymsg move container to workspace number "$prev"
  swaymsg workspace number "$prev"
fi
