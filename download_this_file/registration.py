"""
Created by: Rishav Raj and Qie Shang Pua, University of New South Wales
This program constructs and compares a 3D model of a spine.
Input: 1. The spine model in STL format
       2. The csv file for points.
Output: A figure with 3 sub-plots   - STL Model (Ground Truth)
                                    - Segmented Spine Surface from the ultrasound scans
                                    - Combination of those two above with Error Bar/ Colour Bar

Note: This program is only valid for phantom 3 scan 2
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


# ICP registration
def draw_registration_result_original_color(source, target, transformation):
    source_temp = copy.deepcopy(source)
    source_temp.transform(transformation)
    source_temp.paint_uniform_color([0.5, 0.5, 0.5])
    open3d.visualization.draw_geometries([source_temp, target])

def registration(raw):

    correct = np.array(raw)

    # To shift up the points, 11 is a threshold
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

    # Get STL model
    path = "/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl"
    stl_mesh = Mesh.from_file(path)
    points = np.around(np.unique(stl_mesh.vectors.reshape([stl_mesh.vectors.size // 3, 3]), axis=0), 2)  # p2.location

    # Displays the model, eliminate outlier points that are too far
    # Range values for each axis as selected per MATLAB code
    minz = -200
    maxz = 400

    miny = -100
    maxy = 400

    minx = -100
    maxx = 500

    # p represents point cloud
    px = np.bitwise_and(points[0, :] > minx, points[0, :] < maxx)
    py = np.bitwise_and(points[1, :] > miny, points[1, :] < maxy)
    pz = np.bitwise_and(points[2, :] > minz, points[2, :] < maxz)
    p = np.bitwise_and(px, py, pz)

    # c is the colour map
    cx = np.bitwise_and(correct[0, :] > minx, correct[0, :] < maxx)
    cy = np.bitwise_and(correct[1, :] > miny, correct[1, :] < maxy)
    cz = np.bitwise_and(correct[2, :] > minz, correct[2, :] < maxz)
    c = np.bitwise_and(cx, cy, cz)

    segmented_points = np.transpose(correct)

    num_rows = np.ma.size(segmented_points, 0)
    points = np.transpose(points)

    # Array to store the error for colour map
    error = np.ones((num_rows, 1))

    # For loop determines the colour map or the error when mapping segmented points to stl
    for i in range(num_rows):  # 39372
        point = segmented_points[i, :]  # extracting each row from p1
        point_p2 = points[:, i]

        # euclidean distance between the segmented points and the stl model
        dist = scipy.spatial.distance.euclidean(point_p2, point)
        dist = dist / 100

        if (dist > 10):
            error[i] = 0; # if the error is too big then it won't display on the colour map because
                          # it is a point of less interest
        elif np.mean(points[p, 1]) < point[1]:
            error[i] = np.mean(dist)
        else:
            error[i] = np.mean(dist)

    # ignore negative errors
    for i in range(num_rows):
        if (error[i] < 0):
            error[i] = 0

    # Outputs maximum and minimum error
    highest = max(error)
    lowest = min(error)
    print(f"The maximum error is {highest}mm")
    print(f"The minimum error is {lowest}mm")

    # Use a temp variable to store the error array of each point
    temp = error;

    # Convert error array into rgb and store in colours array
    error = error * 255 / highest
    zeroes = np.zeros((39372, 2))
    colours = np.append(zeroes, error, axis=1)

    # Displays colour map depending on error, the threshold are selected using trial and error
    for i in range(len(temp)):
        if temp[i] > 1.7:
            colours[i] = [0, 255, 0] # green colour means more error
            continue

        if temp[i] < 0.5:
            colours[i] = [0, 0, 255] # blue colour means less error
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
    mesh1 = trimesh.load('/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl')
    # Convert stl file to ply
    mesh2 = mesh1.copy()
    mesh2.export('convertedSTL.ply')

    # Set parameters for icp registration
    source = open3d.io.read_point_cloud("convertedSTL.ply")
    target = open3d.io.read_point_cloud("point_cloud_segmented.ply")
    threshold = 0.005
    # Transformation matrix
    trans_init = np.asarray([[1, 0, 0, 0],[0, 1, 0, 0],[0,0, 1, 0], [0, 0, 0, 1]])

    # Evaluate registration performance
    evaluation = open3d.registration.evaluate_registration(source, target,threshold, trans_init)

    # Obtain a registered model
    reg_p2p = open3d.registration.registration_icp(source, target, threshold,
                                               trans_init,open3d.registration.TransformationEstimationPointToPoint())

    # Plot registered model
    draw_registration_result_original_color(source, target, reg_p2p.transformation)

    # Plot the error histogram
    plt.hist(temp, bins=50)
    plt.gca().set(title='Error/Distance', ylabel='Frequency');
    plt.show()

# Main file
def main():

    # Retrieve segmented_points data by running registration.m on MATLAB
    segmented_points_path = "/Users/puaqieshang/Desktop/raw_segmented_points.csv"
    df = pd.read_csv(segmented_points_path, header=None)
    registration(np.array(df))

main()