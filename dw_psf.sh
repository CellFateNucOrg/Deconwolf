#!/bin/bash
#SBATCH --job-name=dw_psf
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=1-0:00:00
#SBATCH --mem 64GB
#SBATCH --gres=gpu:1

# Configuration
dw_dir=/path/to/deconwolf
dw_dir=${dw_dir/Volumes/mnt}
mkdir -p ${dw_dir}/psf
scope=lipsi
mag=(40 60 100)
fluo=(mcherry gfp)
lambda=(640 510)
xy_pixel=(162.5 108.33 65) # LIPSI & Crest: 40x -> 162.5, 60x -> 108.33 100x -> 65
z_pixel=200 
ni=1.518 # LIPSI: 1.518, Crest: 1.516
na=(0.95 1.4 1.45)

# Create PSF
for m in ${!mag[@]}; do
	for f in ${!fluo[@]}; do
		psf_path=${dw_dir}/psf/${scope}_${mag[m]}x_z${z_pixel}_${fluo[f]}.tif
		dw_bw --lambda ${lambda[f]} --resxy ${xy_pixel[m]} --resz $z_pixel --NA ${na[m]} --ni $ni $psf_path
	done
done
		
mkdir -p ${dw_dir}/psf/logs
mv ${dw_dir}/psf/*log.txt ${dw_dir}/psf/logs