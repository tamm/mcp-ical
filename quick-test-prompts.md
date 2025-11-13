# Quick Test Prompts for Calendar Disambiguation

This file contains minimal test prompts to verify the calendar disambiguation feature works correctly. These tests are designed to fail WITHOUT the fix but succeed WITH the fix.

## Prerequisites

Before running these tests, you need to set up your macOS Calendar app with duplicate calendar names:

### Setup Instructions

1. Open Calendar.app on macOS
2. Create two calendars with identical names from different accounts:
   - **Option A:** If you have two iCloud/Exchange accounts:
     - Add a calendar called "Test" to account 1
     - Add a calendar called "Test" to account 2

   - **Option B:** If you only have one account:
     - Create a calendar called "TestDup"
     - Create another calendar called "TestDup" (same account is fine for testing)

3. Note: The default "Calendar" name from multiple Exchange accounts is the real-world scenario this solves.

## Test 1: List Calendars with Disambiguation

**Prerequisites:** Two calendars with the same name (e.g., "TestDup")

**Test Prompt:**
```
list all my calendars
```

**Expected Behavior WITHOUT fix:**
- Only shows calendar names
- Cannot distinguish which "TestDup" is which
- Output: just a simple list like "- TestDup\n- TestDup"

**Expected Behavior WITH fix:**
- Shows calendar name, unique ID, and account/source info
- Each calendar clearly identified by its source
- Output includes:
  ```
  - TestDup
    ID: <unique-id-1>
    Account: iCloud (CalDAV)
  - TestDup
    ID: <unique-id-2>
    Account: Local (Local)
  ```

**Result:** ✅ PASS if you can see unique IDs and source information

---

## Test 2: Create Event in Specific Calendar (Phase 2 - NOT YET IMPLEMENTED)

**Prerequisites:** Two calendars with the same name AND Phase 2 implementation

**Test Prompt:**
```
Create an event called "Team Meeting" tomorrow at 2pm in the TestDup calendar
from my Work Exchange account (ID: <paste-actual-id>)
```

**Expected Behavior WITHOUT Phase 2:**
- Creates event in the FIRST calendar named "TestDup" (whichever that happens to be)
- No way to target a specific calendar when names are duplicated

**Expected Behavior WITH Phase 2:**
- Accepts calendar_id parameter
- Creates event in the specifically identified calendar
- Confirmation shows correct account/source

**Status:** ⏳ NOT YET IMPLEMENTED - Phase 2 required

---

## Test 3: Verify Event Creation with Ambiguous Name (Current Limitation)

**Prerequisites:** Two calendars with the same name (e.g., "TestDup")

**Test Prompt:**
```
Create an event called "Dentist Appointment" tomorrow at 10am in TestDup
```

**Current Behavior (Phase 1):**
- Event is created in the FIRST calendar named "TestDup"
- User cannot control which one
- This is the existing limitation we're documenting

**After Phase 2:**
- MCP client should warn: "Multiple calendars named 'TestDup' found. Please specify calendar_id:"
- Lists the options with IDs
- User can then specify: `calendar_id: ABC-123-456`

**Status:** ⚠️ KNOWN LIMITATION - Phase 2 will address this

---

## Test 4: List Events Filtered by Calendar ID (Phase 2)

**Prerequisites:** Events in both "TestDup" calendars AND Phase 2 implementation

**Test Prompt:**
```
Show me all events in calendar ID <paste-specific-id>
```

**Expected Behavior WITH Phase 2:**
- Filters events to only the specific calendar identified by ID
- Ignores the other calendar with the same name

**Status:** ⏳ NOT YET IMPLEMENTED - Phase 2 required

---

## Quick Validation Checklist

Run these in order to validate the current state:

- [ ] **Test 1** - List calendars and see IDs/sources (✅ SHOULD PASS NOW)
- [ ] **Test 2** - Try creating event with calendar_id parameter (⏳ WILL FAIL - needs Phase 2)
- [ ] **Test 3** - Create event with ambiguous name (⚠️ WORKS but uses first match)
- [ ] **Test 4** - Filter events by calendar ID (⏳ WILL FAIL - needs Phase 2)

## Notes for Manual Testing

1. **This is macOS only** - requires EventKit framework
2. **Calendar permissions** - First run will prompt for Calendar access
3. **Real calendar app** - Tests interact with your actual Calendar.app data
4. **Clean up** - Delete test calendars after testing
5. **Sync delays** - iCloud calendars may have sync delays (wait 5-10 seconds)

## What's Working Now (Phase 1)

✅ Visibility - You can now SEE which calendar is which
✅ Unique IDs exposed
✅ Source/account information displayed

## What's Still Needed (Phase 2)

❌ Operations using calendar_id parameter
❌ Disambiguation when multiple calendars have same name
❌ Warning messages for ambiguous calendar names
❌ Update create_event, update_event, delete_event, list_events to accept calendar_id

---

## How to Use This File

1. Set up test calendars per Prerequisites
2. Run Test 1 to verify Phase 1 is working
3. Use the output to document current behavior
4. Implement Phase 2 following the plan in PHASE2_PLAN.md
5. Re-run all tests to verify complete fix
