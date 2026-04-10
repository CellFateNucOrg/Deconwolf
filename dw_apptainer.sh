#!/bin/bash
#SBATCH --job-name=dw
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=1-0:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem 64GB
##SBATCH --gres=gpu:rtx4090:1
#SBATCH --gres=gpu:rtx6000:1

# Directories with raw images
img_dirs=(
/mnt/external.data/MeisterLab/jsemple/microscopy/sinem_1291_1001/slices_6-51
)

# Configuration
suffix=tif
dw_dir=/mnt/external.data/MeisterLab/jsemple/microscopy/sinem_1291_1001/deconwolf
dw_dir=${dw_dir/Volumes/mnt} # translate mac paths
psf_dir=${dw_dir}/psf
channels=(0 1)
fluos=(gfp mcherry)
scope=crest
mag=100
z_pixel=200
iterations=50
scale=False

# location of apptainer container
dw_sif=/mnt/external.data/MeisterLab/containers/deconwolf_custom.sif

img_dir=${img_dirs[0]}

# Run deconvolution
for img_dir in ${img_dirs[@]}; do

	img_dir=${img_dir/Volumes/mnt} # translate mac path
	imgs=(`ls "$img_dir/" | grep ${suffix}$`) # list images without path
	imgs=("${imgs[@]/#//mnt/img_dir/}")  # add apptainer internal path
		
	echo "Deconvolving images in ${img_dir}."
	
	apptainer exec --nv --bind $img_dir:/mnt/img_dir --bind ${dw_dir}/psf:/mnt/psf \
	--bind /etc/OpenCL/vendors  $dw_sif python /opt/dw_dario/dw.py \
	-i ${imgs[@]} -p /mnt/psf \
	-c ${channels[@]} -f ${fluos[@]} \
	-s $scope -m $mag -z $z_pixel \
	-b $scale -n $iterations
	
	mkdir -p ${img_dir}/dw/logs
	mv ${img_dir}/dw/*log.txt ${img_dir}/dw/logs/
	
done
