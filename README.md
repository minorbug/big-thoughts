# Big Thoughts

A simple, kid-friendly diary app with a leather-bound notebook look, daily prompts, rich text, and optional password protection.

Built for a 7-year-old on an Acer Aspire One with 1GB of RAM. Runs on any Linux or macOS machine with Python 3 and GTK3.

![Big Thoughts diary view](https://raw.githubusercontent.com/minorbug/big-thoughts/main/screenshots/diary.png)

## Features

- **Leather notebook UI** — skeuomorphic leather cover, parchment toolbar, ruled notebook paper with red margin line
- **4 fonts** — Playful, Storybook, Clean, Typewriter
- **Rich text** — bold, italic, underline, bullet lists, 4 text colors
- **Daily prompts** — rotating writing prompts to help kids get started
- **Optional password** — keeps siblings out (UI gate, not encryption)
- **Search** — find old entries by keyword
- **Auto-save** — saves as you type, on navigation, and on close
- **Calendar** — jump to any date, days with entries are marked
- **Parent settings** — Ctrl+Shift+P for password reset and storage location
- **Cross-platform** — Linux and macOS

## Install

### Linux (Debian/Ubuntu)

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

### macOS

```bash
brew install gtk+3 pygobject3
```

## Run

```bash
python3 big_thoughts.py
```

Or copy `big-thoughts.desktop` to `~/.local/share/applications/` for a menu entry on Linux.

## Storage

Entries are saved as HTML files in `~/.big-thoughts/entries/`, one per day:

```
~/.big-thoughts/
  prefs.json
  entries/
    2026-04-03.html
    2026-04-04.html
```

The directory is created with `700` permissions (owner-only). The password is a UI gate — files on disk are plain HTML protected by filesystem permissions, not encryption.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+B | Bold |
| Ctrl+I | Italic |
| Ctrl+U | Underline |
| Ctrl+L | Bullet list |
| Ctrl+F | Search |
| Ctrl+Shift+P | Parent settings |

## Screenshots

### Lock screen
![Lock screen](https://raw.githubusercontent.com/minorbug/big-thoughts/main/screenshots/lock.png)

## Requirements

- Python 3.8+
- GTK 3.20+
- PyGObject (python3-gi)

Runs comfortably in ~45MB of RAM.

## License

MIT
