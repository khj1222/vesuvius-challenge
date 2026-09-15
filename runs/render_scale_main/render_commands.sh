# The two real renders behind real_before_after.png (official renderer image, CPU, S3 streaming).
# Same public mesh, same public ink volume, same settings; only --scale-segmentation differs.
# $root holds inputs/public_w010_spliced (meta.json, x.tif, y.tif, z.tif copied from the public bucket).
image=ghcr.io/scrollprize/villa/volume-cartographer@sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4
ink=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr
mesh=hf://buckets/scrollprize/datasets/spiral/PHercParis4/verified_patches/0000_w010_spliced_flatboi_sel_20260611_234312_1

for f in meta.json x.tif y.tif z.tif; do hf buckets cp "$mesh/$f" "$root/inputs/public_w010_spliced/$f"; done

docker run --rm -v "$root:/work" $image vc_render_tifxyz --segmentation /work/inputs/public_w010_spliced --volume /work/cache/ink --remote-url $ink --group-idx 1 --scale 0.25 --num-slices 5 --scale-segmentation 1 --cache-gb 1 --timeout 10 --tif-output /work/outputs/baseline --log-path /work/logs/baseline.log
docker run --rm -v "$root:/work" $image vc_render_tifxyz --segmentation /work/inputs/public_w010_spliced --volume /work/cache/ink --remote-url $ink --group-idx 1 --scale 0.25 --num-slices 5 --scale-segmentation 4 --cache-gb 1 --timeout 10 --tif-output /work/outputs/scaled4 --log-path /work/logs/scaled4.log
