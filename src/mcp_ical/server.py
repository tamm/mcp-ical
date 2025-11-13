import sys
from datetime import datetime
from functools import lru_cache
from textwrap import dedent

from loguru import logger
from mcp.server.fastmcp import FastMCP

from .ical import CalendarManager
from .models import CreateEventRequest, UpdateEventRequest

mcp = FastMCP("Calendar")

logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)


# Initialize the CalendarManager on demand in order to only request calendar permission
# when a calendar tool is invoked instead of on the launch of the Claude Desktop app.
@lru_cache(maxsize=None)
def get_calendar_manager() -> CalendarManager:
    """Get or initialize the calendar manager with proper error handling."""
    try:
        return CalendarManager()
    except ValueError as e:
        error_msg = dedent("""\
        Calendar access is not granted. Please follow these steps:

        1. Open System Preferences/Settings
        2. Go to Privacy & Security > Calendar
        3. Check the box next to your terminal application or Claude Desktop
        4. Restart Claude Desktop

        Once you've granted access, try your calendar operation again.
        """)
        raise ValueError(error_msg) from e


@mcp.resource("calendars://list")
def get_calendars() -> str:
    """List all available calendars that can be used with calendar operations."""
    try:
        manager = get_calendar_manager()
        calendars = manager.list_calendar_names()
        if not calendars:
            return "No calendars found"
        return "Available calendars:\n" + "\n".join(f"- {cal}" for cal in calendars)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error listing calendars: {str(e)}"


@mcp.tool()
async def list_calendars() -> str:
    """List all available calendars."""
    try:
        manager = get_calendar_manager()
        calendars = manager.list_calendar_names()
        if not calendars:
            return "No calendars found"

        return "Available calendars:\n" + "\n".join(f"- {calendar}" for calendar in calendars)

    except Exception as e:
        return f"Error listing calendars: {str(e)}"


@mcp.tool()
async def list_events(start_date: datetime, end_date: datetime, calendar_name: str | None = None) -> str:
    """List calendar events in a date range.

    The start_date should always use the time such that it represents the beginning of that day (00:00:00).
    The end_date should always use the time such that it represents the end of that day (23:59:59).
    This way, range based searches are always inclusive and can locate all events in that date range.

    Args:
        start_date: Start date in ISO8601 format (YYYY-MM-DDT00:00:00).
        end_date: Optional end date in ISO8601 format (YYYY-MM-DDT23:59:59).
        calendar_name: Optional calendar name to filter by
    """
    try:
        manager = get_calendar_manager()
        events = manager.list_events(start_date, end_date, calendar_name)
        if not events:
            return "No events found in the specified date range"

        return "".join([str(event) for event in events])

    except Exception as e:
        return f"Error listing events: {str(e)}"


@mcp.tool()
async def create_event(create_event_request: CreateEventRequest) -> str:
    """Create a new calendar event.

    Before using this tool, make sure to:
    1. Ask the user which calendar they want to use if not specified (check calendars://list)
    2. Ask if they want to add a location if none provided
    3. Ask if they want to add any notes/description if none provided
    4. Confirm the date and time with the user
    5. Ask if they want to set reminders for the event

    Args:
        title: Event title
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
        notes: Optional event notes/description. Ask user if they want to add notes.
        location: Optional event location. Ask user if they want to specify a location.
        calendar_name: Optional calendar name. Ask user which calendar to use, referencing calendars://list.
        all_day: Whether this is an all-day event
        reminder_offsets: List of minutes before the event to trigger reminders\
            e.g. [60, 1440] means two reminders, the first 24 hours before the event and the second one hour before.
        recurrence_rule: Optional recurrence rule for the event. This should be an instance of `RecurrenceRule` with the following fields:
            - frequency: Frequency of the recurrence (e.g., DAILY, WEEKLY, MONTHLY, YEARLY).
            - interval: Interval between recurrences (e.g., every 2 weeks).
            - end_date: Optional end date for the recurrence. If specified, the recurrence will stop on this date.
            - occurrence_count: Optional number of occurrences. If specified, the recurrence will stop after this many occurrences.
            - days_of_week: Optional list of weekdays for the event. Use integers to represent days:
                - Sunday: 1
                - Monday: 2
                - Tuesday: 3
                - Wednesday: 4
                - Thursday: 5
                - Friday: 6
                - Saturday: 7

    Note: Both `end_date` and `occurrence_count` should not be set simultaneously; choose one or the other, or leave both unset.
    """
    logger.info(f"Incoming Create Event Request: {create_event_request}")
    try:
        manager = get_calendar_manager()

        event = manager.create_event(create_event_request)
        if not event:
            return "Failed to create event. Please check calendar permissions and try again."

        return f"Successfully created event: {event.title} (ID: {event.identifier})"

    except Exception as e:
        return f"Error creating event: {str(e)}"


