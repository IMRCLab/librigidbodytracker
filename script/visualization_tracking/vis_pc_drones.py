import numpy as np
import os
import argparse

# visualization related
import meshcat
import meshcat.geometry as g
import meshcat.transformations as tf
from meshcat.animation import Animation

def parse_rigidbody_data(rigidbody_path):
    with open(rigidbody_path, 'r') as trans_file:
        rigidbody_data = trans_file.read().split(sep='\n')
    # print('Transformation Data:', rigidbody_data)

    in_transformation_block = False
    in_solution_block = False
    rb_trans_dict = {}
    for line in rigidbody_data[:]:
        if line.startswith('stamp:'):
            key = line
            rb_trans_dict[key] = {"trans":{},"solution":{}}	
            in_transformation_block = False
        elif line.startswith('solution:'):
            in_solution_block = True
        elif line.startswith('transformation:'):
            in_transformation_block = True
            in_solution_block = False
        elif in_solution_block:
            if line:
                # print("line",line)
                index, values = line.split(': ', 1)
                rb_trans_dict[key]["solution"][int(index)] = list(map(int, values.split()))

        elif in_transformation_block:
            # print("line",line)
            if line:
                index, values = line.split(': ', 1)
                rb_trans_dict[key]["trans"][int(index)] = list(map(float, values.split()))
    # print('rb_trans_dict',rb_trans_dict)
    return rb_trans_dict

def parse_pc_data(pc_path):
    with open(pc_path, 'r') as pc_file:
        point_cloud_data = pc_file.read().split(sep='\n')

    pc_dict = {}
    key = ''

    in_stamp_block = False
    for line in point_cloud_data[:]:
        if line.startswith('stamp:'):
            key = line
            pc_dict[key] = []
            in_stamp_block = True
        elif in_stamp_block:
            pc_dict[key].append(line)

    for key in pc_dict:
        points = [list(map(float, point.split(','))) for point in pc_dict[key] if point]
        pc_dict[key] = points
    return pc_dict

def one_vis(rigidbody_path,pc_path):
    rb_trans_dict = parse_rigidbody_data(rigidbody_path)

    pc_dict = parse_pc_data(pc_path)

    vis = meshcat.Visualizer()
    # vis.open()

    vis["/Cameras/default"].set_transform(
        tf.translation_matrix([0, 0, 0]).dot(
        tf.euler_matrix(0, np.radians(-30), -np.pi/2)))

    vis["/Cameras/default/rotated/<object>"].set_transform(
        tf.translation_matrix([1, 0, 0]))

    # rb initial
    max_index = max(max(sub_dict["trans"].keys()) for sub_dict in rb_trans_dict.values() if sub_dict)
    # print('max_index',max_index)
    for i in range(max_index+1):
        vis[f"Quadrotor{i}"].set_object(
            g.StlMeshGeometry.from_file('script/visualization_tracking/meshes/cf2_assembly.stl'))

    # pc initial
    box = meshcat.geometry.Box([0.01, 0.01, 0.01])
    max_length = max(len(value) for value in pc_dict.values())
    # colors = [0xff0000, 0x00ff00, 0x0000ff, 0xffff00, 0xff00ff, 0x00ffff]  # Add more colors as needed
    # print('max_length',max_length)
    for i in range(max_length):
        vis[f"pc{i}"].set_object(box, g.MeshBasicMaterial(color=0xff0000))
        # color = colors[i % len(colors)]  # Cycle through colors
        # vis[f"pc{i}"].set_object(box, g.MeshBasicMaterial(color=color))


    anim = Animation()
    i = 0
    # use the point cloud key
    for pc_key, pc_frame_points in pc_dict.items():
        if not pc_frame_points:
            print("not pc_frame_points","pc_key",pc_key)
            continue
        with anim.at_frame(vis, i) as frame:
            # print("frame ",i)
            # print("len(pc_frame_points)",len(pc_frame_points))
            for k,point in enumerate(pc_frame_points):
                frame[f"pc{k}"].set_transform(tf.translation_matrix(point))

            # rb_trans = rb_trans_dict[pc_key]["trans"]
            rb_trans = rb_trans_dict.get(pc_key, {}).get("trans")
            rb_solution_agents = rb_trans_dict.get(pc_key, {}).get("solution")
            if not rb_trans:
                print(f'!!!not rb_trans!!! in frame {i} ','pc_key',pc_key)
                continue

            # if len(rb_solution_agents) <3:
            # 	print('rb_solution_agents',rb_solution_agents)
            for agent,row in rb_trans.items():
                if agent in rb_solution_agents: 
                    frame[f"Quadrotor{agent}"].set_transform(
                        tf.translation_matrix([row[0], row[1], row[2]]).dot(
                            tf.quaternion_matrix([row[6], row[3], row[4], row[5]])))
                else:   # No results for this agent					
                    frame[f"Quadrotor{agent}"].set_transform(
                        tf.translation_matrix([1e5,1e5,1e5]).dot(
                            tf.quaternion_matrix([row[6], row[3], row[4], row[5]])))
                                        
            i= i+1

    vis.set_animation(anim)
    res = vis.static_html()
    # save to a file
    # Path("results").mkdir(exist_ok=True)
    # output_html_path = Path("results") / f"{input_file_name}.html"

    filename_with_extension = rigidbody_path.split('/')[-1]
    input_file_name = filename_with_extension.split('.')[0]
    # input_file_name = rigidbody_file_name.replace('.txt', '')
    folder_path = os.path.dirname(rigidbody_path)

    output_html_path = f'{folder_path}/{input_file_name}.html'
    with open(output_html_path, "w") as f:
        f.write(res)
    print('output_html_path:',output_html_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate and save random data")
    parser.add_argument('-r', '--result_file', default='data/output/test0.txt', help='Tracking result path')
    parser.add_argument('-p', '--pointcloud_file', default='data/output/test0_pointcloud.txt', help='Pointcloud path')

    args = parser.parse_args()
    rigidbody_path = args.result_file
    pc_path = args.pointcloud_file

    one_vis(rigidbody_path,pc_path)









    