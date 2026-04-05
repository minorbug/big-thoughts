# tests/test_big_thoughts.py
import sys, os, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_default_prefs():
    from big_thoughts import default_prefs
    p = default_prefs()
    assert p["diary_name"] == "Big Thoughts"
    assert "theme" not in p
    assert p["font"] == "playful"
    assert p["font_size"] == 24
    assert p["password_hash"] == ""

def test_save_and_load_prefs():
    from big_thoughts import save_prefs, load_prefs, default_prefs
    d = tempfile.mkdtemp()
    try:
        path = os.path.join(d, "prefs.json")
        p = default_prefs()
        p["diary_name"] = "My Secret Book"
        save_prefs(p, path)
        loaded = load_prefs(path)
        assert loaded["diary_name"] == "My Secret Book"
        assert loaded["font_size"] == 24
    finally:
        shutil.rmtree(d)

def test_load_prefs_missing_file():
    from big_thoughts import load_prefs, default_prefs
    loaded = load_prefs("/tmp/nonexistent_prefs_xyz.json")
    assert loaded == default_prefs()

def test_app_css_exists():
    from big_thoughts import APP_CSS
    assert isinstance(APP_CSS, str)
    assert ".lock-screen" in APP_CSS
    assert ".diary-titlebar" in APP_CSS
    assert ".notebook-text" in APP_CSS

def test_fonts_exist():
    from big_thoughts import FONTS
    assert "playful" in FONTS
    assert "storybook" in FONTS
    assert "clean" in FONTS
    assert "typewriter" in FONTS
    for name, f in FONTS.items():
        assert "label" in f
        assert "family" in f

def test_prompt_deterministic():
    from big_thoughts import get_prompt
    p1 = get_prompt("2026-04-03")
    p2 = get_prompt("2026-04-03")
    p3 = get_prompt("2026-04-04")
    assert p1 == p2
    assert isinstance(p1, str)
    assert len(p1) > 5
    # Different dates can give different prompts (not guaranteed but likely)

def test_password_hash():
    from big_thoughts import hash_password, check_password
    h = hash_password("secret123")
    assert h.startswith("sha256:")
    assert check_password("secret123", h) is True
    assert check_password("wrong", h) is False

def test_entry_path():
    from big_thoughts import entry_path
    p = entry_path("/home/felix/.big-thoughts", "2026-04-03")
    assert p == "/home/felix/.big-thoughts/entries/2026-04-03.html"

def test_ensure_storage_dir():
    from big_thoughts import ensure_storage_dir
    d = tempfile.mkdtemp()
    try:
        storage = os.path.join(d, "test-diary")
        ensure_storage_dir(storage)
        assert os.path.isdir(os.path.join(storage, "entries"))
        assert oct(os.stat(storage).st_mode)[-3:] == "700"
    finally:
        shutil.rmtree(d)

def test_save_and_load_entry_html():
    from big_thoughts import save_entry_html, load_entry_html, entry_path
    d = tempfile.mkdtemp()
    try:
        storage = os.path.join(d, "diary")
        os.makedirs(os.path.join(storage, "entries"))
        path = entry_path(storage, "2026-04-03")
        save_entry_html(path, "<b>Hello</b> world")
        assert load_entry_html(path) == "<b>Hello</b> world"
    finally:
        shutil.rmtree(d)

def test_load_entry_html_missing():
    from big_thoughts import load_entry_html
    assert load_entry_html("/tmp/nonexistent_entry_xyz.html") == ""

def test_strip_html_tags():
    from big_thoughts import strip_tags
    assert strip_tags("<b>Hello</b> <i>world</i>") == "Hello world"
    assert strip_tags("plain text") == "plain text"
    assert strip_tags('<span style="color:red">red</span>') == "red"

def test_search_entries():
    from big_thoughts import search_entries
    d = tempfile.mkdtemp()
    try:
        entries_dir = os.path.join(d, "entries")
        os.makedirs(entries_dir)
        with open(os.path.join(entries_dir, "2026-04-01.html"), "w") as f:
            f.write("<b>I saw a big dog</b> at the park")
        with open(os.path.join(entries_dir, "2026-04-02.html"), "w") as f:
            f.write("Today was <i>rainy</i> and cold")
        with open(os.path.join(entries_dir, "2026-04-03.html"), "w") as f:
            f.write("The dog came back!")
        results = search_entries(d, "dog")
        dates = [r[0] for r in results]
        assert "2026-04-01" in dates
        assert "2026-04-03" in dates
        assert "2026-04-02" not in dates
        # Each result has (date, snippet)
        for date, snippet in results:
            assert "dog" in snippet.lower()
    finally:
        shutil.rmtree(d)
