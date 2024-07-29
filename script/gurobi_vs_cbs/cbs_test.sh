#!/bin/sh

# Define the root directory for random data
save_path="data"

group=3
task_list="3"
agent_list="5"
input_file="random_2.txt"

for task in $task_list; do
    for agent in $agent_list; do
        base_dir="G${group}_T${task}_A${agent}"
        input_dir="${save_path}/${base_dir}/random_data_${base_dir}"
        output_dir="${save_path}/cbs_test"
        # output_dir="${save_path}/${base_dir}/cbs_${base_dir}"
        
        echo "input_dir: $input_dir"
        echo "output_dir: $output_dir"

        mkdir -p $output_dir
        
        input_file="${input_dir}/${input_file}"
        echo "input_file: $input_file"

        base_name=$(basename "$input_file" .txt)
        echo "base_name: $base_name"
        output_file="${output_dir}/${base_dir}_cbs_${base_name}.yaml"

        ./build/cbs_group_constraint -i "$input_file" -o "$output_file"
    done
done
