#!/usr/bin/env python3
"""
Script to merge events from Excel workbook with existing ICS calendar file.
Reads events from 'Meetups and Networking.xlsx' and merges them with 
'Attending & Attended Meetups.ics' to create a combined ICS file.
"""

import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
import re

def read_ics_file(filename):
    """Read existing ICS file and return its content."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Creating new calendar.")
        return None

def read_exclusion_table(excel_file):
    """Read exclusion table from Excel file."""
    try:
        df = pd.read_excel(excel_file, sheet_name='Meetup Attended Event Exclude')
        exclusions = []
        for _, row in df.iterrows():
            date = row.get('Date')
            event_text = row.get('Meetup Event')
            if not pd.isna(date) and not pd.isna(event_text):
                # Parse date if it's a string
                if isinstance(date, str):
                    try:
                        date = pd.to_datetime(date)
                    except:
                        continue
                exclusions.append({
                    'date': date,
                    'text': str(event_text).strip().lower()
                })
        print(f"Loaded {len(exclusions)} exclusion rules")
        return exclusions
    except Exception as e:
        print(f"Warning: Could not read exclusion table: {e}")
        return []

def extract_existing_events(ics_content, exclusions=None):
    """Extract existing events from ICS content to avoid duplicates."""
    existing_events = set()
    excluded_events = []
    
    if ics_content:
        # Extract event summaries and dates for duplicate detection
        events = re.findall(r'BEGIN:VEVENT.*?END:VEVENT', ics_content, re.DOTALL)
        for event in events:
            summary_match = re.search(r'SUMMARY:(.*)', event)
            dtstart_match = re.search(r'DTSTART[^:]*:(\d{8})', event)
            if summary_match and dtstart_match:
                summary = summary_match.group(1).strip()
                date = dtstart_match.group(1)
                
                # Check if event should be excluded
                if exclusions and should_exclude_event(summary, date, exclusions):
                    excluded_events.append((summary, date))
                else:
                    existing_events.add((summary, date))
    
    return existing_events, excluded_events

def should_exclude_event(summary, date_str, exclusions):
    """Check if an event should be excluded based on exclusion rules."""
    # Parse date from YYYYMMDD format
    try:
        event_date = datetime.strptime(date_str, '%Y%m%d')
    except:
        return False
    
    summary_lower = summary.lower()
    
    for exclusion in exclusions:
        # Check if dates match (comparing just the date part)
        if event_date.date() == exclusion['date'].date():
            # Check if exclusion text is contained in the summary
            if exclusion['text'] in summary_lower:
                return True
    
    return False

def format_datetime_for_ics(dt, timezone="America/Denver"):
    """Format datetime for ICS file."""
    if pd.isna(dt):
        return None
    
    # Handle pandas Timestamp or datetime objects
    if isinstance(dt, (pd.Timestamp, datetime)):
        return dt.strftime('%Y%m%dT%H%M%S')
    
    # If it's a string, try to parse it first
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt)
            return dt.strftime('%Y%m%dT%H%M%S')
        except:
            return None
    
    return None

def clean_summary(summary):
    """Clean event summary for ICS format."""
    if pd.isna(summary):
        return "Untitled Event"
    
    # Remove problematic characters and limit length
    summary = str(summary).replace('\n', ' ').replace('\r', ' ')
    summary = re.sub(r'[,;\\]', ' ', summary)
    return summary.strip()[:75]  # Limit to 75 characters

def create_event_block(event_data, existing_events):
    """Create an ICS event block from event data."""
    start_date = event_data.get('Start')
    end_date = event_data.get('End')
    summary = event_data.get('Meetup/Networking Event', 'Untitled Event')
    
    # Skip if start date is invalid
    if pd.isna(start_date):
        return None
    
    # Parse start date if it's a string
    if isinstance(start_date, str):
        try:
            start_date = pd.to_datetime(start_date)
        except:
            print(f"Warning: Could not parse start date: {start_date}")
            return None
    
    # Parse end date, use start date + 2 hours if not provided
    if pd.isna(end_date):
        end_date = start_date + timedelta(hours=2)
    elif isinstance(end_date, str):
        try:
            end_date = pd.to_datetime(end_date)
        except:
            print(f"Warning: Could not parse end date: {end_date}, using start + 2 hours")
            end_date = start_date + timedelta(hours=2)
    
    # Check for duplicates
    date_str = start_date.strftime('%Y%m%d')
    clean_sum = clean_summary(summary)
    if (clean_sum, date_str) in existing_events:
        print(f"Skipping duplicate event: {clean_sum} on {date_str}")
        return None
    
    # Format datetime
    dtstart = format_datetime_for_ics(start_date)
    if not dtstart:
        return None
    
    dtend = format_datetime_for_ics(end_date)
    
    # Generate unique UID
    event_uid = f"event_{uuid.uuid4().hex[:12]}@excel-import.local"
    
    # Current timestamp
    now = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    
    # Create event block
    event_block = f"""BEGIN:VEVENT
