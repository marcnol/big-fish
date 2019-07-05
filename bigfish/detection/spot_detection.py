# -*- coding: utf-8 -*-

"""
Class and functions to detect RNA spots in 2-d and 3-d.
"""

from bigfish import stack

import scipy.ndimage as ndi
import numpy as np

from skimage.measure import label, regionprops


# TODO complete documentation methods
# TODO add sanity check functions
# TODO improve documentation with optional output

# ### LoG detection ###

def log_lm(image, sigma, threshold, minimum_distance=1):
    """Apply LoG filter followed by a Local Maximum algorithm to detect spots
    in a 2-d or 3-d image.

    1) We smooth the image with a LoG filter.
    2) We apply a multidimensional maximum filter.
    3) A pixel which has the same value in the original and filtered images
    is a local maximum.
    4) We remove local peaks under a threshold.

    Parameters
    ----------
    image : np.ndarray
        Image with shape (z, y, x) or (y, x).
    sigma : float or Tuple(float)
        Sigma used for the gaussian filter (one for each dimension). If it's a
        float, the same sigma is applied to every dimensions.
    threshold : float or int
        A threshold to detect peaks.
    minimum_distance : int
        Minimum distance (in number of pixels) between two local peaks.

    Returns
    -------
    spots : np.ndarray, np.int64
        Coordinate of the spots with shape (nb_spots, 3) or (nb_spots, 2)
        for 3-d or 2-d images respectively.
    radius : float, Tuple[float]
        Radius of the detected peaks.

    """
    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=False)
    stack.check_parameter(sigma=(float, int, tuple),
                          minimum_distance=(float, int),
                          threshold=(float, int))

    # cast image in np.float and apply LoG filter
    image_filtered = stack.log_filter(image, sigma, keep_dtype=True)

    # find local maximum
    mask = local_maximum_detection(image_filtered, minimum_distance)

    # remove spots with a low intensity and return coordinates and radius
    spots, radius, _ = spots_thresholding(image, sigma, mask, threshold)

    return spots, radius


def local_maximum_detection(image, minimum_distance):
    """Compute a mask to keep only local maximum, in 2-d and 3-d.

    1) We apply a multidimensional maximum filter.
    2) A pixel which has the same value in the original and filtered images
    is a local maximum.

    Parameters
    ----------
    image : np.ndarray, np.uint
        Image to process with shape (z, y, x) or (y, x).
    minimum_distance : int, float
        Minimum distance (in number of pixels) between two local peaks.

    Returns
    -------
    mask : np.ndarray, bool
        Mask with shape (z, y, x) or (y, x) indicating the local peaks.

    """
    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=False)
    stack.check_parameter(minimum_distance=(float, int))

    # compute the kernel size (centered around our pixel because it is uneven)
    kernel_size = int(2 * minimum_distance + 1)

    # apply maximum filter to the original image
    image_filtered = ndi.maximum_filter(image, size=kernel_size)

    # we keep the pixels with the same value before and after the filtering
    mask = image == image_filtered

    return mask


def spots_thresholding(image, sigma, mask_lm, threshold):
    """Filter detected spots and get coordinates of the remaining
    spots.

    Parameters
    ----------
    image : np.ndarray, np.uint
        Image with shape (z, y, x) or (y, x).
    sigma : float or Tuple(float)
        Sigma used for the gaussian filter (one for each dimension). If it's a
        float, the same sigma is applied to every dimensions.
    mask_lm : np.ndarray, bool
        Mask with shape (z, y, x) or (y, x) indicating the local peaks.
    threshold : float or int
        A threshold to detect peaks.

    Returns
    -------
    spots : np.ndarray, np.int64
        Coordinate of the local peaks with shape (nb_peaks, 3) or
        (nb_peaks, 2) for 3-d or 2-d images respectively.
    radius : float or Tuple(float)
        Radius of the detected peaks.
    mask : np.ndarray, bool
        Mask with shape (z, y, x) or (y, x) indicating the spots.

    """
    # TODO make 'radius' output more consistent
    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=False)
    stack.check_array(mask_lm,
                      ndim=[2, 3],
                      dtype=[bool],
                      allow_nan=False)
    stack.check_parameter(sigma=(float, int, tuple),
                          threshold=(float, int))

    # remove peak with a low intensity
    mask = (mask_lm & (image > threshold))

    # get peak coordinates
    spots = np.nonzero(mask)
    spots = np.column_stack(spots)

    # compute radius
    if isinstance(sigma, tuple):
        radius = [np.sqrt(image.ndim) * sigma_ for sigma_ in sigma]
        radius = tuple(radius)
    else:
        radius = np.sqrt(image.ndim) * sigma

    return spots, radius, mask


