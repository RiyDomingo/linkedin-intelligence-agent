#!/usr/bin/env python3
"""Copy the complete skill pack to an explicit discovery directory, without overwrites."""
import argparse
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parent.parent / 'skills'


def install(destination):
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError(f'symlink destination refused: {destination}')
    destination = destination.parent.resolve() / destination.name
    for component in (destination, *destination.parents):
        if component.is_symlink():
            raise ValueError(f'symlink destination refused: {component}')
    skills = sorted(p for p in SOURCE.iterdir() if (p / 'SKILL.md').is_file())
    for skill in skills:
        if (destination / skill.name).exists() or (destination / skill.name).is_symlink():
            raise ValueError(f'existing skill refused: {destination / skill.name}')
        if any(p.is_symlink() for p in skill.rglob('*')):
            raise ValueError(f'symlink resource refused: {skill}')
    if destination == SOURCE or SOURCE in destination.parents:
        raise ValueError('cannot install inside source skills')
    for name in ('LICENSE', 'NOTICE.md'):
        target = destination / ('linkedin-agent-' + name)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f'unsafe attribution destination: {target}')
    destination.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        shutil.copytree(skill, destination / skill.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    # Attribution must accompany substantial copies, including skill-only installs.
    for name in ('LICENSE', 'NOTICE.md'):
        target = destination / ('linkedin-agent-' + name)
        if not target.exists():
            with target.open('x', encoding='utf-8') as fh:
                fh.write((SOURCE.parent / name).read_text(encoding='utf-8'))
    return [p.name for p in skills]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dest', required=True, help='e.g. <project>/.agents/skills')
    args = ap.parse_args()
    try:
        print('Installed: ' + ', '.join(install(args.dest)))
    except (OSError, ValueError) as exc:
        ap.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
