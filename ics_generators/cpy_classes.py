#!/usr/bin/env python3
"""Generate an ICS calendar file from a CorePower Yoga class history HTML page.

Usage:
    python generators/cpy_classes.py
    python generators/cpy_classes.py input/cpy_class_hist/CPY\ Class\ History.html output/cpy_classes.ics

The HTML file is the "Class History" page saved from the CorePower Yoga website.
"""

from __future__ import annotations

import argparse
import html
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from path_config import resolve_input_path, resolve_output_path

CARD_SPLIT_TOKEN = '<div class="d-flex flex-column p-3 py-md-4 px-sm-4 mt-3 border rounded-lg">'

# Fixed UTC offsets used to convert local class times into UTC.
TZ_OFFSETS = {
    "UTC": 0,
    "GMT": 0,
    "EST": -5,
    "EDT": -4,
    "CST": -6,
    "CDT": -5,
    "MST": -7,
    "MDT": -6,
    "PST": -8,
    "PDT": -7,
    "AKST": -9,
    "AKDT": -8,
    "HST": -10,
}


def _first_group(pattern: str, text: str, flags: int = 0) -> Optional[str]:
    # Convenience helper for one-off regex extractions from each card block.
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def _parse_date(date_text: str) -> datetime.date:
    return datetime.strptime(date_text, "%a, %b %d, %Y").date()


def _parse_clock(time_text: str) -> datetime.time:
    # Normalize spacing/casing first so a single parser can handle variations
    # like "9am", "9 AM", and "9:00 pm" after extraction.
    normalized = re.sub(r"\s+", " ", time_text.strip()).upper()
    for fmt in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Could not parse time: {time_text!r}")


def _ical_escape(value: str) -> str:
    # Escape characters that have special meaning in iCalendar text fields.
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold_ical_line(line: str, limit: int = 75) -> list[str]:
    # RFC 5545 recommends folding long content lines at 75 octets.
    # We fold by UTF-8 bytes (not characters) to keep multibyte text valid.
    encoded = line.encode("utf-8")
    if len(encoded) <= limit:
        return [line]

    chunks: list[str] = []
    current = b""
    for ch in line:
        ch_bytes = ch.encode("utf-8")
        if len(current) + len(ch_bytes) > limit:
            # Continuation lines must start with a single space.
            chunks.append(current.decode("utf-8"))
            current = b" " + ch_bytes
        else:
            current += ch_bytes
    if current:
        chunks.append(current.decode("utf-8"))
    return chunks


def _to_utc_or_floating(local_dt: datetime, tz_abbrev: str) -> tuple[str, str]:
    offset = TZ_OFFSETS.get(tz_abbrev.upper()) if tz_abbrev else None
    if offset is None:
        # If timezone is unknown, keep a floating local datetime so clients
        # interpret it in the viewer's local timezone.
        return ("LOCAL", local_dt.strftime("%Y%m%dT%H%M%S"))

    local_tz = timezone(timedelta(hours=offset))
    utc_dt = local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
    return ("UTC", utc_dt.strftime("%Y%m%dT%H%M%SZ"))