def log_cc(image, sigma, threshold):
    """Find connected regions above a fixed threshold on a LoG filtered image.

    Parameters
    ----------
    image : np.ndarray
        Image with shape (z, y, x) or (y, x).
    sigma : float or Tuple(float)
        Sigma used for the gaussian filter (one for each dimension). If it's a
        float, the same sigma is applied to every dimensions.
    threshold : float or int
        A threshold to detect peaks. Considered as a relative threshold if
        float.

    Returns
    -------
    cc : np.ndarray, np.int64
        Image labelled with shape (z, y, x) or (y, x).

    """
    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=False)
    stack.check_parameter(sigma=(float, int, tuple),
                          threshold=(float, int))

    # cast image in np.float and apply LoG filter
    image_filtered = stack.log_filter(image, sigma, keep_dtype=True)

    # find connected components
    cc = get_cc(image_filtered, threshold)

    # TODO return coordinate of the centroid

    return cc


def get_cc(image, threshold):
    """Find connected regions above a fixed threshold.

    Parameters
    ----------
    image : np.ndarray
        Image with shape (z, y, x) or (y, x).
    threshold : float or int
        A threshold to detect peaks.

    Returns
    -------
    cc : np.ndarray, np.int64
        Image labelled with shape (z, y, x) or (y, x).

    """
    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=True)
    stack.check_parameter(threshold=(float, int))

    # Compute binary mask of the filtered image
    mask = image > threshold

    # find connected components
    cc = label(mask)

    return cc


