#!/usr/bin/env python3
"""Add YAML frontmatter to skills that don't have it."""

import re
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"


def extract_description(content: str) -> str:
    """Extract a description from the skill content."""
    # Skip any existing frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    # Try to find the first paragraph after the title
    lines = content.strip().split("\n")
    description_lines = []
    in_description = False

    for line in lines:
        # Skip the title
        if line.startswith("# "):
            in_description = True
            continue

        if in_description:
            # Stop at next heading or empty line after content
            if line.startswith("#"):
                break
            if line.strip() == "" and description_lines:
                break
            if line.strip():
                description_lines.append(line.strip())

    description = " ".join(description_lines)

    # Truncate to ~200 chars for frontmatter
    if len(description) > 200:
        description = description[:197] + "..."

    return description or "A skill extracted from YouTube content."


def add_frontmatter(skill_path: Path) -> bool:
    """Add frontmatter to a skill file if missing."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return False

    content = skill_file.read_text(encoding="utf-8")

    # Check if already has frontmatter
    if content.strip().startswith("---"):
        return False

    # Get skill name from directory
    name = skill_path.name

    # Extract description from content
    description = extract_description(content)

    # Escape any quotes in description
    description = description.replace('"', '\\"')

    # Create frontmatter
    frontmatter = f'''---
name: {name}
description: "{description}"
---

'''

    # Prepend frontmatter
    new_content = frontmatter + content
    skill_file.write_text(new_content, encoding="utf-8")

    return True


def main():
    updated = 0
    skipped = 0

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue

        if add_frontmatter(skill_dir):
            print(f"✓ Updated: {skill_dir.name}")
            updated += 1
        else:
            skipped += 1

    print(f"\nDone! Updated {updated} skills, skipped {skipped} (already had frontmatter)")


if __name__ == "__main__":
    main()
