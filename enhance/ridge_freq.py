# -*- coding: utf-8 -*-
"""
Created on Tue Apr 19 12:14:49 2016

@author: utkarsh
"""


# RIDGEFREQ - Calculates a ridge frequency image
#
# Function to estimate the fingerprint ridge frequency across a
# fingerprint image. This is done by considering blocks of the image and
# determining a ridgecount within each block by a call to FREQEST.
#
# Usage:
#  [freqim, medianfreq] =  ridgefreq(im, mask, orientim, blksze, windsze, ...
#                                    minWaveLength, maxWaveLength)
#
# Arguments:
#         im       - Image to be processed.
#         mask     - Mask defining ridge regions (obtained from RIDGESEGMENT)
#         orientim - Ridge orientation image (obtained from RIDGORIENT)
#         blksze   - Size of image block to use (say 32) 
#         windsze  - Window length used to identify peaks. This should be
#                    an odd integer, say 3 or 5.
#         minWaveLength,  maxWaveLength - Minimum and maximum ridge
#                     wavelengths, in pixels, considered acceptable.
# 
# Returns:
#         freqim     - An image  the same size as im with  values set to
#                      the estimated ridge spatial frequency within each
#                      image block.  If a  ridge frequency cannot be
#                      found within a block, or cannot be found within the
#                      limits set by min and max Wavlength freqim is set
#                      to zeros within that block.
#         medianfreq - Median frequency value evaluated over all the
#                      valid regions of the image.
#
# Suggested parameters for a 500dpi fingerprint image
#   [freqim, medianfreq] = ridgefreq(im,orientim, 32, 5, 5, 15);
#

# See also: RIDGEORIENT, FREQEST, RIDGESEGMENT

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
from .frequest import frequest

def ridge_freq(im, mask, orient, blksze, windsze, minWaveLength, maxWaveLength):
    rows, cols = im.shape
    freq = np.zeros((rows, cols))

    # Loop over blocks of the image
    for r in range(0, rows - blksze, blksze):
        for c in range(0, cols - blksze, blksze):
            # Corrected 2D slicing
            blkim = im[r:r + blksze, c:c + blksze]
            blkor = orient[r:r + blksze, c:c + blksze]
            
            # Compute the frequency for the block
            freq_block = frequest(blkim, blkor, windsze, minWaveLength, maxWaveLength)
            freq[r:r + blksze, c:c + blksze] = freq_block

    # Apply mask to frequency
    freq = freq * mask

    # Reshape frequency matrix into a 1D array and get non-zero elements
    freq_1d = freq.flatten()  # Flatten the matrix to 1D array
    non_zero_indices = np.where(freq_1d > 0)[0]  # Find indices of non-zero elements
    
    # Check if there are any valid frequencies
    if len(non_zero_indices) == 0:
        return freq, 0  # Return 0 mean frequency if no valid frequencies found

    # Extract non-zero frequency elements
    non_zero_elems_in_freq = freq_1d[non_zero_indices]
    
    # Calculate mean and median frequencies
    meanfreq = np.mean(non_zero_elems_in_freq)
    medianfreq = np.median(non_zero_elems_in_freq)  # This should work as long as there are valid non-zero elements

    return freq, meanfreq