def filter_cc(image, cc, spots, min_area, min_nb_spots, min_intensity_factor):
    """Filter connected regions.

    Parameters
    ----------
    image : np.ndarray
        Image with shape (z, y, x) or (y, x).
    cc : np.ndarray, np.int64
        Image labelled with shape (z, y, x) or (y, x).
    spots : np.ndarray, np.int64
        Coordinate of the spots with shape (nb_spots, 3).
    min_area : int
        Minimum number of pixels in the connected region.
    min_nb_spots : int
        Minimum number of spot detected in this region.
    min_intensity_factor : int or float
        Minimum pixel intensity in the connected region is equal to
        median(intensity) * min_intensity_factor.

    Returns
    -------
    regions_filtered : np.ndarray
        Array with filtered skimage.measure._regionprops._RegionProperties.
    spots_out_region : np.ndarray, np.int64
        Coordinate of the spots outside the regions with shape (nb_spots, 3).

    """
    # TODO manage the difference between 2-d and 3-d data

    # check parameters
    stack.check_array(image,
                      ndim=[2, 3],
                      dtype=[np.uint8, np.uint16, np.float32, np.float64],
                      allow_nan=True)
    stack.check_array(cc,
                      ndim=[2, 3],
                      dtype=[np.int64],
                      allow_nan=True)
    stack.check_array(spots,
                      ndim=2,
                      dtype=[np.int64],
                      allow_nan=True)
    stack.check_parameter(min_area=int,
                          min_nb_spots=int,
                          min_intensity_factor=(float, int))

    # get properties of the different connected regions
    regions = regionprops(cc, intensity_image=image, cache=True)

    # get different features of the regions
    area = []
    intensity = []
    bbox = []
    for i, region in enumerate(regions):
        area.append(region.area)
        intensity.append(region.max_intensity)
        bbox.append(region.bbox)
    regions = np.array(regions)
    area = np.array(area)
    intensity = np.array(intensity)
    bbox = np.array(bbox)

    # keep regions with a minimum size
    big_area = area > min_area
    regions = regions[big_area]
    intensity = intensity[big_area]
    bbox = bbox[big_area]

    # case where no region big enough were detected
    if regions.size == 0:
        regions_filtered = np.array([])
        spots_out_region = np.array([], dtype=np.int64).reshape((0, 2))
        return regions_filtered, spots_out_region

    # TODO remove copy()?
    # count spots in the regions
    nb_spots_in = []
    for box in bbox:
        (min_z, min_y, min_x, max_z, max_y, max_x) = box
        mask_spots_in = spots[:, 0] <= max_z
        mask_spots_in = (mask_spots_in & (spots[:, 1] <= max_y))
        mask_spots_in = (mask_spots_in & (spots[:, 2] <= max_x))
        mask_spots_in = (mask_spots_in & (min_z <= spots[:, 0]))
        mask_spots_in = (mask_spots_in & (min_y <= spots[:, 1]))
        mask_spots_in = (mask_spots_in & (min_x <= spots[:, 2]))
        spots_in = spots.copy()
        spots_in = spots_in[mask_spots_in]
        nb_spots_in.append(spots_in.shape[0])

    # keep regions with a minimum number of spots
    nb_spots_in = np.array(nb_spots_in)
    multiple_spots = nb_spots_in > min_nb_spots

    # keep regions which reach a minimum intensity value
    high_intensity = intensity > np.median(intensity) * min_intensity_factor

    # filter regions and labels
    mask = multiple_spots | high_intensity
    regions_filtered = regions[mask]
    bbox = bbox[mask]

    # case where no foci were detected
    if regions.size == 0:
        spots_out_region = np.array([], dtype=np.int64).reshape((0, 2))
        return regions_filtered, spots_out_region

    # TODO make it in a separate function
    # count spots outside the regions
    mask_spots_out = np.ones(spots[:, 0].shape, dtype=bool)
    for box in bbox:
        (min_z, min_y, min_x, max_z, max_y, max_x) = box
        mask_spots_in = spots[:, 0] <= max_z
        mask_spots_in = (mask_spots_in & (spots[:, 1] <= max_y))
        mask_spots_in = (mask_spots_in & (spots[:, 2] <= max_x))
        mask_spots_in = (mask_spots_in & (min_z <= spots[:, 0]))
        mask_spots_in = (mask_spots_in & (min_y <= spots[:, 1]))
        mask_spots_in = (mask_spots_in & (min_x <= spots[:, 2]))
        mask_spots_out = mask_spots_out & (~mask_spots_in)
    spots_out_region = spots.copy()
    spots_out_region = spots_out_region[mask_spots_out]

    return regions_filtered, spots_out_region


# ### Signal-to-Noise ratio ###

def compute_snr(image, sigma, minimum_distance=1,
                threshold_signal_detection=2000, neighbor_factor=3):
    """Compute Signal-to-Noise ratio for each spot detected.

    Parameters
    ----------
    image : np.ndarray, np.uint
        Image with shape (z, y, x) or (y, x).
    sigma : float or Tuple(float)
        Sigma used for the gaussian filter (one for each dimension). If it's a
        float, the same sigma is applied to every dimensions.
    minimum_distance : int
        Minimum distance (in number of pixels) between two local peaks.
    threshold_signal_detection : float or int
        A threshold to detect peaks. Considered as a relative threshold if
        float.
    neighbor_factor : int or float
        The ratio between the radius of the neighborhood defining the noise
        and the radius of the signal.

    Returns
    -------

    """
    # cast image in np.float, apply LoG filter and find local maximum
    mask = log_lm(image, sigma, minimum_distance)

    # apply a specific threshold to filter the detected spots and compute snr
    l_snr = from_threshold_to_snr(image, sigma, mask,
                                  threshold_signal_detection,
                                  neighbor_factor)

    return l_snr


