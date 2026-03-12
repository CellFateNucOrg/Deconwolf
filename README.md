# Install deconwolf & dependencies
Log into `izblisbon`. In case you don't have mamba (or conda) yet, install it:
```
cd $HOME # Navigate to your home directory
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" # Download the script to install miniforge
bash Miniforge3-$(uname)-$(uname -m).sh # Run the script
rm Miniforge3-$(uname)-$(uname -m).sh # Remove the script
```
## Get mamba-installable dependencies
LibTIFF & OpenMG can be installed with mamba (or conda):
```
mamba create -n deconwolf # Create a deconwolf env
mamba activate deconwolf
mamba install libtiff openmp
pip install numpy zarr json bioio bioio_tifffile bioio_nd2 bioio_czi bioio_lif bioio_bioformats
```
## Build remaining dependencies
The other dependencies cannot be installed with conda and have to be downloaded and compiled manually.
1. Make a directory for the source files to be compiled:
```
mkdir $HOME/.local/src # Make folder in your home directory for the source files (for compilcation)
export CMAKE_PREFIX_PATH=$HOME/.local # Ensure CMake finds the source files
export PATH=$HOME/.local/bin # Make binaries in .local visible
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH # Make shared libraries in .local visible
```
2. Download the following libraries (should be archived files ending in .tar, .tar.xz or .tar.gz):
	- FFTW3 (for running Fourier transforms on the CPU): https://www.fftw.org/download.html
	- GSL (GNU Scientific Library): https://ftp.gnu.org/gnu/gsl/
	- LibPNG (to handle PNG files): https://sourceforge.net/projects/libpng/files/
3. Move the files to a directory on the server you can access (e.g., your personal folder in the `MeisterLab` directory)
4. Navigate to the directory you put the files in (modify the path below):
```
cd /mnt/external.data/MeisterLab/Dario/
```
5. Extract the files (adjust the numbers after `fftw` and `rm` in case you downloaded a newer version of a library):
```
tar -xf fftw-3.3.10.tar.gz -C $HOME/.local/src && rm fftw-3.3.10.tar
tar -xf gsl-latest.tar -C $HOoME/.local/src && rm gsl-latest.tar
tar -xf libpng-1.6.55.tar.xz -C $HOME/.local/src && rm libpng-1.6.55.tar.xz
```
6. Compile and install the extracted files (again, adjust the version numbers if necessary):
```
# Install FFTW3 with double (64 bit) precision
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

```
# Install GSL
cd $HOME/.local/src/gsl-2.8
./configure --prefix=$HOME/.local
make
make install
```

```
# Install LibPNG
cd $HOME/.local/src/libpng-1.6.55
mkdir builddir && cd builddir
cmake .. 
cmake --build .
cmake --install . --prefix=$HOME/.local
```
7. Verify that the dependencies have been installed:
```
ls $HOME/.local/lib | grep fftw
# This should list 'libfftw3' AND 'libfftw3f' files with .a/.so extensions

ls $HOME/.local/lib | grep libpng
# This should list 'libpng' files with .a/.so extensions

ls $HOME/.local/lib | grep gsl
# This should list 'libgsl' files with .a/.so extensions
```
## Link OpenCL
GPU acceleration requires the OpenCL library, which is installed on the cluster but needs to be linked in `.local`.
1. Get the headers (files required by the compiler) and move them to `.local`:
```
mkdir -p $HOME/.local/include/CL
git clone https://github.com/KhronosGroup/OpenCL-Headers.git
cp OpenCL-Headers/CL/* $HOME/.local/include/CL/ && rm -rf OpenCL-Headers
```
2.  Link the OpenCL shared library  in `.local/lib`:
```
ln -sf /usr/lib/x86_64-linux-gnu/libOpenCL.so.1 $HOME/.local/lib/libOpenCL.so
```
3. Export OpenCL variables (so the compiler finds OpenCL when installing deconwolf):
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
## Install deconwolf
Once all of the dependencies have been installed, you can install deconwolf.
1. Clone the repository from github and compile it:
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
3. IGNORE THIS STEP FOR NOW: Clone the deconwolf repository from the lab github (so you get the scripts for running deconwolf): 
   ```
   cd / # Adjust this line depending on where you want to put the scripts
   git clone https://github.com/CellFateNucOrg/deconwolf.git
   ```
   ## Remove source files
Once the dependencies and deconwolf have been installed, you can optinally remove the source files (again, adjust the version numbers if necessary):
```
cd $HOME/.local/src
rm fftw-3.3.10
rm gsl-2.8
rm libpng-1.6.55
rm deconwolf
```
