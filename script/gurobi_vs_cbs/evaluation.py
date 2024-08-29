import os
import yaml
import matplotlib.pyplot as plt
import argparse

def get_matched_files_dict(gurobi_dir,cbs_dir,random_data_dir):
    gurobi_files = os.listdir(gurobi_dir)
    cbs_files = os.listdir(cbs_dir)
    random_data_files = os.listdir(random_data_dir)
    random_data_files = sorted(random_data_files, key=lambda x: int(os.path.splitext(x)[0].split('_')[-1]))
    match_dict = {}
    for random_data_file in random_data_files:
        file_name = os.path.splitext(random_data_file)[0]
        # new_filename = filename.replace('cbs_', '')
        matching_cbs = [cbs for cbs in cbs_files if file_name == cbs.replace('cbs_', '').replace('.yaml', '')]
        matching_gurobi = [gurobi for gurobi in gurobi_files if file_name == gurobi.replace('gurobi_', '').replace('.yaml', '')]
        
        if len(matching_cbs) == 1 and len(matching_gurobi) == 1:
            match_dict[file_name] = {
                'cbs': matching_cbs[0],
                'gurobi': matching_gurobi[0]
            }
            # print(f'File Name: {file_name}, Matching cbs: {matching_cbs}, Matching Gurobis: {matching_gurobi}')
        else:
            # print(f'Match not found for {file_name}')
            print(f'Match not found for {file_name},matching_cbs{matching_cbs},matching_gurobi{matching_gurobi}')
            quit()
    return match_dict

def parse_res(gurobi_dir,cbs_dir,matching_gurobi,matching_cbs):
    res_gurobi_path = os.path.join(gurobi_dir, matching_gurobi)
    res_cbs_path = os.path.join(cbs_dir, matching_cbs)

    try:
        with open(res_gurobi_path, 'r') as gurobi_file, open(res_cbs_path, 'r') as cbs_file:
            res_gurobi = yaml.safe_load(gurobi_file)
            res_cbs = yaml.safe_load(cbs_file)
            return res_gurobi,res_cbs
    except FileNotFoundError as e:
        print(f'Error: File not found - {e.filename}')
    except yaml.YAMLError as e:
        print(f'Error loading YAML file: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')
        quit()
    return None,None

