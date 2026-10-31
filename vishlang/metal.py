"""Work around ml-explore/mlx#4525: the macOS 26 wheel targets 26.2, so on an M5 running
26.0/26.1 MLX selects NAX kernels the OS Metal compiler cannot build. Pretending to be an
M4-class GPU makes MLX take the older kernel path. Slower, but it runs. Update macOS to
26.2 or later to get the real thing; the override is skipped automatically then."""
import os
import platform
import subprocess

FIXED_MACOS = (26, 2)
FALLBACK_ARCH = "applegpu_g16g"  # M4 family


def _chip() -> str:
    try:
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def _version(s: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in s.split(".")[:2])
    except ValueError:
        return (0, 0)


def nax_workaround(chip: str | None = None, macos: str | None = None, env=os.environ) -> bool:
    """Set MLX_METAL_GPU_ARCH when needed. Returns True if it changed the environment."""
    if "MLX_METAL_GPU_ARCH" in env:
        return False
    chip = _chip() if chip is None else chip
    macos = platform.mac_ver()[0] if macos is None else macos
    if "M5" not in chip or not (26, 0) <= _version(macos) < FIXED_MACOS:
        return False
    env["MLX_METAL_GPU_ARCH"] = FALLBACK_ARCH
    return True
