import numpy as np
import os
import meshcat
import meshcat.geometry as g
import meshcat.transformations as tf
from meshcat.animation import Animation

def parse_pc_data(pc_path):
	with open(pc_path, 'r') as pc_file:
		point_cloud_data = pc_file.read().split(sep='\n')

	pc_dict = {}
	key = ''
	for line in point_cloud_data[:]:
		if line.startswith('stamp:'):
			key = line
			pc_dict[key] = []
		elif key:
			pc_dict[key].append(line)

	for key in pc_dict:
		points = [list(map(float, point.split(','))) for point in pc_dict[key] if point]
		pc_dict[key] = points
	return pc_dict

def visualize_pointcloud(input_file_name, input_dir):
	point_cloud_file_name = input_file_name + '_pointcloud.txt'
	pc_path = os.path.join(input_dir, point_cloud_file_name)
	pc_dict = parse_pc_data(pc_path)

	vis = meshcat.Visualizer()

	vis["/Cameras/default"].set_transform(
		tf.translation_matrix([0, 0, 0]).dot(
		tf.euler_matrix(0, np.radians(-30), -np.pi/2)))

	vis["/Cameras/default/rotated/<object>"].set_transform(
		tf.translation_matrix([1, 0, 0]))

	box = meshcat.geometry.Box([0.01, 0.01, 0.01])
	max_length = max(len(value) for value in pc_dict.values())
	for i in range(max_length):
		vis[f"pc{i}"].set_object(box, g.MeshBasicMaterial(color=0xff0000))

	anim = Animation()
	i = 0
	for pc_key, pc_frame_points in pc_dict.items():
		if not pc_frame_points:
			print("not pc_frame_points", "pc_key", pc_key)
			continue
		with anim.at_frame(vis, i) as frame:
			for k, point in enumerate(pc_frame_points):
				frame[f"pc{k}"].set_transform(tf.translation_matrix(point))
			i += 1

	vis.set_animation(anim)
	res = vis.static_html()
	output_html_path = f'{input_dir}/{input_file_name}.html'
	with open(output_html_path, "w") as f:
		f.write(res)
	print('output_html_path:', output_html_path)
	print('end')

if __name__ == '__main__':
	# input_dir = '/home/nan/ros2_ws/src/motion_capture_tracking/motion_capture_tracking/deps/librigidbodytracker/data/output_add_remove_old_multi_mode_0701'
	# input_file_names = [
	#	 '2d_7m_mo',
	#	 '3d_8m_mo1'
	# ]

	input_dir = '/home/nan/ros2_ws/src/motion_capture_tracking/motion_capture_tracking/deps/librigidbodytracker/data/030225runtime_grc'
	input_file_names = [
		'2d_8m',
		'4d_4m',
		'4d_10m',
		'4d_16m',
		'8d_20m',
		'8d_22m2',
	]


	for input_file_name in input_file_names:
		visualize_pointcloud(input_file_name, input_dir)