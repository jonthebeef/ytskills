"""YouTube video and transcript handling using yt-dlp."""

import json
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoInfo:
    """Information about a YouTube video."""
    id: str
    title: str
    channel: str
    duration: int  # seconds
    view_count: int
    url: str
    thumbnail: Optional[str] = None


def get_channel_videos(channel_url: str, limit: int = 50) -> list[VideoInfo]:
    """Get list of videos from a YouTube channel."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(limit),
        channel_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to fetch channel: {result.stderr}")

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        videos.append(VideoInfo(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            channel=data.get("channel", data.get("uploader", "Unknown")),
            duration=data.get("duration") or 0,
            view_count=data.get("view_count") or 0,
            url=f"https://www.youtube.com/watch?v={data.get('id', '')}",
            thumbnail=data.get("thumbnail"),
        ))

    return videos


def get_video_info(video_url: str) -> VideoInfo:
    """Get info for a single video."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        video_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to fetch video: {result.stderr}")

    data = json.loads(result.stdout)
    return VideoInfo(
        id=data.get("id", ""),
        title=data.get("title", "Unknown"),
        channel=data.get("channel", data.get("uploader", "Unknown")),
        duration=data.get("duration") or 0,
        view_count=data.get("view_count") or 0,
        url=video_url,
        thumbnail=data.get("thumbnail"),
    )


def get_transcript(video_url: str, output_dir: Path) -> Optional[str]:
    """
    Fetch transcript for a YouTube video.
    Returns the transcript text or None if unavailable.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "transcript")

    # Try manual subtitles first (highest quality)
    cmd = [
        "yt-dlp",
        "--write-sub",
        "--sub-lang", "en",
        "--skip-download",
        "--output", output_template,
        video_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Check for .vtt file
    vtt_files = list(output_dir.glob("transcript*.vtt"))

    if not vtt_files:
        # Fallback to auto-generated subtitles
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--output", output_template,
            video_url
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        vtt_files = list(output_dir.glob("transcript*.vtt"))

    if not vtt_files:
        return None

    # Parse VTT to plain text
    vtt_path = vtt_files[0]
    return parse_vtt(vtt_path)


def parse_vtt(vtt_path: Path) -> str:
    """Parse VTT subtitle file to plain text, removing duplicates."""
    content = vtt_path.read_text(encoding="utf-8")

    # Remove VTT header
    lines = content.split("\n")
    text_lines = []
    seen = set()

    for line in lines:
        # Skip timestamps, headers, and empty lines
        if not line.strip():
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}", line):
            continue
        if re.match(r"^[\d\s:\.->]+$", line):
            continue

        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", line)
        clean = clean.strip()

        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    return " ".join(text_lines)


def format_duration(seconds) -> str:
    """Format duration in MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


def format_views(count: int) -> str:
    """Format view count with K/M suffix."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
