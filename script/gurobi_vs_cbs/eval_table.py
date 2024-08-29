import glob 
import os
import yaml

if __name__ == '__main__':
    random_data_root_dir = 'data'
    conclusion_files = glob.glob(f'{random_data_root_dir}/evaluation_conclusion*')
    # for file in conclusion_files:
    #     print(file)  # Print or process the files as needed

    if len(conclusion_files) != 1:
        print(len(conclusion_files) != 1)
        print('conclusion_files',conclusion_files)
        quit()
    conclusion_file = conclusion_files[0] 


    if os.path.exists(conclusion_file):
        try:
            with open(conclusion_file, 'r') as file:
                conclusion_dict = yaml.safe_load(file)
                # If you expect the file to be a specific type of YAML structure, you might want to validate it here
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
        except IOError as e:
            print(f"Error opening file: {e}")
    else:
        print("File does not exist.")
    
    # print('conclusion_dict',conclusion_dict)


    for key, value in conclusion_dict.items():
        # avg_gurobi_runtime = value.get('average_gurobi_runtime', 'N/A')
        # avg_cbs_runtime = value.get('average_cbs_runtime', 'N/A')  # frequency_gurobi_runtime
        frequency_gurobi_runtime = value.get('frequency_gurobi_runtime', 'None')
        frequency_cbs_runtime = value.get('frequency_cbs_runtime', 'None')  

        if frequency_gurobi_runtime > frequency_cbs_runtime:
            frequency_gurobi_runtime = f"\\textbf{{{frequency_gurobi_runtime:.1f}}}"
            frequency_cbs_runtime = f"{frequency_cbs_runtime:.1f}"
        elif frequency_cbs_runtime>frequency_gurobi_runtime:
            frequency_gurobi_runtime = f"{frequency_gurobi_runtime:.1f}"
            frequency_cbs_runtime = f"\\textbf{{{frequency_cbs_runtime:.1f}}}"
        else:
            print('!!wrong!!')

        print(f"{key} & {frequency_gurobi_runtime} & {frequency_cbs_runtime} \\\\")







