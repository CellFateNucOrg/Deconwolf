#!/bin/bash
#SBATCH --job-name=dw
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=0-01:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem 64GB
#SBATCH --gres=gpu:rtx4090:1

# Directories with raw images
img_dirs=(
# /Volumes/external.data/MeisterLab/Dario/SDC/SDC1/1273/20260326_e_if
# /Volumes/external.data/MeisterLab/Dario/SDC/DPY27/1268/20260325_e_if
/Volumes/external.data/MeisterLab/Dario/Code/test
)

# Configuration
suffix=nd2
dw_dir=/Volumes/external.data/MeisterLab/Dario/Code/dw
dw_dir=${dw_dir/Volumes/mnt}
psf_dir=${dw_dir}/psf
channels=(0 1)
fluos=(mcherry gfp)
scope=lipsi
mag=100
z_pixel=200
scale=False
iterations=50

# Activate env
source $HOME/miniforge3/bin/activate dw

# Run deconvolution
for img_dir in ${img_dirs[@]}; do

	img_dir=${img_dir/Volumes/mnt}
	imgs=("${img_dir}/*${suffix}")
	
	echo "Deconvolving images in ${img_dir}"
	
	python ${dw_dir}/dw.py \
	-i ${imgs[@]} -p $psf_dir \
	-c ${channels[@]} -f ${fluos[@]} \
	-s $scope -m $mag -z $z_pixel \
	-b $scale -n $iterations
	
	mkdir -p ${img_dir}/dw/logs
	mv ${img_dir}/dw/*log.txt ${img_dir}/dw/logs/
	
done
