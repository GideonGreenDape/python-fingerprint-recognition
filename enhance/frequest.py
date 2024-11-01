# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 02:51:53 2016

@author: utkarsh
"""



# FREQEST - Estimate fingerprint ridge frequency within image block
#
# Function to estimate the fingerprint ridge frequency within a small block
# of a fingerprint image.  This function is used by RIDGEFREQ
#
# Usage:
#  freqim =  freqest(im, orientim, windsze, minWaveLength, maxWaveLength)
#
# Arguments:
#         im       - Image block to be processed.
#         orientim - Ridge orientation image of image block.
#         windsze  - Window length used to identify peaks. This should be
#                    an odd integer, say 3 or 5.
#         minWaveLength,  maxWaveLength - Minimum and maximum ridge
#                     wavelengths, in pixels, considered acceptable.
# 
# Returns:
#         freqim    - An image block the same size as im with all values
#                     set to the estimated ridge spatial frequency.  If a
#                     ridge frequency cannot be found, or cannot be found
#                     within the limits set by min and max Wavlength
#                     freqim is set to zeros.
#
# Suggested parameters for a 500dpi fingerprint image
#   freqim = freqest(im,orientim, 5, 5, 15);
#
# See also:  RIDGEFREQ, RIDGEORIENT, RIDGESEGMENT

### REFERENCES

# Peter Kovesi 
# School of Computer Science & Software Engineering
# The University of Western Australia
# pk at csse uwa edu au
# http://www.csse.uwa.edu.au/~pk


import numpy as np
import math
import scipy.ndimage

def frequest(im, orientim, windsze, minWaveLength, maxWaveLength):
    rows, cols = np.shape(im)
    
    # Find mean orientation within the block by averaging sine and cosine
    cosorient = np.mean(np.cos(2 * orientim))
    sinorient = np.mean(np.sin(2 * orientim))
    orient = math.atan2(sinorient, cosorient) / 2
    
    # Rotate the image block so that the ridges are vertical
    rotim = scipy.ndimage.rotate(im, orient / np.pi * 180 + 90, axes=(1, 0), reshape=False, order=3, mode='nearest')
    
    # Crop the image to avoid invalid regions
    cropsze = int(np.fix(rows / np.sqrt(2)))
    offset = int(np.fix((rows - cropsze) / 2))
    rotim = rotim[offset:offset + cropsze, offset:offset + cropsze]  # Fixed slicing

    # Sum down the columns to get a projection of the grey values
    proj = np.sum(rotim, axis=0)

    # Perform dilation
    dilation = scipy.ndimage.grey_dilation(proj, windsze, structure=np.ones(windsze))
    temp = np.abs(dilation - proj)

    peak_thresh = 2

    # Detect the peaks
    maxpts = (temp < peak_thresh) & (proj > np.mean(proj))
    maxind = np.where(maxpts)

    # Extract the number of peaks
    if len(maxind[0]) < 2:
        freqim = np.zeros(im.shape)
    else:
        NoOfPeaks = len(maxind[0])
        waveLength = (maxind[0][-1] - maxind[0][0]) / (NoOfPeaks - 1)
        
        # Check if the wavelength is within bounds
        if minWaveLength <= waveLength <= maxWaveLength:
            freqim = (1 / np.double(waveLength)) * np.ones(im.shape)
        else:
            freqim = np.zeros(im.shape)

    return freqim

    