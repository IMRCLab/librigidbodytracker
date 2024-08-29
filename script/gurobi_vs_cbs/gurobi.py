import os
import gurobipy as gp
from gurobipy import GRB
import yaml
import time  
import argparse

def parse_random_data(data,additional_cost = 1e4,additional_group = 50):
    assignments_dic = {}
    all_tasks = []
    for line in data.split('\n'):
        parts = line.split()
        if len(parts) < 3:
            continue
        agent = 'a' + parts[0]
        cost = int(parts[1])
        tasks = ['t' + task for task in sorted(parts[2:])] 
        all_tasks.extend(tasks)
        group = tuple(set(tasks))  
        # print('group',group)
        if len(group) < len(tasks):  # skip the group with duplicate number
            continue
        group_str = '_'.join(sorted(group))
        if (agent, group_str) in assignments_dic:
            if cost > assignments_dic[agent, group_str]:
                continue  # skip when current cost is bigger
        assignments_dic[agent, group_str] = cost    
    agents = tuple(set(agent for agent, _ in assignments_dic.keys()))
    for agent in agents:
        assignments_dic[agent,'t' + str(additional_group)] = additional_cost
        additional_group = additional_group + 1
    groups = tuple(set(group for _, group in assignments_dic.keys()))
    tasks_list = tuple(set(all_tasks)) 
    return assignments_dic,agents,groups,tasks_list

def gurobi_optimization_model(assignments_dic,agents, groups, tasks_list):
    if not assignments_dic:
        print("assignments_dic is empty. Exiting the function.")
        return None,None,None
    
    combinations, ms = gp.multidict(assignments_dic)    # keys and diction

    model = gp.Model('RAP')
    model.setParam('OutputFlag', 0)
    x = model.addVars(combinations,vtype=GRB.BINARY, name="assign")

    groupsConstrs = model.addConstrs((x.sum('*',g) <= 1 for g in groups), 'groupsConstrs')  # one group can only be asigned to one agent
    agentsConstrs = model.addConstrs((x.sum(a,'*') == 1 for a in agents), 'agentsConstrs')  # one agent can only have one group
    for task in tasks_list:
        comb_containing = [
            (agent, group) for (agent, group) in assignments_dic
            if any(t == task for t in group.split('_')) 
        ]
        taskConstr = model.addConstr(gp.quicksum(x[a, g] for (a,g) in comb_containing) <= 1, task+'Constr')

    model.setObjective(x.prod(ms), GRB.MINIMIZE)

    # save model for inspection
    save_model = 0
    if save_model:
        output_dir = 'data/gurobi_model'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, f'RAP_{random_data_file}.lp')
        model.write(output_file)

    model.optimize()

    # if model.SolCount > 0:
    #     print('Total matching score: {0}'.format(model.objVal))
    # else:
    #     print("No solution found")
    return model,x,combinations

def save_result(model,x,combinations,gurobi_save_dir,random_data_file,runtime,additional_cost=1e4,additional_group = 50):
    if model is None:
        output_data = {'cost': 0,
                       'assignment':None}
    else:
        output_data = {
            'cost': model.objVal,
            'assignment': {
                int(agent[1:]): int(group[1:]) if '_' not in group else ' '.join(str(int(t[1:])) for t in group.split('_'))   
                for agent, group in combinations if (abs(x[agent, group].x) > 1e-6)
            },
            'runtime':runtime
        }
        # remove additional group and additional_cost
        for key, value in list(output_data['assignment'].items()):
            if isinstance(value, int) and int(value) >= additional_group:
                del output_data['assignment'][key]
                output_data['cost'] = output_data['cost'] - additional_cost

    if not os.path.exists(gurobi_save_dir):
        os.makedirs(gurobi_save_dir)
    if 'txt' in random_data_file:
        random_data_file = random_data_file.replace('.txt', '')

    save_file_name = f'gurobi_{random_data_file}.yaml'
    save_file_path = os.path.join(gurobi_save_dir, save_file_name)
    print('save_file_path',save_file_path)
    with open(save_file_path, 'w') as file:
        yaml.dump(output_data, file, sort_keys=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate and save random data")
    parser.add_argument('-p', '--data_path', default='data', help='Root directory for random data.')
    parser.add_argument('-g', '--group', default=5, help='Maximum number of groups.')
    parser.add_argument('-t', '--task', default=3, help='List of maximum number of tasks.')
    parser.add_argument('-a', '--agent', default=5, help='List of maximum number of agents.')

    # Parse the arguments
    args = parser.parse_args()
    random_data_root_dir = args.data_path
    max_group_num = int(args.group)
    max_task_num = int(args.task)
    max_agent_num = int(args.agent)


    base_name = f'G{max_group_num}_T{max_task_num}_A{max_agent_num}'
    gurobi_save_dir = f'{random_data_root_dir}/{base_name}/gurobi_{base_name}'
    random_inputs_dir = f'{random_data_root_dir}/{base_name}/random_data_{base_name}'
    if os.path.exists(gurobi_save_dir):
        os.system(f'rm -rf {gurobi_save_dir}')
    additional_group = max_task_num*max_agent_num + 30
    additional_cost = 1e4

    random_data_files = os.listdir(random_inputs_dir)  # 100 files
    for random_data_file in random_data_files:
        random_data_file_path = os.path.join(random_inputs_dir, random_data_file)
        with open(random_data_file_path, 'r') as file:
            random_data = file.read()
        start_time = time.time()
        assignments_dic, agents, groups, tasks_list = parse_random_data(random_data,additional_cost = additional_cost, additional_group = additional_group)
        model,x,combinations = gurobi_optimization_model(assignments_dic,agents, groups, tasks_list)
        end_time = time.time()
        runtime = end_time - start_time

        save_result(model,x,combinations,gurobi_save_dir,random_data_file,runtime,
                        additional_cost=additional_cost,additional_group = additional_group) 
    
    
    
    
    print('end')