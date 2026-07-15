def unpack_zarr(zarr_dir):
    """
    Extract groups and arrays from a Zarr directory.
    """
    from pathlib import Path
    import zarr
    import json
    
    if not (isinstance(zarr_dir, (str, Path)) and Path(zarr_dir).suffix == '.zarr'):
        raise ValueError(f'zarr_dir must be a Zarr directory')
    
    groups, arrays = [], []

    for meta in Path(zarr_dir).rglob('zarr.json'):
        with open(meta) as f:
            node_type = json.load(f).get('node_type')
        if node_type == 'group':
            groups.append(meta.parent)
        elif node_type == 'array':
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
        raise ValueError(f'Input must be a path (str or Path) or a list/tuple of paths')

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
