
from pathlib import Path
import re
import itertools
from bioio import BioImage
from bioio_ome_tiff.writers import OmeTiffWriter
import numpy as np


def collect_images(dir_, ftypes=None, in_and=None, in_or=None, out_and=None, out_or=None):
    p = Path(dir_)
    ftypes = ['.tif','.nd2','.czi','.lif'] if ftypes is None else ftypes
    imgs = []
    for item in p.iterdir():
        if item.suffix not in ftypes:
            continue
        if in_or and not any(f in item.name for f in in_or):
            continue
        if in_and and not all(f in item.name for f in in_and):
            continue
        if out_or and any(f in item.name for f in out_or):
            continue
        if out_and and all(f in item.name for f in out_and):
            continue
        imgs.append(item)
    return sorted(imgs)

            
def _make_suffixes(dim, n):
    """
    Generate a filename suffix for a given dimension (e.g., 'Z', 2 returns ['_z000', '_z001']).
    """
    return [f'_{dim.lower()}{str(i).zfill(3)}' for i in range(n)]
    

def _extract_index(dim, string):
    """
    Extract dimension indices from filename (e.g., arguments 'Z' and a string ending in '_z001' returns 1).
    """
    match = re.search(rf'_{dim.lower()}(\d+)', string)
    return int(match.group(1))


def _slice_data(data, frames, channels, planes):
    """
    Slice data according to to the specified frames, channels, and planes.
    """
    # Make a dict with the received slices
    slices_dict = {
        'T': slice(frames[0], frames[1]),
        'C': slice(channels[0], channels[1]),
        'Z': slice(planes[0], planes[1]),
    }

    # Add 'T', 'C', and 'Z' slices and slice(None) for 'X'/'Y' to the list
    slices = [(slices_dict[dim] if dim in slices_dict else slice(None)) for dim in 'TCZYX']
   
    # Return the sliced data
    return data[tuple(slices)]


def split_stack(img, split_dims='C', keep_img=True, tifffile_kwargs={}):
    """
    Split an image stack into Zarr arrays or TIFF files, each file named after the slice it contains.

    Args:
        img (str or Path): Image path.
        split_dims (str): Dimensions to split on ('T', 'C', 'Z', e.g., 'C' or 'TC'). Default 'C'.
        keep_img (bool): Whether to keep the input image after splitting. Default True.

    Returns:
        Path: Path to the generated Zarr group containing split arrays.
    """
    
    valid_dims = {'T', 'Z', 'C'}
    if not all(d in valid_dims for d in split_dims):
        raise ValueError(f"'split_dims' must only contain a combination of 'T', 'Z', C'. Got: '{split_dims}'")

    data = BioImage(img).get_image_data('TCZYX')

    # Get dim sizes
    t, c, z = BioImage(data).dims['T', 'C', 'Z']

    # Make dict with dim letter & size
    suffixes_map = {
            'T': _make_suffixes('T', t),
            'C': _make_suffixes('C', c),
            'Z': _make_suffixes('Z', z),
        }

    # Make a list with all possible suffix combinations
    split_dims = split_dims.upper()
    selected_suffixes = [suffixes_map[dim] for dim in split_dims]
    combined_suffixes = [''.join(combo) for combo in itertools.product(*selected_suffixes)]

    # Make a list for the paths of the split images to be returned
    paths = []

    # Iterate over suffixes, extract slices, and save them as arrays
    for suffix in combined_suffixes:

        # Select slices (frames, channels, and planes) based on the suffix if they are to be split, else select all slices
        t1 = _extract_index('T', suffix) if 'T' in split_dims else 0
        z1 = _extract_index('Z', suffix) if 'Z' in split_dims else 0
        c1 = _extract_index('C', suffix) if 'C' in split_dims else 0
        t2 = t1 + 1 if 'T' in split_dims else t
        z2 = z1 + 1 if 'Z' in split_dims else z
        c2 = c1 + 1 if 'C' in split_dims else c

        # Split stack
        split_data = _slice_data(data, frames=(t1, t2), channels=(c1, c2), planes=(z1, z2))

        # Save split images as TIFF
        p = Path(img)
        tif_path = p.parent / f'{p.stem}{suffix}.tif'
        paths.append(tif_path)
        OmeTiffWriter.save(
            split_data.astype(data.dtype),
            tif_path,
            tifffile_kwargs=tifffile_kwargs
        )
    
    # Optionally delete input image after splitting
    if not keep_img:
        remove_paths(img)

    return paths


def stack_images(imgs, stack_dims='C', keep_imgs=True, tifffile_kwargs={}):
    """
    Stack multiple images or Zarr arrays along specified dimensions.

    Args:
        imgs (str, Path or list/tuple[str] or list/tuple[Path]): List/tuple of images or a Zarr directory.
        stack_dims (str): Dimension letter(s) along which to stack ('T', 'C', 'Z', e.g. 'C' or 'TC').
        keep_imgs (bool): Whether to keep input files. Default True.

    Returns:
        list[Path]: Path to the stacked TIFF file.
    """
    # Optionally mark input images to be deleted
    to_delete = imgs if not keep_imgs else []
    
    # Make dict with image paths & data
    current_imgs = {path : BioImage(path).get_image_data('TZCYX') for path in imgs}

    # Make list for the stack paths to be returned
    paths = []

    for i, dim in enumerate(stack_dims):
        # If this is not the first iteration, mark the previous stacks to be deleted & reset the paths list
        if i > 0:
            to_delete.append([path for path in current_imgs.keys()])
            paths = []

        # Make a dict for the stacks to be created
        stacks = {}  

        # Add paths & data to stack to the dict
        for path, data in current_imgs.items():
            p = Path(path)
            # Set path for the stack, i.e., the image name minus the suffix
            name = re.sub(rf'_{dim.lower()}\d+', '', p.stem)
            new_path = p.parent / f'{name}.tif'
            data = BioImage(p).get_image_data('TCZYX')

            # If the new path is present in the dict, append the data to its list, else add the path and make a new list with the data
            stacks.setdefault(new_path, []).append(data)

        # Make stacks & add them to a dict
        new_imgs = {}
        axis = 'TCZYX'.index(dim)
        for path, _ in stacks.items():
            stacked_data = np.concatenate(stacks[path], axis=axis)
            new_imgs[path] = stacked_data
            OmeTiffWriter.save(
                stacked_data.astype(data.dtype),
                path,
                tifffile_kwargs=tifffile_kwargs
            )

            # If this is the last iteration, add the stack to the list of paths to be returned
            if i == len(stack_dims) - 1:
                paths.append(path)

        # Override current images (either input images or stacks from previous iteration) with new stacks
        current_imgs = new_imgs

    # Delete input and/or intermediate stacks
    remove_paths(to_delete)
    
    return paths


def _flatten(items):
    """
    Flatten a nested list or tuple.
    """
    for item in items:
        if isinstance(item, (list, tuple)):
            yield from _flatten(item)
        else:
            yield item


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
        raise ValueError(f'Input must be a path (str or Path) or a list/tuple of paths')

    if isinstance(paths, (list, tuple)):
        paths = list(_flatten(paths))
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