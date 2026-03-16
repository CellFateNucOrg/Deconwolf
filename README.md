Deconvolve microscopy images using the Deconwolf software (https://github.com/elgw/deconwolf). This repository contains instructions on how to install Deconwolf as well as scripts for using it on multi-dimensional datasets.
# How to install Deconwolf
## 1. Get mamba-installable dependencies
1. Log into `izblisbon`.
2. In case you don't have mamba/conda yet, install it:
```
cd $HOME # Navigate to your home directory
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" # Get the script to install miniforge
bash Miniforge3-$(uname)-$(uname -m).sh # Run the script
rm Miniforge3-$(uname)-$(uname -m).sh # Remove the script
```
3. Install LibTIFF and OpenMP:
```
mamba create -n dw python=3.13.2 # Make an env with python < 3.14
mamba activate deconwolf
mamba install libtiff openmp # Install the libraries
```
## 2. Get remaining dependencies
The remaining dependencies cannot be installed with conda and have to be downloaded and compiled manually.
1. Make a directory for the source files to be compiled:
```
mkdir $HOME/.local/src # Make folder in your home directory for the source files
export CMAKE_PREFIX_PATH=$HOME/.local # Ensure CMake (the compiler) finds the source files
export PATH=$HOME/.local/bin:$PATH # Make binaries in .local visible to the shell
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH # Make shared libraries in .local visible to the shell
```
2. Download the following libraries (should be archived such as .tar, .tar.xz or .tar.gz):
	- FFTW3 (for running Fourier transforms): https://www.fftw.org/download.html
	- GSL (GNU Scientific Library): https://ftp.gnu.org/gnu/gsl/
	- LibPNG (to handle PNG files): https://sourceforge.net/projects/libpng/files/
3. Move the files to a directory on the server you can access, e.g., your personal folder in the `MeisterLab` directory.
4. Navigate to the directory you put the files in. Modify the path below accordingly:
```
cd /dir/with/files
```
5. Extract the files. Adjust the numbers after `fftw` and `rm` in case you downloaded a newer version of any of the libraries:
```
tar -xf fftw-3.3.10.tar.gz -C $HOME/.local/src && rm fftw-3.3.10.tar
tar -xf gsl-latest.tar -C $HOoME/.local/src && rm gsl-latest.tar
tar -xf libpng-1.6.55.tar.xz -C $HOME/.local/src && rm libpng-1.6.55.tar.xz
```
6. Install FFTW3 with 64-bit and 32-bit precision (Deconwolf requires both):
```
# Install FFTW with double (64 bit) precision:
cd $HOME/.local/src/fftw-3.3.10
make clean # Get rid of temp files
./configure --prefix=$HOME/.local --enable-shared --enable-threads --enable-openmp # Prepare files for the compilation
make # Start the compilation (this may take a few minutes)
make install # Install, i.e., move the compiled files to where they belong
```

```
# Install FFTW3 with float (32 bit) precision
cd $HOME/.local/src/fftw-3.3.10
make clean
./configure --prefix=$HOME/.local --enable-shared --enable-threads --enable-float --enable-openmp
make
make install
```
7. Install the GSL library:
```
cd $HOME/.local/src/gsl-2.8
./configure --prefix=$HOME/.local
make
make install
```
8. Install LibPNG:
```
# Install LibPNG
cd $HOME/.local/src/libpng-1.6.55
mkdir builddir && cd builddir
cmake .. 
cmake --build .
cmake --install . --prefix=$HOME/.local
```
9. Verify that the dependencies have been installed in `.local`:
```
ls $HOME/.local/lib | grep fftw
# This should list 'libfftw3' AND 'libfftw3f' files with .a/.so extensions

ls $HOME/.local/lib | grep libpng
# This should list 'libpng' files with .a/.so extensions

ls $HOME/.local/lib | grep gsl
# This should list 'libgsl' files with .a/.so extensions
```
## 3. Link OpenCL
GPU acceleration requires the OpenCL library, which is installed on the server but needs to be linked in `.local`.
1. Get the headers (contains instructions for the compiler) and move them to `.local`:
```
mkdir -p $HOME/.local/include/CL
git clone https://github.com/KhronosGroup/OpenCL-Headers.git
cp OpenCL-Headers/CL/* $HOME/.local/include/CL/ && rm -rf OpenCL-Headers
```
2.  Link the OpenCL shared library (the `.so` file)  in `.local/lib`:
```
ln -sf /usr/lib/x86_64-linux-gnu/libOpenCL.so.1 $HOME/.local/lib/libOpenCL.so
```
3. Export OpenCL variables (so the compiler finds the library when installing Deconwolf):
```
export OpenCL_INCLUDE_DIR=$HOME/.local/include
export OpenCL_LIBRARY=$HOME/.local/lib/libOpenCL.so
```
4. Verify that OpenCL is present in `.local`:
```
ls $HOME/.local/lib | grep OpenCL
# This should list libOpenCL.so

ls $HOME/.local/include/CL | grep cl
# This should list a number of .h files
```
## 4. Install Deconwolf
Once all of the dependencies have been installed, you can install deconwolf.
1. Clone the repository from Github and compile it:
```
cd $HOME/.local/src
git clone https://github.com/elgw/deconwolf
mkdir deconwolf/builddir && cd deconwolf/builddir
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/.local
cmake --build .
cmake --install .
```
2. Verify that the files have been installed:
```
ls $HOME/.local/bin | grep dw
# This should list dw (for deconvolution) and dw_bw (to generate PSFs)
```
## 5. Remove source files
Once the dependencies and deconwolf have been installed, you can optinally remove the source files (again, adjust the version numbers if necessary):
```
cd $HOME/.local/src
rm fftw-3.3.10
rm gsl-2.8
rm libpng-1.6.55
rm deconwolf
```
## 6. Get scripts to run Deconwolf
1. Clone the Deconwolf repository from the lab Github:
   ```
   cd /dir/for/scripts # Navigate to where you want to put the Deconwolf repository
   git clone https://github.com/CellFateNucOrg/deconwolf.git
   ```
2. Install the required dependencies:
```
mamba activate dw
pip install numpy zarr json tifffile bioio bioio_tifffile bioio_nd2 bioio_czi bioio_lif bioio_bioformats
```
3. Install the `img_utils` package (contains helper functions for processing images):
```
cd ./deconwolf
pip install -e img_utils
```
# How to use Deconwolf
Deconvolution requires the image of a point spread function (a PSF, i.e., the probability distribution of light emitted by a single point source). Every unique combination of emission wavelength, numerical aperture (NA) of the objective, refractive index (n) of the used immersion oil, lateral pixel size (in the final image) and vertical pixel size (the spacing between the planes in a 3D image) requires an individual PSF. There are two ways of acquiring a PSF image: you can either measure them using fluorescent beads (not covered here) or model them, which Deconwolf provides a small program for. The next section explains how you can generate your PSFs using the `dw_psf.sh` script.
## Generate PSF images
### Required parameters
To generate a PSF, you have to provide the following parameters:
- Emission wavelength: the wavelength emitted by the fluorophore after excitation. If you don't know this value, you can look it up in a database: https://www.fpbase.org.
- NA of the objective: how strongly an objective refracts (and thus collects) light. This is specified on the casing of the objective (usually around 0.95 for 40x, 1.4 for 60x, and 1.45 for 100x).
- Refractive index of the oil: how strongly the immersion oil refracts light. This should be specified on the vial (usually around 1.51–1.52).
- Lateral pixel size: the physical distance in nm a single pixel in your raw image corresponds to, which should be specified in the raw image's metadata. You can also calculate this yourself by dividing the physical pixel size of the camera sensor by the total magnification (e.g., for the 100x objective on the LIPSI: 6.5 um / 100 = 65 nm).
- Vertical pixel size: the distance in nm between two planes in a 3D stack. This should also be specified in the metadata of the raw image.
### Run the script
In the `dw_psf.sh`script, specify the following parameters:
- `dw_dir`: the directory containing your Deconwolf scripts.
- `scope`: the name of the microscope.
- `mag`: the magnification of the objective.
- `fluo`: the name of the fluorophore.
- `lambda`: the emission wavelength.
- `xy_pixel`: the lateral pixel size.
- `z_pixel`: the vertical pixel size.
- `na`: the objective's numerical aperture.
Note that the script allows you to generate multiple PSF images at once, but the order of values must match between `mag`, `xy_pixel`, and `na`, and likewise the order between `fluo` and `lambda`. The following configuration, for example, would work:
```
fluo=(mcherry gfp)
lambda=(610 510) # 610 corresponds to mcherry and 510 to gfp
mag=(40 60 100)
xy_pixel=(162.5 108.33 65) # 162.5 corresponds to 40, 108.33 to 60, and 65 to 100
na=(0.95 1.4 1.45) # 0.95 corresponds to 40, 1.4 to 60, and 1.45 to 100
```
To launch the script, log into `izblisbon` and navigate to your Deconwolf directory:
```
cd /path/to/deconwolf/ # Navigate to your Deconwolf directory
sbatch dw_psf.sh # Launch the script
```
### Output PSF images
The script saves a `.tif` file of each generated PSF in a subfolder named `psf`. Since every image slice has to be matched with the correct PSF, the files must be named in a consistent manner. The script builds PSF filenames based on the name of the microscope, the magnification, the vertical pixel size, and the fluorophore, for example:`lipsi_100x_z200_gfp.tif`. Notably, the filename does not specify NA, refractive index, and lateral pixel size, which are determined by the objective, the immersion oil, and the combination of objective and camera pixel size, respectively. Since these parameters are not likely to change much for a given microscope, this naming logic should be sufficiently specific—and also more convenient than specifying every single parameter.
This repository comes with a few previously generated PSF files based on:
- 40x, 60x, and 100x magnifications.
- Immersion oils used with LIPSI (1.518) and Crest (1.516).
- A vertical pixel size of 200 nm.
- The fluorophores DAPI/Hoechst 33342 (461 nm), GFP/mStayGold (510 nm), Alexa Fluor 488 (520 nm), mCherry (640 nm), Janelia Fluor 646 (664 nm), and Alexa Fluor 647 (665 nm). 
## Deconvolve images
To run Deconwolf, specify the following parameters in the `dw.sh` script:
- `img_dirs`: the directories containing the raw images you want to deconvolve. Note that all of the images must have the same acquisition parameters (pixel size, channels, etc.)
- `suffix`: the file extension of your raw images, e.g. `tif` or `nd2`. This is to ensure that you don't pass any files other than your images to the Python script.
- `dw_dir`: your Deconwolf directory (which should contain the `dw_psf.sh` script).
- `channels`: the indexes of the channels you want to deconvolve, starting from zero. For example, if you have an image with three channels and you want to deconvolve channels two and three, this should be `channels=(1 2)`.
- `fluos`: the fluorophores (i.e., channels) in your image you want to deconvolve. The names of the fluorophores must be identical to those in the PSF filenames and their order must correspond to that of `channels`. Using the previous example, if you have an image with three channels, say Brightfield, mCherry, and GFP, and you want to skip the first channel, this should be: `fluos=(gfp mcherry)`.
- `scope`: the name of the microscope, which must match that of the corresponding PSF image.
- `mag`: the magnification used to acquire the image.
- `z_pixel`: the spacing between planes in nm.
- `iterations`: the number of rounds of deconvolution you want. The default is 50 iterations.
To launch the script, log into `izblisbon` and navigate to your Deconwolf directory:
```
cd /path/to/deconwolf/ # Navigate to your Deconwolf directory
sbatch dw.sh # Launch the script
```
4D and 5D raw images are split into 3D stacks before deconvolution and then stacked back together. The intermediate files, but not the raw images, will be deleted after stacking. The deconvolved images, as well as a maximum intensity projection of each image, are store in a subfolder named `dw`. Lastly, for each deconvolved image, a log file is saved in a subfolder named `logs`.
