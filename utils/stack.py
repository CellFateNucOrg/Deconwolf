
from pathlib import Path
import re
import itertools
import zarr
from bioio import BioImage
from bioio_ome_tiff.writers import OmeTiffWriter

# import sys
# sys.append('..')
from utils.io import remove_paths, unpack_zarr


def _make_suffixes(dim, n):
    """
    Generate a filename suffix for a given dimension.
    """
    return [f'_{dim.lower()}{str(i).zfill(3)}' for i in range(n)]
    

def _extract_index(dim, suffix):
    """
    Extract dimension indices from filename.
    """
    match = re.search(f'_{dim.lower()}(\\d+)', suffix)
    return int(match.group(1))


def _parse_suffix(filename):
    """
    Maps dimension letters to indices (e.g., '_t000_c001' returns {'T': 0, 'C': 1}).
    """
    matches = re.findall(r'_([tcz])(\d+)', filename.lower())
    return {dim.upper(): int(idx) for dim, idx in matches}


def _make_slices(data, frames, channels, planes):
    """
    Slice data according to dims.
    """
    index_map = {
        'T': slice(frames[0], frames[1]),
        'C': slice(channels[0], channels[1]),
        'Z': slice(planes[0], planes[1]),
    }

    slices = []

    for d in 'TCZYX':
        if d in index_map:
            slices.append(index_map[d])
        else:
            slices.append(slice(None))
    
    return data[tuple(slices)]


def _do_stack(array_list, dim, zarr_dir):
    """
    Stack a list of arrays along a specified dimension.
    """
    # Get axis along which to stack
    axis = 'TCZYX'.index(dim)
    
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


def split_stack(img, split_dims='C', tif=False, keep_img=True):
    """
    Split an image stack into Zarr arrays or TIFF files, each file named after the slice it contains.

    Args:
        img (str or Path): Image or Zarr directory.
        split_dims (str): Dimensions to split on ('T', 'C', 'Z', e.g., 'C' or 'TC'). Default 'C'.
        tif (bool): Whether to store the images as TIFF files. Default True.
        keep_img (bool): Whether to keep the input image after splitting. Default False.

    Returns:
        Path: Path to the generated Zarr group containing split arrays.
    """
    
    if not (isinstance(img, (str, Path))):
        raise ValueError(f'Input must be a Zarr or TIFF path (str or Path), or a list/tuple of paths.')
    valid_dims = {'T', 'Z', 'C'}
    if not all(d in valid_dims for d in split_dims):
        raise ValueError(f"'split_dims' must only contain a combination of 'T', 'Z', C'. Got: '{split_dims}'")

    p = Path(img)
    filename = p.stem
    split_dims = split_dims.upper()

    # Load image data depending on input format
    if p.suffix == '.zarr':
        _, arrays = unpack_zarr(img)
        data = zarr.open_array(arrays[0])
    else:
        data = BioImage(img).get_image_data('TCZYX')

    # Get dimensions
    t = BioImage(data).dims['T'][0]
    c = BioImage(data).dims['C'][0]
    z = BioImage(data).dims['Z'][0]

    suffixes_map = {
            'T': _make_suffixes('T', t),
            'C': _make_suffixes('C', c),
            'Z': _make_suffixes('Z', z),
        }

    # Create all combinations of suffixes for the selected dimensions
    selected_suffixes = [suffixes_map[dim] for dim in split_dims if dim in suffixes_map]
    combined_suffixes = [''.join(combo) for combo in itertools.product(*selected_suffixes)]

    # Create output Zarr group to store split arrays
    zarr_dir = p.parent / f'{filename}_{split_dims.lower()}.zarr'
    root = zarr.create_group(store=zarr_dir, overwrite=True)

    # Iterate over suffixes, extract slices, and save them as arrays
    for suffix in combined_suffixes:

        array_name = f'{filename}{suffix}'

        t1 = _extract_index('T', suffix) if 'T' in split_dims else 0
        z1 = _extract_index('Z', suffix) if 'Z' in split_dims else 0
        c1 = _extract_index('C', suffix) if 'C' in split_dims else 0

        t2 = t1 + 1 if 'T' in split_dims else t
        z2 = z1 + 1 if 'Z' in split_dims else z
        c2 = c1 + 1 if 'C' in split_dims else c

        array_data = _make_slices(data, frames=(t1, t2), channels=(c1, c2), planes=(z1, z2))

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

            OmeTiffWriter.save(data.astype(data.dtype), tif_path)

        remove_paths(zarr_dir)

        return tif_paths
    
    else:
        return zarr_dir


