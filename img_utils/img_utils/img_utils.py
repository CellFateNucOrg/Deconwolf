import numpy as np


def normalise_data(data, channel_axis, mode='channel', pth=(1, 99), dtype=None):
    """
    Normalise image intensities based on percentile range.

    Args:
        data (numpy.ndarray): Data to normalise.
        channel_axis (int): Axis corresponding to channels.
        mode ('channel' or 'global'): Whether to normalise channel-wise (default) or globally. 
        pth (list[int] or tuple[int, int]): Percentiles for normalization (min, max).
        dtype (np.dtype, optional): Output type (default np.uint16).

    Returns:
        np.ndarray: Normalized array, same shape as input.
    """
    if not isinstance(data, np.ndarray):
        raise ValueError(f"Input data must be a numpy array.")
    if not pth[1] > pth[0]:
        raise ValueError(f"Maximum percentile must be greater than minimum percentile.")
    
    out = np.empty_like(data, dtype=np.float32)
    
    n_channels = data.shape[channel_axis]

    if mode == 'channel':
        for c in range(n_channels):
            c_data = np.take(data, c, axis=channel_axis)
            min_px, max_px = np.percentile(c_data, pth)
            idx = [slice(None)] * data.ndim
            idx[channel_axis] = c
            out[tuple(idx)] = np.clip((c_data - min_px) / (max_px - min_px + 1e-12), 0, 1)
    elif mode == 'global':
        min_px, max_px = np.percentile(data, pth)
        out = np.clip((data - min_px) / (max_px - min_px + 1e-12), 0, 1)

    if dtype is None:
        return out
    else:
        return (out * np.iinfo(dtype).max).astype(dtype)


def order_dims(data, dims, out_dims):
    """
    Args:
        data (np.ndarray): Input data.
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X', e.g., 'TZCYX').
        out_dims (str): Dimension order in output data ('T', 'Z', 'C', 'Y', 'X', e.g., 'TZCYX').

    Returns:
        np.ndarray: Transposed data.
    """
    if sorted(dims) != sorted(out_dims):
        raise ValueError("dims and out_dims must contain the same dimension labels.")

    out_axes = [dims.index(dim) for dim in out_dims]

    return np.transpose(data, axes=out_axes)


def shift_data(data, dim='C', dims='TZCYX', indices=0, shift=(0, 0), pad=False):
    """
    Shift image slices along a specified dimension by given pixel offset with optional padding.

    Args:
        data (numpy.ndarray): Data to shift.
        dim (str): Dimension letter to shift over ('T', 'Z', 'C', 'Y', 'X').
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        indices (int, list[int] or tuple[int]): Indices along dim to apply the shift.
        shift (tuple[int, int]): (x_shift, y_shift) pixel shift values.
        pad (bool): If True, pad with zeros to keep original size; if False, crop instead.

    Returns:
        Path: Path to shifted image saved to disk.
    """
    if not isinstance(data, np.ndarray):
        raise ValueError(f"Input data must be a numpy array.")
    if dim not in 'TCZYX':
        raise ValueError(f"Invalid dim '{dim}'. Must be one of 'T', 'Z', 'C', 'Y', 'X'.")
    if not (isinstance(indices, int) or all(isinstance(i, int) for i in indices)):
        raise ValueError(f"'indices' must be an int or a sequence of ints, got: {indices}")
    if not isinstance(shift, tuple) or len(shift) != 2 or not all(isinstance(s, int) for s in shift):
        raise ValueError(f"'shift' must be a tuple of two integers, got: {shift}")
    if not isinstance(pad, bool):
        raise ValueError(f"'pad' must be a boolean, got: {pad}")

    t, c, z, y, x = data.shape
    axis = dims.index(dim)
    dim_size = data.shape[axis]

    indices = [indices] if isinstance(indices, int) else list(indices)
    x_shift, y_shift = shift

    # Prepare output array shape depending on padding
    if pad:
        shifted_data = np.zeros_like(data)
    else:
        shifted_data = np.empty((t, z, c, y - abs(y_shift), x - abs(x_shift)), dtype=data.dtype)

    # Shift only specified indices, copy others unchanged
    for i in range(dim_size):
        t1 = i if dim == 'T' else 0
        t2 = i + 1 if dim == 'T' else t
        z1 = i if dim == 'Z' else 0
        z2 = i + 1 if dim == 'Z' else z
        c1 = i if dim == 'C' else 0
        c2 = i + 1 if dim == 'C' else c

        if i in indices:
            # Calculate source slice coordinates depending on shift direction
            raw_y1 = abs(y_shift) if y_shift < 0 else 0
            raw_y2 = y if y_shift < 0 else y - abs(y_shift)
            raw_x1 = abs(x_shift) if x_shift < 0 else 0
            raw_x2 = x if x_shift < 0 else x - abs(x_shift)
        else:
            raw_y1 = 0 if y_shift < 0 else abs(y_shift)
            raw_y2 = y - abs(y_shift) if y_shift < 0 else y
            raw_x1 = 0 if x_shift < 0 else abs(x_shift)
            raw_x2 = x - abs(x_shift) if x_shift < 0 else x

        shifted_y1 = 0 if y_shift < 0 else abs(y_shift)
        shifted_y2 = y - abs(y_shift) if y_shift < 0 else y
        shifted_x1 = 0 if x_shift < 0 else abs(x_shift)
        shifted_x2 = x - abs(x_shift) if x_shift < 0 else x

        if pad:
            shifted_data[t1:t2, z1:z2, c1:c2, shifted_y1:shifted_y2, shifted_x1:shifted_x2] = \
                data[t1:t2, z1:z2, c1:c2, raw_y1:raw_y2, raw_x1:raw_x2]
        else:
            shifted_data[t1:t2, z1:z2, c1:c2, ...] = data[t1:t2, z1:z2, c1:c2, raw_y1:raw_y2, raw_x1:raw_x2]

    return shifted_data


