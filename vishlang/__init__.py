from .metal import nax_workaround

if nax_workaround():  # must run before mlx is imported anywhere
    import sys

    print("vishlang: M5 on macOS < 26.2, using MLX_METAL_GPU_ARCH=applegpu_g16g (see mlx#4525)", file=sys.stderr)