UID:{event_uid}
SEQUENCE:1
DTSTAMP:{now}
DTSTART;TZID=America/Denver:{dtstart}
DTEND;TZID=America/Denver:{dtend}
SUMMARY:{clean_sum}
DESCRIPTION:Event imported from Excel spreadsheet
STATUS:CONFIRMED
CREATED:{now}
LAST-MODIFIED:{now}
CLASS:PUBLIC
END:VEVENT"""
    
    return event_block

def create_merged_ics(excel_file, existing_ics_file, output_file):
    """Main function to create merged ICS file."""
    print(f"Reading Excel file: {excel_file}")
    
    # Read Excel file
    try:
        df = pd.read_excel(excel_file)
        print(f"Found {len(df)} rows in Excel file")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return False
    
    # Read exclusion table
    exclusions = read_exclusion_table(excel_file)
    
    # Read existing ICS file
    existing_ics = read_ics_file(existing_ics_file)
    existing_events, excluded_events = extract_existing_events(existing_ics, exclusions)
    print(f"Found {len(existing_events)} existing events in ICS file")
    
    # Print excluded events
    if excluded_events:
        print("\n" + "=" * 50)
        print(f"EXCLUDED {len(excluded_events)} EVENTS:")
        print("=" * 50)
        for summary, date_str in sorted(excluded_events, key=lambda x: x[1]):
            # Format date for display
            try:
                display_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
            except:
                display_date = date_str
            print(f"  {display_date}: {summary}")
        print("=" * 50 + "\n")
    
    # Start building new ICS content
    # Always use our custom header with "Meetups and Networking" name
    ics_header = create_ics_header()
    
    if existing_ics:
        # Extract existing events (filter out excluded ones)
        all_event_blocks = re.findall(r'BEGIN:VEVENT.*?END:VEVENT', existing_ics, re.DOTALL)
        existing_event_blocks = []
        
        for event in all_event_blocks:
            summary_match = re.search(r'SUMMARY:(.*)', event)
            dtstart_match = re.search(r'DTSTART[^:]*:(\d{8})', event)
            if summary_match and dtstart_match:
                summary = summary_match.group(1).strip()
                date = dtstart_match.group(1)
                # Only include if not excluded
                if not should_exclude_event(summary, date, exclusions):
                    existing_event_blocks.append(event)
    else:
        existing_event_blocks = []
    
    # Create new events from Excel
    new_events = []
    for _, row in df.iterrows():
        event_data = {
            'Start': row.get('Start'),
            'End': row.get('End'),
            'Meetup/Networking Event': row.get('Meetup/Networking Event')
        }
        
        event_block = create_event_block(event_data, existing_events)
        if event_block:
            new_events.append(event_block)
    
    print(f"Created {len(new_events)} new events from Excel")
    
    # Combine everything
    ics_content = ics_header
    
    # Add existing events
    for event in existing_event_blocks:
        ics_content += event + "\n"
    
    # Add new events
    for event in new_events:
        ics_content += event + "\n"
    
    # Close calendar
    ics_content += "END:VCALENDAR\n"
    
    # Write to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(ics_content)
        print(f"Successfully created merged ICS file: {output_file}")
        print(f"Total events: {len(existing_event_blocks)} existing + {len(new_events)} new = {len(existing_event_blocks) + len(new_events)}")
        return True
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False

def create_ics_header():
    """Create ICS header for new calendar."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Python Script//Merged Calendar 1.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
NAME:Meetups and Networking
X-WR-CALNAME:Meetups and Networking
BEGIN:VTIMEZONE
TZID:America/Denver
TZURL:http://tzurl.org/zoneinfo-outlook/America/Denver
X-LIC-LOCATION:America/Denver
BEGIN:DAYLIGHT
TZOFFSETFROM:-0700
TZOFFSETTO:-0600
TZNAME:MDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0600
TZOFFSETTO:-0700
TZNAME:MST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
"""

def main():
    """Main execution function."""
    # File paths (assuming files are in the same directory as script)
    excel_file = "Meetups and Networking.xlsx"
    existing_ics = "Attending & Attended Meetups.ics" 
    output_file = "Merged_Meetups_and_Networking.ics"
    
    print("=" * 50)
    print("Meetups and Networking ICS Merger")
    print("=" * 50)
    
    # Check if files exist
    if not os.path.exists(excel_file):
        print(f"Error: {excel_file} not found!")
        return
    
    # Create merged ICS file
    success = create_merged_ics(excel_file, existing_ics, output_file)
    
    if success:
        print("\n" + "=" * 50)
        print("SUCCESS! Merged calendar created.")
        print(f"Output file: {output_file}")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED! Could not create merged calendar.")
        print("=" * 50)

    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
