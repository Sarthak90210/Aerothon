#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/logs/user_birdseye_split_v38_s20261003_retry3_20261009/birds_eye_view'
ffmpeg -v error -y -f concat -safe 0 -i timeline.ffconcat -vf fps=15 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart ../birds_eye.mp4
ffmpeg -v error -i ../birds_eye.mp4 -f null - 2> ../birds_eye_decode.log
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,nb_frames -of json ../birds_eye.mp4 > ../birds_eye_video_probe.json
ffmpeg -v error -y -i ../birds_eye.mp4 -vf 'setpts=PTS/4,fps=15' -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart ../birds_eye_4x.mp4
ffmpeg -v error -i ../birds_eye_4x.mp4 -f null - 2> ../birds_eye_4x_decode.log
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,nb_frames -of json ../birds_eye_4x.mp4 > ../birds_eye_4x_video_probe.json
