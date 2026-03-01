#!/bin/bash

current=$(swaymsg -t get_workspaces | jq '.[] | select(.focused).num')
next=$((current + 1))

swaymsg move container to workspace number "$next"
swaymsg workspace number "$next"

