#!/bin/bash
#SBATCH --job-name=dw
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=0-12:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem 64GB
#SBATCH --gres=gpu:rtx6000:1

#### Config ####

src_dirs=(

)
filter_out=(DS_Store)
dw_dir=/path/to/deconwolf
psf_dir=/Volumes/meister.data/deconwolf/psf
channels=(0)
fluos=(gfp)
scope=lipsi
mag=100
z_pixel=200
tiles=0
scale=false
iterations=50
skip_old=true

#### Script ####

# Run deconvolution
source $HOME/miniforge3/bin/activate dw

for img_dir in ${img_dirs[@]}; do

	img_dir=${img_dir/Volumes/mnt}
	imgs=("${img_dir}/*${suffix}")
	
	echo "Deconvolving images in ${img_dir}"
	
	python ${dw_dir}/dw.py \
	-i ${imgs[@]} -p $psf_dir \
	-c ${channels[@]} -f ${fluos[@]} \
	-s $scope -m $mag -z $z_pixel \
	-t $tiles -b $scale \
	-n $iterations
	
	mkdir -p ${img_dir}/dw/logs
	mv ${img_dir}/dw/*log.txt ${img_dir}/dw/logs/
	
done
