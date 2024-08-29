#!/bin/sh

# Define the root directory for random data
data_path="data"

group=3
task_list="3 4 5"
agent_list="5 10 15"

# task_list="4"
# agent_list="15"

for task in $task_list; do
    for agent in $agent_list; do
        echo "evaluation with max_task_num=$task and max_agent_num=$agent"
        python3 ./script/evaluation.py -p "$data_path" -g "$group" -t "$task" -a "$agent"
    done
done
