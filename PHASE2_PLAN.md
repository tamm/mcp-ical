# Phase 2 Implementation Plan: Calendar ID-Based Operations

## Overview

Phase 1 (✅ COMPLETED) exposed calendar unique identifiers and source information to users. Phase 2 will enable operations to use these IDs, fully solving the duplicate calendar name issue.

## Current State (After Phase 1)

✅ Users can see:
- Unique calendar ID
- Calendar name
- Source/account name
- Source type

❌ Users cannot:
- Specify which calendar to use when names are duplicated
- Operations still use `_find_calendar_by_name()` which returns the first match

## Phase 2 Goals

Enable operations to target specific calendars using their unique ID while maintaining backward compatibility with name-based operations.

---

## Implementation Tasks

### 1. Update CalendarManager Methods

#### 1.1 Enhance `_find_calendar_by_name()` to Handle Duplicates

**File:** `src/mcp_ical/ical.py:389-404`

**Current behavior:**
- Returns first calendar matching name
- No warning about duplicates

**New behavior:**
```python
def _find_calendar_by_name(self, calendar_name: str, raise_on_duplicate: bool = False) -> Any | None:
    """Find a calendar by name

    Args:
        calendar_name: Name of the calendar to find
        raise_on_duplicate: If True, raise exception when multiple calendars have the same name

    Returns:
        Calendar object or None

    Raises:
        MultipleCalendarsException: If raise_on_duplicate=True and multiple calendars found
    """
    matches = []
    for calendar in self.event_store.calendars():
        if calendar.title() == calendar_name:
            matches.append(calendar)

    if len(matches) == 0:
        logger.info(f"Calendar '{calendar_name}' not found")
        return None

    if len(matches) > 1:
        if raise_on_duplicate:
            calendar_ids = [cal.calendarIdentifier() for cal in matches]
            sources = [cal.source().title() for cal in matches]
            error_msg = (
                f"Multiple calendars named '{calendar_name}' found:\n"
                + "\n".join([f"  - ID: {cid}, Account: {src}"
                           for cid, src in zip(calendar_ids, sources)])
            )
            raise MultipleCalendarsException(error_msg)
        else:
            logger.warning(f"Multiple calendars named '{calendar_name}' found, using first match")

    return matches[0]
```

**New Exception Needed:**
```python
class MultipleCalendarsException(Exception):
    """Raised when multiple calendars with the same name are found"""
    pass
```

#### 1.2 Add Calendar Lookup by ID or Name

**File:** `src/mcp_ical/ical.py`

**New method:**
```python
def _find_calendar(self, calendar_id: str | None = None, calendar_name: str | None = None) -> Any | None:
    """Find a calendar by ID or name

    Args:
        calendar_id: Unique calendar identifier (preferred)
        calendar_name: Calendar name (falls back to this if no ID)

    Returns:
        Calendar object or None

    Raises:
        ValueError: If neither calendar_id nor calendar_name provided
        MultipleCalendarsException: If calendar_name matches multiple calendars
    """
    if not calendar_id and not calendar_name:
        raise ValueError("Either calendar_id or calendar_name must be provided")

    # Prefer ID lookup if provided
    if calendar_id:
        return self._find_calendar_by_id(calendar_id)

    # Fall back to name lookup, but raise error if duplicates found
    return self._find_calendar_by_name(calendar_name, raise_on_duplicate=True)
```

### 2. Update Request Models

**File:** `src/mcp_ical/models.py`

#### 2.1 Update CreateEventRequest

```python
class CreateEventRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    calendar_name: str | None = None
    calendar_id: str | None = None  # NEW FIELD
    location: str | None = None
    notes: str | None = None
    alarms_minutes_offsets: list[int] | None = None
    url: str | None = None
    all_day: bool = False
    recurrence_rule: RecurrenceRule | None = None

    @model_validator(mode="after")
    def validate_calendar_specification(self) -> Self:
        """Ensure at least one calendar identifier is provided"""
        if self.calendar_id is None and self.calendar_name is None:
            # This is okay - will use default calendar
            pass
        return self
```

#### 2.2 Update UpdateEventRequest

