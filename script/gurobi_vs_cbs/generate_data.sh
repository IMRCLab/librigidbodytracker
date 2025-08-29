#!/bin/sh

# Define the root directory for random data
save_path="data"

group=3
task_list="3 4 5"
agent_list="5 10 15"

for task in $task_list; do
    for agent in $agent_list; do
        echo "Running with max_task_num=$task and max_agent_num=$agent"
        python3 ./script/random_data_generator.py -p "$save_path" -g "$group" -t "$task" -a "$agent"
    done
done
