import argparse
import subprocess
from pathlib import Path
import zarr
import tifffile
from bioio import BioImage
from img_utils import img_utils


def run_dw(img, channels, dw_dir, psf_dir, fluos, scope, mag, z_pixel, iterations=50):
    """
    Deconvolve 4D and 5D images using Deconwolf. Channels and/or frames are split up, deconvolved using the corresponding PSF image, and then stacked back together. Deconvolved images and a maximum intensity projection of each image are stored in a subfolder ('dw').
    
    Args:
        img (str or Path): Path of the input image.
        channels (list[int]): Channels to deconvolve. Order must match that of 'fluos'.
        dw_dir (str or Path): Directory of the deconwolf repository.
        fluos (list[str]): Names of the imaged fluorophores. Order must match that of 'channels'.
        scope (str): Name of the microscope.
        mag (str): Total magnification.
        z_pixel (str): Vertical pixel size.
        iterations (int): Numer of iterations of deconvolution. Default 50.
    """
    p = Path(img)
    
    split_dims = "".join([d for d in 'TC' if BioImage(img).dims[d][0] > 1])
    
    tif_paths = []
    dw_paths = []
    to_delete = []

    # If the image is 4D/5D, split it up and save the slices as plain TIFF
    if len(split_dims) >= 1:
        zarr_dir = img_utils.split_stack(img=p, split_dims=split_dims) # Input should be TZCYX
        groups, arrays = img_utils.unpack_zarr(zarr_dir)
        to_delete.append(groups)
        
        make_tifs = [a for a in arrays for c in channels if str(c).zfill(3) in str(a)]

        for array in make_tifs:
            tif_path = Path(img).with_name(array.stem).with_suffix('.tif')
            tifffile.imwrite(
                tif_path,
                zarr.open_array(array)[:],
                imagej=True,
                metadata={'axes': 'TZCYX'})
            tif_paths.append(tif_path)
            to_delete.append(tif_path)

    # If the image is 3D, save it as a plain TIFF
    else:
        tif_paths = [img_utils.make_tif(img)]
        to_delete.append(tif_paths)
        
    for i, c in enumerate(channels):
        current_tifs = [p for p in tif_paths if f'c{str(c).zfill(3)}' in str(p)]
        for tif_path in current_tifs:
            p = Path(tif_path)
            data = BioImage(p).get_image_data('TZCYX')
            dw_path = dw_dir.joinpath(f"{p.stem}_dw.tif")
            dw_paths.append(dw_path)
            
            psf_path = f"{psf_dir}/{scope}_{mag}x_z{z_pixel}_{fluos[i]}.tif"

            params = [
                "dw",
                "--iter", str(iterations),
                "--gpu",
                "--out", str(dw_path),
                str(tif_path),
                str(psf_path)
            ]
            
            subprocess.run(params, check=True)

    dw_stacks = img_utils.stack_images(
        imgs=dw_paths,
        stack_dims=split_dims,
        tif=True,
        keep_imgs=False
    )

    for stack in dw_stacks:
        p = Path(stack)
        img = BioImage(stack)
        
        tif_path = p.parent / f"{p.stem}_max.tif"
        
        data = img.get_image_data('TZCYX')
        proj_data = img_utils.project_data(data)
        
        tifffile.imwrite(
            tif_path,
            proj_data.astype(proj_data.dtype),
            imagej=True,
            metadata={'axes': 'TZCYX'}
        )

    img_utils.remove_paths(to_delete)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--imgs", nargs="+", required=True, help="Directory with images to deconvolve")
    parser.add_argument("-c", "--channels", nargs="+", required=True, help="List of channels to deconvolve")
    parser.add_argument("-p", "--psf_dir", required=True, help="Directory with PSF images")
    parser.add_argument("-f", "--fluos", nargs="+", required=True, help="List of used fluorophores (required to locate PSF)")
    parser.add_argument("-s", "--scope", required=True, help="Name of the microscope (required to locate PSF)")
    parser.add_argument("-m", "--mag", required=True, help="Magnification of the objective (required to locate PSF)")
    parser.add_argument("-z", "--z_pixel", required=True, help="Vertical pixel size in nm (required to locate PSF)")
    parser.add_argument("-n", "--iterations", type=int, required=True, help="Number of iterations of deconvolution")
    return parser.parse_args()


def main():
    args = get_args()
    imgs = args.imgs
    channels = [int(i) for i in args.channels]
    scope = args.scope
    mag = args.mag
    z_pixel = args.z_pixel
    fluos = args.fluos
    psf_dir = args.psf_dir
    iterations = args.iterations

    dw_dir = Path(imgs[0]).parent / 'dw'
    dw_dir.mkdir(parents=True, exist_ok=True)

    for img in imgs:
        print(f'Deconvolving image {img}')
        run_dw(
            img=img,
            channels=channels,
            psf_dir=psf_dir,
            fluos=fluos,
            scope=scope,
            mag=mag,
            z_pixel=z_pixel,
            iterations=iterations,
            dw_dir=dw_dir
        )


if __name__=='__main__':
    main()
