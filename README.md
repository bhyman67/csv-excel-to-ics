# Personal ICS Calendar Generators

A collection of Python scripts that generate Outlook-importable `.ics` calendar files from various personal data sources.

Each generator lives in `generators/` and is a self-contained script with its own inputs and outputs.

## Setup

Use the steps below to recreate the environment on a new machine.

Minimum Python version: 3.14

Create and activate a virtual environment in the repo root, then install pinned dependencies:

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Path Configuration (OneDrive Friendly)

The scripts can resolve paths from configurable input/output roots so each computer can use its own OneDrive location.

Path resolution rules:

1. Absolute paths are used exactly as provided.
2. Relative input paths are resolved under the configured input root.
3. Relative output paths are resolved under the configured output root.

### Option A: Local config file (recommended)

Copy `paths.local.example.json` to `paths.local.json` and update values for your machine.

Example:

```json
{
    "input_root": "C:/Users/<you>/OneDrive/Documents/personal-ics/input",
    "output_root": "C:/Users/<you>/OneDrive/Documents/personal-ics/output"
}
```

`paths.local.json` is ignored by git, so each machine can keep its own paths.

### Option B: Environment variables

Set either or both of these:

- `ICS_INPUT_ROOT`
- `ICS_OUTPUT_ROOT`

Optional override for config-file location:

- `ICS_PATHS_CONFIG` (path to a JSON config file)

## Generators

### CorePower Yoga Classes — `ics_generators/cpy_classes.py`

Parses the "Class History" page saved from the CorePower Yoga website and produces a calendar of past/upcoming classes.

**Input:** Save the Class History page as HTML from your browser, place it in `input/cpy_class_hist/`.

```bash
python ics_generators/cpy_classes.py
# defaults to: <input_root>/cpy_class_hist/CPY Class History.html -> <output_root>/cpy_classes.ics

python ics_generators/cpy_classes.py "input/cpy_class_hist/CPY Class History.html" output/cpy_classes.ics
```

---

### Meetups — `ics_generators/meetups.py`

Converts a Meetup events CSV or Excel export into a calendar. Column names are auto-detected from common aliases; use explicit flags when needed.

**Input:** Export your events to CSV or XLSX, place it in `input/meetups/`.

```bash
python ics_generators/meetups.py \
    --input "input/meetups/Data & Automation Career + BytePeak Engineering.CSV" \
    --output meetups.ics

# Merge new events into an existing ICS (deduplicates by title + start time):
python ics_generators/meetups.py \
    --input "input/meetups/events.csv" \
    --output meetups.ics \
    --existing-ics meetups.ics

# Override column names and timezone:
python ics_generators/meetups.py \
    --input "input/meetups/events.csv" \
    --output meetups.ics \
    --title-column "Event Name" \
    --start-column "Start Date" \
    --end-column "End Date" \
    --timezone "America/Denver"
```

If `--output` is omitted, Meetups defaults to `<output_root>/meetups.ics`.

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
ics_generators/           # one script per ICS generator
    cpy_classes.py          # CorePower Yoga HTML -> ICS
    meetups.py              # Meetup CSV/Excel -> ICS
    path_config.py          # shared input/output root resolution
requirements.txt          # pinned Python dependencies
paths.local.example.json  # copy to paths.local.json on each machine
paths.local.json          # local machine paths (git-ignored)

# Under your configured input root (in OneDrive):
input/
    cpy_class_hist/         # CorePower Yoga HTML exports
    meetups/                # Meetup CSV/Excel exports

# Under your configured output root (in OneDrive):
output/                   # generated .ics files (import into Outlook)
```

## Adding a New Generator

1. Create `ics_generators/<name>.py` with a `main()` and `if __name__ == "__main__"` block.
2. Add a matching `input/<name>/` subfolder for its source data.
3. Document the run command in this README under a new `###` section.

