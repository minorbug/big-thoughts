#!/usr/bin/env python3
"""Big Thoughts — A kid-friendly diary app."""

import os
import json
import hashlib
import re
import shutil
from html.parser import HTMLParser

# ── Fonts ───────────────────────────────────────────────────────────────────

FONTS = {
    "playful": {
        "label": "Playful",
        "family": "Andika, Quicksand, Comic Sans MS, Chalkboard SE, cursive",
    },
    "storybook": {
        "label": "Storybook",
        "family": "URW Bookman, Bookman Old Style, Georgia, serif",
    },
    "clean": {
        "label": "Clean",
        "family": "Quicksand, DejaVu Sans, Liberation Sans, sans-serif",
    },
    "typewriter": {
        "label": "Typewriter",
        "family": "DejaVu Sans Mono, Courier New, monospace",
    },
}

# Text colors used for formatting (shared between CSS, tags, and serialization)
TEXT_COLORS = {
    "green": "#2a3a1e",
    "blue": "#1565c0",
    "purple": "#7b1fa2",
    "red": "#c62828",
}

# ── Prompts ─────────────────────────────────────────────────────────────────

PROMPTS = [
    "What made you happy today?",
    "How are you feeling right now?",
    "What was the best part of your day?",
    "Did anything make you laugh today?",
    "What are you thankful for today?",
    "Was anything tricky today?",
    "What made you proud today?",
    "Did you help someone today?",
    "What adventure did you have today?",
    "Tell me about something you saw today",
    "What did you learn today?",
    "Did you go anywhere fun?",
    "What did you play today?",
    "Did you make anything today?",
    "What's something cool that happened?",
    "If today was a movie, what would it be called?",
    "What do you want to do tomorrow?",
    "Did you read or hear a good story?",
    "What's something new you tried?",
    "Draw or describe your favourite moment today",
]


def get_prompt(date_str):
    """Return a deterministic prompt for a given date string like '2026-04-03'."""
    h = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    return PROMPTS[h % len(PROMPTS)]


# ── Password ────────────────────────────────────────────────────────────────

def hash_password(password):
    """Hash a password with sha256 and a fixed prefix."""
    digest = hashlib.sha256(password.encode()).hexdigest()
    return f"sha256:{digest}"


def check_password(password, stored_hash):
    """Check a password against a stored hash."""
    return hash_password(password) == stored_hash


# ── Preferences ─────────────────────────────────────────────────────────────

def default_prefs():
    return {
        "password_hash": "",
        "diary_name": "Big Thoughts",
        "font": "playful",
        "font_size": 24,
        "storage_path": os.path.join(os.path.expanduser("~"), ".big-thoughts"),
    }


def load_prefs(path):
    """Load prefs from JSON file, returning defaults for missing keys."""
    defaults = default_prefs()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path) as f:
            data = json.load(f)
        for key in defaults:
            if key not in data:
                data[key] = defaults[key]
        return data
    except (json.JSONDecodeError, IOError):
        return defaults


def save_prefs(prefs, path):
    """Save prefs dict to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(prefs, f, indent=2)


# ── Storage ─────────────────────────────────────────────────────────────────

def entry_path(storage_dir, date_str):
    """Return the path to an entry file for a given date."""
    return os.path.join(storage_dir, "entries", f"{date_str}.html")


def ensure_storage_dir(storage_dir):
    """Create storage directory with 700 permissions if it doesn't exist."""
    entries_dir = os.path.join(storage_dir, "entries")
    os.makedirs(entries_dir, exist_ok=True)
    os.chmod(storage_dir, 0o700)


def save_entry_html(path, html):
    """Save HTML string to an entry file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html)


def load_entry_html(path):
    """Load HTML string from an entry file, or empty string if missing."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path) as f:
            return f.read()
    except IOError:
        return ""


# ── Search ──────────────────────────────────────────────────────────────────

