# Meetup and Networking Calendar Merger

A Python utility for merging meetup events from an Excel workbook with existing ICS calendar files.

## Description

This tool reads events from an Excel spreadsheet and merges them with an existing ICS calendar file, creating a combined calendar that can be imported into calendar applications like Google Calendar, Outlook, or Apple Calendar.

## Features

- Merges events from Excel workbook into ICS calendar format
- Supports event exclusion rules to filter out unwanted events
- Avoids duplicate event entries
- Generates standard iCalendar (.ics) format output

## Files

- `meetup_calendar_merger.py` - Main Python script for merging calendars
- `Attending & Attended Meetups.ics` - Source ICS calendar file (ignored by git)
- `Merged_Meetups_and_Networking.ics` - Output merged calendar file (ignored by git)
- `.gitignore` - Excludes ICS and XLSX files from version control

## Usage

Run the script to merge your meetup events:

```bash
python meetup_calendar_merger.py
```

The script expects:
- An Excel file named `Meetups and Networking.xlsx` with event data
- An existing ICS file named `Attending & Attended Meetups.ics` (optional)

Output will be generated as `Merged_Meetups_and_Networking.ics`.

## Requirements

- Python 3.x
- pandas
- openpyxl (for Excel file support)

Install dependencies:

```bash
pip install pandas openpyxl
```

## License

Personal project for managing meetup calendars.
