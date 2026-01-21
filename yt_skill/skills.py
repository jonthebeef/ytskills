"""Skill extraction using Claude CLI."""

import subprocess
import re
from pathlib import Path
from typing import Optional


SKILLS_DIR = Path.home() / ".claude" / "skills"

EXTRACTION_PROMPT = """You are analyzing a YouTube video transcript to extract actionable skills, methodologies, and techniques that can be turned into a Claude Code skill.

A Claude Code skill is a markdown file (SKILL.md) that teaches Claude how to perform a specific task. Skills should be:
- Actionable and specific
- Have clear step-by-step instructions
- Include examples where helpful
- Be reusable across different contexts

VIDEO TITLE: {title}
CHANNEL: {channel}

TRANSCRIPT:
{transcript}

---

Based on this video, extract the most valuable skill or methodology being taught. If the video covers multiple distinct skills, focus on the primary/most important one.

Output a complete SKILL.md file in this format:

```markdown
# [Skill Name]

[One paragraph description of what this skill does and when to use it]

## When to Use This Skill

- [Bullet points of scenarios when this skill applies]

## Instructions

[Step-by-step instructions for Claude to follow when using this skill. Be specific and actionable.]

### Step 1: [Step Name]
[Details]

### Step 2: [Step Name]
[Details]

[Continue as needed]

## Examples

[Optional: Include 1-2 concrete examples if they help clarify the skill]

## Tips

- [Any important tips, gotchas, or best practices mentioned in the video]
```

Only output the markdown content, nothing else. If the video doesn't contain any actionable skill or methodology worth extracting, output: NO_SKILL_FOUND"""


def extract_skill(
    transcript: str,
    title: str,
    channel: str,
) -> Optional[str]:
    """
    Use Claude CLI to extract a skill from a video transcript.
    Returns the SKILL.md content or None if no skill found.
    """
    # Truncate transcript if too long (keep ~100k chars for context)
    max_chars = 100_000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[Transcript truncated...]"

    prompt = EXTRACTION_PROMPT.format(
        title=title,
        channel=channel,
        transcript=transcript
    )

    # Call claude CLI with -p (print mode) for non-interactive output
    # Using stdin to pass long prompts safely
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=300  # 5 min timeout for long transcripts
    )

    content = result.stdout.strip()

    if not content or "NO_SKILL_FOUND" in content:
        return None

    # Clean up markdown code blocks if present
    if content.startswith("```markdown"):
        content = content[11:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def generate_skill_name(title: str) -> str:
    """Generate a kebab-case skill name from video title."""
    # Remove common prefixes/suffixes
    name = title.lower()
    name = re.sub(r'^(how to|how i|my|the|a|an)\s+', '', name)
    name = re.sub(r'\s+(tutorial|guide|explained|walkthrough)$', '', name)

    # Convert to kebab-case
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    name = name.strip('-')

    # Limit length
    if len(name) > 50:
        name = name[:50].rsplit('-', 1)[0]

    return name or "extracted-skill"


def save_skill(skill_content: str, skill_name: str) -> Path:
    """Save a skill to the Claude skills directory."""
    skill_dir = SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(skill_content, encoding="utf-8")

    return skill_path


def list_existing_skills() -> list[str]:
    """List all existing skills in the skills directory."""
    if not SKILLS_DIR.exists():
        return []

    skills = []
    for path in SKILLS_DIR.iterdir():
        if path.is_dir() and (path / "SKILL.md").exists():
            skills.append(path.name)

    return sorted(skills)