```python
class UpdateEventRequest(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    calendar_name: str | None = None
    calendar_id: str | None = None  # NEW FIELD
    location: str | None = None
    notes: str | None = None
    alarms_minutes_offsets: list[int] | None = None
    url: str | None = None
    all_day: bool | None = None
    recurrence_rule: RecurrenceRule | None = None
```

### 3. Update CalendarManager Operations

**File:** `src/mcp_ical/ical.py`

#### 3.1 Update `create_event()`

**Current:** Lines 112-123

**Changes:**
```python
def create_event(self, request: CreateEventRequest) -> Event:
    """Create a calendar event

    Args:
        request: Event creation request with calendar_id (preferred) or calendar_name
    """
    # Find calendar using ID or name
    if request.calendar_id or request.calendar_name:
        calendar = self._find_calendar(
            calendar_id=request.calendar_id,
            calendar_name=request.calendar_name
        )
        if not calendar:
            id_or_name = request.calendar_id or request.calendar_name
            raise NoSuchCalendarException(f"Calendar not found: {id_or_name}")
    else:
        calendar = self.event_store.defaultCalendarForNewEvents()

    # Rest of the implementation stays the same
    # ...
```

#### 3.2 Update `update_event()`

**Current:** Lines 173-178

**Changes:**
```python
# Update calendar if requested
if request.calendar_id or request.calendar_name:
    target_calendar = self._find_calendar(
        calendar_id=request.calendar_id,
        calendar_name=request.calendar_name
    )
    if not target_calendar:
        id_or_name = request.calendar_id or request.calendar_name
        raise NoSuchCalendarException(f"Calendar not found: {id_or_name}")
    event.setCalendar_(target_calendar)
```

#### 3.3 Update `list_events()`

**Current:** Lines 64-68

**Changes:**
```python
def list_events(
    self,
    start_date: datetime,
    end_date: datetime,
    calendar_id: str | None = None,
    calendar_name: str | None = None,
) -> list[Event]:
    """List events in a date range, optionally filtered by calendar

    Args:
        start_date: Start of date range
        end_date: End of date range
        calendar_id: Optional calendar ID to filter by (preferred)
        calendar_name: Optional calendar name to filter by (fallback)
    """
    predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
        start_date, end_date, None
    )

    ek_events = self.event_store.eventsMatchingPredicate_(predicate)
    events = [Event.from_ekevent(event) for event in ek_events]

    # Filter by calendar if specified
    if calendar_id or calendar_name:
        target_calendar = self._find_calendar(
            calendar_id=calendar_id,
            calendar_name=calendar_name
        )
        if not target_calendar:
            id_or_name = calendar_id or calendar_name
            raise NoSuchCalendarException(f"Calendar not found: {id_or_name}")

        target_id = target_calendar.calendarIdentifier()
        events = [e for e in events if e._raw_event.calendar().calendarIdentifier() == target_id]

    return events
```

### 4. Update MCP Tool Interfaces

**File:** `src/mcp_ical/server.py`

#### 4.1 Update `create_event` tool

**Current:** Lines 99-146

**Changes:**
```python
@mcp.tool()
async def create_event(
    title: str,
    start_time: datetime,
    end_time: datetime,
    calendar_name: str | None = None,
    calendar_id: str | None = None,  # NEW PARAMETER
    location: str | None = None,
    notes: str | None = None,
    all_day: bool = False,
    alarms_minutes_offsets: list[int] | None = None,
    url: str | None = None,
    recurrence_rule: RecurrenceRule | None = None,
) -> str:
    """Create a new calendar event.

    Args:
        title: Event title
        start_time: Event start time (ISO format)
        end_time: Event end time (ISO format)
        calendar_name: Optional calendar name (for backward compatibility)
        calendar_id: Optional calendar ID (preferred when multiple calendars have same name)
        location: Optional event location
        notes: Optional event notes
        all_day: Whether this is an all-day event
        alarms_minutes_offsets: List of alarm offsets in minutes before event
        url: Optional event URL
        recurrence_rule: Optional recurrence rule for recurring events

    Note: If both calendar_id and calendar_name are provided, calendar_id takes precedence.
    If neither is provided, the default calendar will be used.
    """
    try:
        manager = get_calendar_manager()
        request = CreateEventRequest(
            title=title,
            start_time=start_time,
            end_time=end_time,
            calendar_name=calendar_name,
            calendar_id=calendar_id,  # Pass through
            location=location,
            notes=notes,
            all_day=all_day,
            alarms_minutes_offsets=alarms_minutes_offsets,
            url=url,
            recurrence_rule=recurrence_rule,
        )
        event = manager.create_event(request)
        return f"Event created: {event.title} on {event.start_time.strftime('%Y-%m-%d %H:%M')}"

    except MultipleCalendarsException as e:
        # Return helpful error message with calendar options
        return f"Error: {str(e)}\n\nPlease use the list_calendars tool to see calendar IDs, then specify calendar_id parameter."
    except Exception as e:
        return f"Error creating event: {str(e)}"
```

