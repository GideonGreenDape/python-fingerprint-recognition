import sys
import numpy as np
import cv2
import json
import base64
from skimage.morphology import skeletonize
from enhance import image_enhance

def removedot(invertThin):
    temp0 = np.array(invertThin[:])
    temp1 = temp0 / 255
    temp2 = np.array(temp1)
    filtersize = 6
    W, H = temp0.shape[:2]

    for i in range(W - filtersize):
        for j in range(H - filtersize):
            filter0 = temp1[i:i + filtersize, j:j + filtersize]
            flag = 0
            if sum(filter0[:, 0]) == 0: flag += 1
            if sum(filter0[:, filtersize - 1]) == 0: flag += 1
            if sum(filter0[0, :]) == 0: flag += 1
            if sum(filter0[filtersize - 1, :]) == 0: flag += 1
            if flag > 3:
                temp2[i:i + filtersize, j:j + filtersize] = np.zeros((filtersize, filtersize))

    return temp2

def get_descriptors(img):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    img = image_enhance.image_enhance(img)
    img = np.array(img, dtype=np.uint8)

    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    img[img == 255] = 1

    skeleton = skeletonize(img)
    skeleton = np.array(skeleton, dtype=np.uint8)
    skeleton = removedot(skeleton)

    harris_corners = cv2.cornerHarris(img, 3, 3, 0.04)
    harris_normalized = cv2.normalize(harris_corners, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32FC1)

    threshold_harris = 125
    keypoints = [cv2.KeyPoint(int(y), int(x), 1) for x in range(harris_normalized.shape[0])
                 for y in range(harris_normalized.shape[1]) if harris_normalized[x][y] > threshold_harris]

    orb = cv2.ORB_create()
    keypoints, des = orb.compute(img, keypoints)
    
    return des

if __name__ == '__main__':
    # Read base64-encoded image data from stdin
    img_data_base64 = sys.stdin.read()

    # Decode base64 image data
    img_data = base64.b64decode(img_data_base64)
    img_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

    # Process image to get descriptors
    des = get_descriptors(img)
    
    # Output the descriptors as JSON
    print(json.dumps(des.tolist() if des is not None else None))
