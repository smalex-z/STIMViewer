#!/usr/bin/env bash
set -e

ts=$(date +%Y%m%d_%H%M%S)
outdir="machine_snapshot_$ts"
mkdir -p "$outdir"

echo "Saving shell environment…"
printenv > "$outdir"/shell_env.txt

echo "Saving Python deps (pip freeze)…"
pip freeze > "$outdir"/requirements.txt

# if you’re in a conda env:
# conda env export  > "$outdir"/conda_env.yaml

echo "Saving apt-installed packages…"
dpkg --get-selections > "$outdir"/apt_packages.txt

echo "Saving loaded kernel modules…"
lsmod > "$outdir"/kernel_modules.txt

echo "Saving PCI devices + drivers…"
lspci -k > "$outdir"/lspci_drivers.txt

echo "Saving OpenGL info…"
glxinfo > "$outdir"/glxinfo.txt || echo "(glxinfo failed)" >> "$outdir"/glxinfo.txt

echo "Saving NVIDIA GPU status…"
nvidia-smi > "$outdir"/nvidia-smi.txt 2>&1 || echo "(nvidia-smi failed)" >> "$outdir"/nvidia-smi.txt

echo "Saving uname/kernel version…"
uname -a > "$outdir"/uname.txt

echo "Snapshot saved in $outdir/"
