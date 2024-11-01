# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 03:02:23 2016

@author: utkarsh
"""

import numpy as np
from frequest import frequest

def rifdge_freq(im, mask, orient, blksze, windsze, minWaveLength, maxWaveLength):
    rows, cols = im.shape
    freq = np.zeros((rows, cols))

    for r in range(0, rows - blksze, blksze):
        for c in range(0, cols - blksze, blksze):
            # Corrected 2D slicing
            blkim = im[r:r + blksze, c:c + blksze]
            blkor = orient[r:r + blksze, c:c + blksze]
            
            # Calculate frequency using frequest and apply it to the block
            freq_block = frequest(blkim, blkor, windsze, minWaveLength, maxWaveLength)
            freq[r:r + blksze, c:c + blksze] = freq_block

    # Apply mask to the frequency
    freq = freq * mask

    # Reshape freq and find non-zero elements
    freq_1d = freq.reshape(1, rows * cols)
    ind = np.where(freq_1d > 0)[1]  # Extract the valid indices
    
    if ind.size == 0:
        # If no valid frequencies are found, return 0
        return 0
    
    # Extract non-zero frequency elements
    non_zero_elems_in_freq = freq_1d[0][ind]

    # Calculate the median of non-zero frequency elements
    medianfreq = np.median(non_zero_elems_in_freq)

    return medianfreq
