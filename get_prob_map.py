import pandas as pd
import cv2
import np
import os
from skimage import data, color
import matplotlib.pyplot as plt
from skimage.color import rgb2gray
from skimage.transform import rescale, resize, downscale_local_mean
from skimage.io import imread


def find_best_path_jumping():

    # Test for one image first
    path = r'/Users/puaqieshang/Desktop/Taste of Research/everything/phantom_images/phantom_3/scan_2/WirelessUSG2019-11-01-16-50-01.png'
    original = cv2.imread(path)

    # Convert to grayscale
    grayscale = rgb2gray(original)
    # print(grayscale)

    # Start prob map as simple intensity
    prob_map = rescale(grayscale, 0.25, anti_aliasing=False)
    print(np.shape(prob_map))

    print("--------- after gausian blur ---------")

    # Create probablity map from intensity after gausian filtering
    gausian = cv2.gausianBlur(prob_map, (5, 5), 5)
    print(np.shape(gausian))

    num = np.multiply(gausian, prob_map)
    den = num + np.multiply((1-gausian), (1-prob_map))
    prob_map = np.divide(num, den)
    # prob_map = (gausian.* prob_map). / (gausian. * prob_map + (1 - gausian). * (1 - prob_map));

    print(prob_map)
    print(np.shape(prob_map))

    # Filter for horizontal edges
    slight_gaus = cv2.gausianBlur(grayscale, (5, 5), 0.5) # https://www.pyimagesearch.com/2016/07/25/convolutions-with-opencv-and-python/ CONVOLUTION
    slight_gaus2 = rescale(grayscale, 0.25, anti_aliasing=False)

    # Show image
    cv2.imshow("prob_map", prob_map)
    cv2.imshow("slight gause", slight_gaus)
    k = cv2.waitKey(0) & 0xFF
    if k == 27:  # wait for ESC key to exit
        cv2.destroyAllWindows()
    elif k == ord('s'):  # wait for 's' key to save and exit
        cv2.imwrite('messigray.png', prob_map)
        cv2.destroyAllWindows()




find_best_path_jumping()