def project_data(data, proj_dim='Z', dims='TZCYX', slices=None, proj='max'):
    """
    Project image along the Z axis using specified projection method.

    Args:
        data (numpy.ndarray): Data to project.
        proj_dim (str): proj_dimension letter along which to stack ('T', 'C', 'Z'). Default 'C'.
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        slices (list[ints] or tuple[ints]): Image planes to project (default all).
        proj (str): Projection method ('max', 'min', 'mean', 'median', 'sum'). Default 'max'.

    Returns:
        Path: Path to projected image saved to disk.
    """
    if not isinstance(data, np.ndarray):
        raise ValueError(f"Input data must be a numpy array.")
    valid_proj = {'max', 'min', 'mean', 'median', 'sum'}
    if proj not in valid_proj:
        raise ValueError(f"Invalid proj '{proj}'. Must be one of {valid_proj}.")
    if proj_dim not in 'TCZ':
        raise ValueError(f"Invalid proj_dim '{proj_dim}'. Must be one of 'T', 'C', 'Z'")
    if slices:
        if not all(isinstance(s, int) for s in slices):
            raise ValueError(f"All slices must be integers.")
        if min(slices) < 0 or max(slices) >= data.shape[2]:
            raise ValueError(f"Slices indices must be in range [0, {data.shape[2] - 1}].")

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


def make_rgb(data, channels, channel_axis=1, mode='global', pth=(1, 99), weights=[(1, 0, 0), (0, 1, 0), (0, 0, 1)]):
    """
    Merge channels into a single RGB array.

    Args:
        data (numpy.ndarray): Input data of shape (t, z, c, y, x).
        channels(int, list[ints] or tuple[ints]): Channels to merge.
        channel_axis(int): Index of channel axis.
        pth (tuple[int, int]): Percentile range for normalization.
        weights (list[tuple]): RGB weights for each channel.

    Returns:
        numpy.ndarray: Merged RGB image data of shape (t, z, 1, y, x, 3).
    """
    if not isinstance(data, np.ndarray) or data.ndim != 5:
        raise ValueError(f"Input data must be a 5D numpy array with shape (t, z, c, y, x).")
    if not len(channels) == len(weights):
        raise ValueError(f"'channels' ({len(channels)}) and 'weights' ({len(colors)}) must have the same size")
    
    data = data[:, :, channels, ...]
    t, z, _, y, x = data.shape

    # Normalise data
    norm_data = normalise_data(data, channel_axis=channel_axis, mode=mode, pth=pth, dtype=None)
    # Make array with an extra dimension for RGB values
    rgb_data = np.zeros((t, z, 1, y, x, 3), dtype=np.float32)

    for i, weight in enumerate(weights):
        # Add color-weighted channel ('norm_data' broadcast to 'rgb_data')
        for rgb_i in range(3):
            rgb_data[..., rgb_i] += norm_data[:, i] * weight[rgb_i]
    
    # Ensure values stay in [0, 1]
    return np.clip(rgb_data, 0, 1)


