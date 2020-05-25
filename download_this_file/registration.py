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
import numpy as np
import math

import openmesh
import pandas as pd
from stl import mesh
from mpl_toolkits import mplot3d
import matplotlib.pyplot
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from stl.mesh import Mesh
import vtkplotlib as vpl
import open3d
import scipy
import scipy.io
import openmesh as om
import copy
from pyntcloud import PyntCloud




def registration(test):
    correct = np.array(test)
    numCols = len(test[2])
    to_shift_up = [0] * numCols
    for col in range(numCols):
        if test[2][col] < 11:
            to_shift_up[col] = 1
        else:
            to_shift_up[col] = 0

    # print(to_shift_up)
    test[0] = test[0] + np.multiply(30, to_shift_up)

    x_shift = -43.5;
    y_shift = 95;
    z_shift = 148;

    correct[0] = test[1] * 90.0 / 569.0 + x_shift
    correct[1] = (test[0] * (-88) / 569) + y_shift
    correct[2] = test[2] * (-5.01) + z_shift

    np.set_printoptions(precision=3)  # Prints array in 3 decimal places

    # THIS KIND OF ROTATOIN IS INCORRECT(ISH)
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
    meshy = Mesh.from_file(path)
    points = np.around(np.unique(meshy.vectors.reshape([meshy.vectors.size // 3, 3]), axis=0), 2)  # p2.location

    # vpl.mesh_plot(meshy)
    # vpl.show()

    minz = -200
    maxz = 400

    miny = -100
    maxy = 400

    minx = -100
    maxx = 500
    px = np.bitwise_and(points[0, :] > minx, points[0, :] < maxx)
    py = np.bitwise_and(points[1, :] > miny, points[1, :] < maxy)
    pz = np.bitwise_and(points[2, :] > minz, points[2, :] < maxz)
    p = np.bitwise_and(px, py, pz)

    cx = np.bitwise_and(correct[0, :] > minx, correct[0, :] < maxx)
    cy = np.bitwise_and(correct[1, :] > miny, correct[1, :] < maxy)
    cz = np.bitwise_and(correct[2, :] > minz, correct[2, :] < maxz)
    c = np.bitwise_and(cx, cy, cz)

    fixed_points = np.transpose(correct)  # p1.location

    # figure = pyplot.figure()
    # axes = mplot3d.Axes3D(figure)
    #
    # model = mesh.Mesh.from_file('/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl')
    # axes.add_collection3d(mplot3d.art3d.Poly3DCollection(model.vectors))
    # scale = model.points.flatten(-1)
    # axes.auto_scale_xyz(scale, scale, scale)

    # pyplot.show()
    # points = np.around(np.unique(mesh.vectors.reshape([mesh.vectors.size / 3, 3]), axis=0), 2)

    num_rows = np.ma.size(fixed_points, 0)
    points = np.transpose(points)
    ble = np.ones((num_rows, 1))

    for i in range(num_rows):  # 39372
        point = fixed_points[i, :]  # extracting each row from p1
        point_p2 = points[:, i]
        dist = scipy.spatial.distance.euclidean(point_p2, point)
        dist = dist / 100

        if (dist > 10):
            ble[i] = 0;
        elif np.mean(points[p, 1]) < point[1]:
            ble[i] = np.mean(dist)
        else:
            ble[i] = np.mean(dist)

    for i in range(num_rows):
        if (ble[i] < 0):
            ble[i] = 0


    highest = max(ble)
    lowest = min(ble)
    print(f"The maximum error is {highest}mm")
    print(f"The minimum error is {lowest}mm")

    temp = ble;



    ble = ble * 255 / highest
    # print(ble)
    zeroes = np.zeros((39372, 2))

    colours = np.append(zeroes, ble, axis=1)
    # print(ble)
    for i in range(len(temp)):
        if temp[i] > 1.7:
            colours[i] = [0, 255, 0] # green colour means less accurate
            continue

        if temp[i] < 0.5:
            colours[i] = [0, 0, 255] # blue colour means more accurate
            continue


    pcd_image = open3d.geometry.PointCloud()
    pcd_image.points = open3d.utility.Vector3dVector(fixed_points)
    pcd_image.colors = open3d.utility.Vector3dVector(colours)
    print(colours)
    print(colours.shape)
    open3d.io.write_point_cloud("puaiiiii.ply", pcd_image)
    pcd_image = open3d.io.read_point_cloud("puaiiiii.ply")  # Read the point cloud
    # open3d.visualization.draw_geometries([pcd_image])


    import trimesh

    mesh1 = trimesh.load('/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl')
    mesh2 = mesh1.copy()
    mesh2.export('stuff_stl.ply')

    def draw_registration_result_original_color(source, target, transformation):
        source_temp = copy.deepcopy(source)
        source_temp.transform(transformation)
        source_temp.paint_uniform_color([0.5, 0.5, 0.5])
        open3d.visualization.draw_geometries([source_temp, target])
    
    
    source = open3d.io.read_point_cloud("stuff_stl.ply")

    target = open3d.io.read_point_cloud("puaiiiii.ply")
    threshold = 0.005
    trans_init = np.asarray([[1, 0, 0, 0],[0, 1, 0, 0],[0,0, 1, 0], [0, 0, 0, 1]])
    # draw_registration_result(source, target, trans_init)

    # target.estimate_normals(search_param=open3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    # source.estimate_normals(search_param=open3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))



    evaluation = open3d.registration.evaluate_registration(source, target,threshold, trans_init)
    reg_p2p = open3d.registration.registration_icp(source, target, threshold, trans_init,open3d.registration.TransformationEstimationPointToPoint())
    draw_registration_result_original_color(source, target, reg_p2p.transformation)
    # reg_p2l = open3d.registration.registration_icp(source, target, threshold, trans_init, open3d.registration.TransformationEstimationPointToPlane())
    # draw_registration_result_original_color(source, target, reg_p2l.transformation)



    # print(result_icp)
    
    # openmesh.write_mesh(mesh1, "mesh_stl.ply")
    # pupu = mesh1
    # print(pupu)
    # import pymesh
    # mesh2 = pymesh.load_mesh("/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl")
    # pymesh.save_mesh("meshTest.ply", mesh2, ascii = True)
    # print(mesh2)

    # human_face = PyntCloud.from_file("puaiiiii.ply")
    #########
    # cm = plt.cm.get_cmap('RdGy')
    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')
    # xs = fixed_points[:, 0]
    # ys = fixed_points[:, 1]
    # zs = fixed_points[:, 2]
    #
    #
    # ax.set_xlabel('X Label')
    # ax.set_ylabel('Y Label')
    # ax.set_zlabel('Z Label')
    #
    # inn = ax.scatter(xs, ys, zs, s=10, c=(colours[:, 0]) / 255 , depthshade=True, cmap = cm)
    # plt.colorbar(inn)
    # plt.show()
    import matplotlib.pyplot as plt
    # print()
    plt.hist(temp, bins=50)
    plt.gca().set(title='Error/Distance', ylabel='Frequency');
    plt.show()


    # https://matplotlib.org/3.1.1/gallery/images_contours_and_fields/multi_image.html#sphx-glr-gallery-images-contours-and-fields-multi-image-py
    # CHECK THIS WEBSITE FOR MULTIPLE SUBPLOTS


# read from csv
file_location = "/Users/puaqieshang/Desktop/Taste of Research/everything/inital_experiments/pua.csv"  # saved from points.mat from MATLAB
# file_location = "/Users/puaqieshang/Desktop/Taste of Research/original code [DO NOT EDIT]/inital_experiments/pua_phantom.csv"
df = pd.read_csv(file_location, header=None)
df = np.array(df)
registration(np.array(df))  # Make it a np array - easier
