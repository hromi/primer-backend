#!/bin/bash

# Function to convert KB to human-readable format
convert_kb_to_human() {
    local kb_size=$1
    if [ "$kb_size" -lt 1024 ]; then
        echo "${kb_size}K"
    elif [ "$kb_size" -lt 1048576 ]; then
        echo "$(awk "BEGIN {printf \"%.2f\", ${kb_size}/1024}")M"
    else
        echo "$(awk "BEGIN {printf \"%.2f\", ${kb_size}/1048576}")G"
    fi
}

# Get the PID of the last background process
pid=$!

# Check if user provided a PID as an argument
if [ ! -z "$1" ]; then
    pid=$1
fi

# Check every second
while true; do
    output=$(ps -p $pid -o vsz,rss,cmd --no-headers)
    vsz=$(echo $output | awk '{print $1}')
    rss=$(echo $output | awk '{print $2}')
    cmd=$(echo $output | awk '{$1=$2=""; print $0}')

    echo -e "VSZ: $(convert_kb_to_human $vsz)\tRSS: $(convert_kb_to_human $rss)\tCMD: $cmd"
    sleep 1
done

