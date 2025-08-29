#!/bin/sh

# Define the root directory for random data
data_path="data"

group=3
task_list="3 4 5"
agent_list="5 10 15"

task_list="4"
agent_list="15"

for task in $task_list; do
    for agent in $agent_list; do
        base_dir="G${group}_T${task}_A${agent}"
        input_dir="${data_path}/${base_dir}/random_data_${base_dir}"
        output_dir="${data_path}/${base_dir}/cbs_${base_dir}"
        
        echo "input_dir: $input_dir"
        echo "output_dir: $output_dir"

        if [ -d "$output_dir" ]; then
            echo "Removing the previous output_dir: $output_dir"
            rm -rf "$output_dir"
        fi
        mkdir -p $output_dir

        for input_file in $input_dir/*.txt
        do
            base_name=$(basename "$input_file" .txt)
            echo "base_name: $base_name"
            output_file="${output_dir}/cbs_${base_name}.yaml"

            ./build/cbs_group_constraint -i "$input_file" -o "$output_file"
        done
    done
done
