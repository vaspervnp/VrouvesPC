#!/bin/bash
# Record the game with Godot's Movie Maker (60 fps, picture and sound) into an .avi in
# scratch/video/, for making a video (add --music for the music; without it only the sound
# effects are recorded).     tools/record.sh NAME SECS [game args...]
NAME=$1; SECS=$2; shift 2
G="/mnt/c/Program Files/Godot/Godot_v4.7.2-stable_win64.exe"
P='\\wsl.localhost\Ubuntu\home\vasilhs\repos\VrouvesPC'
T=/mnt/c/Users/vasilhs/AppData/Local/Temp/vrouves_video
D=$(dirname "$0")/../scratch/video
mkdir -p "$T" "$D"; rm -f "$T/$NAME.avi"
# a 1350 x 1080 window (1080p high) for this run only, through Godot's override.cfg
OV=$(dirname "$0")/../override.cfg
printf '[display]\nwindow/size/window_width_override=1350\nwindow/size/window_height_override=1080\n' > "$OV"
trap 'rm -f "$OV"' EXIT
timeout $((SECS * 20 + 120)) "$G" --path "$P" --write-movie "C:\\Users\\vasilhs\\AppData\\Local\\Temp\\vrouves_video\\$NAME.avi" \
    --fixed-fps 60 -- --exit "$SECS" "$@" >/dev/null 2>&1
mv "$T/$NAME.avi" "$D/$NAME.avi" && ls -la "$D/$NAME.avi"