def from_threshold_to_snr(image, sigma, mask, threshold=2000,
                          neighbor_factor=3):
    """

    Parameters
    ----------
    image : np.ndarray, np.uint
        Image with shape (z, y, x) or (y, x).
    sigma : float or Tuple(float)
        Sigma used for the gaussian filter (one for each dimension). If it's a
        float, the same sigma is applied to every dimensions.
    mask : np.ndarray, bool
        Mask with shape (z, y, x) or (y, x) indicating the local peaks.
    threshold : float or int
        A threshold to detect peaks. Considered as a relative threshold if
        float.
    neighbor_factor : int or float
        The ratio between the radius of the neighborhood defining the noise
        and the radius of the signal.

    Returns
    -------

    """
    # remove peak with a low intensity
    if isinstance(threshold, float):
        threshold *= image.max()
    mask_ = (mask & (image > threshold))

    # no spot detected
    if mask_.sum() == 0:
        return []

    # we get the xy coordinate of the detected spot
    spot_coordinates = np.nonzero(mask_)
    spot_coordinates = np.column_stack(spot_coordinates)

    # compute radius for the spot and the neighborhood
    s = np.sqrt(image.ndim)
    (z_radius, yx_radius) = (int(s * sigma[0]), int(s * sigma[1]))
    (z_neigh, yx_neigh) = (int(s * sigma[0] * neighbor_factor),
                           int(s * sigma[1] * neighbor_factor))

    # we enlarge our mask to localize the complete signal and not just
    # the peak
    kernel_size_z = 2 * z_radius + 1
    kernel_size_yx = 2 * yx_radius + 1
    kernel_size = (kernel_size_z, kernel_size_yx, kernel_size_yx)
    mask_ = ndi.maximum_filter(mask_, size=kernel_size,
                               mode='constant')

    # we define a binary matrix of noise
    noise = image.astype(np.float64)
    noise[mask_] = np.nan

    l_snr = []
    for i in range(spot_coordinates.shape[0]):
        (z, y, x) = (spot_coordinates[i, 0],
                     spot_coordinates[i, 1],
                     spot_coordinates[i, 2])

        max_z, max_y, max_x = image.shape
        if (z_neigh <= z <= max_z - z_neigh - 1
                and yx_neigh <= y <= max_y - yx_neigh - 1
                and yx_neigh <= x <= max_x - yx_neigh - 1):
            pass
        else:
            l_snr.append(np.nan)
            continue

        # extract local signal
        local_signal = image[z - z_radius: z + z_radius + 1,
                             y - yx_radius: y + yx_radius + 1,
                             x - yx_radius: x + yx_radius + 1].copy()

        # extract local noise
        local_noise = noise[z - z_neigh: z + z_neigh + 1,
                            y - yx_neigh: y + yx_neigh + 1,
                            x - yx_neigh: x + yx_neigh + 1].copy()
        local_noise[z_neigh - z_radius: z_neigh + z_radius + 1,
                    yx_neigh - yx_radius: yx_neigh + yx_radius + 1,
                    yx_neigh - yx_radius: yx_neigh + yx_radius + 1] = np.nan

        # compute snr
        snr = np.nanmean(local_signal) / np.nanstd(local_noise)
        l_snr.append(snr)

    return l_snr


# ### Utils ###

def get_sigma(resolution_z=300, resolution_yx=103, psf_z=400, psf_yx=200):
    """Compute the standard deviation of the PSF of the spots.

    Parameters
    ----------
    resolution_z : float
        Height of a voxel, along the z axis, in nanometer.
    resolution_yx : float
        Size of a voxel on the yx plan, in nanometer.
    psf_yx : int
        Theoretical size of the PSF emitted by a spot in
        the yx plan, in nanometer.
    psf_z : int
        Theoretical size of the PSF emitted by a spot in
        the z plan, in nanometer.

    Returns
    -------
    sigma_z : float
        Standard deviation of the PSF, along the z axis, in pixel.
    sigma_xy : float
        Standard deviation of the PSF, along the yx plan, in pixel.
    """
    # TODO rename "resolution"
    # compute sigma
    sigma_z = psf_z / resolution_z
    sigma_yx = psf_yx / resolution_yx

    return sigma_z, sigma_yx
