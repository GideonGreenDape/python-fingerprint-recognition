import cv2
import sys
import numpy as np
import json
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
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img = clahe.apply(img)
    img = image_enhance.image_enhance(img)
    img = np.array(img, dtype=np.uint8)

    # Thresholding
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    img[img == 255] = 1

    # Thinning
    skeleton = skeletonize(img)
    skeleton = np.array(skeleton, dtype=np.uint8)
    skeleton = removedot(skeleton)

    # Harris corners
    harris_corners = cv2.cornerHarris(img, 3, 3, 0.04)
    harris_normalized = cv2.normalize(harris_corners, None, 0, 255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32FC1)

    # Thresholding and keypoint detection
    threshold_harris = 125
    keypoints = [cv2.KeyPoint(int(y), int(x), 1) for x in range(harris_normalized.shape[0])
             for y in range(harris_normalized.shape[1]) if harris_normalized[x][y] > threshold_harris]

    # ORB descriptors
    orb = cv2.ORB_create()
    keypoints, des = orb.compute(img, keypoints)

    # Return None if no descriptors were found
    if des is None or len(des) == 0:
        return None, None

    return keypoints, des

def compare_fingerprints(des1, des2):
    if des1 is None or des2 is None:
        return float('inf'), []  # Return max score for no match if descriptors are invalid

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda match: match.distance)

    # Calculate the average match score (lower is better)
    score = sum(match.distance for match in matches) / len(matches) if matches else float('inf')
    return score, matches

if __name__ == '__main__':
    uploaded_image_path = sys.argv[1]
    descriptors_file_path = sys.argv[2]

    try:
        # Load stored descriptors from file
        with open(descriptors_file_path, 'r') as f:
            stored_descriptors = json.load(f)

        # Load and get descriptors for the uploaded fingerprint image
        uploaded_fingerprint = cv2.imread(uploaded_image_path, cv2.IMREAD_GRAYSCALE)
        if uploaded_fingerprint is None:
            raise ValueError(f"Could not load image from path: {uploaded_image_path}")

        kp1, des1 = get_descriptors(uploaded_fingerprint)

        if des1 is None:
            raise ValueError("No descriptors found in uploaded fingerprint image.")

        best_match = -1
        best_score = float('inf')
        match_percentage = 0

        # Loop through each stored fingerprint descriptor
        for idx, stored_des in enumerate(stored_descriptors):
            try:
                # Convert stored descriptors from list to numpy array (if necessary)
                stored_des = np.array(stored_des, dtype=np.uint8)

                # Compare descriptors if both are valid
                if stored_des is not None:
                    score, matches = compare_fingerprints(des1, stored_des)
                    
                    # Determine best match based on score (lower score is better)
                    if score < best_score:
                        best_score = score
                        best_match = idx
                        # Adjust match percentage to be more meaningful
                    match_percentage = max(0, min((1 - best_score / 40), 1)) * 100  # Scale match percentage

            except Exception as e:
                print(f"Error processing stored descriptors at index {idx}: {str(e)}", file=sys.stderr)

        # Result indicating best match index and match percentage
        result = {
            "matchIndex": best_match,
            "matchPercentage": match_percentage if best_match != -1 else None
        }

        # Output result to stdout
        print(json.dumps(result))

    except Exception as e:
        error_result = {
            "error": str(e)
        }
        print(json.dumps(error_result))
