# personal-ics-generators

A collection of Python scripts that generate Outlook-importable `.ics` calendar files from various personal data sources.

Each generator lives in `generators/` and is a self-contained script with its own inputs and outputs.

## Setup

```bash
pip install -r requirements.txt
```

## Generators

### CorePower Yoga Classes — `ics_generators/cpy_classes.py`

Parses the "Class History" page saved from the CorePower Yoga website and produces a calendar of past/upcoming classes.

**Input:** Save the Class History page as HTML from your browser, place it in `input/cpy/`.

```bash
python ics_generators/cpy_classes.py
# defaults to: input/cpy/CPY Class History.html → output/cpy_classes.ics

python ics_generators/cpy_classes.py "input/cpy/CPY Class History.html" output/cpy_classes.ics
```

---

### Meetups — `ics_generators/meetups.py`

Converts a Meetup events CSV or Excel export into a calendar. Column names are auto-detected from common aliases; use explicit flags when needed.

**Input:** Export your events to CSV or XLSX, place it in `input/meetups/`.

```bash
python ics_generators/meetups.py \
    --input "input/meetups/Data & Automation Career + BytePeak Engineering.CSV" \
    --output output/meetups.ics

# Merge new events into an existing ICS (deduplicates by title + start time):
python ics_generators/meetups.py \
    --input "input/meetups/events.csv" \
    --output output/meetups.ics \
    --existing-ics output/meetups.ics

# Override column names and timezone:
python ics_generators/meetups.py \
    --input "input/meetups/events.csv" \
    --output output/meetups.ics \
    --title-column "Event Name" \
    --start-column "Start Date" \
    --end-column "End Date" \
    --timezone "America/Denver"
```

**All flags:**

| Flag | Description |
|---|---|
| `--input` | Path to `.csv`, `.xlsx`, or `.xls` file |
| `--output` | Path for generated `.ics` |
| `--existing-ics` | Existing `.ics` to merge into (deduplicates) |
| `--timezone` | Timezone for naive datetimes (default: `America/Denver`) |
| `--calendar-name` | Calendar name shown in Outlook (default: `Meetups`) |
| `--default-duration-minutes` | Duration when end time is missing (default: `60`) |
| `--title-column` | Override auto-detected title column |
| `--start-column` | Override auto-detected start column |
| `--end-column` | Override auto-detected end column |
| `--description-column` | Override auto-detected description column |
| `--location-column` | Override auto-detected location column |

---

## Folder Layout

```
ics_generators/     # one script per ICS generator
input/
  cpy/              # CorePower Yoga HTML exports
  meetups/          # Meetup CSV/Excel exports
output/             # generated .ics files (import these into Outlook)
Old Data/           # archived ICS files
```

## Adding a New Generator

1. Create `ics_generators/<name>.py` with a `main()` and `if __name__ == "__main__"` block.
2. Add a matching `input/<name>/` subfolder for its source data.
3. Document the run command in this README under a new `###` section.

