import numpy as np


def project_data(data, proj_dim='Z', dims='TCZYX', slices=None, proj='max'):
    """
    Project image along the Z axis using specified projection method.

    Args:
        data (numpy.ndarray): Data to project.
        proj_dim (str): proj_dimension letter along which to stack ('T', 'C', 'Z'). Default 'C'.
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X'). Default 'TCZYX'.
        slices (list[ints] or tuple[ints]): Image planes to project (default all).
        proj (str): Projection method ('max', 'min', 'mean', 'median', 'sum'). Default 'max'.

    Returns:
        Path: Path to projected image saved to disk.
    """
    if not isinstance(data, np.ndarray):
        raise ValueError(f'Input data must be a numpy array.')
    valid_proj = {'max', 'min', 'mean', 'median', 'sum'}
    if proj not in valid_proj:
        raise ValueError(f"Invalid proj '{proj}'. Must be one of {valid_proj}.")
    if proj_dim not in 'TCZ':
        raise ValueError(f"Invalid proj_dim '{proj_dim}'. Must be one of 'T', 'C', 'Z'")
    if slices:
        if not all(isinstance(s, int) for s in slices):
            raise ValueError(f'All slices must be integers.')
        if min(slices) < 0 or max(slices) >= data.shape[2]:
            raise ValueError(f'Slices indices must be in range [0, {data.shape[2] - 1}].')

    axis = dims.index(proj_dim)
    data = data.take(axis=axis, indices=slices) if slices else data
    
    proj_funcs = {
        'min': data.min,
        'max': data.max,
        'mean': data.mean,
        'median': np.median,
        'sum': data.sum,
    }
    proj_data = proj_funcs[proj](axis=axis, keepdims=True)
    
    return proj_data