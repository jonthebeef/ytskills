"""TUI application for YT Skill."""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Input, Button,
    ProgressBar, Label, ListItem, ListView
)
from textual.binding import Binding
from textual.message import Message
from textual import work

from .youtube import (
    get_channel_videos, get_video_info, get_transcript,
    format_duration, format_views, VideoInfo
)
from .skills import (
    extract_skill, generate_skill_name, save_skill,
    list_existing_skills, SKILLS_DIR
)


ASCII_LOGO = """
[bold cyan]██╗   ██╗████████╗    ███████╗██╗  ██╗██╗██╗     ██╗
╚██╗ ██╔╝╚══██╔══╝    ██╔════╝██║ ██╔╝██║██║     ██║
 ╚████╔╝    ██║       ███████╗█████╔╝ ██║██║     ██║
  ╚██╔╝     ██║       ╚════██║██╔═██╗ ██║██║     ██║
   ██║      ██║       ███████║██║  ██╗██║███████╗███████╗
   ╚═╝      ╚═╝       ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝[/bold cyan]
[dim]              Learning from YouTube, one video at a time[/dim]
"""


class VideoCard(Container):
    """Display a video with its info and processing status."""

    class Selected(Message):
        def __init__(self, video: VideoInfo) -> None:
            self.video = video
            super().__init__()

    def __init__(self, video: VideoInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self.video = video
        self.status = "pending"  # pending, processing, done, error

    def compose(self) -> ComposeResult:
        yield Static(self._render_content(), id="video-content")

    def _render_content(self) -> str:
        status_colors = {
            "pending": "white",
            "processing": "yellow",
            "done": "green",
            "error": "red"
        }
        status_text = {
            "pending": "Ready",
            "processing": "Analyzing with AI...",
            "done": "Skill extracted!",
            "error": "Failed"
        }
        color = status_colors[self.status]
        title = self.video.title[:50] + "..." if len(self.video.title) > 50 else self.video.title

        return f"""[bold]{title}[/bold]
[dim]{format_duration(self.video.duration)} | {format_views(self.video.view_count)} views[/dim]
[{color}]{status_text[self.status]}[/{color}]"""

    def update_status(self, status: str) -> None:
        self.status = status
        self.query_one("#video-content", Static).update(self._render_content())


class SkillList(Container):
    """Display list of extracted skills."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.skills: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static(self._render_content(), id="skills-content")

    def _render_content(self) -> str:
        if not self.skills:
            return "[dim]No skills extracted yet[/dim]"

        lines = [f"[bold magenta]Skill Library ({len(self.skills)} skills)[/bold magenta]"]
        for skill in self.skills[-10:]:  # Show last 10
            lines.append(f"  [green]+[/green] {skill}")

        return "\n".join(lines)

    def add_skill(self, name: str) -> None:
        if name not in self.skills:
            self.skills.append(name)
        self.query_one("#skills-content", Static).update(self._render_content())

    def refresh_skills(self) -> None:
        self.skills = list_existing_skills()
        self.query_one("#skills-content", Static).update(self._render_content())


class YTSkillApp(App):
    """Main YT Skill application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #logo {
        height: auto;
        padding: 1;
        text-align: center;
    }

    #url-input {
        margin: 1 2;
    }

    #main-container {
        height: 1fr;
        padding: 1 2;
    }

    #left-panel {
        width: 1fr;
    }

    #channel-info {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #video-list {
        height: 1fr;
        border: solid $secondary;
        padding: 1;
    }

    .video-card {
        height: auto;
        border: solid $primary-lighten-2;
        padding: 1;
        margin-bottom: 1;
    }

    .video-card:hover {
        border: solid $accent;
    }

    #skills-panel {
        width: 40;
        border: solid magenta;
        padding: 1;
        margin-left: 1;
    }

    #status-line {
        height: auto;
        padding: 0 2;
        color: $text-muted;
    }

    #progress-container {
        height: auto;
        padding: 1 2;
    }

    ProgressBar {
        padding: 0 2;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh Skills"),
        Binding("enter", "process", "Process Videos"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.videos: list[VideoInfo] = []
        self.current_channel = ""
        self.processing = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(ASCII_LOGO, id="logo")
        yield Input(placeholder="Enter YouTube channel or video URL...", id="url-input")

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield Static("", id="channel-info")
                yield ScrollableContainer(id="video-list")

            yield SkillList(id="skills-panel")

        yield Static("", id="status-line")

        with Horizontal(id="progress-container"):
            yield ProgressBar(total=100, show_eta=False, id="progress")
            yield Button("Process All", id="process-btn", variant="primary")
            yield Button("Stop", id="stop-btn", variant="error", disabled=True)

        yield Footer()

    def on_mount(self) -> None:
        self.query_one(SkillList).refresh_skills()
        self.query_one("#url-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        url = event.value.strip()
        if not url:
            return

        self.query_one("#channel-info", Static).update("[yellow]Loading...[/yellow]")
        self.load_videos(url)

    def set_status(self, msg: str) -> None:
        """Update the status line."""
        self.query_one("#status-line", Static).update(f"[dim]{msg}[/dim]")

    @work(exclusive=True)
    async def load_videos(self, url: str) -> None:
        """Load videos from URL in background."""
        try:
            self.set_status("Fetching videos...")

            # Check if it's a single video or channel
            if "watch?v=" in url or "youtu.be/" in url:
                video = await asyncio.to_thread(get_video_info, url)
                self.videos = [video]
                self.current_channel = video.channel
            else:
                self.videos = await asyncio.to_thread(get_channel_videos, url, 50)
                # Extract channel name from URL if not in video data
                if self.videos:
                    self.current_channel = self.videos[0].channel
                    if not self.current_channel or self.current_channel == "Unknown":
                        # Try to extract from URL
                        if "/@" in url:
                            self.current_channel = url.split("/@")[1].split("/")[0]
                        elif "/c/" in url:
                            self.current_channel = url.split("/c/")[1].split("/")[0]
                        else:
                            self.current_channel = "YouTube Channel"

            self._update_video_list()
            self.set_status(f"Loaded {len(self.videos)} videos. Press 'Process All' to start.")

        except Exception as e:
            self.query_one("#channel-info", Static).update(f"[red]Error: {e}[/red]")
            self.set_status(f"Error: {e}")

    def _update_video_list(self) -> None:
        """Update the video list display."""
        channel_info = self.query_one("#channel-info", Static)
        channel_info.update(
            f"[bold cyan]Channel: {self.current_channel}[/bold cyan]\n"
            f"{len(self.videos)} videos to process"
        )

        video_list = self.query_one("#video-list", ScrollableContainer)
        video_list.remove_children()

        for video in self.videos:
            card = VideoCard(video, classes="video-card")
            video_list.mount(card)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "process-btn":
            if not self.processing and self.videos:
                self.process_videos()
        elif event.button.id == "stop-btn":
            self.processing = False

    @work(exclusive=True)
    async def process_videos(self) -> None:
        """Process all videos and extract skills."""
        self.processing = True
        self.query_one("#process-btn", Button).disabled = True
        self.query_one("#stop-btn", Button).disabled = False

        progress = self.query_one("#progress", ProgressBar)
        total = len(self.videos)
        completed = 0
        errors = 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for i, video in enumerate(self.videos):
                if not self.processing:
                    self.set_status("Stopped by user.")
                    break

                # Update progress
                pct = ((i + 1) / total) * 100
                progress.update(progress=pct)
                self.set_status(f"[{i+1}/{total}] Fetching transcript: {video.title[:40]}...")

                # Find the video card
                cards = self.query(VideoCard)
                card = None
                for c in cards:
                    if c.video.id == video.id:
                        card = c
                        break

                if card:
                    card.update_status("processing")

                try:
                    # Get transcript
                    transcript = await asyncio.to_thread(
                        get_transcript, video.url, tmp_path / video.id
                    )

                    if not transcript:
                        self.set_status(f"[{i+1}/{total}] No transcript available for: {video.title[:40]}")
                        if card:
                            card.update_status("error")
                        errors += 1
                        continue

                    # Extract skill
                    self.set_status(f"[{i+1}/{total}] Extracting skill with Claude: {video.title[:40]}...")
                    skill_content = await asyncio.to_thread(
                        extract_skill,
                        transcript,
                        video.title,
                        video.channel
                    )

                    if skill_content:
                        skill_name = generate_skill_name(video.title)
                        save_skill(skill_content, skill_name)

                        self.query_one(SkillList).add_skill(skill_name)
                        self.set_status(f"[{i+1}/{total}] Skill saved: {skill_name}")

                        if card:
                            card.update_status("done")
                        completed += 1
                    else:
                        self.set_status(f"[{i+1}/{total}] No skill extracted from: {video.title[:40]}")
                        if card:
                            card.update_status("error")
                        errors += 1

                except Exception as e:
                    self.log.error(f"Error processing {video.title}: {e}")
                    self.set_status(f"[{i+1}/{total}] Error: {str(e)[:50]}")
                    if card:
                        card.update_status("error")
                    errors += 1

        progress.update(progress=100)
        self.processing = False
        self.query_one("#process-btn", Button).disabled = False
        self.query_one("#stop-btn", Button).disabled = True
        self.set_status(f"Done! {completed} skills extracted, {errors} errors.")

    def action_refresh(self) -> None:
        self.query_one(SkillList).refresh_skills()

    def action_process(self) -> None:
        if not self.processing and self.videos:
            self.process_videos()


def main():
    """Entry point for the application."""
    app = YTSkillApp()
    app.run()


if __name__ == "__main__":
    main()