def make_tif(path, imagej=True, axes='TZCYX'):
    """
    Convert an image to plain TIFF.

    Args:
        path (str or Path): Path of input image.
        imagej (bool): Whether to save as ImageJ hyperstack compatible TIFF. Default True.
        axes (str): Dimension order ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'. Also defaults to 'TZCYX' if imagej=True.
    """
    from pathlib import Path
    import tifffile
    from bioio import BioImage

    axes = 'TZCYX' if imagej == True else axes
    
    path = Path(path)
    tif_path = path.parent / f"{path.stem}.tif"
    plain_tif_path = path.parent / f"{path.stem}_plain.tif"

    if path.suffix.lower() in {".tif", ".tiff"}:
        with tifffile.TiffFile(path) as tif:
            if tif.is_ome or tif.is_bigtiff:
                data = tif.asarray()
                
                tifffile.imwrite(
                    plain_tif_path,
                    data.astype(data.dtype),
                    imagej=imagej,
                    metadata={'axes': axes},
                )
                
                return plain_tif_path

        return path

    else:
        img = BioImage(path)
        data = img.data
        tifffile.imwrite(
            plain_tif_path,
            data.astype(data.dtype),
            imagej=imagej,
            metadata={'axes': axes},
        )
        
        return tif_path


def unpack_zarr(zarr_dir):
    """
    Extract groups and arrays from a Zarr directory.
    """
    from pathlib import Path
    import zarr
    import json
    
    if not (isinstance(zarr_dir, (str, Path)) and Path(zarr_dir).suffix == '.zarr'):
        raise ValueError(f"zarr_dir must be a Zarr directory")
    
    groups, arrays = [], []

    for meta in Path(zarr_dir).rglob("zarr.json"):
        with open(meta) as f:
            node_type = json.load(f).get("node_type")
        if node_type == "group":
            groups.append(meta.parent)
        elif node_type == "array":
            arrays.append(meta.parent)

    return groups, arrays


def remove_paths(paths):
    """
    Delete files or directories; silently skip non-existent paths.

    Args:
        paths (str, Path, list[str], list[Path], tuple[str] or tuple[Path]): List/tuple of image paths or a single image path.
    """
    from os import remove, PathLike
    from pathlib import Path
    import shutil
    
    if not isinstance(paths, (str, PathLike, list, tuple)):
        raise ValueError(f"Input must be a path (str or Path) or a list/tuple of paths")

    def flatten(items):
        """
        Flatten a nested list or tuple.
        """
        for item in items:
            if isinstance(item, (list, tuple)):
                yield from flatten(item)
            else:
                yield item

    if isinstance(paths, (list, tuple)):
        paths = list(flatten(paths))
    else:
        paths = [paths]

    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink()


