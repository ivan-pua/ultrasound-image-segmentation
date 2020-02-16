# Register detected points to model and plot the two with error
# (only valid for phantom 3 scan 2)
import numpy as np
import math
import pandas as pd
from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot
from stl.mesh import Mesh
import vtkplotlib as vpl
import open3d
import scipy
from pyntcloud import PyntCloud


# (from the single_find_path)

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
    points = np.around(np.unique(meshy.vectors.reshape([meshy.vectors.size//3, 3]), axis=0),2) # p2.location

    vpl.mesh_plot(meshy)
    vpl.show()

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

    fixed_points = np.transpose(correct) #p1.location




    # human_face = PyntCloud.from_file("puaiiiii.ply")
    #
    # human_face.plot()

    # figure = pyplot.figure()
    # axes = mplot3d.Axes3D(figure)
    #
    # model = mesh.Mesh.from_file('/Users/puaqieshang/Desktop/Taste of Research/everything/models/Segmentation_bone.stl')
    # axes.add_collection3d(mplot3d.art3d.Poly3DCollection(model.vectors))
    # scale = model.points.flatten(-1)
    # axes.auto_scale_xyz(scale, scale, scale)
    #
    # pyplot.show()
    # points = np.around(np.unique(mesh.vectors.reshape([mesh.vectors.size / 3, 3]), axis=0), 2)

    num_rows = np.ma.size(fixed_points, 0)
    points = np.transpose(points)
    ble = np.ones((num_rows, 1))


    for i in range(num_rows): #39372
        point = fixed_points[i, :] # extracting each row from p1
        point_p2 = points[:, i]
        dist = scipy.spatial.distance.euclidean(point_p2, point)
        dist = dist/100

        if (dist > 10):
            ble[i] = 0;
        elif np.mean(points[p, 1]) < point[1]:
            ble[i] = np.mean(dist) - 1
        else:
            ble[i] = np.mean(dist) - 1


    pcd = open3d.geometry.PointCloud()
    pcd.points = open3d.utility.Vector3dVector(fixed_points)
    pcd.colors = open3d.utility.Vector3dVector(fixed_points)
    open3d.io.write_point_cloud("puaiiiii.ply", pcd)
    pcd = open3d.io.read_point_cloud("puaiiiii.ply")  # Read the point cloud
    open3d.visualization.draw_geometries([pcd])

    highest = max(ble)
    ble = ble*255/highest
    print(ble)

# read from csv
file_location = "/Users/puaqieshang/Desktop/Taste of Research/everything/inital_experiments/pua.csv"
df = pd.read_csv(file_location, header=None)
df = np.array(df)

registration(np.array(df))  # Make it a np array - easier
