#!/usr/bin/env python3
import re
import xml.sax.saxutils as saxutils
from pathlib import Path


def parse_skill(file_path: Path, skills_dir: Path):
    """Parse a single SKILL.md file and extract metadata."""
    with open(file_path, 'r') as file:
        content = file.read()

    match = re.search(r'^---$(.*?)^---$', content, re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError("Metadata section not found.")

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        if ': ' in line:
            key, value = line.split(': ', 1)
            metadata[key.strip()] = value.strip()

    if 'name' not in metadata or 'description' not in metadata:
        raise ValueError(f"Missing required fields 'name' and/or 'description' in {file_path}")

    relative_path = file_path.relative_to(skills_dir)
    container_path = f"/skills/{relative_path}"

    name = saxutils.escape(metadata["name"])
    description = saxutils.escape(metadata["description"])
    location = saxutils.escape(container_path)

    return (
        '<skill>\n'
        f'<name>{name}</name>\n'
        f'<description>{description}</description>\n'
        f'<location>{location}</location>\n'
        '</skill>'
    )


def find_and_parse_skills(skills_dir: Path):
    """Find all SKILL.md files and parse them into XML."""
    skills_xml = []
    skill_files = list(skills_dir.rglob("SKILL.md"))
    
    for skill_file in skill_files:
        try:
            xml_content = parse_skill(skill_file, skills_dir)
            skills_xml.append(xml_content)
        except Exception as e:
            print(f"Error parsing {skill_file}: {e}")
    
    return '\n'.join(skills_xml)