def violin_box_plot(data,frequency_cbs,average_cbs,frequency_gurobi,average_gurobi,base_name,evaluation_save_dir):
    # print(" Creating violin plot")
    plt.close()
    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))
    # fig = plt.figure(figsize=(8,6))
    axs[0].violinplot(data, showmeans=False,showmedians=True)
    axs[0].set_xticks([1, 2], ['Gurobi', 'Cbs'])
    axs[0].set_ylabel('Runtime')
    axs[0].set_title(f'Box plot gurobi {frequency_gurobi:.2f} runtime {average_gurobi:.4f}')

    axs[1].boxplot(data)
    axs[1].set_xticks([1, 2], ['Gurobi', 'Cbs'])
    axs[1].set_ylabel('Runtime')
    axs[1].set_title(f'Violin plot frequency CBS {frequency_cbs:.2f} runtime {average_cbs:.4f}')

    violin_path = evaluation_save_dir + f'/violin_box_{base_name}.png'
    print('violin_path',violin_path)
    plt.savefig(violin_path, bbox_inches='tight')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Generate and save random data")
    parser.add_argument('-p', '--data_path', default='data', help='Root directory for random data.')
    parser.add_argument('-g', '--group', default=3, help='Maximum number of groups.')
    parser.add_argument('-t', '--task', default=5, help='List of maximum number of tasks.')
    parser.add_argument('-a', '--agent', default=15, help='List of maximum number of agents.')

    # Parse the arguments
    args = parser.parse_args()
    random_data_root_dir = args.data_path
    max_group_num = int(args.group)
    max_task_num = int(args.task)
    max_agent_num = int(args.agent)

    base_name = f'G{max_group_num}_T{max_task_num}_A{max_agent_num}'

    random_data_dir = f'{random_data_root_dir}/{base_name}/random_data_{base_name}'
    cbs_dir = f'{random_data_root_dir}/{base_name}/cbs_{base_name}'
    gurobi_dir = f'{random_data_root_dir}/{base_name}/gurobi_{base_name}'
    evaluation_save_dir = f'{random_data_root_dir}/{base_name}/evaluation_{base_name}'

    match_dict = get_matched_files_dict(gurobi_dir,cbs_dir,random_data_dir)
    match_cout = 0
    gurobi_runtime_list,cbs_runtime_list =[],[]

    if os.path.exists(evaluation_save_dir):
        os.system(f'rm -rf {evaluation_save_dir}')
    os.makedirs(evaluation_save_dir)

    for matched_name,matched_files in match_dict.items():
        # print('matched_name',matched_name,'matched_files',matched_files)
        matching_gurobi = matched_files.get('gurobi')
        matching_cbs = matched_files.get('cbs')

        if not matching_gurobi or not matching_cbs:
            print("Error: 'gurobi' or 'cbs' key not found in dictionary.")
            continue

        res_gurobi,res_cbs = parse_res(gurobi_dir,cbs_dir,matching_gurobi,matching_cbs)
        # print('res_gurobi',res_gurobi)
        # print('res_cbs',res_cbs)

        if 'runtime' in res_gurobi and 'runtime' in res_cbs:
            gurobi_runtime_list.append(res_gurobi['runtime'])
            cbs_runtime_list.append(res_cbs['runtime'])
        # else:
        #     print('matched_name',matched_name)
        #     print('res_gurobi',res_gurobi)
        #     print('res_cbs',res_cbs)

        if (res_gurobi['cost'] == res_cbs['cost'] 
            and res_gurobi['assignment'] == res_cbs['assignment']):
            # and 'runtime' in res_gurobi and 'runtime' in res_cbs):
            # print("Content of 'res_gurobi' and 'res_cbs' is the same.")
            match_cout += 1
        else:
            print("Content of 'res_gurobi' and 'res_cbs' is different.")

            # record the different input and also all the outputs            
            filename = f'{evaluation_save_dir}/eval_{matched_name}.txt'
            print('filename',filename)
            with open(f'{random_data_dir}/{matched_name}.txt', 'r') as random_file:
                random_data = random_file.read()
            with open(filename, 'w') as file:
                file.write(f"res_gurobi:\n{res_gurobi}\n")
                file.write(f"res_cbs:\n{res_cbs}\n")
                print('random_data',random_data)
                file.write(f"content in {matched_name}.txt:\n{random_data}\n")


    gurobi_runtime_length = len(gurobi_runtime_list)
    cbs_runtime_length = len(cbs_runtime_list)

    # print('gurobi_runtime_list',gurobi_runtime_list)
    # print('cbs_runtime_list',cbs_runtime_list)
    print("Length of gurobi_runtime_list:", gurobi_runtime_length)
    print("Length of cbs_runtime_list:", cbs_runtime_length)

    print('base_name',base_name)
    average_gurobi = sum(gurobi_runtime_list) / gurobi_runtime_length
    frequency_gurobi = 1/average_gurobi
    print(f'Average Runtime of !gurobi!: {average_gurobi} seconds')
    print(f'Frequency of !gurobi! Average Runtime: {frequency_gurobi}')


    average_cbs = sum(cbs_runtime_list) / cbs_runtime_length
    frequency_cbs = 1/average_cbs
    print(f'Average Runtime of !CBS!: {average_cbs} seconds')
    print(f'Frequency of !CBS! Average Runtime: {frequency_cbs}')

    print('match_cout',match_cout)

    data = [gurobi_runtime_list, cbs_runtime_list]
    violin_box_plot(data,frequency_cbs,average_cbs,frequency_gurobi,average_gurobi,base_name,evaluation_save_dir)

    conclusion_file_path = f'{random_data_root_dir}/evaluation_conclusion.yaml'

    if os.path.exists(conclusion_file_path):
        with open(conclusion_file_path, 'r') as file:
            conclusion_data = yaml.safe_load(file) or {}
    else:
        conclusion_data = {}

    conclusion_data[base_name] = {
        "gurobi_runtime_length": gurobi_runtime_length,
        "cbs_runtime_length": cbs_runtime_length,
        "average_gurobi_runtime": average_gurobi,
        "frequency_gurobi_runtime": frequency_gurobi,
        "average_cbs_runtime": average_cbs,
        "frequency_cbs_runtime": frequency_cbs,
        "match_count": match_cout
    }

    with open(conclusion_file_path, 'w') as file:
        yaml.safe_dump(conclusion_data, file)

    print('end--------')
























