# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 03:15:03 2016

@author: utkarsh
"""


# RIDGEFILTER - enhances fingerprint image via oriented filters
#
# Function to enhance fingerprint image via oriented filters
#
# Usage:
#  newim =  ridgefilter(im, orientim, freqim, kx, ky, showfilter)
#
# Arguments:
#         im       - Image to be processed.
#         orientim - Ridge orientation image, obtained from RIDGEORIENT.
#         freqim   - Ridge frequency image, obtained from RIDGEFREQ.
#         kx, ky   - Scale factors specifying the filter sigma relative
#                    to the wavelength of the filter.  This is done so
#                    that the shapes of the filters are invariant to the
#                    scale.  kx controls the sigma in the x direction
#                    which is along the filter, and hence controls the
#                    bandwidth of the filter.  ky controls the sigma
#                    across the filter and hence controls the
#                    orientational selectivity of the filter. A value of
#                    0.5 for both kx and ky is a good starting point.
#         showfilter - An optional flag 0/1.  When set an image of the
#                      largest scale filter is displayed for inspection.
# 
# Returns:
#         newim    - The enhanced image
#
# See also: RIDGEORIENT, RIDGEFREQ, RIDGESEGMENT

# Reference: 
# Hong, L., Wan, Y., and Jain, A. K. Fingerprint image enhancement:
# Algorithm and performance evaluation. IEEE Transactions on Pattern
# Analysis and Machine Intelligence 20, 8 (1998), 777 789.

### REFERENCES

# Peter Kovesi  
# School of Computer Science & Software Engineering
# The University of Western Australia
# pk at csse uwa edu au
# http://www.csse.uwa.edu.au/~pk



import numpy as np
import scipy.ndimage

def ridge_filter(im, orient, freq, kx, ky):
    angleInc = 3
    im = np.double(im)
    rows, cols = im.shape
    newim = np.zeros((rows, cols))
    
    # Flatten and find indices where frequency > 0
    freq_1d = np.reshape(freq, (1, rows * cols))
    ind = np.where(freq_1d > 0)[1]  # Corrected indexing here
    
    # Round the array of frequencies to reduce distinct values
    non_zero_elems_in_freq = freq_1d[0][ind]
    non_zero_elems_in_freq = np.round(non_zero_elems_in_freq * 100) / 100.0
    unfreq = np.unique(non_zero_elems_in_freq)

    # Generate filters for distinct frequencies and orientations
    sigmax = 1 / unfreq[0] * kx
    sigmay = 1 / unfreq[0] * ky
    sze = int(np.round(3 * np.max([sigmax, sigmay])))

    x, y = np.meshgrid(np.linspace(-sze, sze, 2 * sze + 1), np.linspace(-sze, sze, 2 * sze + 1))
    reffilter = np.exp(-(((x ** 2) / (sigmax ** 2)) + ((y ** 2) / (sigmay ** 2)))) * np.cos(2 * np.pi * unfreq[0] * x)

    # Prepare Gabor filters
    filt_rows, filt_cols = reffilter.shape
    gabor_filter = np.zeros((int(180 / angleInc), filt_rows, filt_cols))

    for o in range(int(180 / angleInc)):
        # Generate rotated versions of the filter
        rot_filt = scipy.ndimage.rotate(reffilter, -(o * angleInc + 90), reshape=False)
        gabor_filter[o] = rot_filt

    # Boundary conditions for valid pixels
    maxsze = int(sze)
    temp = freq > 0
    validr, validc = np.where(temp)
    
    temp1 = validr > maxsze
    temp2 = validr < rows - maxsze
    temp3 = validc > maxsze
    temp4 = validc < cols - maxsze
    final_temp = temp1 & temp2 & temp3 & temp4
    finalind = np.where(final_temp)

    # Convert orientation matrix values to index
    maxorientindex = int(np.round(180 / angleInc))
    orientindex = np.round(orient / np.pi * 180 / angleInc).astype(int)  # Convert to integer
    
    # Ensure orientation indices are within bounds
    orientindex = np.where(orientindex < 1, orientindex + maxorientindex, orientindex)
    orientindex = np.where(orientindex > maxorientindex, orientindex - maxorientindex, orientindex)

    # Perform filtering
    finalind_rows, finalind_cols = np.shape(finalind)
    sze = int(sze)
    for k in range(finalind_cols):
        r = validr[finalind[0][k]]
        c = validc[finalind[0][k]]
        
        # Correct slicing
        img_block = im[r-sze:r+sze + 1, c-sze:c+sze + 1]
        
        newim[r, c] = np.sum(img_block * gabor_filter[orientindex[r, c] - 1])

    return newim