@mcp.tool()
async def update_event(
    event_id: str,
    update_event_request: UpdateEventRequest,
    update_future_events: bool = False,
    occurrence_date: datetime | None = None,
) -> str:
    """Update an existing calendar event or a specific occurrence of a recurring event.

    CRITICAL: When updating specific occurrences of recurring events, you MUST use the EXACT datetime
    from list_events. The datetime should be in the format YYYY-MM-DDTHH:MM:SS in your local timezone
    WITHOUT a timezone offset (e.g., "2025-11-15T09:00:00", not "2025-11-15T09:00:00+11:00").
    Do NOT construct dates manually - always copy from list_events output and remove any timezone suffix.

    Before using this tool, make sure to:
    1. Ask the user which fields they want to update
    2. For recurring events, ask if they want to update:
        - Just one occurrence: provide occurrence_date, update_future_events=False (default)
        - This occurrence and all future ones: provide occurrence_date, update_future_events=True
        - All occurrences: don't provide occurrence_date
    3. If moving to a different calendar, verify the calendar exists using calendars://list
    4. If updating time, confirm the new time with the user
    5. Ask if they want to add/update location if not specified
    6. Ask if they want to add/update notes if not specified
    7. Ask if they want to set reminders for the event

    Args:
        event_id: Unique identifier of the event (master event ID for recurring events)
        update_event_request: Object containing the fields to update:
            - title: Optional new title
            - start_time: Optional new start time in ISO format
            - end_time: Optional new end time in ISO format
            - notes: Optional new notes/description. Ask user if they want to update notes.
            - location: Optional new location. Ask user if they want to specify/update location.
            - calendar_name: Optional new calendar. Ask user which calendar to use, referencing calendars://list.
            - all_day: Optional all-day flag
            - reminder_offsets: List of minutes before the event to trigger reminders\
                e.g. [60, 1440] means two reminders, the first 24 hours before the event and the second one hour before.
            - recurrence_rule: Optional recurrence rule for the event. This should be an instance of `RecurrenceRule` with the following fields:
                - frequency: Frequency of the recurrence (e.g., DAILY, WEEKLY, MONTHLY, YEARLY).
                - interval: Interval between recurrences (e.g., every 2 weeks).
                - end_date: Optional end date for the recurrence. If specified, the recurrence will stop on this date.
                - occurrence_count: Optional number of occurrences. If specified, the recurrence will stop after this many occurrences.
                - days_of_week: Optional list of weekdays for the event. Use integers to represent days:
                    - Sunday: 1
                    - Monday: 2
                    - Tuesday: 3
                    - Wednesday: 4
                    - Thursday: 5
                    - Friday: 6
                    - Saturday: 7
        update_future_events: When True with occurrence_date, updates this occurrence and all future ones.
                             When False (default) with occurrence_date, updates only this specific occurrence.
                             Ignored when occurrence_date is None.
        occurrence_date: The EXACT start time from list_events output in local timezone format.
                        Required when updating a specific occurrence of a recurring event.
                        Format: YYYY-MM-DDTHH:MM:SS (e.g., "2025-11-23T14:00:00")
                        IMPORTANT: Remove any timezone suffix like +11:00 - use local time only.
                        DO NOT construct this manually - copy from list_events and remove timezone suffix.

    Usage Examples:
        - Update non-recurring event: update_event("event-id-123", {...})
        - Update just one occurrence (default): update_event("event-id-456", {...}, occurrence_date="2025-11-23T14:00:00")
        - Update from occurrence forward: update_event("event-id-456", {...}, occurrence_date="2025-11-23T14:00:00", update_future_events=True)
        - Update all occurrences: update_event("event-id-456", {...})

    Note:
        Both `end_date` and `occurrence_count` should not be set simultaneously; choose one or the other, or leave both unset.
        The exact datetime format is CRITICAL for occurrence updates. Always use list_events first and copy the exact
        datetime string, removing any timezone offset (e.g., remove the "+11:00" suffix).

        When update_future_events=True is used with occurrence_date, it creates a separate recurring series
        from that point forward. Subsequent updates to the master event will not affect this forked series.
    """
    logger.info(
        f"Attempting to update event with ID: {event_id}, "
        f"update_future_events={update_future_events}, "
        f"occurrence_date={occurrence_date}"
    )
    try:
        manager = get_calendar_manager()
        event = manager.update_event(event_id, update_event_request, update_future_events, occurrence_date)
        if not event:
            return f"Failed to update event. Event with ID {event_id} not found or update failed."

        # Build informative success message
        if occurrence_date and update_future_events:
            scope = f"occurrence at {occurrence_date.isoformat()} and all future occurrences"
        elif occurrence_date:
            scope = f"occurrence at {occurrence_date.isoformat()}"
        else:
            scope = "event"

        return f"Successfully updated {scope}: {event.title}"

    except Exception as e:
        return f"Error updating event: {str(e)}"


