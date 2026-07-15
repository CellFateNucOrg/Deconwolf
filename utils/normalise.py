import numpy as np


def normalise_data(data, c_axis, pth=(1, 99), dtype=np.uint16):
    """
    Normalise image intensities based on percentile range.

    Args:
        data (numpy.ndarray): Data to normalise.
        c_axis (int): Axis corresponding to channels.
        pth (list[int] or tuple[int, int]): Percentiles for normalisation (min, max).
        dtype (np.dtype, optional): Output type (default np.uint16).

    Returns:
        np.ndarray: Normalised array, same shape as input.
    """
    if not isinstance(data, np.ndarray):
        raise ValueError(f'Input data must be a numpy array.')
    if not pth[1] > pth[0]:
        raise ValueError(f'Maximum percentile must be greater than minimum percentile.')
    
    # Make empty array (32-bit float) with same the same shape as the input
    out = np.empty_like(data, dtype=np.float32)
    c = data.shape[c_axis]
    
    # Normalise data channel-wise
    for ci in range(c):
        c_data = np.take(data, ci, axis=c_axis)
        min_px, max_px = np.percentile(c_data, pth) 
        idx = [slice(None)] * data.ndim # Make slice with data.ndim ellipses...
        idx[c_axis] = ci # ...and replace channel axis with current channel
        out[tuple(idx)] = np.clip((c_data - min_px) / (max_px - min_px + 1e-12), 0, 1)

    # Return 
    return (out * np.iinfo(dtype).max).astype(dtype)