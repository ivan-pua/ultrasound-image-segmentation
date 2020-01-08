import pandas as pd
import cv2
import numpy as np
import os
import scipy.ndimage
import statistics
from skimage import data, color
import matplotlib.pyplot as plt
from skimage.color import rgb2gray
from skimage.transform import rescale, resize, downscale_local_mean
from skimage.io import imread


def find_best_path_jumping():

    # Test for one image first
    path = r'/Users/puaqieshang/Desktop/Taste of Research/everything/phantom_images/phantom_3/scan_2/WirelessUSG2019-11-01-16-14-07.png'
    original = cv2.imread(path)

    # Convert to grayscale
    grayscale = rgb2gray(original)
    # print(grayscale)

    # Start prob map as simple intensity
    intensity_map = rescale(grayscale, .5, anti_aliasing=False)
    intensity_map = np.asarray(intensity_map)
    prob_map = intensity_map*0.5
    print(np.shape(prob_map))

    print("--------- after gausian blur ---------")

    # Create probablity map from intensity after gausian filtering
    gausian = cv2.GaussianBlur(prob_map, (5, 5), 5)
    gausian = np.asarray(gausian)
    print(np.shape(gausian))

    num = np.multiply(gausian, prob_map)
    den = num + np.multiply((1-gausian), (1-prob_map))
    prob_map = np.divide(num, den)
    # prob_map = (gausian.* prob_map). / (gausian. * prob_map + (1 - gausian). * (1 - prob_map));

    print(prob_map)
    print(np.shape(prob_map))

    # Filter for horizontal edges
    slight_gaus = cv2.GaussianBlur(grayscale, (5, 5), 0.5) # https://www.pyimagesearch.com/2016/07/25/convolutions-with-opencv-and-python/ CONVOLUTION
    slight_gaus2 = rescale(grayscale, .5, anti_aliasing=False)

    filt_top = np.array([[-1],[0],[1]])
    filt_top_1 = np.array([[-2,-2, -2, -2, -2],[-1, -1, -1, -1, -1],[0,  0,  0,  0,  0],[1,  1,  1,  1,  1],[2,  2,  2,  2,  2]])
    kernel1 = np.ones((3,3), np.float32)/9
    kernel1[1][1] = 0.8888889
    # filt_left = np.array([[0, -1, -1, -2, -2],[1,  0, -1, -1, -2],[1,  1,  0, -1, -1],[2,  1,  1,  0, -1],[2,  2,  1,  1,  0]])
    # filt_right = np.array([[-2, -2, -1, -1,  0],[-2, -1, -1,  0,  1],[-1, -1,  0,  1,  1,],[-1,  0,  1,  1,  2],[0,  1,  1,  2,  2]])
    upper_filt = cv2.filter2D(slight_gaus2.astype(np.float32),-1,filt_top)
    upper_filt1 = (upper_filt - upper_filt.min()) / (upper_filt.max() - upper_filt.min())
    cv2.imshow('hello',upper_filt1)
    # left_filt = rescale(cv2.filter2D(slight_gaus2,-1,filt_left))
    # right_filt = rescale(cv2.filter2D(slight_gaus2,-1,filt_right))
    # Show image
    cv2.imshow("prob_map", prob_map)
    cv2.imshow("slight gause", slight_gaus)
    y= 1
    x= 1
    shadow = np.ones((y,x))*0.2
    overall_mean = np.mean(np.mean(intensity_map))

    for i in range(1,x):
        j = y
        while(j>0 and (gausian[j, i] < overall_mean*1.5 or np.mean(gausian[j-10:j-1, i]) < overall_mean*1.5)):
            shadow[j, i] = 0.1
            j = j - 1
        while(j > 0 and (gausian[j, i] > overall_mean*1.5) or j > 5 and np.mean(gausian[j-5:j-1, i])> overall_mean*1.5):
            shadow[j, i] = intensity_map(j, i)
            j = j - 1
    shadow = cv2.GaussianBlur(shadow, (5, 5), 5)
    prob_map = (shadow * prob_map) / (shadow * prob_map + (1 - shadow) * (1 - prob_map))
    cv2.imshow('pua it will work', prob_map)

    k = cv2.waitKey(0) & 0xFF
    if k == 27:  # wait for ESC key to exit
        cv2.destroyAllWindows()
    elif k == ord('s'):  # wait for 's' key to save and exit
        cv2.imwrite('rishav.png', prob_map)
        cv2.destroyAllWindows()




find_best_path_jumping()