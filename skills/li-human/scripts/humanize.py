#!/usr/bin/env python3
"""Local deterministic style normalization adapted from Jake Schincariol.
Not an authorship classifier. Review lexical edits for meaning. URLs and email
addresses are protected. Joiners and directional marks are preserved by default.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = os.path.join(HERE, "..", "references", "slop.json")

URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")
FLAG_RE = re.compile(r"\U0001F3F4[\U000E0030-\U000E0039\U000E0061-\U000E007A]{2,}\U000E007F")
SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")


def load_lexicon(path=LEX):
    with open(path, encoding="utf-8") as fh:
        lex = json.load(fh)
    if not isinstance(lex, dict):
        raise ValueError("lexicon must be an object")
    required = {"invisible": ("cp", "name", "action"),
                "typographic": ("from", "name", "to"),
                "words": ("find", "replace", "family"),
                "phrases": ("find", "replace", "family"),
                "structures": ("id", "regex", "name", "fix")}
    for key, fields in required.items():
        if not isinstance(lex.get(key), list):
            raise ValueError(f"lexicon requires a {key} list")
        for entry in lex[key]:
            if not isinstance(entry, dict) or any(not isinstance(entry.get(field), str) for field in fields):
                raise ValueError(f"invalid {key} entry")
    for entry in lex["words"] + lex["phrases"]:
        if not isinstance(entry.get("find"), str) or not entry["find"]:
            raise ValueError("lexicon find must be a nonempty string")
        if not isinstance(entry.get("replace"), str):
            raise ValueError("lexicon replace must be a string")
    for entry in lex["invisible"]:
        if entry["action"] not in ("delete", "space"):
            raise ValueError("invalid invisible action")
        cp = _cp(entry["cp"])
        low, high = cp if isinstance(cp, tuple) else (cp, cp)
        if not 0 <= low <= high <= 0x10FFFF:
            raise ValueError("invalid Unicode codepoint range")
    for entry in lex["typographic"]:
        if not isinstance(entry["from"], str) or len(entry["from"]) != 1 or not isinstance(entry["to"], str):
            raise ValueError("invalid typography entry")
    for entry in lex["structures"]:
        try:
            re.compile(entry["regex"], re.MULTILINE)
        except re.error as exc:
            raise ValueError("invalid structure regex") from exc
    return lex


def _cp(spec):
    """'U+200B' -> '\\u200b';  'U+E0000-U+E007F' -> (start, end)."""
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a[2:], 16), int(b[2:], 16))
    return int(spec[2:], 16)


def pass_invisible(text, lex, aggressive=False):
    """Delete or space-normalise invisible characters. Returns (text, hits)."""
    hits = []
    for entry in lex["invisible"]:
        if not aggressive and entry["cp"] in {
            "U+200C", "U+200D", "U+061C", "U+200E", "U+200F"
        }:
            continue  # Orthography, emoji composition and bidirectional text.
        cp = _cp(entry["cp"])
        if isinstance(cp, tuple):
            pattern = "[" + re.escape(chr(cp[0])) + "-" + re.escape(chr(cp[1])) + "]"
        else:
            pattern = re.escape(chr(cp))
        n = len(re.findall(pattern, text))
        if n:
            hits.append({"name": entry["cp"] + " " + entry["name"], "count": n,
                         "action": entry["action"]})
            text = re.sub(pattern, "" if entry["action"] == "delete" else " ", text)
    # Any remaining Cf (format) character is invisible by definition.
    stray = [c for c in text if unicodedata.category(c) == "Cf"]
    if stray and aggressive:
        hits.append({"name": "other invisible format chars", "count": len(stray),
                     "action": "delete"})
        text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return text, hits


def pass_typographic(text, lex):
    hits = []
    for entry in lex["typographic"]:
        ch = entry["from"]
        n = text.count(ch)
        if not n:
            continue
        hits.append({"name": f"{ch} {entry['name']}", "count": n, "to": entry["to"].strip() or "(space)"})
        if ch == "—":
            # " word — word " and "word—word" both collapse to a comma + space.
            text = re.sub(r"[ \t]*—[ \t]*", ", ", text)
        elif ch == "–":
            text = re.sub(r"[ \t]*–[ \t]*(?=\d)", "-", text)      # 5–10  -> 5-10
            text = re.sub(r"[ \t]+–[ \t]+", ", ", text)            # used as em dash
            text = text.replace("–", "-")
        else:
            text = text.replace(ch, entry["to"])
    # A comma inserted before existing punctuation reads wrong.
    text = re.sub(r",\s*([,.;:!?])", r"\1", text)
    text = re.sub(r",\s*\n", "\n", text)
    return text, hits


def _match_case(src, repl):
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def pass_lexical(text, lex):
    """Replace slop words and phrases. Longest first so phrases win."""
    hits = []
    entries = sorted(lex["phrases"] + lex["words"],
                     key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        find = entry["find"]
        pattern = re.compile(r"(?<!\w)" + re.escape(find).replace(r"\ ", r"[ \t]+") + r"(?!\w)",
                             re.IGNORECASE)
        found = pattern.findall(text)
        if not found:
            continue
        hits.append({"find": find, "replace": entry["replace"] or "(deleted)",
                     "count": len(found), "family": entry["family"]})
        text = pattern.sub(lambda m: _match_case(m.group(0), entry["replace"]), text)
    # Clean up after deletions.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"(?m)^[ \t]*([,.;:])\s*", "", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # An em dash that became a comma, followed by a sentence connective, leaves
    # a splice ("is important, also, it's proof"). Promote it to a full stop.
    text = re.sub(r",\s*(also|so|still|basically|in the end)\s*,\s*",
                  lambda m: ". " + m.group(1)[0].upper() + m.group(1)[1:] + ", ", text)
    return text, hits


def scan_structures(text, lex):
    flags = []
    for s in lex["structures"]:
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error as exc:
            raise ValueError(f"invalid structure regex: {s['id']}") from exc
        found = pattern.findall(text)
        if found:
            flags.append({"name": s["name"], "count": len(found), "fix": s["fix"]})
    # Sentence-length uniformity is structural too.
    lens = [len(s.split()) for s in SENT_RE.findall(text) if len(s.split()) > 2]
    if len(lens) >= 4:
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        if cv < 0.35:
            flags.append({
                "name": f"Uniform sentence length (variation {cv:.2f})",
                "count": len(lens),
                "fix": "Review rhythm in context; variation is a preference, not an authorship signal.",
            })
    return flags


def humanize(text, lex, aggressive=False, lexical=True, typography=True):
    report = {key: [] for key in ("invisible", "typographic", "lexical", "structures")}

    def clean_span(span):
        if not span.strip():
            return span
        span, hits = pass_invisible(span, lex, aggressive)
        report["invisible"].extend(hits)
        if typography:
            span, hits = pass_typographic(span, lex)
            report["typographic"].extend(hits)
        if lexical:
            span, hits = pass_lexical(span, lex)
            report["lexical"].extend(hits)
        return span

    parts, cursor = [], 0
    protected = URL_RE if aggressive else re.compile(URL_RE.pattern + "|" + FLAG_RE.pattern)
    for match in protected.finditer(text):
        parts.extend((clean_span(text[cursor:match.start()]), match.group(0)))
        cursor = match.end()
    parts.append(clean_span(text[cursor:]))
    clean = "".join(parts).strip()
    report["structures"] = scan_structures(clean, lex)
    return clean + ("\n" if clean else ""), report


def render_report(report, out=sys.stderr):
    def head(title):
        print(f"\n{title}\n" + "-" * len(title), file=out)

    total = sum(h["count"] for h in report["invisible"]) \
        + sum(h["count"] for h in report["typographic"]) \
        + sum(h["count"] for h in report["lexical"])

    head("HUMANIZE REPORT")
    print(f"{total} style changes applied, "
          f"{len(report['structures'])} structural patterns flagged for review", file=out)

    if report["invisible"]:
        head("1. INVISIBLE CHARACTERS")
        for h in report["invisible"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['action']}", file=out)
    if report["typographic"]:
        head("2. TYPOGRAPHY")
        for h in report["typographic"]:
            print(f"  {h['count']:>3}x  {h['name']}  -> {h['to']}", file=out)
    if report["lexical"]:
        head("3. SLOP LEXICON")
        for h in report["lexical"]:
            print(f"  {h['count']:>3}x  {h['find']}  -> {h['replace']}   [{h['family']}]", file=out)
    if report["structures"]:
        head("4. STRUCTURAL TELLS  (not auto-fixed - rewrite these yourself)")
        for h in report["structures"]:
            print(f"  {h['count']:>3}x  {h['name']}\n        {h['fix']}", file=out)
    if not any(report.values()):
        head("CLEAN")
        print("  Nothing to strip.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Normalize local writing style; review edits for meaning.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("-o", "--out", help="write cleaned text here instead of stdout")
    ap.add_argument("--report", action="store_true", help="print what changed, to stderr")
    ap.add_argument("--json", action="store_true", help="emit {text, report} as JSON")
    ap.add_argument("--lexicon", default=LEX, help="path to slop.json")
    ap.add_argument("--aggressive-invisibles", action="store_true",
                    help="also remove joiners/direction marks; may change Unicode meaning")
    ap.add_argument("--no-lexical", action="store_true", help="preserve vocabulary")
    ap.add_argument("--no-typography", action="store_true", help="preserve typography")
    args = ap.parse_args()
    if args.json and args.out:
        ap.error("--json and --out are mutually exclusive")

    try:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            with open(args.input, encoding="utf-8") as fh:
                raw = fh.read()
        lex = load_lexicon(args.lexicon)
        clean, report = humanize(raw, lex, args.aggressive_invisibles,
                                 not args.no_lexical, not args.no_typography)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, f"error: {exc}\n")

    if args.json:
        print(json.dumps({"text": clean, "report": report}, indent=2, ensure_ascii=False))
        return
    if args.out:
        try:
            # Exclusive creation also rejects existing symlinks and input aliases.
            with open(args.out, "x", encoding="utf-8") as fh:
                fh.write(clean)
        except OSError as exc:
            ap.exit(2, f"error: {exc}\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(clean)
    if args.report:
        render_report(report)


if __name__ == "__main__":
    main()
