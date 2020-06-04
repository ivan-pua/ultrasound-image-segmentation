"""
Created by: Rishav Raj and Qie Shang Pua, University of New South Wales
This program performs image processing to obtain multiple segments of a patient's spine.
Input: Ultrasound scans of the patient's back (in png format)
Output: 1. Processed Spine Images
        2. A csv file that will be fed into registration.py
"""

# Import Packages
import os
import cv2
import glob
import math
import pandas as pd
import cv2
import numpy as np
import scipy.ndimage
import statistics
from skimage import data, color
import matplotlib.pyplot as plt
from skimage.color import rgb2gray
from skimage.transform import rescale, resize, downscale_local_mean
from timeit import default_timer as timer
import sys
from skimage.io import imread


# Python Migration of "find_best_path_jumping.m" of MATLAB
# Applies Dynamic Programming to calculate the path of least cost.
def find_best_path_jumping(curr):
    x = 151  # these are hardcoded - should be determined instead.
    y = 289

    # if at end
    if curr[1] == y:
        curr_cost = 0
        cost[int(curr[0]), int(curr[1])] = curr_cost  # Casted into int to access array index
        nexts[int(curr[0]), int(curr[1])] = 0
        return

    max_jump = 50
    no_cells = max_jump * 2 + 1

    min_next = [0, 0]
    min_cost = math.inf  # inf gives the largest num in float
    # print(curr)
    # print(int(curr[0]))

    # calc costs
    for i in range(no_cells):

        # cell no
        next = [0, 0]
        next[0] = curr[0] + i - max_jump - 1
        next[1] = curr[1] + 1
        # print(next)

        # out of bounds
        if next[0] < 1 or next[0] > x:
            next_cost = math.inf

        # already calculated
        elif cost[int(next[0]), int(next[1])] != math.inf:
            next_cost = cost[int(next[0]), int(next[1])]

        # need to recursively calculate
        else:
            next_cost = find_best_path_jumping(next)

        # print(next_cost)
        # add penalty if needed
        if abs(curr[0] - next[0]) > 2:
            if next_cost == None:
                next_cost = 0
            next_cost = next_cost + 0.2

        # calculate running min
        if next_cost != None and next_cost < min_cost:
            min_cost = next_cost
            min_next = next[0]

    # set results

    # print([int(curr[0]), int(curr[1])])
    curr_cost = inv_prob[int(curr[0]), int(curr[1])] + min_cost
    cost[int(curr[0]), int(curr[1])] = curr_cost
    nexts[int(curr[0]), int(curr[1])] = min_next

    return curr_cost

# Python Migration of "get_prob_map.m" of MATLAB
# Produces processed image in black and white
def get_prob_map(grayscale):

    # Start prob map as simple intensity
    intensity_map = rescale(grayscale, .5, anti_aliasing=False)
    intensity_map = np.asarray(intensity_map)
    prob_map = intensity_map * 0.5
    # print(np.shape(prob_map))

    # Create probablity map from intensity after gaussian filtering
    gausian = cv2.GaussianBlur(prob_map, (5, 5), 5)
    gausian = np.asarray(gausian)
    # print(np.shape(gausian))

    num = np.multiply(gausian, prob_map)
    den = num + np.multiply((1 - gausian), (1 - prob_map))
    prob_map = np.divide(num, den)

    kernel1 = np.ones((3, 3), np.float32) / 9
    kernel1[1][1] = 0.8888889

    y = 1
    x = 1
    shadow = np.ones((y, x)) * 0.2
    overall_mean = np.mean(np.mean(intensity_map))

    for i in range(1, x):
        j = y
        while (j > 0 and (
                gausian[j, i] < overall_mean * 1.5 or np.mean(gausian[j - 10:j - 1, i]) < overall_mean * 1.5)):
            shadow[j, i] = 0.1
            j = j - 1
        while (j > 0 and (gausian[j, i] > overall_mean * 1.5) or j > 5 and np.mean(
                gausian[j - 5:j - 1, i]) > overall_mean * 1.5):
            shadow[j, i] = intensity_map(j, i)
            j = j - 1
    shadow = cv2.GaussianBlur(shadow, (5, 5), 5)
    prob_map = (shadow * prob_map) / (shadow * prob_map + (1 - shadow) * (1 - prob_map))

    return prob_map

    k = cv2.waitKey(0) & 0xFF
    if k == 27:  # wait for ESC key to exit
        cv2.destroyAllWindows()
    elif k == ord('s'):  # wait for 's' key to save and exit
        cv2.imwrite('prob map of a single scan.png', prob_map)
        cv2.destroyAllWindows()


# Main File
# Similar to single_line_path.m of MATLAB
def main():

    points = []
    images = glob.glob('/Users/puaqieshang/Desktop/Taste of Research/MATLAB code/everything/phantom_images/phantom_3/scan_2/*.png')
    images.sort()

    count = 0
    startTime = timer()
    for fname in images:
        print(f"Image No.{count+1}")
        img = cv2.imread(fname)
        # im = plt.imread(fname)
        # implot = plt.imshow(im)
        count = count + 1

        us_img = img[80:400, 270:850]
        gray = cv2.cvtColor(us_img, cv2.COLOR_BGR2GRAY)
        # cv2.imshow('gray_image',gray)
        # [x, y] = np.shape(gray)
        # print(x)
        # print(y)
        prob_map = get_prob_map(gray)
        highlyLikely = 0.05*np.max(prob_map)
        np.savetxt("prob_map.csv", prob_map, delimiter=",")
        # print(np.shape(prob_map))

        """
        Dynamic Programming Section
        global variables are defined below
        """
        global inv_prob
        inv_prob = 0.5 - prob_map
        [a, b] = np.shape(prob_map)
        start = [np.floor(a/2), 1]
        global cost
        cost = np.ones([a, b]) * np.Inf
        global nexts
        nexts = np.ones([a, b]) * -1
        find_best_path_jumping(start)

        # get points on this scan
        point_scan = np.zeros([1, b])

        implot = plt.imshow(prob_map)
        # print(start[0])
        curr_x = start[0]
        for curr_y in range(b):
            point_scan[0, curr_y] = curr_x

            if prob_map[int(curr_x), int(curr_y)] > highlyLikely: #NEED TO CHANGE TO HIGHLY LIKELY!!!!!
                # print("helloooooo")
                # cv2.circle(gray, (int(curr_y), int(curr_x)), 1, (0, 0, 255), 1)
                # append coloured points
                plt.scatter(curr_x, curr_y, c='r', s=20)
                coloured_pt = [curr_x, curr_y, count * 0.2]
                # points = np.concatenate((points, coloured_pt), axis=1)
                points.append(coloured_pt)

            else:
                # cv2.circle(gray, (int(curr_y), int(curr_x)), 1, (255, 0, 0), 1)
                plt.scatter(curr_x, curr_y, c='b', s=20)

            curr_x = nexts[int(curr_x), int(curr_y)]

        plt.show()

        endTime = timer()
        # print(str(endTime - startTime) + " seconds")
        print(f"The time taken is {endTime - startTime} seconds")

    np.savetxt("pls-work.csv", [*zip(*points)], delimiter=",") # Transpose points data and save into csv format

    key = cv2.waitKey(0) & 0xFF
    if key == ord("q"):
        cv2.destroyAllWindows()


main()
