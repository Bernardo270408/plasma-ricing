#!/bin/bash

current=$(swaymsg -t get_workspaces | jq '.[] | select(.focused).num')
next=$((current + 1))

swaymsg workspace number "$next"
