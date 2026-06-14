# Excel/CSV to Outlook ICS Utility

A generic Python utility for converting event rows from Excel or CSV files into Outlook-friendly `.ics` calendar files.

## What It Does

The script reads tabular data and creates a new ICS calendar file designed for reliable Outlook import.

It supports:

- CSV, XLSX, and XLS input files
- Auto-detecting common event column names
- Explicit column mapping via CLI flags
- Optional merge with an existing ICS file
- Timed and all-day events
- Outlook-oriented ICS fields (`METHOD:PUBLISH`, Microsoft busy status properties, CRLF line endings)

## Expected Data Columns

Required:

- Title/subject column (examples: `title`, `subject`, `summary`, `event`)
- Start date/time column (examples: `start`, `start date`, `start datetime`)

Optional:

- End date/time (`end`, `finish`)
- Description (`description`, `notes`, `details`)
- Location (`location`, `venue`, `address`)
- All-day indicator (`all day`, `all_day`)
- Categories (`category`, `tags`)

If `end` is missing, duration defaults to 60 minutes (configurable).

## Installation

```bash
pip install -r requirements.txt
```

## Recommended Folders

- `input/` for source `.csv`, `.xlsx`, and existing `.ics` files
- `output/` for generated `.ics` files

## Usage

Basic:

```bash
python excel_csv_to_outlook_ics.py --input input/events.xlsx --output output/events.ics
```

CSV input:

```bash
python excel_csv_to_outlook_ics.py --input input/events.csv --output output/events.ics
```

Specify column mappings explicitly:

```bash
python excel_csv_to_outlook_ics.py \
	--input input/events.xlsx \
	--output output/events.ics \
	--title-column "Event Name" \
	--start-column "Start Date" \
	--end-column "End Date" \
	--description-column "Notes" \
	--location-column "Venue"
```

Set timezone/default duration/calendar name:

```bash
python excel_csv_to_outlook_ics.py \
	--input input/events.xlsx \
	--output output/events.ics \
	--timezone "America/Denver" \
	--default-duration-minutes 90 \
	--calendar-name "Work Events"
```

Merge into an existing ICS file:

```bash
python excel_csv_to_outlook_ics.py \
	--input input/events.xlsx \
	--existing-ics input/current_calendar.ics \
	--output output/merged_calendar.ics
```

Merge with timezone and custom calendar name:

```bash
python excel_csv_to_outlook_ics.py \
	--input input/events.xlsx \
	--existing-ics input/current_calendar.ics \
	--output output/merged_calendar.ics \
	--timezone "America/Denver" \
	--calendar-name "Merged Work Events"
```

When `--existing-ics` is used, existing events are carried forward and duplicate new events are skipped using `summary + DTSTART` matching.

## CLI Options

- `--input` **Required** path to `.csv`, `.xlsx`, or `.xls`
- `--output` **Required** output `.ics` path
- `--existing-ics` Existing `.ics` file to merge with generated events
- `--sheet` Excel sheet name or index
- `--csv-delimiter` CSV delimiter (default `,`)
- `--title-column` Explicit title column
- `--start-column` Explicit start datetime column
- `--end-column` Explicit end datetime column
- `--description-column` Explicit description column
- `--location-column` Explicit location column
- `--all-day-column` Explicit all-day flag column
- `--categories-column` Explicit categories column
- `--timezone` Timezone used for naive datetimes
- `--default-duration-minutes` Fallback event duration
- `--calendar-name` Calendar display name in Outlook
- `--uid-domain` Domain suffix for generated event UIDs

## Outlook Import Notes

- Timed events are exported as UTC timestamps (`...Z`), which Outlook handles consistently.
- All-day events use `VALUE=DATE` with an exclusive `DTEND`, which is the expected iCalendar pattern.
- Output uses CRLF line endings for better Outlook compatibility.

