from pathlib import Path
import importlib.util
import json
import pytest

spec = importlib.util.spec_from_file_location(
    "audit_inventory", Path(__file__).resolve().parents[1] / "scripts" / "audit_inventory.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_inventory_only_metadata(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "underkeep.exe").write_bytes(b"fake executable")
    local = game / "localization"
    local.mkdir()
    (local / "strings_en.txt").write_text("COPYRIGHTED-PLACEHOLDER", encoding="utf-8")

    result = module.inventory(game)
    serialized = json.dumps(result)
    assert result["file_count"] == 2
    assert result["total_size_bytes"] > 0
    assert "localization/strings_en.txt" in result["localization_candidate_paths"]
    assert "COPYRIGHTED-PLACEHOLDER" not in serialized
    assert all(len(info["sha256"]) == 64 for info in result["files"])
    assert all(not Path(info["path"]).is_absolute() for info in result["files"])


def test_never_write_output_into_game(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    with pytest.raises(SystemExit) as exc:
        module.main(["--game-root", str(game), "--output", str(game / "inventory.json")])
    assert exc.value.code == 2
    assert not (game / "inventory.json").exists()


def test_engine_signals_are_unverified():
    hints = module.detect_engine(["Game_Data/globalgamemanagers", "UnityPlayer.dll"])
    assert hints == [{"candidate": "Unity", "status": "indicator_only"}]