def split_stack(img, split_dims='C', dims='TZCYX', out_dims='TZCYX', tif=False, keep_img=True):
    """
    Split an image stack into Zarr arrays or TIFF files, each file named after the slice it contains.

    Args:
        img (str or Path): Image or Zarr directory.
        split_dims (str): Dimensions to split on ('T', 'C', 'Z', e.g., 'C' or 'TC'). Default 'C'.
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        out_dims (str): Dimension order in output data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        tif (bool): Whether to store the images as TIFF files. Default True.
        keep_img (bool): Whether to keep the input image after splitting. Default False.

    Returns:
        Path: Path to the generated Zarr group containing split arrays.
    """
    from pathlib import Path
    import re
    import itertools
    import zarr
    from bioio import BioImage
    import bioio_tifffile, bioio_nd2, bioio_czi, bioio_lif, tifffile
    
    if not (isinstance(img, (str, Path))):
        raise ValueError(f"Input must be a Zarr or TIFF path (str or Path), or a list/tuple of paths.")
    valid_dims = {'T', 'Z', 'C'}
    if not all(d in valid_dims for d in split_dims):
        raise ValueError(f"'split_dims' must only contain a combination of 'T', 'Z', C'. Got: '{split_dims}'")
    if sorted(dims) != sorted('TZCYX'):
        raise ValueError("dims must be a combination of ('T', 'Z', 'C', 'Y', 'X').")

    p = Path(img)
    filename = p.stem
    split_dims = split_dims.upper()

    # Load image data depending on input format
    if p.suffix == '.zarr':
        _, arrays = unpack_zarr(img)
        data = zarr.open_array(arrays[0])
    else:
        data = BioImage(img).get_image_data(dims)

    # Reorder dims if necessary
    if dims != out_dims:
        data = order_dims(data, dims, out_dims)

    # Get dimensions
    t = data.shape[dims.upper().index('T')]
    c = data.shape[dims.upper().index('C')]
    z = data.shape[dims.upper().index('Z')]

    def make_suffixes(dim, n):
        """
        Generate a filename suffix for a given dimension.
        """
        return [f"_{dim.lower()}{str(i).zfill(3)}" for i in range(n)]

    suffixes_map = {
        'T': make_suffixes('T', t),
        'C': make_suffixes('C', c),
        'Z': make_suffixes('Z', z),
    }

    # Create all combinations of suffixes for the selected dimensions
    selected_suffixes = [suffixes_map[dim] for dim in split_dims if dim in suffixes_map]
    combined_suffixes = [''.join(combo) for combo in itertools.product(*selected_suffixes)]

    # Create output Zarr group to store split arrays
    zarr_dir = p.parent / f"{filename}_{split_dims.lower()}.zarr"
    root = zarr.create_group(store=zarr_dir, overwrite=True)

    def extract_index(dim, suffix):
        """
        Extract dimension indices from filename.
        """
        match = re.search(f"_{dim.lower()}(\\d+)", suffix)
        return int(match.group(1))

    def make_slices(data, dims, t1, t2, z1, z2, c1, c2):
        """
        Slice data depending according to dims.
        """
        index_map = {
            'T': slice(t1, t2),
            'C': slice(c1, c2),
            'Z': slice(z1, z2),
        }

        slices = []

        for d in dims:
            if d in index_map:
                slices.append(index_map[d])
            else:
                slices.append(slice(None))

        return data[tuple(slices)]

    # Iterate over suffixes, extract slices, and save them as arrays
    for suffix in combined_suffixes:

        array_name = f"{filename}{suffix}"

        t1 = extract_index('T', suffix) if 'T' in split_dims else 0
        z1 = extract_index('Z', suffix) if 'Z' in split_dims else 0
        c1 = extract_index('C', suffix) if 'C' in split_dims else 0

        t2 = t1 + 1 if 'T' in split_dims else t
        z2 = z1 + 1 if 'Z' in split_dims else z
        c2 = c1 + 1 if 'C' in split_dims else c

        array_data = make_slices(data, dims, t1, t2, z1, z2, c1, c2)

        root.create_array(
            name=array_name,
            data=array_data,
            overwrite=True
        )

    # Optionally delete input image after splitting
    if not keep_img:
        remove_paths(img)

    # Optionally store output as TIFF
    if tif:
        tif_paths = []

        _, arrays = unpack_zarr(zarr_dir)
        
        for array in arrays:
            data = zarr.open_array(array)[:]
            
            tif_path = p.parent / Path(array.stem).with_suffix('.tif')
            tif_paths.append(tif_path)

            tifffile.imwrite(
                tif_path,
                data.astype(data.dtype),
                imagej=True,
                metadata={'axes': out_dims}
            )

        remove_paths(zarr_dir)

        return tif_paths
    
    else:
        return zarr_dir


