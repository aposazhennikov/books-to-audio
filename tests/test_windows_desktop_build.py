from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_desktop_module():
    script = Path("scripts/build_windows_desktop.py").resolve()
    spec = spec_from_file_location("test_windows_desktop_build_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pyinstaller_commands_define_gui_and_cli_executables(tmp_path: Path) -> None:
    module = _load_desktop_module()

    gui = module.pyinstaller_command(
        tmp_path,
        name=module.APP_NAME,
        entrypoint=module.GUI_ENTRYPOINT,
        windowed=True,
    )
    cli = module.pyinstaller_command(
        tmp_path,
        name=module.CLI_NAME,
        entrypoint=module.CLI_ENTRYPOINT,
        windowed=False,
        onefile=True,
    )

    assert "--windowed" in gui
    assert "--onedir" in gui
    assert module.APP_NAME in gui
    assert str(module.GUI_ENTRYPOINT) in gui
    assert "--console" in cli
    assert "--onefile" in cli
    assert module.CLI_NAME in cli
    assert str(module.CLI_ENTRYPOINT) in cli


def test_portable_layout_contains_local_state_dirs_and_launchers(tmp_path: Path) -> None:
    module = _load_desktop_module()
    bundle = tmp_path / module.APP_NAME
    bundle.mkdir()

    module.write_portable_layout(bundle)

    assert (bundle / "models").is_dir()
    assert (bundle / "data").is_dir()
    assert (bundle / "output").is_dir()
    assert module.APP_NAME in (bundle / "Books to Audio.bat").read_text(encoding="utf-8")
    assert module.CLI_NAME in (bundle / "Normalize Book CLI.bat").read_text(encoding="utf-8")
    assert "models\\" in (bundle / "README.txt").read_text(encoding="utf-8")
    assert (bundle / "Create Desktop Shortcut.ps1").exists()
