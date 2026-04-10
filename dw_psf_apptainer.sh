#!/bin/bash
#SBATCH --job-name=dw_psf
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=1-0:00:00
#SBATCH --mem 64GB
#SBATCH --gres=gpu:1

# Configuration
dw_dir=/mnt/external.data/MeisterLab/jsemple/microscopy/sinem_1291_1001/deconwolf
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

# location of apptainer container
dw_sif=/mnt/external.data/MeisterLab/containers/deconwolf_custom.sif


# Create PSF
for m in ${!mag[@]}; do
	for f in ${!fluo[@]}; do
		psf_file=${scope}_${mag[m]}x_z${z_pixel}_${fluo[f]}.tif
		psf_path=${dw_dir}/psf
		
		apptainer exec --nv --bind /etc/OpenCL/vendors \
		--bind  ${psf_path}:/mnt/psf \
	        $dw_sif dw_bw --lambda ${lambda[f]} --resxy ${xy_pixel[m]} --resz $z_pixel --NA ${na[m]} --ni $ni /mnt/psf/${psf_file}
	done
done
		
mkdir -p ${dw_dir}/psf/logs
mv ${dw_dir}/psf/*log.txt ${dw_dir}/psf/logs
