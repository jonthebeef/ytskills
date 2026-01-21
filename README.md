# YT Skill

A terminal UI app that watches YouTube videos and extracts actionable skills for [Claude Code](https://claude.ai/code).

Feed it a YouTube channel or video, and it will:
1. Fetch transcripts using `yt-dlp`
2. Send them to Claude to extract skills/methodologies
3. Save them as `SKILL.md` files in your Claude Code skills directory

![YT Skill TUI](https://img.shields.io/badge/TUI-Textual-cyan)

## What are Claude Code Skills?

Skills are markdown files that teach Claude how to perform specific tasks. They live in `~/.claude/skills/` and Claude Code loads them dynamically when relevant. This tool automates turning YouTube tutorial content into reusable skills.

## Requirements

- Python 3.9+
- [Claude Code](https://claude.ai/code) installed and authenticated (uses `claude` CLI)
- macOS/Linux (Windows untested)

## Installation

```bash
# Clone the repo
git clone https://github.com/jonthebeef/ytskills.git
cd ytskills

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install textual yt-dlp
```

## Usage

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the app
python -m yt_skill.app
```

### In the TUI:

1. **Enter a YouTube URL** - paste a channel URL (e.g., `https://www.youtube.com/@ChannelName`) or a single video URL
2. **Press Enter** - loads the video list
3. **Click "Process All"** - starts extracting skills from each video
4. **Watch the progress** - status line shows what's happening
5. **Press `q` to quit**

### Keyboard shortcuts:

- `Enter` - Process videos
- `r` - Refresh skills list
- `q` - Quit

## Where are skills saved?

Skills are saved to `~/.claude/skills/<skill-name>/SKILL.md`

Each video becomes a skill folder. Claude Code will automatically discover and use these skills.

## How it works

```
YouTube URL
    ↓
yt-dlp (fetch transcript)
    ↓
Claude CLI (extract skill from transcript)
    ↓
~/.claude/skills/skill-name/SKILL.md
```

### Claude Code Integration

The app doesn't use the Anthropic API directly. Instead, it shells out to the `claude` CLI that comes with Claude Code:

```python
subprocess.run(["claude", "-p", prompt], capture_output=True, text=True)
```

The `-p` (print) flag runs Claude Code in non-interactive mode:
- Takes a prompt as an argument
- Sends it to Claude using your existing authentication
- Returns the response to stdout

This means:
- **No separate API key needed** - uses your Claude Code auth
- **No extra costs** - uses your existing Claude Code subscription
- **Same model access** - whatever model you have access to in Claude Code

It's essentially automating what you'd do manually: paste a transcript into Claude Code and ask "extract a skill from this".

## Limitations

- Only works with videos that have transcripts/captions (most do)
- English transcripts only (for now)
- Some videos don't contain extractable skills (entertainment, vlogs, etc.)
- Processing speed depends on transcript length and Claude's response time

## License

MIT
