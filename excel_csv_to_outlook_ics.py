#!/usr/bin/env python3
"""Generic CSV/Excel to Outlook-friendly ICS converter."""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


COLUMN_ALIASES = {
    "title": [
        "title",
        "subject",
        "summary",
        "event",
        "event name",
        "meetup/networking event",
        "meetup event",
    ],
    "start": [
        "start",
        "start date",
        "start time",
        "start datetime",
        "begin",
        "begin date",
    ],
    "end": ["end", "end date", "end time", "end datetime", "finish", "finish date"],
    "description": ["description", "details", "notes", "body", "agenda"],
    "location": ["location", "where", "venue", "address"],
    "all_day": ["all day", "all_day", "allday", "is all day", "is_all_day"],
    "categories": ["category", "categories", "tag", "tags"],
}


def normalize_column_name(name: str) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def load_table(path: Path, sheet_name: str | int | None, csv_delimiter: str) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, delimiter=csv_delimiter)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError("Input must be .csv, .xlsx, or .xls")


def resolve_column(
    df: pd.DataFrame,
    preferred_name: str | None,
    alias_key: str,
    required: bool,
) -> str | None:
    if preferred_name:
        if preferred_name not in df.columns:
            raise ValueError(f"Column '{preferred_name}' was not found.")
        return preferred_name

    normalized = {normalize_column_name(col): col for col in df.columns}
    for alias in COLUMN_ALIASES[alias_key]:
        found = normalized.get(normalize_column_name(alias))
        if found is not None:
            return found

    if required:
        raise ValueError(
            f"Could not auto-detect required '{alias_key}' column. "
            f"Use --{alias_key.replace('_', '-')}-column to specify it."
        )
    return None


def parse_datetime(value: Any, local_tz: ZoneInfo) -> datetime | None:
    if pd.isna(value):
        return None
    try:
        parsed = pd.to_datetime(value)
    except Exception:
        return None

    if isinstance(parsed, pd.Timestamp):
        parsed = parsed.to_pydatetime()

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(local_tz)


def escape_ics_text(value: Any) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text.strip()


def fold_ics_line(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    parts: list[str] = []
    while len(line) > limit:
        parts.append(line[:limit])
        line = line[limit:]
    parts.append(line)
    return "\r\n ".join(parts)


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_all_day_flag(value: Any) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"true", "yes", "y", "1", "all day", "allday"}


def build_uid(title: str, start: datetime, row_index: int, domain: str) -> str:
    digest = hashlib.sha1(f"{title}|{start}|{row_index}".encode("utf-8")).hexdigest()[:16]
    return f"{digest}@{domain}"


def create_event_lines(
    row: pd.Series,
    idx: int,
    columns: dict[str, str | None],
    local_tz: ZoneInfo,
    default_duration_minutes: int,
    uid_domain: str,
) -> list[str] | None:
    title_value = row.get(columns["title"]) if columns["title"] else ""
    title = escape_ics_text(title_value) or "Untitled Event"

    start_raw = row.get(columns["start"]) if columns["start"] else None
    start_dt = parse_datetime(start_raw, local_tz)
    if start_dt is None:
        return None

    end_raw = row.get(columns["end"]) if columns["end"] else None
    end_dt = parse_datetime(end_raw, local_tz)
    if end_dt is None:
        end_dt = start_dt + timedelta(minutes=default_duration_minutes)

    all_day = False
    if columns["all_day"]:
        all_day = parse_all_day_flag(row.get(columns["all_day"]))

    description = ""
    if columns["description"]:
        description = escape_ics_text(row.get(columns["description"]))

    location = ""
    if columns["location"]:
        location = escape_ics_text(row.get(columns["location"]))

    categories = ""
    if columns["categories"]:
        categories = escape_ics_text(row.get(columns["categories"]))

    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = build_uid(title, start_dt, idx, uid_domain)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_utc}",
        "SEQUENCE:0",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "X-MICROSOFT-CDO-BUSYSTATUS:BUSY",
        "X-MICROSOFT-CDO-INTENDEDSTATUS:BUSY",
    ]

    if all_day:
        start_date = start_dt.date()
        end_date = end_dt.date()
        if end_date <= start_date:
            end_date = start_date + timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}")
    else:
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=default_duration_minutes)
        lines.append(f"DTSTART:{format_utc(start_dt)}")
        lines.append(f"DTEND:{format_utc(end_dt)}")

    lines.append(f"SUMMARY:{title}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location:
        lines.append(f"LOCATION:{location}")
    if categories:
        lines.append(f"CATEGORIES:{categories}")

    lines.append("END:VEVENT")
    return lines


def event_key_from_lines(lines: list[str]) -> tuple[str, str] | None:
    summary = ""
    dtstart = ""
    for line in lines:
        if line.startswith("SUMMARY:"):
            summary = line.split(":", 1)[1].strip().lower()
        elif line.startswith("DTSTART"):
            dtstart = line.split(":", 1)[1].strip()
    if not summary or not dtstart:
        return None
    return (summary, dtstart)


def extract_vevent_blocks(ics_content: str) -> list[str]:
    return re.findall(r"BEGIN:VEVENT.*?END:VEVENT", ics_content, flags=re.DOTALL)


def event_key_from_block(block: str) -> tuple[str, str] | None:
    summary_match = re.search(r"^SUMMARY:(.*)$", block, flags=re.MULTILINE)
    dtstart_match = re.search(r"^DTSTART[^:]*:(.*)$", block, flags=re.MULTILINE)
    if not summary_match or not dtstart_match:
        return None
    return (summary_match.group(1).strip().lower(), dtstart_match.group(1).strip())


def normalize_block_line_endings(block: str) -> str:
    return "\r\n".join(line.rstrip() for line in block.splitlines())


def build_calendar_text(calendar_name: str, event_blocks: list[str]) -> str:
    header = [
        "BEGIN:VCALENDAR",
        "PRODID:-//Excel CSV to ICS//Outlook Calendar Utility//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name) or 'Imported Calendar'}",
        "X-WR-TIMEZONE:UTC",
    ]

    all_lines: list[str] = header
    folded_header = [fold_ics_line(line) for line in all_lines]
    body = "\r\n".join(folded_header)
    if event_blocks:
        body += "\r\n" + "\r\n".join(event_blocks)
    body += "\r\nEND:VCALENDAR\r\n"
    return body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Excel or CSV event data into an Outlook-friendly ICS file."
    )
    parser.add_argument("--input", required=True, help="Path to input .csv/.xlsx/.xls file")
    parser.add_argument("--output", required=True, help="Path to output .ics file")
    parser.add_argument("--existing-ics", help="Path to existing .ics file to merge into output")
    parser.add_argument("--sheet", help="Excel sheet name or index (Excel inputs only)")
    parser.add_argument("--csv-delimiter", default=",", help="CSV delimiter (default: ,)")

    parser.add_argument("--title-column", help="Column containing event title/subject")
    parser.add_argument("--start-column", help="Column containing event start date/time")
    parser.add_argument("--end-column", help="Column containing event end date/time")
    parser.add_argument("--description-column", help="Column containing event description")
    parser.add_argument("--location-column", help="Column containing event location")
    parser.add_argument("--all-day-column", help="Column indicating all-day events")
    parser.add_argument("--categories-column", help="Column containing event categories")

    parser.add_argument(
        "--timezone",
        default="America/Denver",
        help="Timezone for naive datetime values in the source data",
    )
    parser.add_argument(
        "--default-duration-minutes",
        type=int,
        default=60,
        help="Default duration when end time is missing (default: 60)",
    )
    parser.add_argument(
        "--calendar-name",
        default="Imported Calendar",
        help="Calendar name visible in Outlook",
    )
    parser.add_argument(
        "--uid-domain",
        default="excel-csv-import.local",
        help="Domain used for generated event UIDs",
    )
    return parser.parse_args()


