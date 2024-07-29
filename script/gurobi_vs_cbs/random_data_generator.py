import random
# from gurobi_group_constraint import Gurobi
import os
import argparse

def gen_data(max_agent_num,max_group_num,max_task_num):
    num_agent = random.randint(1, max_agent_num)  # range(num_agent) is the agent name
    data = ''
    max_task_id = num_agent * max_task_num
    print("max_task_id",max_task_id)
    for a in range(num_agent):
        # print('a',a)
        # group_size = 2
        num_group = random.randint(1, max_group_num)
        group_size = random.randint(1, max_task_num)  # how many tasks in a group
        for i in range(num_group):
            group = ' '.join([str(random.randint(0, max_task_id)) for _ in range(group_size)])  # Generate tasks with 't'
            cost = random.randint(1, 100)
            data += f'{a} {cost} {group}\n'  # Use f-string for string formatting
    return data

def save_input_txt(save_dir,data,i):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    random_data_file_name =  f'random_{i}.txt'
    random_data_file_path = os.path.join(save_dir, random_data_file_name)
    print('random_data_file_path',random_data_file_path)
    with open(random_data_file_path, 'w') as file:
        file.write(data)
    return random_data_file_name

def test():
    random_data_root_dir = 'data'
    max_group_num = 5   # dont be too much 
    max_task_num_list = [3,4,5]
    max_agent_num_list = list(range(5,25,5))


    if not os.path.exists(random_data_root_dir):
        os.makedirs(random_data_root_dir)

    for max_task_num in max_task_num_list:
        for max_agent_num in max_agent_num_list:

            base_name = f'G{max_group_num}_T{max_task_num}_A{max_agent_num}'
            random_data_dir = f'{random_data_root_dir}/{base_name}/random_data_{base_name}'
            # gurobi_res_dir = f'data/{base_name}/gurobi_{base_name}'
            # additional_group = max_task_num*max_agent_num + 30   # G3_T10_A50 will cost cbs really a lot of time 
            for i in range(100):
                print("-----------",i)
                data = gen_data(max_agent_num,max_group_num,max_task_num)
                # input_txt_name = save_input_txt(random_data_dir,data,i)        
                # runtime = Gurobi(input_txt_name,data,gurobi_res_dir,additional_group)  # runtime without read the file and write the result into the file


if __name__ == '__main__':
    # max_task_num = 4
    # max_agent_num = 30 # have 8 robot in the flight space
    # test()

    parser = argparse.ArgumentParser(description="Generate and save random data")
    parser.add_argument('-p', '--save_path', default='data', help='Root directory for random data.')
    parser.add_argument('-g', '--group', default=5, help='Maximum number of groups.')
    parser.add_argument('-t', '--task', default=3, help='List of maximum number of tasks.')
    parser.add_argument('-a', '--agent', default=5, help='List of maximum number of agents.')

    # Parse the arguments
    args = parser.parse_args()
    random_data_root_dir = args.save_path
    max_group_num = int(args.group)
    max_task_num = int(args.task)
    max_agent_num = int(args.agent)

    if not os.path.exists(random_data_root_dir):
        os.makedirs(random_data_root_dir)
    base_name = f'G{max_group_num}_T{max_task_num}_A{max_agent_num}'
    random_data_dir = f'{random_data_root_dir}/{base_name}/random_data_{base_name}'

    for i in range(100):
        print("-----------",i)
        data = gen_data(max_agent_num,max_group_num,max_task_num)
        input_txt_name = save_input_txt(random_data_dir,data,i) 
    print('random_data_dir',random_data_dir)















