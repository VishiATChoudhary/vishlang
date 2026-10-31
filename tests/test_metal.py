from vishlang.metal import nax_workaround


def test_sets_arch_override_on_m5_with_old_macos():
    env = {}
    assert nax_workaround(chip="Apple M5", macos="26.1", env=env) is True
    assert env["MLX_METAL_GPU_ARCH"] == "applegpu_g16g"


def test_no_override_on_fixed_macos_or_other_chips():
    env = {}
    assert nax_workaround(chip="Apple M5", macos="26.2", env=env) is False
    assert nax_workaround(chip="Apple M4 Pro", macos="26.1", env=env) is False
    assert nax_workaround(chip="Apple M5", macos="27.0", env=env) is False
    assert env == {}


def test_respects_existing_user_setting():
    env = {"MLX_METAL_GPU_ARCH": "applegpu_g15g"}
    assert nax_workaround(chip="Apple M5", macos="26.1", env=env) is False
    assert env["MLX_METAL_GPU_ARCH"] == "applegpu_g15g"
