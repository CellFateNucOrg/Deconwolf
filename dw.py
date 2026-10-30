import argparse
import subprocess
from pathlib import Path
from bioio import BioImage
from bioio_ome_tiff.writers import OmeTiffWriter
from utils import  collect_images, remove_paths, split_stack, stack_images


def run_dw(
    img,
    channels,
    dw_dir,
    psf_dir,
    fluos,
    scope,
    mag,
    z_pixel,
    scale=False,
    tiles=False,
    iterations=50,
):
    """
    Deconvolve 4D and 5D images using Deconwolf. Channels and/or frames are split up, deconvolved using the corresponding PSF image, and then stacked back together. Deconvolved images and a maximum intensity projection of each image are stored in a subfolder named 'dw'.
    
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
    read_img = BioImage(img)
    if read_img.dims['Z'][0] > 1:
        # Make a list for the deconvolved slices to stack later
        dw_slice_paths = []
        
        # Make a list for input and/or intermediate files to delete late
        to_delete = []

        # Split channels and/or frames (3D images are treated as multi-channel)
        split_dims = 'TC' if read_img.dims['T'][0] > 1 else 'C'
        slice_paths = split_stack(
            img=img,
            split_dims=split_dims,
            tifffile_kwargs={"compression": 0}
        )
        to_delete.append(slice_paths)

        # Loop over channels
        for i, channel in enumerate(channels):
            # Deconovlve slices for current channel
            channel_slices = [p for p in slice_paths if f'c{str(channel).zfill(3)}' in str(p)]
            for slice_path in channel_slices:
                # Set PSF path
                psf_path = f'{psf_dir}/{scope}_{mag}x_z{z_pixel}_{fluos[i]}.tif'

                # Set path for the deconvolved image
                dw_slice_path = dw_dir.joinpath(f"{slice_path.stem}_dw.tif")
                dw_slice_paths.append(dw_slice_path)

                # Set deconwolf params
                params = [
                    "dw",
                    "--iter", str(iterations),
                    "--gpu",
                    "--out", str(dw_slice_path),
                    str(slice_path),
                    str(psf_path)
                ]
                if tiles > 0:
                    params += ["--tilesize", str(tiles)]
                if not scale:
                    params += ["--scaling", "1"] # Set scaling to 1 if scale == False

                # Run deconwolf 
                subprocess.run(params, check=True)

        # Stack deconvolved images
        dw_stacks = stack_images(
            imgs=dw_slice_paths,
            stack_dims=split_dims,
            keep_imgs=False,
        )

        # Project the deconvolved image
        for path in dw_stacks:
            img = BioImage(path)
            data = img.get_image_data('TCZYX')
            proj_data = data.max(axis=2, keepdims=True)
            proj_path = path.parent / f"{path.stem}_max.tif"
            OmeTiffWriter.save(
                proj_data.astype(data.dtype),
                proj_path,
                dim_order='TCZYX'
            )

        # Delete intermediate files
        remove_paths(to_delete)
    
    # Skip single-plane images
    else:
        print(f'Skipping image {img.name} because it is not 3D.')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src_dir", required=True, help="Directory with images to deconvolve")
    parser.add_argument("--filter_out", nargs="+", required=True, help="Expression(s) to filter out specific files")
    parser.add_argument("--channels", nargs="+", required=True, help="List of channels to deconvolve")
    parser.add_argument("--psf_dir", required=True, help="Directory with PSF images")
    parser.add_argument("--fluos", nargs="+", required=True, help="List of used fluorophores (required to locate PSF)")
    parser.add_argument("--scope", required=True, help="Name of the microscope (required to locate PSF)")
    parser.add_argument("--mag", required=True, help="Magnification of the objective (required to locate PSF)")
    parser.add_argument("--z_pixel", required=True, help="Vertical pixel size in nm (required to locate PSF)")
    parser.add_argument("--tiles", type=int, required=True, help="Wheter tile the image before deconvolution")
    parser.add_argument("--scale", required=True, help="Wheter to scale the deconvolved image to the full bit depth")
    parser.add_argument("--iterations", type=int, required=True, help="Number of iterations of deconvolution")
    parser.add_argument("--skip_old", required=True, help="Whether to skip previously deconvolved images or override them.")
    return parser.parse_args()


def main():
    args = get_args()
    src_dir = args.src_dir
    filter_out = [s for s in args.filter_out]
    channels = [int(c) for c in args.channels]
    scope = args.scope
    mag = args.mag
    z_pixel = args.z_pixel
    fluos = args.fluos
    psf_dir = args.psf_dir
    tiles = args.tiles
    scale = args.scale.lower() in ('1', 'true')
    iterations = args.iterations
    skip_old = args.skip_old.lower() in ('1', 'true')

    # Collect images
    imgs = collect_images(src_dir, out_or=filter_out)

    # Make dir for deconvolved images
    dw_dir = Path(imgs[0]).parent / 'dw'
    dw_dir.mkdir(parents=True, exist_ok=True)

    # Loop over images
    for img in imgs:
        # Skip old files if specified
        dw_path = img.parent / f'{img.stem}_dw.tif'
        if dw_path.exists() and skip_old:
            continue
        else:
            run_dw(
                img=img,
                channels=channels,
                psf_dir=psf_dir,
                fluos=fluos,
                scope=scope,
                mag=mag,
                z_pixel=z_pixel,
                iterations=iterations,
                scale=scale,
                tiles=tiles,
                dw_dir=dw_dir
            )


if __name__=='__main__':
    main()