#### 4.2 Update `update_event` tool

**Current:** Lines 149-197

**Changes:** Similar to `create_event`, add `calendar_id` parameter

#### 4.3 Update `list_events` tool

**Current:** Lines 74-95

**Changes:**
```python
@mcp.tool()
async def list_events(
    start_date: datetime,
    end_date: datetime,
    calendar_name: str | None = None,
    calendar_id: str | None = None,  # NEW PARAMETER
) -> str:
    """List calendar events in a date range.

    Args:
        start_date: Start of date range (should be beginning of day, 00:00:00)
        end_date: End of date range (should be end of day, 23:59:59)
        calendar_name: Optional calendar name to filter by (for backward compatibility)
        calendar_id: Optional calendar ID to filter by (preferred)

    Note: If both calendar_id and calendar_name are provided, calendar_id takes precedence.
    """
    try:
        manager = get_calendar_manager()
        events = manager.list_events(
            start_date,
            end_date,
            calendar_id=calendar_id,
            calendar_name=calendar_name
        )

        if not events:
            cal_filter = f" in calendar {calendar_id or calendar_name}" if (calendar_id or calendar_name) else ""
            return f"No events found{cal_filter}"

        return "\n\n".join(str(event) for event in events)

    except MultipleCalendarsException as e:
        return f"Error: {str(e)}\n\nPlease use the list_calendars tool to see calendar IDs, then specify calendar_id parameter."
    except Exception as e:
        return f"Error listing events: {str(e)}"
```

### 5. Add Exception Classes

**File:** `src/mcp_ical/ical.py` (top of file, near NoSuchCalendarException)

```python
class MultipleCalendarsException(Exception):
    """Raised when multiple calendars with the same name are found and disambiguation is required"""
    pass
```

### 6. Update Tests

**File:** `tests/test_calendar_manager_integration.py`

#### New test for duplicate calendar handling:

```python
def test_create_event_with_duplicate_calendar_names(calendar_manager):
    """Test creating events when multiple calendars have the same name"""
    # Create two calendars with the same name
    dup_name = f"test_duplicate_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    cal1 = calendar_manager._create_calendar(dup_name)
    cal2 = calendar_manager._create_calendar(dup_name)

    try:
        # Using calendar_name should raise MultipleCalendarsException
        with pytest.raises(MultipleCalendarsException) as exc_info:
            calendar_manager.create_event(
                CreateEventRequest(
                    title="Test Event",
                    start_time=datetime.now() + timedelta(days=1),
                    end_time=datetime.now() + timedelta(days=1, hours=1),
                    calendar_name=dup_name,
                )
            )

        assert "Multiple calendars" in str(exc_info.value)

        # Using calendar_id should work fine
        event1 = calendar_manager.create_event(
            CreateEventRequest(
                title="Test Event 1",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
                calendar_id=cal1.calendarIdentifier(),
            )
        )

        event2 = calendar_manager.create_event(
            CreateEventRequest(
                title="Test Event 2",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
                calendar_id=cal2.calendarIdentifier(),
            )
        )

        # Verify events are in different calendars
        assert event1._raw_event.calendar().calendarIdentifier() == cal1.calendarIdentifier()
        assert event2._raw_event.calendar().calendarIdentifier() == cal2.calendarIdentifier()

    finally:
        # Cleanup
        calendar_manager.delete_event(event1.identifier)
        calendar_manager.delete_event(event2.identifier)
        calendar_manager._delete_calendar(cal1.uniqueIdentifier())
        calendar_manager._delete_calendar(cal2.uniqueIdentifier())
```