def stack_images(imgs, stack_dims='C', dims='TZCYX', out_dims='TZCYX', tif=False, keep_imgs=True):
    """
    Stack multiple images or Zarr arrays along specified dimensions.

    Args:
        imgs (str, Path or list/tuple[str] or list/tuple[Path]): List/tuple of images or a Zarr directory.
        stack_dims (str): Dimension letter(s) along which to stack ('T', 'C', 'Z', e.g. 'C' or 'TC').
        dims (str): Dimension order in input data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        out_dims (str): Dimension order in output data ('T', 'Z', 'C', 'Y', 'X'). Default 'TZCYX'.
        tif (bool): Whether to save the stack as a TIFF file. If false (default), stack is stored in a Zarr directory.
        keep_imgs (bool): Whether to keep input files. Default True.

    Returns:
        list[Path]: Path to the stacked Zarr arrays or TIFF file.
    """
    from pathlib import Path
    import re
    import zarr
    from bioio import BioImage
    import bioio_tifffile, bioio_nd2, bioio_czi, bioio_lif, tifffile

    # If input is Zarr, collect the array paths
    if isinstance(imgs, (str, Path)) and Path(imgs).suffix == '.zarr':
        _, arrays = unpack_zarr(imgs)
        to_delete = [imgs] if not keep_imgs else []
        parent_dir = Path(imgs).parent

    # If input is a list of images, convert them to Zarr and collect the array paths
    elif isinstance(imgs, (list, tuple)):
        
        if not imgs:
            raise ValueError("Input list/tuple is empty.")
        
        temp_zarr = Path(imgs[0]).with_name('temp.zarr')
        root = zarr.create_group(store=temp_zarr, overwrite=True)

        for img in imgs:
            name = Path(img).stem
            data = BioImage(img).get_image_data(dims)
            root.create_array(name=name, data=data, overwrite=True)

        _, arrays = unpack_zarr(temp_zarr)
        
        parent_dir = (imgs[0]).parent

        to_delete = [temp_zarr] + (imgs if not keep_imgs else [])

    else:
        raise ValueError(f"Input must be a Zarr directory or a list/tuple of images.")
    
    valid_dims = {'T', 'C', 'Z'}
    if not all(d in valid_dims for d in stack_dims.upper()):
        raise ValueError(f"Invalid stacking stack_dims '{stack_dims}'. Must be a combination of 'T', 'C', 'Z'.")

    def parse_suffix(filename):
        """
        Maps dimension letters to indices (e.g., '_t000_c001' returns {'T': 0, 'C': 1}).
        """
        matches = re.findall(r'_([tcz])(\d+)', filename.lower())
        return {dim.upper(): int(idx) for dim, idx in matches}

    def do_stack(array_list, dim, zarr_dir):
        """
        Stack a list of arrays along a specified dimension.
        """
        # Get axis along which to stack
        axis = dims.index(dim)

        # Load arrays
        datas = [zarr.open_array(store=str(a.parent), path=a.name)[:] for a in array_list]

        # Compute output shape
        out_shape = list(datas[0].shape)
        out_shape[axis] = sum(d.shape[axis] for d in datas)

        # Create output array
        out = zarr.create_array(
            store=zarr_dir,
            shape=out_shape,
            dtype=datas[0].dtype,
            overwrite=True,
        )

        # Fill output array
        idx = 0
        
        for d in datas:
            slices = [slice(None)] * len(out_shape)
            slices[axis] = slice(idx, idx + d.shape[axis])
            out[tuple(slices)] = d
            idx += d.shape[axis]

        return zarr_dir
    
    current_arrays = arrays

    for i, dim in enumerate(stack_dims):
        # Group arrays by name minus dim in the suffix
        groups = {}
        
        for path in current_arrays:
            name = re.sub(f"_{dim.lower()}\\d+", "", path.stem)
            groups.setdefault(name, []).append(path)

        new_arrays = []
        
        for name, group in groups.items():
            # Sort arrays along the current dimenson
            sorted_group = sorted(group, key=lambda p: parse_suffix(p.stem)[dim])
            zarr_dir = parent_dir / name
            # Stack along the current dimension and add to new_arrays
            new_arrays.append(do_stack(sorted_group, dim, zarr_dir))

        # Delete intermediate arrays after first iteration
        if i > 0:
            remove_paths(current_arrays)

        current_arrays = new_arrays

    remove_paths(to_delete)

    if tif:
        tif_paths = []

        for array in current_arrays:
            data = zarr.open_array(array)[:]

            if dims != out_dims:
                order_dims(data, dims, out_dims)

            tif_path = array.with_name(array.stem + '.tif')
            tifffile.imwrite(
                tif_path,
                data.astype(data.dtype),
                imagej=True,
                metadata={'axes': out_dims}
            )

            tif_paths.append(tif_path)

        remove_paths(current_arrays)

        return tif_paths
        
    else:
        return current_arrays