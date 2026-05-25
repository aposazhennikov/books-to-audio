from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_fetcher_module() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "fetch_quality_corpus.py"
    spec = importlib.util.spec_from_file_location("fetch_quality_corpus", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fetch_public_corpus_writes_texts_language_map_and_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_fetcher_module()
    downloaded_urls: list[str] = []

    def fake_download(url: str, *, timeout: float) -> str:
        downloaded_urls.append(url)
        assert timeout == 12.0
        if "gutenberg.org/ebooks/1342" in url:
            return (
                "Project header\n"
                "*** START OF THE PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***\n"
                "Chapter One\n\n"
                "It is a truth universally acknowledged, that a single man in possession "
                "of a good fortune, must be in want of a wife.\n"
                "*** END OF THE PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***\n"
                "Project footer"
            )
        if "gutenberg.org/ebooks/25431" in url:
            return (
                "Project header\n"
                "*** START OF THIS PROJECT GUTENBERG EBOOK GUI TIAN LU ***\n"
                "歸田錄\n\n"
                "卷一\n歐陽修記其聞見，文辭簡潔，足供中文品質基準測試使用。\n"
                "此段保留足夠文字，避免下載內容過短，並檢查中文標點、章節和段落能否正常進入品質流程。\n"
                "人物對話與敘述文字都應保留，讓後續分段和角色分析有真實材料。\n"
                "*** END OF THIS PROJECT GUTENBERG EBOOK GUI TIAN LU ***\n"
            )
        if "Xalq" in url:
            return (
                "{{Header}}\n"
                "== Xalq ==\n"
                "[[Muallif|Abdulla]] xalq haqida so'z yuritadi. "
                "Bu ochiq matn o'zbek tilidagi sifat benchmarki uchun yetarli uzunlikda. "
                "[uz:Eski havola]\n[[Category:Uzbek]]"
            )
        return (
            "{{header}}\n"
            "== Абылай хан ==\n"
            "[[Автор|Жазушы]] Абылай хан туралы баяндайды. "
            "Бұл ашық мәтін қазақ тіліндегі сапа benchmark үшін жеткілікті ұзын. "
            "<ref>note</ref>\n[[Category:Kazakh]]"
        )

    monkeypatch.setattr(module, "_download_text", fake_download)

    out_dir = tmp_path / "public_quality_corpus"
    written = module.fetch_public_corpus(out_dir=out_dir, force=False, timeout=12.0)

    assert len(written) == 4
    assert {path.name for path in written} == {
        "pride_and_prejudice.txt",
        "gui_tian_lu.txt",
        "abylai_khan.txt",
        "xalq.txt",
    }
    assert downloaded_urls == [source.url for source in module.PUBLIC_CORPUS_SOURCES]

    language_map = json.loads((out_dir / "languages.json").read_text(encoding="utf-8"))
    assert language_map == {
        "english/*.txt": "en",
        "chinese/*.txt": "zh",
        "kazakh/*.txt": "kk",
        "uzbek/*.txt": "uz",
    }

    sources = json.loads((out_dir / "sources.json").read_text(encoding="utf-8"))
    assert {record["language"] for record in sources} == {"en", "zh", "kk", "uz"}
    assert all(record["url"].startswith("https://") for record in sources)
    assert all(record["license_note"] for record in sources)

    english_text = (out_dir / "english" / "pride_and_prejudice.txt").read_text(encoding="utf-8")
    kazakh_text = (out_dir / "kazakh" / "abylai_khan.txt").read_text(encoding="utf-8")
    uzbek_text = (out_dir / "uzbek" / "xalq.txt").read_text(encoding="utf-8")

    assert "PROJECT GUTENBERG" not in english_text
    assert "It is a truth universally acknowledged" in english_text
    assert "{{" not in kazakh_text
    assert "[[" not in kazakh_text
    assert "Category" not in kazakh_text
    assert "Абылай хан" in kazakh_text
    assert "Xalq" in uzbek_text


def test_fetch_public_corpus_reuses_existing_files_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_fetcher_module()
    out_dir = tmp_path / "public_quality_corpus"
    for source in module.PUBLIC_CORPUS_SOURCES:
        path = out_dir / source.subdir / source.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Existing text for {source.language} " * 10, encoding="utf-8")

    def fail_download(url: str, *, timeout: float) -> str:
        raise AssertionError(f"Unexpected network call: {url} {timeout}")

    monkeypatch.setattr(module, "_download_text", fail_download)

    written = module.fetch_public_corpus(out_dir=out_dir, force=False)

    assert len(written) == 4
    assert json.loads((out_dir / "languages.json").read_text(encoding="utf-8"))["kazakh/*.txt"] == "kk"


def test_clean_downloaded_text_strips_supported_boilerplate() -> None:
    module = _load_fetcher_module()

    gutenberg = module.clean_downloaded_text(
        "Header\n*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE ***\nBody\n\n\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE ***\nFooter",
        "gutenberg_txt",
    )
    wikisource = module.clean_downloaded_text(
        "{{header}}\n== Title ==\n[[Author|Name]] text <ref>x</ref>\n[[Category:Test]]",
        "wikisource_raw",
    )

    assert gutenberg == "Body"
    assert wikisource == "Title\nName text"