---

## Backward Compatibility

All changes maintain backward compatibility:

1. ✅ `calendar_name` parameter still works for calendars with unique names
2. ✅ `calendar_id` is always optional
3. ✅ Existing code continues to work unchanged
4. ✅ New functionality only activates when calendar_id is provided
5. ✅ Clear error messages guide users when disambiguation is needed

---

## Error Handling Strategy

When a user specifies `calendar_name` and multiple matches are found:

1. **Raise `MultipleCalendarsException`** with helpful message:
   ```
   Multiple calendars named 'Calendar' found:
     - ID: ABC-123-456, Account: Exchange - Work
     - ID: XYZ-789-012, Account: Exchange - Personal

   Please use the list_calendars tool to see calendar IDs,
   then specify calendar_id parameter.
   ```

2. **MCP tool catches exception** and returns user-friendly message

3. **User runs `list_calendars`** to see options

4. **User retries with `calendar_id`** parameter

---

## Testing Strategy

### Unit Tests (in test suite)
- ✅ Test `_find_calendar()` with ID
- ✅ Test `_find_calendar()` with name (unique)
- ✅ Test `_find_calendar()` with name (duplicate) → raises exception
- ✅ Test event creation with calendar_id
- ✅ Test event creation with duplicate calendar_name → raises exception
- ✅ Test list_events filtered by calendar_id

### Integration Tests (manual, on macOS)
- ✅ See `quick-test-prompts.md`
- ✅ Set up duplicate calendar names
- ✅ Verify list_calendars shows IDs
- ✅ Create events using calendar_id
- ✅ Filter events by calendar_id
- ✅ Test error messages when using ambiguous names

---

## Rollout Plan

### Step 1: Implement Core Changes (1-2 hours)
- Add `MultipleCalendarsException`
- Update `_find_calendar()` methods
- Add `_find_calendar()` unified method

### Step 2: Update Models (30 mins)
- Add `calendar_id` to CreateEventRequest
- Add `calendar_id` to UpdateEventRequest

### Step 3: Update CalendarManager (1 hour)
- Update `create_event()`
- Update `update_event()`
- Update `list_events()`

### Step 4: Update MCP Tools (1 hour)
- Update `create_event` tool
- Update `update_event` tool
- Update `list_events` tool
- Add error handling for MultipleCalendarsException

### Step 5: Add Tests (1 hour)
- Write unit tests for duplicate handling
- Write integration test for calendar_id usage

### Step 6: Manual Testing (1 hour)
- Follow `quick-test-prompts.md`
- Verify all scenarios
- Test error messages

### Total Estimated Time: 5-6 hours

---

## Future Enhancements (Phase 3)

After Phase 2 is complete and stable:

1. **Smart calendar suggestion** - When ambiguous name is used, suggest most likely calendar based on context
2. **Calendar aliases** - Allow users to set up aliases for calendars with IDs
3. **Bulk operations** - Apply operations to multiple calendars at once
4. **Calendar creation with specific source** - More control over where new calendars are created

---

## Success Criteria

Phase 2 is complete when:

- ✅ All operations accept `calendar_id` parameter
- ✅ Operations with `calendar_id` work correctly
- ✅ Duplicate `calendar_name` usage raises helpful error
- ✅ All tests pass
- ✅ Manual testing scenarios in `quick-test-prompts.md` pass
- ✅ Backward compatibility maintained
- ✅ Error messages are clear and actionable
- ✅ Documentation updated

---

## Files to Modify

1. `src/mcp_ical/ical.py` - CalendarManager methods
2. `src/mcp_ical/models.py` - Request models
3. `src/mcp_ical/server.py` - MCP tool interfaces
4. `tests/test_calendar_manager_integration.py` - Tests

## Files Already Modified (Phase 1)

✅ `src/mcp_ical/models.py` - Added CalendarInfo
✅ `src/mcp_ical/ical.py` - Added get_calendars_info()
✅ `src/mcp_ical/server.py` - Enhanced list_calendars
✅ `tests/test_calendar_manager_integration.py` - Added test for get_calendars_info()