def parse_sheet_arg(sheet_arg: str | None) -> str | int | None:
    if sheet_arg is None:
        return None
    if sheet_arg.isdigit():
        return int(sheet_arg)
    return sheet_arg


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        local_tz = ZoneInfo(args.timezone)
    except Exception as exc:
        raise ValueError(f"Invalid timezone '{args.timezone}'") from exc

    sheet_value = parse_sheet_arg(args.sheet)
    df = load_table(input_path, sheet_value, args.csv_delimiter)
    if df.empty:
        raise ValueError("Input file has no rows.")

    columns = {
        "title": resolve_column(df, args.title_column, "title", required=True),
        "start": resolve_column(df, args.start_column, "start", required=True),
        "end": resolve_column(df, args.end_column, "end", required=False),
        "description": resolve_column(df, args.description_column, "description", required=False),
        "location": resolve_column(df, args.location_column, "location", required=False),
        "all_day": resolve_column(df, args.all_day_column, "all_day", required=False),
        "categories": resolve_column(df, args.categories_column, "categories", required=False),
    }

    existing_blocks: list[str] = []
    existing_keys: set[tuple[str, str]] = set()
    if args.existing_ics:
        existing_path = Path(args.existing_ics)
        if not existing_path.exists():
            raise FileNotFoundError(f"Existing ICS file not found: {existing_path}")
        with open(existing_path, "r", encoding="utf-8", errors="replace") as handle:
            existing_content = handle.read()
        for block in extract_vevent_blocks(existing_content):
            existing_blocks.append(normalize_block_line_endings(block))
            key = event_key_from_block(block)
            if key is not None:
                existing_keys.add(key)

    new_event_blocks: list[str] = []
    skipped = 0
    duplicates = 0
    for idx, row in df.iterrows():
        event_lines = create_event_lines(
            row,
            idx,
            columns,
            local_tz,
            args.default_duration_minutes,
            args.uid_domain,
        )
        if event_lines is None:
            skipped += 1
            continue
        key = event_key_from_lines(event_lines)
        if key is not None and key in existing_keys:
            duplicates += 1
            continue
        if key is not None:
            existing_keys.add(key)
        new_event_blocks.append("\r\n".join(event_lines))

    if not existing_blocks and not new_event_blocks:
        raise ValueError("No valid events were created. Check your column mappings and date values.")

    calendar_text = build_calendar_text(args.calendar_name, existing_blocks + new_event_blocks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(calendar_text)

    print(f"Input rows: {len(df)}")
    print(f"Existing events merged: {len(existing_blocks)}")
    print(f"New events created: {len(new_event_blocks)}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Rows skipped (missing/invalid start date): {skipped}")
    print(f"Wrote Outlook-friendly ICS file: {output_path}")


if __name__ == "__main__":
    main()