@mcp.tool()
async def delete_event(
    event_id: str, delete_entire_series: bool = False, occurrence_date: datetime | None = None
) -> str:
    """Delete a calendar event or specific occurrence(s) of a recurring event.

    CRITICAL: When deleting specific occurrences, you MUST use the EXACT datetime from list_events.
    The datetime should be in the format YYYY-MM-DDTHH:MM:SS in your local timezone WITHOUT a
    timezone offset (e.g., "2025-11-15T09:00:00", not "2025-11-15T09:00:00+11:00").
    Do NOT construct dates manually - always copy from list_events output and remove any timezone suffix.

    Before using this tool, make sure to:
    1. Confirm with the user that they want to delete this event
    2. For recurring events:
        Consider if they want to:
            - Delete just one occurrence: provide occurrence_date (default behavior)
            - Delete from an occurrence forward: provide occurrence_date + delete_entire_series=True
            - Delete the entire series: set delete_entire_series=True (no occurrence_date)
        - Ask which occurrence(s) they want to delete if that isn't very clear
        - Use list_events first to get exact datetimes if you don't have them
        - Use the EXACT datetime from list_events (remove any timezone suffix)

    Args:
        event_id: Unique identifier of the event (master event ID for recurring events)
        delete_entire_series: When True with occurrence_date, deletes that occurrence and all future ones.
                             When True without occurrence_date, deletes all occurrences.
                             When False (default), deletes only the specific occurrence.
        occurrence_date: The EXACT start time from list_events output in local timezone format.
                        REQUIRED when deleting a specific occurrence.
                        Format: YYYY-MM-DDTHH:MM:SS (e.g., "2025-11-23T14:00:00")
                        IMPORTANT: Remove any timezone suffix like +11:00 - use local time only.
                        DO NOT construct this manually - copy from list_events and remove timezone suffix.

    Usage Examples:
        - Delete non-recurring event: delete_event("event-id-123")
        - Delete one occurrence:
          1. First: list_events to get exact datetime
          2. Then: delete_event("event-id-456", occurrence_date="2025-11-23T14:00:00")
        - Delete from occurrence forward: delete_event("event-id-456", occurrence_date="2025-11-23T14:00:00", delete_entire_series=True)
        - Delete all occurrences: delete_event("event-id-456", delete_entire_series=True)

    Note:
        The exact datetime format is CRITICAL. Always use list_events first and copy the exact
        datetime string, removing any timezone offset (e.g., remove the "+11:00" suffix).
    """
    logger.info(
        f"Attempting to delete event with ID: {event_id}, "
        f"delete_entire_series={delete_entire_series}, "
        f"occurrence_date={occurrence_date}"
    )
    try:
        manager = get_calendar_manager()

        # Delete the event - this handles all the logic and error checking
        success = manager.delete_event(event_id, delete_entire_series, occurrence_date)

        if success:
            return "Event deleted successfully"
        else:
            return f"Failed to delete event with ID {event_id}"

    except Exception as e:
        return f"Error deleting event: {str(e)}"


def main():
    logger.info("Running mcp-ical server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
