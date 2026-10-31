from vishlang.config import load_config


def test_load_config_fills_defaults(tmp_path):
    p = tmp_path / "v.toml"
    p.write_text('[author]\nnames=["X"]\n')
    cfg = load_config(p)
    assert cfg["author"]["names"] == ["X"]
    assert cfg["author"]["emails"] == []
    assert cfg["model"]["base"] == "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    assert cfg["clean"]["min_words"] == 8
    assert cfg["sources"]["chatgpt"]["weight"] == 0.0
    assert cfg["sources"]["gmail"]["before"] == ""