def strip_tags(html):
    """Strip HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html)


def search_entries(storage_dir, query):
    """Search all entries for a query string. Returns list of (date, snippet)."""
    entries_dir = os.path.join(storage_dir, "entries")
    if not os.path.isdir(entries_dir):
        return []
    results = []
    query_lower = query.lower()
    for filename in sorted(os.listdir(entries_dir), reverse=True):
        if not filename.endswith(".html"):
            continue
        date_str = filename[:-5]
        filepath = os.path.join(entries_dir, filename)
        try:
            with open(filepath) as f:
                html = f.read()
        except IOError:
            continue
        text = strip_tags(html)
        if query_lower in text.lower():
            # Extract a snippet around the match
            idx = text.lower().index(query_lower)
            start = max(0, idx - 30)
            end = min(len(text), idx + len(query) + 30)
            snippet = text[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            results.append((date_str, snippet))
    return results


# ── HTML serialization ───────────────────────────────────────────────────────

def buffer_to_html(buf):
    """Serialize a GtkTextBuffer to HTML string."""
    start_iter = buf.get_start_iter()
    end_iter = buf.get_end_iter()
    if start_iter.equal(end_iter):
        return ""

    html_parts = []
    pos = start_iter.copy()

    def tag_names(tags):
        return sorted([t.get_property("name") for t in tags if t.get_property("name")])

    def open_html_tags(names):
        parts = []
        for name in names:
            if name == "bold":
                parts.append("<b>")
            elif name == "italic":
                parts.append("<i>")
            elif name == "underline":
                parts.append("<u>")
            elif name and name.startswith("color-"):
                color_key = name[len("color-"):]
                hex_val = TEXT_COLORS.get(color_key)
                if hex_val:
                    parts.append(f'<span style="color:{hex_val}">')
        return "".join(parts)

    def close_html_tags(names):
        parts = []
        for name in reversed(names):
            if name == "bold":
                parts.append("</b>")
            elif name == "italic":
                parts.append("</i>")
            elif name == "underline":
                parts.append("</u>")
            elif name and name.startswith("color-"):
                color_key = name[len("color-"):]
                if TEXT_COLORS.get(color_key):
                    parts.append("</span>")
        return "".join(parts)

    while pos.compare(end_iter) < 0:
        names = tag_names(pos.get_tags())
        # Find end of this run (consecutive chars with same tags)
        run_end = pos.copy()
        run_end.forward_char()
        while run_end.compare(end_iter) < 0 and tag_names(run_end.get_tags()) == names:
            run_end.forward_char()

        text = buf.get_text(pos, run_end, True)
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        escaped = escaped.replace("\n", "<br>")

        html_parts.append(open_html_tags(names))
        html_parts.append(escaped)
        html_parts.append(close_html_tags(names))

        pos = run_end

    return "".join(html_parts)


class DiaryHTMLParser(HTMLParser):
    """Parser for diary HTML that populates a GtkTextBuffer with tagged text."""

    # Build reverse map from hex color to tag name
    _hex_to_tag = {v: f"color-{k}" for k, v in TEXT_COLORS.items() if v}

    def __init__(self, buf):
        super().__init__()
        self.buf = buf
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "b":
            self.tag_stack.append("bold")
        elif tag == "i":
            self.tag_stack.append("italic")
        elif tag == "u":
            self.tag_stack.append("underline")
        elif tag == "span":
            for attr_name, attr_val in attrs:
                if attr_name == "style" and "color:" in attr_val:
                    color = attr_val.split("color:")[1].strip().rstrip(";")
                    tag_name = self._hex_to_tag.get(color, None)
                    if tag_name:
                        self.tag_stack.append(tag_name)
        elif tag == "br":
            self.buf.insert(self.buf.get_end_iter(), "\n")

    def handle_endtag(self, tag):
        tag_map = {"b": "bold", "i": "italic", "u": "underline", "span": None}
        if tag in tag_map:
            expected = tag_map[tag]
            if expected and expected in self.tag_stack:
                self.tag_stack.remove(expected)
            elif tag == "span" and self.tag_stack:
                # Remove last color tag
                for i in range(len(self.tag_stack) - 1, -1, -1):
                    if self.tag_stack[i].startswith("color-"):
                        self.tag_stack.pop(i)
                        break

    def handle_data(self, data):
        if not data:
            return
        start_offset = self.buf.get_char_count()
        self.buf.insert(self.buf.get_end_iter(), data)
        end_offset = self.buf.get_char_count()
        start_iter = self.buf.get_iter_at_offset(start_offset)
        end_iter = self.buf.get_iter_at_offset(end_offset)
        for tag_name in self.tag_stack:
            self.buf.apply_tag_by_name(tag_name, start_iter, end_iter)


def html_to_buffer(buf, html):
    """Parse HTML string and populate a GtkTextBuffer with tagged text."""
    buf.set_text("")
    if not html:
        return

    parser = DiaryHTMLParser(buf)
    parser.feed(html)


# ── GTK UI ──────────────────────────────────────────────────────────────────

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, Pango, GLib
    _GTK_AVAILABLE = True
    _GtkWindowBase = Gtk.Window
except (ImportError, ValueError):
    _GTK_AVAILABLE = False
    _GtkWindowBase = object

import datetime


APP_CSS = """
/* Lock screen */
.lock-screen {
    background-color: #2d4222;
}
.lock-title {
    font-size: 32px;
    font-weight: bold;
    color: #d4c8a8;
}
.lock-subtitle {
    font-size: 14px;
    color: #8a8a70;
}
.lock-entry {
    font-size: 18px;
    padding: 10px 16px;
    border-radius: 8px;
    min-width: 200px;
}
.lock-btn {
    font-size: 16px;
    font-weight: bold;
    padding: 10px 20px;
    border-radius: 8px;
    background: #e8e0d0;
    color: #2a3a20;
}
.lock-quit-btn {
    background: none;
    border: none;
    color: #666666;
    font-size: 12px;
    padding: 6px 12px;
}
.lock-quit-btn:hover {
    color: #999999;
}
.lock-error {
    color: #ffcdd2;
    font-size: 13px;
}

/* Title bar */
.diary-titlebar {
    background-color: #243a1a;
    padding: 6px 14px;
    border-bottom: 1px solid #1a2a12;
}
.diary-titlebar label {
    color: #c8bc98;
    font-size: 15px;
    font-weight: bold;
}
.titlebar-menu-btn {
    background: #1a2a14;
    border: 1px solid #2a3a22;
    border-radius: 5px;
    min-width: 32px;
    min-height: 28px;
    font-size: 16px;
    color: #b0a880;
    padding: 0px 6px;
}
.titlebar-menu-btn:hover {
    background: #2a3a22;
}

/* Nav bar */
.diary-navbar {
    background-color: #324a28;
    padding: 5px 14px;
    border-bottom: 1px solid #243a1a;
}
.nav-btn {
    background: #1a2a14;
    color: #c8bc98;
    border-radius: 14px;
    font-weight: bold;
    font-size: 12px;
    padding: 4px 14px;
    border: 1px solid #2a3a22;
}
.nav-btn:hover {
    background: #2a3a22;
}
.nav-date {
    font-size: 15px;
    font-weight: bold;
    color: #d4c8a8;
}

/* Prompt bar */
.prompt-bar {
    background: #f5e6b8;
    border-bottom: 2px solid #d4c090;
    padding: 6px 14px;
}
.prompt-text {
    color: #8a6a20;
    font-size: 13px;
}
.prompt-dismiss {
    background: none;
    border: none;
    color: #b09460;
    font-size: 16px;
    padding: 2px 6px;
}
.prompt-dismiss:hover {
    color: #8a6a20;
}

/* Toolbar */
.fmt-toolbar {
    background: #ede0c0;
    border-bottom: 1px solid #d4c090;
    padding: 4px 14px;
}
.fmt-btn {
    background: #f5ecd8;
    border: 1px solid #c8b888;
    border-radius: 4px;
    min-width: 30px;
    min-height: 26px;
    font-size: 13px;
    color: #5a4a2a;
    padding: 0px;
}
.fmt-btn:hover {
    background: #ede0c0;
}
.color-btn {
    border-radius: 16px;
    min-width: 28px;
    min-height: 28px;
    padding: 0px;
    border: 3px solid #999999;
}

/* Notebook */
.notebook-frame {
    border: none;
    margin: 0;
}
.notebook-text {
    background: #fffdf5;
    color: #2a3a1e;
}

