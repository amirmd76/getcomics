#!/usr/bin/env bash
link=$1
filename=$2
mkdir -p downloads
axel -an 10 $link -o downloads/$filename
mv downloads/$filename /opt/comics/$filename