def stack_images(imgs, stack_dims='C', tif=False, keep_imgs=True):
    """
    Stack multiple images or Zarr arrays along specified dimensions.

    Args:
        imgs (str, Path or list/tuple[str] or list/tuple[Path]): List/tuple of images or a Zarr directory.
        stack_dims (str): Dimension letter(s) along which to stack ('T', 'C', 'Z', e.g. 'C' or 'TC').
        tif (bool): Whether to save the stack as a TIFF file. If false (default), stack is stored in a Zarr directory.
        keep_imgs (bool): Whether to keep input files. Default True.

    Returns:
        list[Path]: Path to the stacked Zarr arrays or TIFF file.
    """

    # If input is Zarr, collect the array paths
    if isinstance(imgs, (str, Path)) and Path(imgs).suffix == '.zarr':
        _, arrays = unpack_zarr(imgs)
        to_delete = [imgs] if not keep_imgs else []
        parent_dir = Path(imgs).parent

    # If input is a list of images, convert them to Zarr and collect the array paths
    elif isinstance(imgs, (list, tuple)):
        if not imgs:
            raise ValueError('Input list/tuple is empty.')
            
        temp_zarr = Path(imgs[0]).with_name('temp.zarr')
        root = zarr.create_group(store=temp_zarr, overwrite=True)
        
        for img in imgs:
            name = Path(img).stem
            data = BioImage(img).get_image_data('TCZYX')
            root.create_array(name=name, data=data, overwrite=True)
            
        _, arrays = unpack_zarr(temp_zarr)
        
        parent_dir = (imgs[0]).parent
         
        to_delete = [temp_zarr] + (imgs if not keep_imgs else [])
        
    else:
        raise ValueError(f'Input must be a Zarr directory or a list/tuple of images.')
    
    valid_dims = {'T', 'C', 'Z'}
    if not all(d in valid_dims for d in stack_dims.upper()):
        raise ValueError(f"Invalid stacking stack_dims '{stack_dims}'. Must be a combination of 'T', 'C', 'Z'.")
    
    current_arrays = arrays
    for i, dim in enumerate(stack_dims):
        
        # Group arrays by name minus dim in the suffix
        groups = {}  
        for path in current_arrays:
            name = re.sub(f'_{dim.lower()}\\d+', '', path.stem)
            groups.setdefault(name, []).append(path)
            
        new_arrays = []
        
        for name, group in groups.items():
            # Sort arrays along the current dimenson
            sorted_group = sorted(group, key=lambda p: _parse_suffix(p.stem)[dim])
            zarr_dir = parent_dir / name
            # Stack along the current dimension and add to new_arrays
            new_arrays.append(_do_stack(sorted_group, dim, zarr_dir))

        # Delete intermediate arrays after first iteration
        if i > 0:
            remove_paths(current_arrays)

        current_arrays = new_arrays

    remove_paths(to_delete)

    if tif:
        tif_paths = []
        
        for array in current_arrays:
            data = zarr.open_array(array)[:]
            tif_path = array.with_name(array.stem + '.tif')
            OmeTiffWriter.save(data.astype(data.dtype), tif_path)
            tif_paths.append(tif_path)
            
        remove_paths(current_arrays)
        
        return tif_paths
        
    else:
        return current_arrays
