#!/usr/bin/env python3
"""Observable local writing diagnostics; never a scientific authorship score."""
import argparse
from collections import Counter
import json
import re
import statistics
import sys
import unicodedata
from humanize import URL_RE, load_lexicon, scan_structures

WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def analyze(text, lex):
    plain = URL_RE.sub('', text)
    words = WORD_RE.findall(plain)
    lengths = [len(WORD_RE.findall(s)) for s in re.split(r'[.!?…\n]+', plain)
               if WORD_RE.search(s)]
    hits = []
    for entry in lex['words'] + lex['phrases']:
        pattern = r'(?<!\w)' + re.escape(entry['find']).replace(r'\ ', r'[ \t]+') + r'(?!\w)'
        count = len(re.findall(pattern, plain, re.I))
        if count:
            hits.append({'phrase': entry['find'], 'count': count})
    generic = sum(h['count'] for h in hits)
    normalized = [' '.join(WORD_RE.findall(s.casefold())) for s in re.split(r'[.!?\n]+', plain)]
    repeated = sorted(s for s, count in Counter(normalized).items() if s and count > 1)
    cv = (statistics.pstdev(lengths) / statistics.mean(lengths)
          if len(lengths) >= 4 and statistics.mean(lengths) else None)
    return {
        'word_count': len(words), 'sentence_count': len(lengths),
        'sentence_variation': {'coefficient': round(cv, 3) if cv is not None else None,
                               'lengths': lengths, 'note': 'Insufficient sample' if cv is None else 'Descriptive, no target'},
        'generic_language': {'hits': hits, 'per_100_words': round(generic * 100 / len(words), 2) if words else 0},
        'formatting_artefacts': {'format_characters': sum(unicodedata.category(c) == 'Cf' for c in text),
                                 'nonbreaking_spaces': text.count('\u00a0') + text.count('\u202f'),
                                 'em_dashes': text.count('—'), 'curly_quotes': sum(text.count(c) for c in '‘’“”')},
        'structural_repetition': {'repeated_sentences': repeated, 'patterns': scan_structures(plain, lex)},
        'specificity': {'numeric_markers': len(re.findall(r'\b\d+(?:[.,]\d+)*', plain)),
                        'note': 'Markers are not verified evidence; never add numbers to improve this panel'},
        'voice_consistency': 'Requires human/agent comparison with voice.md; not measured',
        'evidence_density': 'Requires claim/source review; not measured',
        'limitations': 'Local style heuristics, not proof of authorship or detector avoidance. No detector APIs.'
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', nargs='?', default='-')
    ap.add_argument('compare', nargs='?')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--lexicon')
    args = ap.parse_args()
    if args.input == '-' and args.compare == '-':
        ap.error('stdin can only be read once')
    try:
        lex = load_lexicon(args.lexicon) if args.lexicon else load_lexicon()
        panels = []
        for name in [args.input] + ([args.compare] if args.compare else []):
            if name == '-':
                text = sys.stdin.read()
            else:
                with open(name, encoding='utf-8') as fh:
                    text = fh.read()
            panels.append({'source': name, **analyze(text, lex)})
        if args.json:
            print(json.dumps(panels if args.compare else panels[0], ensure_ascii=False, indent=2))
        else:
            for panel in panels:
                print('WRITING QUALITY PANEL — ' + panel['source'])
                for key, value in panel.items():
                    if key != 'source':
                        print(f'{key}: {json.dumps(value, ensure_ascii=False)}')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
