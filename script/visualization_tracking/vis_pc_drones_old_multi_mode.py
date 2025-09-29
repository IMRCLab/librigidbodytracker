import numpy as np
import os

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
	for line in point_cloud_data[:]:
		if line.startswith('stamp:'):
			# print('line',line)
			key = line
			pc_dict[key] = []
		elif key:
			pc_dict[key].append(line)

	for key in pc_dict:
		points = [list(map(float, point.split(','))) for point in pc_dict[key] if point]
		pc_dict[key] = points
	return pc_dict

def one_vis(input_file_name,input_dir):
	rigidbody_file_name = input_file_name + '.txt'
	rigidbody_path = os.path.join(input_dir, rigidbody_file_name)
	rb_trans_dict = parse_rigidbody_data(rigidbody_path)

	# input_file_name = '3d_8m_mo1_28646591'
	point_cloud_file_name = input_file_name + '_pointcloud.txt'

	pc_path = os.path.join(input_dir, point_cloud_file_name)
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
			# print('rb_trans',rb_trans)
			rb_solution_agents = rb_trans_dict.get(pc_key, {}).get("solution")
			if not rb_trans:
				print(f'!!!not rb_trans!!! in frame {i} ','pc_key',pc_key)
				continue

			for agent,row in rb_trans.items():
				# if agent in rb_solution_agents: 
				frame[f"Quadrotor{agent}"].set_transform(
					tf.translation_matrix([row[0], row[1], row[2]]).dot(
						tf.quaternion_matrix([row[6], row[3], row[4], row[5]])))
				# else:   # No results for this agent					
				# 	frame[f"Quadrotor{agent}"].set_transform(
				# 		tf.translation_matrix([1e5,1e5,1e5]).dot(
				# 			tf.quaternion_matrix([row[6], row[3], row[4], row[5]])))
										
			i= i+1

	vis.set_animation(anim)
	res = vis.static_html()
	# save to a file
	# Path("results").mkdir(exist_ok=True)
	# output_html_path = Path("results") / f"{input_file_name}.html"
	input_file_name = rigidbody_file_name.replace('.txt', '')
	output_html_path = f'{input_dir}/{input_file_name}.html'
	with open(output_html_path, "w") as f:
		f.write(res)
	print('output_html_path:',output_html_path)

	print('end')

if __name__ == '__main__':
	# input_dir = '/home/nan/ros2_ws/src/motion_capture_tracking/motion_capture_tracking/deps/librigidbodytracker/data/output'
	
	# input_dir = '/home/nan/ros2_ws/src/motion_capture_tracking/motion_capture_tracking/deps/librigidbodytracker/data/2608runtime'
	# input_file_names = [
	# 	# '3d_8m_mo1_28696988',	# gt   works
	# 	# '3d_8m_mo1_28697091',    # with noise remove points works
	# 	# 'noise_icp'
	# 	# 'figure8_2d_5m1',
	# 	# 'figure8_2d_5m2',
	# 	# 'figure8_3d_8m1',
	# 	'figure8_3d_8m2',
	# 	# 'figure8_4d_9m1f',
	# 	# 'figure8_4d_9m2',
	# 	# 'figure8_4d_9m3f',
	# 	# 'figure8_4d_9m4',
	# 	# 'figure8_4d_9m5',
	# 	# 'figure8_4d_9m6f',
	# 	# 'figure8_4d_9m7'
	# ]

	input_dir = '/home/nan/ros2_ws/src/motion_capture_tracking/motion_capture_tracking/deps/librigidbodytracker/data/output_add_remove_old_multi_mode_2d_7m_mo_0701'
	input_file_names = [
		# 'test0',	# gt
		'test19'	# remove 9135	
	]

	print('input_dir:',input_dir)

	for input_file_name in input_file_names:
		one_vis(input_file_name, input_dir)
	# one_vis('ori', input_dir)









	