def _build_event(block: str, idx: int, now_utc: str) -> Optional[list[str]]:
    # Pull the fields we need from one "class card" block.
    date_text = _first_group(r"letter-spacing-1\">([^<]+)</div>", block)
    time_text = _first_group(r"session-card_sessionTime__[^\"]*\">([^<]+)</div>", block)
    tz_abbrev = _first_group(r"session-card_sessionTimeZone__[^\"]*\">([^<]+)</div>", block) or ""
    title = _first_group(r"session-title-link line-height-inherit\">([^<]+)</div>", block) or "Class"
    studio = _first_group(r"session-card_sessionStudio__[^\"]*\">([^<]+)</div>", block) or ""
    teacher = _first_group(r"session-card_sessionTeacher__[^\"]*\"[^>]*>([^<]+)</a>", block) or ""

    if not date_text or not time_text:
        return None

    # Expected format is "start - end" (e.g., "9:00 AM - 10:00 AM").
    time_parts = [p.strip() for p in time_text.split("-")]
    if len(time_parts) != 2:
        return None

    class_date = _parse_date(date_text)
    start_time = _parse_clock(time_parts[0])
    end_time = _parse_clock(time_parts[1])

    start_local = datetime.combine(class_date, start_time)
    end_local = datetime.combine(class_date, end_time)
    if end_local <= start_local:
        # Handle classes that pass midnight.
        end_local += timedelta(days=1)

    _, dtstart = _to_utc_or_floating(start_local, tz_abbrev)
    mode, dtend = _to_utc_or_floating(end_local, tz_abbrev)

    description_lines = []
    html_description_lines = []
    if teacher:
        description_lines.append(f"Teacher: {teacher}")
        html_description_lines.append(f"<b>Teacher:</b> {html.escape(teacher)}")
    if studio:
        description_lines.append(f"Studio: {studio}")
        html_description_lines.append(f"<b>Studio:</b> {html.escape(studio)}")

    uid = f"cpy-class-{idx}-{dtstart}@local"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_utc}",
        f"SUMMARY:{_ical_escape(title)}",
    ]

    if mode == "UTC":
        lines.append(f"DTSTART:{dtstart}")
        lines.append(f"DTEND:{dtend}")
    else:
        # Floating local datetimes (without trailing Z).
        lines.append(f"DTSTART:{dtstart}")
        lines.append(f"DTEND:{dtend}")

    if studio:
        lines.append(f"LOCATION:{_ical_escape(studio)}")
    if description_lines:
        lines.append(f"DESCRIPTION:{_ical_escape(chr(10).join(description_lines))}")
    if html_description_lines:
        lines.append(
            f"X-ALT-DESC;FMTTYPE=text/html:{_ical_escape('<br>'.join(html_description_lines))}"
        )

    lines.append("END:VEVENT")
    return lines


def export_html_to_ics(input_path: Path, output_path: Path) -> tuple[int, int]:
    raw = input_path.read_text(encoding="utf-8")
    # The page has repeated card containers; split once, then parse each card.
    blocks = raw.split(CARD_SPLIT_TOKEN)

    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    events: list[list[str]] = []

    for idx, block in enumerate(blocks[1:], start=1):
        try:
            # Parsing is intentionally resilient: skip malformed cards and keep going.
            event_lines = _build_event(block, idx, now_utc)
        except ValueError:
            event_lines = None
        if event_lines:
            events.append(event_lines)

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CPY Class History Export//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:CorePower Yoga Classes",
        "NAME:CorePower Yoga Classes",
    ]

    for event in events:
        for line in event:
            ics_lines.extend(_fold_ical_line(line))

    ics_lines.append("END:VCALENDAR")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use \n in text mode so Windows writes a single CRLF sequence per line.
    output_path.write_text("\n".join(ics_lines) + "\n", encoding="utf-8")

    total_cards = max(0, len(blocks) - 1)
    return total_cards, len(events)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract classes from a CPY Class History HTML page and write an Outlook-importable ICS file."
    )
    parser.add_argument(
        "input_html",
        nargs="?",
        default=None,
        help=(
            "Path to the saved class history HTML file. "
            "Absolute paths are used as-is; relative paths are resolved under the configured input root."
        ),
    )
    parser.add_argument(
        "output_ics",
        nargs="?",
        default=None,
        help=(
            "Path for the output ICS file. "
            "Absolute paths are used as-is; relative paths are resolved under the configured output root."
        ),
    )
    args = parser.parse_args()

    input_path = resolve_input_path(args.input_html, "cpy_class_hist/CPY Class History.html")
    output_path = resolve_output_path(args.output_ics, "cpy_classes.ics")

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    total_cards, exported = export_html_to_ics(input_path, output_path)
    print(f"Detected class cards : {total_cards}")
    print(f"Exported events      : {exported}")
    print(f"ICS written to       : {output_path.resolve()}")


if __name__ == "__main__":
    main()
