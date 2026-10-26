#!/bin/bash
# Run the game in a window from WSL; it closes itself after SECS seconds, saving a
# screenshot every 3 s into scratch/.      tools/run_windowed.sh SECS [game args...]
SECS=$1; shift
G="/mnt/c/Program Files/Godot/Godot_v4.7.2-stable_win64.exe"
P='\\wsl.localhost\Ubuntu\home\vasilhs\repos\VrouvesPC'
T=/mnt/c/Users/vasilhs/AppData/Local/Temp/vrouves_shots
D=$(dirname "$0")/../scratch
rm -rf "$T"; mkdir -p "$T"; rm -f "$D"/shot_*.png
SHOTS="--shots C:/Users/vasilhs/AppData/Local/Temp/vrouves_shots"
[ -n "$NOSHOTS" ] && SHOTS=""
timeout $((SECS + 30)) "$G" --path "$P" --log-file 'C:\Users\vasilhs\AppData\Local\Temp\vrouves_shots\run.log' \
    -- --exit "$SECS" $SHOTS "$@" >/dev/null 2>&1
cp "$T"/shot_*.png "$D"/ 2>/dev/null
grep -iE "error|at: " "$T/run.log" | head -20
ls "$D"/shot_*.png 2>/dev/null | tr '\n' ' '; echo