/* Diary background */
.diary-bg {
    background: #f0e8d0;
}
"""


class BigThoughtsApp(_GtkWindowBase):
    def __init__(self):
        super().__init__(title="Big Thoughts")
        self.set_default_size(1024, 600)

        # Load prefs
        self.storage_path = os.path.join(os.path.expanduser("~"), ".big-thoughts")
        self.prefs_path = os.path.join(self.storage_path, "prefs.json")
        self.prefs = load_prefs(self.prefs_path)
        self.storage_path = self.prefs["storage_path"]
        ensure_storage_dir(self.storage_path)

        self.current_date = datetime.date.today()
        self.prompt_dismissed = False

        # Apply CSS theme
        self._apply_css()

        # Main stack to switch between lock screen and diary
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(200)
        self.add(self.stack)

        self._build_lock_screen()
        self._build_diary_view()

        # Keyboard shortcuts — connected at window level so they work on all screens
        self.connect("key-press-event", self._on_key_press)
        self.connect("destroy", Gtk.main_quit)
        self.show_all()

        # Set visible child AFTER show_all to ensure it takes effect
        if self.prefs["password_hash"]:
            self.stack.set_visible_child_name("lock")
        else:
            # No password — go straight to diary
            self.stack.set_visible_child_name("diary")
            self._load_current_entry()

        self.present()

    def _apply_css(self):
        """Apply GTK CSS stylesheet."""
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(APP_CSS.encode())
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        except Exception as e:
            import sys
            print(f"Warning: CSS failed to load: {e}", file=sys.stderr)
        self._css_provider = provider

    def _font_family(self):
        return FONTS.get(self.prefs["font"], FONTS["playful"])["family"]

    # ── Lock Screen ─────────────────────────────────────────────────────

    def _build_lock_screen(self):
        # Lock screen (password entry)
        lock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        lock_box.get_style_context().add_class("lock-screen")
        lock_box.connect("draw", self._on_draw_lock_texture)

        lock_center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        lock_center.set_halign(Gtk.Align.CENTER)
        lock_center.set_valign(Gtk.Align.CENTER)

        emoji_label = Gtk.Label()
        emoji_label.set_markup('<span size="72000">\U0001F333</span>')
        lock_center.pack_start(emoji_label, False, False, 0)

        title_label = Gtk.Label()
        title_label.get_style_context().add_class("lock-title")
        title_label.set_markup(
            f'<span size="36000" weight="bold" color="#d4c8a8">'
            f'{GLib.markup_escape_text(self.prefs["diary_name"])}</span>'
        )
        lock_center.pack_start(title_label, False, False, 0)

        subtitle = Gtk.Label()
        subtitle.get_style_context().add_class("lock-subtitle")
        subtitle.set_text("This diary is private!")
        lock_center.pack_start(subtitle, False, False, 4)

        pw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pw_box.set_halign(Gtk.Align.CENTER)

        self.lock_entry = Gtk.Entry()
        self.lock_entry.set_visibility(False)
        self.lock_entry.set_placeholder_text("Password...")
        self.lock_entry.set_width_chars(18)
        self.lock_entry.get_style_context().add_class("lock-entry")
        self.lock_entry.connect("activate", self._on_unlock)
        pw_box.pack_start(self.lock_entry, False, False, 0)

        unlock_btn = Gtk.Button(label="\U0001F513 Open")
        unlock_btn.get_style_context().add_class("lock-btn")
        unlock_btn.connect("clicked", self._on_unlock)
        pw_box.pack_start(unlock_btn, False, False, 0)

        lock_center.pack_start(pw_box, False, False, 12)

        self.lock_error = Gtk.Label()
        self.lock_error.get_style_context().add_class("lock-error")
        lock_center.pack_start(self.lock_error, False, False, 0)

        hint_label = Gtk.Label()
        hint_label.set_markup(
            '<span color="#8a8a70" size="10000">'
            '\U0001F512 Type your secret password to open</span>'
        )
        lock_center.pack_start(hint_label, False, False, 4)

        # Quit button at bottom-right of lock screen
        lock_quit = Gtk.Button(label="Quit")
        lock_quit.set_halign(Gtk.Align.END)
        lock_quit.set_margin_bottom(8)
        lock_quit.set_margin_end(12)
        lock_quit.get_style_context().add_class("lock-quit-btn")
        lock_quit.connect("clicked", lambda w: Gtk.main_quit())
        lock_box.pack_start(lock_center, True, True, 0)
        lock_box.pack_end(lock_quit, False, False, 0)
        self.stack.add_named(lock_box, "lock")

        # Setup screen (first launch — set password)
        setup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        setup_box.get_style_context().add_class("lock-screen")
        setup_box.connect("draw", self._on_draw_lock_texture)

        setup_center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        setup_center.set_halign(Gtk.Align.CENTER)
        setup_center.set_valign(Gtk.Align.CENTER)

        setup_emoji = Gtk.Label()
        setup_emoji.set_markup('<span size="72000">\U0001F333</span>')
        setup_center.pack_start(setup_emoji, False, False, 0)

        setup_title = Gtk.Label()
        setup_title.get_style_context().add_class("lock-title")
        setup_title.set_markup('<span size="36000" weight="bold">Welcome!</span>')
        setup_center.pack_start(setup_title, False, False, 0)

        setup_sub = Gtk.Label()
        setup_sub.get_style_context().add_class("lock-subtitle")
        setup_sub.set_text("Choose a secret password for your diary")
        setup_center.pack_start(setup_sub, False, False, 4)

        self.setup_entry1 = Gtk.Entry()
        self.setup_entry1.set_visibility(False)
        self.setup_entry1.set_placeholder_text("Pick a password...")
        self.setup_entry1.set_width_chars(18)
        self.setup_entry1.get_style_context().add_class("lock-entry")
        self.setup_entry1.set_halign(Gtk.Align.CENTER)
        setup_center.pack_start(self.setup_entry1, False, False, 0)

        self.setup_entry2 = Gtk.Entry()
        self.setup_entry2.set_visibility(False)
        self.setup_entry2.set_placeholder_text("Type it again...")
        self.setup_entry2.set_width_chars(18)
        self.setup_entry2.get_style_context().add_class("lock-entry")
        self.setup_entry2.set_halign(Gtk.Align.CENTER)
        self.setup_entry2.connect("activate", self._on_setup_password)
        setup_center.pack_start(self.setup_entry2, False, False, 0)

        setup_btn = Gtk.Button(label="\U0001F333 Start my diary!")
        setup_btn.get_style_context().add_class("lock-btn")
        setup_btn.connect("clicked", self._on_setup_password)
        setup_btn.set_halign(Gtk.Align.CENTER)
        setup_center.pack_start(setup_btn, False, False, 12)

        self.setup_error = Gtk.Label()
        self.setup_error.get_style_context().add_class("lock-error")
        setup_center.pack_start(self.setup_error, False, False, 0)

        # Quit button at bottom-right of setup screen
        setup_quit = Gtk.Button(label="Quit")
        setup_quit.set_halign(Gtk.Align.END)
        setup_quit.set_margin_bottom(8)
        setup_quit.set_margin_end(12)
        setup_quit.get_style_context().add_class("lock-quit-btn")
        setup_quit.connect("clicked", lambda w: Gtk.main_quit())
        setup_box.pack_start(setup_center, True, True, 0)
        setup_box.pack_end(setup_quit, False, False, 0)
        self.stack.add_named(setup_box, "setup")

    def _on_unlock(self, widget):
        # If no password is set, just go to diary
        if not self.prefs["password_hash"]:
            self.stack.set_visible_child_name("diary")
            self._load_current_entry()
            return
        pw = self.lock_entry.get_text()
        if check_password(pw, self.prefs["password_hash"]):
            self.lock_entry.set_text("")
            self.lock_error.set_text("")
            self.stack.set_visible_child_name("diary")
            self._load_current_entry()
        else:
            self.lock_error.set_markup(
                '<span color="#ffcdd2" size="10000">Wrong password! Try again.</span>'
            )
            self.lock_entry.set_text("")

    def _on_setup_password(self, widget):
        pw1 = self.setup_entry1.get_text()
        pw2 = self.setup_entry2.get_text()
        if len(pw1) < 1:
            self.setup_error.set_markup(
                '<span color="#ffcdd2" size="10000">Type a password!</span>'
            )
            return
        if pw1 != pw2:
            self.setup_error.set_markup(
                '<span color="#ffcdd2" size="10000">Passwords don\'t match! Try again.</span>'
            )
            self.setup_entry2.set_text("")
            return
        self.prefs["password_hash"] = hash_password(pw1)
        save_prefs(self.prefs, self.prefs_path)
        self.setup_entry1.set_text("")
        self.setup_entry2.set_text("")
        self.stack.set_visible_child_name("diary")
        self._load_current_entry()

    def _on_lock(self, widget):
        if not self.prefs["password_hash"]:
            return  # Can't lock without a password set
        self._cancel_autosave()
        self._save_current_entry()
        self.stack.set_visible_child_name("lock")
        self.lock_entry.grab_focus()

    def _on_draw_lock_texture(self, widget, cr):
        """Draw leather texture and stitch border on lock/setup screens."""
        import cairo
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        # Cache the noise surface
        if not hasattr(self, '_leather_cache') or self._leather_cache_size != (w, h):
            self._leather_cache_size = (w, h)
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            ctx = cairo.Context(surface)
            step = 3
            for y in range(0, h, step):
                for x in range(0, w, step):
                    noise = ((x * 73 + y * 137 + x * y * 7) % 255) / 255.0
                    alpha = noise * 0.08
                    if noise > 0.5:
                        ctx.set_source_rgba(1, 1, 1, alpha * 0.3)
                    else:
                        ctx.set_source_rgba(0, 0, 0, alpha * 0.5)
                    ctx.rectangle(x, y, step, step)
                    ctx.fill()
            self._leather_cache = surface

        # Paint cached texture
        cr.set_source_surface(self._leather_cache, 0, 0)
        cr.paint()

        # Vignette
        pat = cairo.RadialGradient(w/2, h/2, min(w,h)*0.3, w/2, h/2, max(w,h)*0.7)
        pat.add_color_stop_rgba(0, 0, 0, 0, 0)
        pat.add_color_stop_rgba(1, 0, 0, 0, 0.2)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Stitch border
        cr.set_source_rgba(0.7, 0.65, 0.5, 0.35)
        cr.set_line_width(2)
        cr.set_dash([8, 6])
        margin = 12
        cr.rectangle(margin, margin, w - 2*margin, h - 2*margin)
        cr.stroke()
        cr.set_dash([])

        return False

    # ── Diary View ──────────────────────────────────────────────────────

    def _build_diary_view(self):
        diary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        diary_box.get_style_context().add_class("diary-bg")

        # ── Title bar ───────────────────────────────────────────────────
        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        titlebar.get_style_context().add_class("diary-titlebar")

        # Hamburger menu in the title bar (left side)
        menu_btn = Gtk.Button(label="\u2630")
        menu_btn.get_style_context().add_class("titlebar-menu-btn")
        titlebar.pack_start(menu_btn, False, False, 0)

        self.title_label = Gtk.Label()
        self._update_title_label()
        titlebar.pack_start(self.title_label, True, True, 0)

        diary_box.pack_start(titlebar, False, False, 0)

        # Popover menu attached to hamburger
        popover = Gtk.Popover()
        popover.set_relative_to(menu_btn)
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        for label, callback in [
            ("\U0001F4C5 Calendar", self._on_show_calendar),
            ("\U0001F50D Search", self._on_toggle_search),
            ("\u2699 Settings", self._on_show_settings),
        ]:
            item = Gtk.ModelButton(label=label)
            item.set_property("xalign", 0)
            item.connect("clicked", lambda w, cb=callback: (popover.popdown(), cb(w)))
            menu_box.pack_start(item, False, False, 0)

        self._lock_sep = Gtk.Separator()
        menu_box.pack_start(self._lock_sep, False, False, 0)
        self._lock_item = Gtk.ModelButton(label="\U0001F512 Lock Diary")
        self._lock_item.set_property("xalign", 0)
        self._lock_item.connect("clicked", lambda w: (popover.popdown(), self._on_lock(w)))
        menu_box.pack_start(self._lock_item, False, False, 0)

        # Quit
        quit_sep = Gtk.Separator()
        menu_box.pack_start(quit_sep, False, False, 0)
        quit_item = Gtk.ModelButton(label="\u274C Quit")
        quit_item.set_property("xalign", 0)
        quit_item.connect("clicked", lambda w: (self._cancel_autosave(), self._save_current_entry(), Gtk.main_quit()))
        menu_box.pack_start(quit_item, False, False, 0)

        # Update lock visibility when menu opens
        def on_popover_show(p):
            has_pw = bool(self.prefs["password_hash"])
            self._lock_item.set_visible(has_pw)
            self._lock_sep.set_visible(has_pw)
        popover.connect("show", on_popover_show)

        menu_box.show_all()
        popover.add(menu_box)
        menu_btn.connect("clicked", lambda w: popover.popup())

        # ── Navigation bar ──────────────────────────────────────────────
        navbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        navbar.get_style_context().add_class("diary-navbar")

        prev_btn = Gtk.Button(label="\u25C0 Yesterday")
        prev_btn.get_style_context().add_class("nav-btn")
        prev_btn.connect("clicked", self._on_prev_day)
        navbar.pack_start(prev_btn, False, False, 0)

        self.date_label = Gtk.Label()
        self.date_label.get_style_context().add_class("nav-date")
        self._update_date_label()
        navbar.set_center_widget(self.date_label)

        next_btn = Gtk.Button(label="Tomorrow \u25B6")
        next_btn.get_style_context().add_class("nav-btn")
        next_btn.connect("clicked", self._on_next_day)
        navbar.pack_end(next_btn, False, False, 0)

        diary_box.pack_start(navbar, False, False, 0)

        # ── Search bar (hidden by default) ──────────────────────────────
        self.search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_bar.set_margin_start(10)
        self.search_bar.set_margin_end(10)
        self.search_bar.set_margin_top(4)
        self.search_bar.set_no_show_all(True)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search your diary...")
        self.search_entry.connect("changed", self._on_search_changed)
        self.search_bar.pack_start(self.search_entry, True, True, 0)

        search_close = Gtk.Button(label="\u2715")
        search_close.connect("clicked", self._on_toggle_search)
        self.search_bar.pack_end(search_close, False, False, 0)

        diary_box.pack_start(self.search_bar, False, False, 0)

        # Search results (hidden by default)
        self.search_results_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2
        )
        self.search_results_box.set_margin_start(10)
        self.search_results_box.set_margin_end(10)
        self.search_results_box.set_no_show_all(True)

        self.search_scroll = Gtk.ScrolledWindow()
        self.search_scroll.set_max_content_height(150)
        self.search_scroll.set_propagate_natural_height(True)
        self.search_scroll.add(self.search_results_box)
        self.search_scroll.set_no_show_all(True)

        diary_box.pack_start(self.search_scroll, False, False, 0)

        # ── Prompt bar ──────────────────────────────────────────────────
        self.prompt_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.prompt_bar.get_style_context().add_class("prompt-bar")

        self.prompt_label = Gtk.Label()
        self.prompt_label.get_style_context().add_class("prompt-text")
        self.prompt_label.set_line_wrap(True)
        self.prompt_label.set_xalign(0)
        self._update_prompt()
        self.prompt_bar.pack_start(self.prompt_label, True, True, 4)

        dismiss_btn = Gtk.Button(label="\u2715")
        dismiss_btn.get_style_context().add_class("prompt-dismiss")
        dismiss_btn.connect("clicked", self._on_dismiss_prompt)
        self.prompt_bar.pack_end(dismiss_btn, False, False, 4)

        diary_box.pack_start(self.prompt_bar, False, False, 0)

        # ── Formatting toolbar ──────────────────────────────────────────
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.get_style_context().add_class("fmt-toolbar")

        for label, tag_name in [("B", "bold"), ("I", "italic"), ("U", "underline")]:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("fmt-btn")
            btn.connect("clicked", self._on_format_toggle, tag_name)
            toolbar.pack_start(btn, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.pack_start(sep, False, False, 4)

        bullet_btn = Gtk.Button(label="\u2022")
        bullet_btn.set_tooltip_text("Bullet list")
        bullet_btn.get_style_context().add_class("fmt-btn")
        bullet_btn.connect("clicked", self._on_bullet_list)
        toolbar.pack_start(bullet_btn, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        toolbar.pack_start(sep2, False, False, 4)

        for color_name, color_hex in TEXT_COLORS.items():
            cbtn = Gtk.Button()
            cbtn.set_size_request(28, 28)
            cbtn.get_style_context().add_class("color-btn")
            # Use inline CSS for per-button background color
            color_provider = Gtk.CssProvider()
            color_provider.load_from_data(
                f"button {{ background: {color_hex}; }}".encode()
            )
            cbtn.get_style_context().add_provider(
                color_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
            )
            cbtn.connect("clicked", self._on_color_pick, color_name)
            toolbar.pack_start(cbtn, False, False, 0)

        diary_box.pack_start(toolbar, False, False, 0)

        # ── Notebook area ───────────────────────────────────────────────
        notebook_frame = Gtk.Frame()
        notebook_frame.get_style_context().add_class("notebook-frame")

        self.textview = Gtk.TextView()
        self.textview.get_style_context().add_class("notebook-text")
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_left_margin(26)
        self.textview.set_right_margin(16)
        self.textview.set_top_margin(12)
        self.textview.set_bottom_margin(12)
        self._apply_font_to_textview()

        # Draw notebook decorations on the textview
        # We use "draw" with after=True so we draw on top of the background but
        # the text renders on top of our lines
        self.textview.connect_after("draw", self._on_draw_notebook_lines)

        self.textbuffer = self.textview.get_buffer()
        self._setup_text_tags()

        # Auto-save on text change (debounced)
        self._save_timeout_id = None
        self.textbuffer.connect("changed", self._on_text_changed)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)
        notebook_frame.add(scroll)

        diary_box.pack_start(notebook_frame, True, True, 0)

        self.stack.add_named(diary_box, "diary")

    def _update_title_label(self):
        name = GLib.markup_escape_text(self.prefs["diary_name"])
        self.title_label.set_markup(
            f'<span color="#c8bc98" weight="bold">{name}</span>'
        )

    def _update_date_label(self):
        today = datetime.date.today()
        if self.current_date.year != today.year:
            date_str = f"{self.current_date.strftime('%A')}, {self.current_date.strftime('%B')} {self.current_date.day}, {self.current_date.year}"
        else:
            date_str = f"{self.current_date.strftime('%A')}, {self.current_date.strftime('%B')} {self.current_date.day}"
        self.date_label.set_markup(
            f'<span weight="bold" color="#d4c8a8">{date_str}</span>'
        )

    def _update_prompt(self):
        if self.prompt_dismissed:
            self.prompt_bar.hide()
            return
        date_str = self.current_date.isoformat()
        prompt = get_prompt(date_str)
        self.prompt_label.set_markup(
            f'<span color="#8a6a20">\U0001F31F {prompt}</span>'
        )
        self.prompt_bar.show()

    def _resolve_font_family(self):
        """Find the first available font from the family fallback chain."""
        families = [f.strip() for f in self._font_family().split(",")]
        # Get list of installed font families
        context = self.textview.get_pango_context()
        installed = {f.get_name() for f in context.list_families()}
        for fam in families:
            if fam in installed:
                return fam
        # Fallback — return the last entry (generic like 'sans-serif')
        return families[-1] if families else "sans"

    def _apply_font_to_textview(self):
        family = self._resolve_font_family()
        size = self.prefs["font_size"]
        # Remove old CSS provider if it exists
        if hasattr(self, '_font_css') and self._font_css:
            self.textview.get_style_context().remove_provider(self._font_css)
        # Apply font via both CSS and override for maximum compatibility
        font_css = Gtk.CssProvider()
        font_css.load_from_data(
            f'.notebook-text {{ font-family: "{family}"; font-size: {size}pt; }}'.encode()
        )
        self.textview.get_style_context().add_provider(
            font_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
        )
        self._font_css = font_css
        font_desc = Pango.FontDescription(f"{family} {size}")
        self.textview.override_font(font_desc)
        # Set line spacing so text aligns with notebook ruled lines
        self.textview.set_pixels_below_lines(int(size * 0.35))
        self.textview.set_pixels_above_lines(0)

    def _on_draw_notebook_lines(self, widget, cr):
        """Draw ruled lines and margin line on the textview."""
        alloc = widget.get_allocation()
        width = alloc.width
        height = alloc.height

        # Get actual line height from font metrics + spacing
        context = widget.get_pango_context()
        font_desc = widget.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        metrics = context.get_metrics(font_desc, None)
        ascent = metrics.get_ascent() / Pango.SCALE
        descent = metrics.get_descent() / Pango.SCALE
        below = widget.get_pixels_below_lines()
        above = widget.get_pixels_above_lines()
        line_height = int(ascent + descent + above + below)
        if line_height < 20:
            line_height = int(self.prefs["font_size"] * 1.6)
        top_margin = widget.get_top_margin()

        # Draw ruled lines
        rgba = Gdk.RGBA()
        rgba.parse("#e0d8c0")
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.5)
        cr.set_line_width(1)
        y = top_margin + ascent + descent + below
        while y < height:
            cr.move_to(0, int(y) + 0.5)
            cr.line_to(width, int(y) + 0.5)
            cr.stroke()
            y += line_height

        # Red margin line
        rgba.parse("#c88888")
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.5)
        cr.set_line_width(2)
        margin_x = 14
        cr.move_to(margin_x, 0)
        cr.line_to(margin_x, height)
        cr.stroke()

        return False  # Let GTK continue drawing the text on top

    def _setup_text_tags(self):
        buf = self.textbuffer
        buf.create_tag("bold", weight=Pango.Weight.BOLD)
        buf.create_tag("italic", style=Pango.Style.ITALIC)
        buf.create_tag("underline", underline=Pango.Underline.SINGLE)
        for color_name, hex_val in TEXT_COLORS.items():
            buf.create_tag(f"color-{color_name}", foreground=hex_val)
        buf.create_tag("bullet-indent", left_margin=72)

    # ── Navigation ──────────────────────────────────────────────────────

    def _cancel_autosave(self):
        if self._save_timeout_id:
            GLib.source_remove(self._save_timeout_id)
            self._save_timeout_id = None

    def _on_prev_day(self, widget):
        self._cancel_autosave()
        self._save_current_entry()
        self.current_date -= datetime.timedelta(days=1)
        self.prompt_dismissed = False
        self._update_date_label()
        self._update_prompt()
        self._load_current_entry()

    def _on_next_day(self, widget):
        self._cancel_autosave()
        self._save_current_entry()
        self.current_date += datetime.timedelta(days=1)
        self.prompt_dismissed = False
        self._update_date_label()
        self._update_prompt()
        self._load_current_entry()

    def _mark_calendar_entries(self, cal):
        """Mark days that have diary entries on the calendar."""
        cal.clear_marks()
        y, m, _d = cal.get_date()
        m += 1  # GtkCalendar months are 0-based
        entries_dir = os.path.join(self.storage_path, "entries")
        if not os.path.isdir(entries_dir):
            return
        prefix = f"{y:04d}-{m:02d}-"
        for filename in os.listdir(entries_dir):
            if filename.startswith(prefix) and filename.endswith(".html"):
                try:
                    day = int(filename[len(prefix):len(prefix)+2])
                    cal.mark_day(day)
                except (ValueError, IndexError):
                    pass

    def _on_show_calendar(self, widget):
        dialog = Gtk.Dialog(
            title="Pick a date", parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.set_default_size(300, 250)
        cal = Gtk.Calendar()
        cal.select_month(self.current_date.month - 1, self.current_date.year)
        cal.select_day(self.current_date.day)
        # Mark days with entries and re-mark when month changes
        self._mark_calendar_entries(cal)
        cal.connect("month-changed", lambda w: self._mark_calendar_entries(w))
        dialog.get_content_area().pack_start(cal, True, True, 0)
        cal.connect(
            "day-selected-double-click",
            lambda w: dialog.response(Gtk.ResponseType.OK),
        )
        dialog.add_button("Go", Gtk.ResponseType.OK)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self._cancel_autosave()
            self._save_current_entry()
            y, m, d = cal.get_date()
            self.current_date = datetime.date(y, m + 1, d)
            self.prompt_dismissed = False
            self._update_date_label()
            self._update_prompt()
            self._load_current_entry()
        dialog.destroy()

    def _on_dismiss_prompt(self, widget):
        self.prompt_dismissed = True
        self.prompt_bar.hide()
        self.textview.grab_focus()

    # ── Formatting ──────────────────────────────────────────────────────

    def _on_format_toggle(self, widget, tag_name):
        buf = self.textbuffer
        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
            if start.has_tag(buf.get_tag_table().lookup(tag_name)):
                buf.remove_tag_by_name(tag_name, start, end)
            else:
                buf.apply_tag_by_name(tag_name, start, end)

    def _on_bullet_list(self, widget):
        buf = self.textbuffer
        mark = buf.get_insert()
        iter_pos = buf.get_iter_at_mark(mark)
        line_start = buf.get_iter_at_line(iter_pos.get_line())
        line_end = line_start.copy()
        if not line_end.ends_line():
            line_end.forward_to_line_end()
        line_text = buf.get_text(line_start, line_end, True)
        if line_text.startswith("\u2022 "):
            # Remove bullet
            bullet_end = line_start.copy()
            bullet_end.forward_chars(2)
            buf.delete(line_start, bullet_end)
            # Refresh line_end after deletion
            line_end = buf.get_iter_at_line(iter_pos.get_line())
            if not line_end.ends_line():
                line_end.forward_to_line_end()
            buf.remove_tag_by_name(
                "bullet-indent", line_start, line_end
            )
        else:
            buf.insert(line_start, "\u2022 ")
            line_end = buf.get_iter_at_line(iter_pos.get_line())
            if not line_end.ends_line():
                line_end.forward_to_line_end()
            buf.apply_tag_by_name(
                "bullet-indent",
                buf.get_iter_at_line(iter_pos.get_line()),
                line_end,
            )

    def _on_color_pick(self, widget, color_name):
        buf = self.textbuffer
        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
            # Remove existing color tags
            for cn in ["green", "blue", "purple", "red"]:
                buf.remove_tag_by_name(f"color-{cn}", start, end)
            buf.apply_tag_by_name(f"color-{color_name}", start, end)

    def _on_key_press(self, widget, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK
        key = Gdk.keyval_name(event.keyval)

        if ctrl and not shift:
            if key == "b":
                self._on_format_toggle(None, "bold")
                return True
            elif key == "i":
                self._on_format_toggle(None, "italic")
                return True
            elif key == "u":
                self._on_format_toggle(None, "underline")
                return True
            elif key == "l":
                self._on_bullet_list(None)
                return True
            elif key == "f":
                self._on_toggle_search(None)
                return True
        if ctrl and shift and key == "P":
            self._on_show_parent_settings(None)
            return True
        return False

    # ── Save / Load ─────────────────────────────────────────────────────

    def _load_current_entry(self):
        date_str = self.current_date.isoformat()
        path = entry_path(self.storage_path, date_str)
        html = load_entry_html(path)
        html_to_buffer(self.textbuffer, html)

    def _save_current_entry(self):
        html = buffer_to_html(self.textbuffer)
        if html or self._entry_exists():
            date_str = self.current_date.isoformat()
            path = entry_path(self.storage_path, date_str)
            save_entry_html(path, html)

    def _entry_exists(self):
        date_str = self.current_date.isoformat()
        path = entry_path(self.storage_path, date_str)
        return os.path.exists(path)

    def _on_text_changed(self, buf):
        if self._save_timeout_id:
            GLib.source_remove(self._save_timeout_id)
        self._save_timeout_id = GLib.timeout_add(1500, self._autosave)

    def _autosave(self):
        self._save_current_entry()
        self._save_timeout_id = None
        return False  # Don't repeat

    # ── Search ──────────────────────────────────────────────────────────

    def _on_toggle_search(self, widget):
        if self.search_bar.get_visible():
            self.search_bar.hide()
            self.search_scroll.hide()
            self.search_results_box.hide()
            self.textview.grab_focus()
        else:
            self.search_bar.show_all()
            self.search_entry.set_text("")
            self.search_entry.grab_focus()
            # Clear old results
            for child in self.search_results_box.get_children():
                self.search_results_box.remove(child)

    def _on_search_changed(self, entry):
        query = entry.get_text().strip()
        # Clear old results
        for child in self.search_results_box.get_children():
            self.search_results_box.remove(child)
        if len(query) < 2:
            self.search_scroll.hide()
            self.search_results_box.hide()
            return
        results = search_entries(self.storage_path, query)
        if not results:
            lbl = Gtk.Label(label="No entries found.")
            lbl.set_xalign(0)
            self.search_results_box.pack_start(lbl, False, False, 2)
        else:
            for date_str, snippet in results[:20]:
                btn = Gtk.Button()
                btn.set_relief(Gtk.ReliefStyle.NONE)
                btn_label = Gtk.Label()
                btn_label.set_markup(
                    f'<b>{date_str}</b>  <span color="#666">{GLib.markup_escape_text(snippet)}</span>'
                )
                btn_label.set_xalign(0)
                btn_label.set_ellipsize(Pango.EllipsizeMode.END)
                btn.add(btn_label)
                btn.connect("clicked", self._on_search_result_click, date_str)
                self.search_results_box.pack_start(btn, False, False, 0)
        self.search_scroll.show_all()
        self.search_results_box.show_all()

    def _on_search_result_click(self, widget, date_str):
        self._cancel_autosave()
        self._save_current_entry()
        y, m, d = date_str.split("-")
        self.current_date = datetime.date(int(y), int(m), int(d))
        self.prompt_dismissed = True
        self._update_date_label()
        self._update_prompt()
        self._load_current_entry()
        self._on_toggle_search(None)

    # ── Kid Settings ────────────────────────────────────────────────────

    def _on_show_settings(self, widget):
        self._cancel_autosave()
        self._save_current_entry()

        dialog = Gtk.Dialog(
            title="Settings", parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.set_default_size(500, 400)
        dialog.add_button("Done", Gtk.ResponseType.OK)

        # Wrap everything in a scrolled window for small screens
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(350)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        scroll.add(content)
        dialog.get_content_area().pack_start(scroll, True, True, 0)

        # ── Row 1: Name + Size side by side ─────────────────────────────
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_label = Gtk.Label()
        name_label.set_markup("<b>\u270F Name</b>")
        name_label.set_xalign(0)
        name_box.pack_start(name_label, False, False, 0)
        name_entry = Gtk.Entry()
        name_entry.set_text(self.prefs["diary_name"])
        name_box.pack_start(name_entry, False, False, 0)
        row1.pack_start(name_box, True, True, 0)

        size_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        size_label = Gtk.Label()
        size_label.set_markup("<b>\U0001F524 Size</b>")
        size_label.set_xalign(0)
        size_box.pack_start(size_label, False, False, 0)
        size_slider = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        size_adj = Gtk.Adjustment(
            value=self.prefs["font_size"], lower=16, upper=32,
            step_increment=1, page_increment=4,
        )
        size_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=size_adj)
        size_scale.set_draw_value(True)
        size_scale.set_digits(0)
        size_scale.set_size_request(150, -1)
        size_slider.pack_start(size_scale, True, True, 0)
        size_box.pack_start(size_slider, False, False, 0)
        row1.pack_start(size_box, True, True, 0)

        content.pack_start(row1, False, False, 0)

        # ── Row 2: Font picker ───────────────────────────────────────────
        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        font_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        font_label = Gtk.Label()
        font_label.set_markup("<b>\u270D Font</b>")
        font_label.set_xalign(0)
        font_box.pack_start(font_label, False, False, 0)

        font_buttons = {}
        current_font = self.prefs["font"]
        for key, f in FONTS.items():
            btn = Gtk.RadioButton.new_with_label_from_widget(
                list(font_buttons.values())[0] if font_buttons else None,
                f["label"],
            )
            btn.set_active(key == current_font)
            family = f["family"].split(",")[0].strip()
            child = btn.get_child()
            if child:
                child.set_markup(
                    f'<span font_family="{family}">{f["label"]}</span>'
                )
            font_box.pack_start(btn, False, False, 0)
            font_buttons[key] = btn

        row2.pack_start(font_box, True, True, 0)

        content.pack_start(row2, False, False, 0)

        # ── Row 3: Password ─────────────────────────────────────────────
        pw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pw_icon = Gtk.Label()
        pw_icon.set_markup("<b>\U0001F512</b>")
        pw_row.pack_start(pw_icon, False, False, 0)
        pw_entry1 = Gtk.Entry()
        pw_entry1.set_visibility(False)
        pw_entry1.set_placeholder_text("New password...")
        pw_row.pack_start(pw_entry1, True, True, 0)
        pw_entry2 = Gtk.Entry()
        pw_entry2.set_visibility(False)
        pw_entry2.set_placeholder_text("Confirm...")
        pw_row.pack_start(pw_entry2, True, True, 0)
        pw_change_btn = Gtk.Button(label="Change")
        pw_row.pack_start(pw_change_btn, False, False, 0)
        content.pack_start(pw_row, False, False, 0)

        pw_status = Gtk.Label()
        pw_status.set_xalign(0)
        content.pack_start(pw_status, False, False, 0)

        def on_pw_change(btn):
            p1 = pw_entry1.get_text()
            p2 = pw_entry2.get_text()
            if not p1:
                pw_status.set_markup('<span color="#c62828">Enter a password!</span>')
                return
            if p1 != p2:
                pw_status.set_markup('<span color="#c62828">Passwords don\'t match!</span>')
                return
            self.prefs["password_hash"] = hash_password(p1)
            save_prefs(self.prefs, self.prefs_path)
            pw_entry1.set_text("")
            pw_entry2.set_text("")
            pw_status.set_markup('<span color="#2e7d32">Password changed!</span>')

        pw_change_btn.connect("clicked", on_pw_change)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # ── Save settings ───────────────────────────────────────────
            self.prefs["diary_name"] = name_entry.get_text() or "Big Thoughts"
            self.prefs["font_size"] = int(size_adj.get_value())
            for key, btn in font_buttons.items():
                if btn.get_active():
                    self.prefs["font"] = key
                    break

            save_prefs(self.prefs, self.prefs_path)
            self._apply_font_to_textview()
            self._update_title_label()
            self._update_date_label()
            self._update_prompt()

        dialog.destroy()

    # ── Parent Settings ─────────────────────────────────────────────────

    def _on_show_parent_settings(self, widget):
        self._cancel_autosave()
        self._save_current_entry()

        dialog = Gtk.Dialog(
            title="Parent Settings", parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        dialog.set_default_size(400, 250)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)

        # Header
        header = Gtk.Label()
        header.set_markup('<span weight="bold" size="14000">\U0001F527 Parent Settings</span>')
        header.set_xalign(0)
        content.pack_start(header, False, False, 0)

        # ── Password reset ──────────────────────────────────────────────
        pw_label = Gtk.Label()
        pw_label.set_markup("<b>\U0001F512 Password Reset</b>")
        pw_label.set_xalign(0)
        content.pack_start(pw_label, False, False, 0)

        pw_desc = Gtk.Label(
            label="Clears the current password. Next launch will ask to set a new one."
        )
        pw_desc.set_xalign(0)
        pw_desc.set_line_wrap(True)
        pw_desc.set_opacity(0.6)
        content.pack_start(pw_desc, False, False, 0)

        reset_btn = Gtk.Button(label="Reset Password")
        reset_btn.set_halign(Gtk.Align.START)

        pw_status = Gtk.Label()

        def on_reset_password(btn):
            self.prefs["password_hash"] = ""
            save_prefs(self.prefs, self.prefs_path)
            pw_status.set_markup(
                '<span color="#2e7d32">Password cleared. Diary is now open.</span>'
            )

        reset_btn.connect("clicked", on_reset_password)
        content.pack_start(reset_btn, False, False, 0)
        content.pack_start(pw_status, False, False, 0)

        # ── Storage location ────────────────────────────────────────────
        sep = Gtk.Separator()
        content.pack_start(sep, False, False, 0)

        loc_label = Gtk.Label()
        loc_label.set_markup("<b>\U0001F4C1 Storage Location</b>")
        loc_label.set_xalign(0)
        content.pack_start(loc_label, False, False, 0)

        loc_desc = Gtk.Label(
            label="Where diary entries are stored. Changing moves all entries."
        )
        loc_desc.set_xalign(0)
        loc_desc.set_line_wrap(True)
        loc_desc.set_opacity(0.6)
        content.pack_start(loc_desc, False, False, 0)

        loc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        loc_entry = Gtk.Entry()
        loc_entry.set_text(self.prefs["storage_path"])
        loc_box.pack_start(loc_entry, True, True, 0)

        loc_status = Gtk.Label()

        def on_save_location(btn):
            new_path = loc_entry.get_text().strip()
            if not new_path:
                return
            new_path = os.path.expanduser(new_path)
            old_path = self.prefs["storage_path"]
            if new_path == old_path:
                return
            try:
                # Move entries
                old_entries = os.path.join(old_path, "entries")
                new_entries = os.path.join(new_path, "entries")
                os.makedirs(new_path, exist_ok=True)
                if os.path.isdir(old_entries):
                    if os.path.exists(new_entries):
                        # Merge
                        for f in os.listdir(old_entries):
                            shutil.move(
                                os.path.join(old_entries, f),
                                os.path.join(new_entries, f),
                            )
                    else:
                        shutil.move(old_entries, new_entries)
                os.chmod(new_path, 0o700)
                self.prefs["storage_path"] = new_path
                self.storage_path = new_path
                # Update prefs path to new location
                self.prefs_path = os.path.join(new_path, "prefs.json")
                save_prefs(self.prefs, self.prefs_path)
                ensure_storage_dir(new_path)
                loc_status.set_markup(
                    f'<span color="#2e7d32">Moved to {new_path}</span>'
                )
            except Exception as e:
                loc_status.set_markup(
                    f'<span color="#c62828">Error: {GLib.markup_escape_text(str(e))}</span>'
                )

        loc_save_btn = Gtk.Button(label="Save")
        loc_save_btn.connect("clicked", on_save_location)
        loc_box.pack_end(loc_save_btn, False, False, 0)
        content.pack_start(loc_box, False, False, 0)
        content.pack_start(loc_status, False, False, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

        # If password was cleared while on lock screen, go to diary
        if not self.prefs["password_hash"]:
            self.stack.set_visible_child_name("diary")
            self._load_current_entry()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    app = BigThoughtsApp()
    Gtk.main()


if __name__ == "__main__":
    main()
