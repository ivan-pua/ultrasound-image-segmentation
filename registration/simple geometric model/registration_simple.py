"""
Created by: Rishav Raj and Qie Shang Pua, University of New South Wales
This program registers a simple geometric model that is segmented from an ultrasound scan to a ground truth model.
Input: 1. The simple geometric model in STL format
       2. The csv file for segmented points.
Output: Two Figures - Registration of STL Model (Ground Truth) with the Segmented Geometric Model
                    - Error Distribution
"""

# Modules to import
import numpy as np
import math
import pandas as pd
from stl.mesh import Mesh
import open3d
import scipy.spatial
import scipy.io
import copy
import trimesh
import matplotlib.pyplot as plt

# ICP Registration
def draw_registration_result_original_color(source, target, transformation):
    source_temp = copy.deepcopy(source)
    source_temp.transform(transformation)
    source_temp.paint_uniform_color([0.5, 0.5, 0.5])
    open3d.visualization.draw_geometries([source_temp, target])

def registration(raw):

    correct = np.array(raw)

    # To shift up the points, 11 is a threshold to determine whether to shift up or not
    numCols = len(raw[2])
    to_shift_up = [0] * numCols
    for col in range(numCols):
        if raw[2][col] < 11:
            to_shift_up[col] = 30
        else:
            to_shift_up[col] = 0

    raw[0] = raw[0] + to_shift_up

    # Axes Transformation, values are selected through trial and error as per MATLAB code
    x_shift = -43.5;
    y_shift = 95;
    z_shift = 148;

    correct[0] = raw[1] * 90.0 / 569.0 + x_shift
    correct[1] = (raw[0] * (-88) / 569) + y_shift
    correct[2] = raw[2] * (-5.01) + z_shift

    np.set_printoptions(precision=3)  # Prints array in 3 decimal places

    # Rotation
    skew_value = 0.08
    skew_y = np.array([[1, 0, skew_value], [0, 1, 0], [0, 0, 1]])

    correct = np.dot(skew_y, correct)

    tz = np.deg2rad(1)
    ty = np.deg2rad(-0.5)

    Rz = [[math.cos(tz), -1 * math.sin(tz), 0], [math.sin(tz), math.cos(tz), 0], [0, 0, 1]]
    Ry = [[math.cos(ty), 0, math.sin(ty)], [0, 1, 0], [-1 * math.sin(ty), 0, math.cos(ty)]]

    correct = np.dot(Rz, correct)
    correct = np.dot(Ry, correct)

    # Get STL (ground truth) model
    path = "ground_truth_in_stl_form.stl"
    stl_mesh = Mesh.from_file(path)
    stl_points = np.around(np.unique(stl_mesh.vectors.reshape([stl_mesh.vectors.size // 3, 3]), axis=0), 2)

    # Displays the model, eliminate outlier points that are too far
    # Range values for each axis as selected per MATLAB code
    minz = -200
    maxz = 400

    miny = -100
    maxy = 400

    minx = -100
    maxx = 500

    # p represents point cloud
    px = np.bitwise_and(stl_points[0, :] > minx, stl_points[0, :] < maxx)
    py = np.bitwise_and(stl_points[1, :] > miny, stl_points[1, :] < maxy)
    pz = np.bitwise_and(stl_points[2, :] > minz, stl_points[2, :] < maxz)
    p = np.bitwise_and(px, py, pz)

    # Transpose segmented points to be in dimensions (number of rows, 3)
    segmented_points = np.transpose(correct)

    num_rows = np.ma.size(segmented_points, 0)
    stl_points = np.transpose(stl_points)

    # Array to store the error for colour map
    error = np.ones((num_rows, 1))

    # For loop determines the colour map or the error when mapping segmented points to stl
    for i in range(num_rows):
        point = segmented_points[i, :]  # extracting each row from segmented points
        point_p2 = stl_points[:, i]

        # euclidean distance between the segmented points and the stl model
        dist = scipy.spatial.distance.euclidean(point_p2, point)
        dist = dist / 100

        if (dist > 10):
            error[i] = 0 # if the error is too big then it won't display on the colour map because
                         # it is a point of less interest
        elif np.mean(stl_points[p, 1]) < point[1]:
            error[i] = np.mean(dist)
        else:
            error[i] = np.mean(dist)

    # Outputs maximum and minimum error
    highest = max(error)
    lowest = min(error)
    print(f"The maximum error is {highest}mm")
    print(f"The minimum error is {lowest}mm")

    # Use a temp variable to store the error array of each point
    temp = error

    # Convert error array into rgb and store in colours array
    error = error * 255 / highest
    zeroes = np.zeros((5640, 2))
    colours = np.append(zeroes, error, axis=1)

    # Displays colour map depending on error, the threshold are selected using trial and error
    for i in range(len(temp)):
        if temp[i] > 1.5:
            colours[i] = [255, 0, 0]  # green colour means less accurate
            continue

        if temp[i] < 1.1:
            colours[i] = [0, 255, 0]  # blue colour means more accurate
            continue

    # Display the STL Point Cloud and Segmented Points
    pcd_image = open3d.geometry.PointCloud()
    pcd_image.points = open3d.utility.Vector3dVector(segmented_points)
    pcd_image.colors = open3d.utility.Vector3dVector(colours)

    # Writing segmented points cloud to an open3d image
    open3d.io.write_point_cloud("point_cloud_segmented.ply", pcd_image)
    # Read the point cloud
    pcd_image = open3d.io.read_point_cloud("point_cloud_segmented.ply")

    # Load original STL file
    mesh1 = trimesh.load('ground_truth_in_stl_form.stl')
    # Convert stl file to ply. The STl file is the ground truth model
    mesh2 = mesh1.copy()
    mesh2.export('ground_truth.ply')

    # Set parameters for icp registration
    source = open3d.io.read_point_cloud("ground_truth.ply")
    target = open3d.io.read_point_cloud("point_cloud_segmented.ply")
    threshold = 0.005

    # Transformation matrix - Identity Matrix
    initial_trans = np.identity(4)

    # Evaluate registration performance
    evaluation = open3d.registration.evaluate_registration(source, target,threshold, initial_trans)

    # Obtain a registered model
    reg_p2p = open3d.registration.registration_icp(source, target, threshold, initial_trans)

    # Plot registered model
    draw_registration_result_original_color(source, target, reg_p2p.transformation)

    # Plot the error distribution
    plt.hist(temp, bins =50)
    plt.gca().set(title='Error/Distance', ylabel='Frequency');
    plt.show()


# Main file
def main():

    # Retrieve segmented_points data by running registration.m on MATLAB
    # change path if located at another file
    segmented_points_path = "raw_segmented_points.csv"
    df = pd.read_csv(segmented_points_path, header=None)
    registration(np.array(df))  # Make it a np array - easier

main()
