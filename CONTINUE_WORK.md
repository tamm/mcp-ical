# How to Continue This Work Locally

## Quick Start: Pull Changes and Test

### 1. Pull the Branch

In your terminal, run:

```bash
cd /path/to/mcp-ical
git fetch origin
git checkout claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
git pull origin claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
```

Or if you want to start fresh:

```bash
cd /path/to/mcp-ical
git fetch origin
git checkout -b test-calendar-fix origin/claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
```

### 2. Review What's Been Done

Check the files that were modified:

```bash
git log --oneline -3
git show HEAD~1  # View Phase 1 implementation
git show HEAD    # View documentation
```

### 3. Test Phase 1 (What's Already Implemented)

**Prerequisites:** Must be on macOS with Calendar.app

1. **Set up test calendars** (see `quick-test-prompts.md` for detailed instructions):
   ```
   Open Calendar.app
   Create two calendars with the same name (e.g., "TestDup")
   ```

2. **Install and run the MCP server:**
   ```bash
   # Install in development mode
   pip install -e .

   # Or if using uv
   uv pip install -e .
   ```

3. **Test using an MCP client** (like Claude Desktop or your terminal MCP client):

   Ask the AI:
   ```
   list all my calendars
   ```

   **Expected output:** Should show calendar IDs and source info for each calendar, making duplicates distinguishable.

4. **Follow the test scenarios** in `quick-test-prompts.md`

### 4. Continue to Phase 2 (Not Yet Implemented)

To complete the fix, you need to implement Phase 2 which adds `calendar_id` parameter support.

**Ask Claude Code:**

```bash
# In your terminal with Claude Code:

claude-code
# Then type:
> I need you to implement Phase 2 from PHASE2_PLAN.md. This adds calendar_id parameter support to all calendar operations (create_event, update_event, list_events) so users can target specific calendars when multiple calendars have the same name. Follow the plan exactly and run tests after implementation.
```

Or more concisely:

```bash
claude-code
> Implement Phase 2 from PHASE2_PLAN.md - add calendar_id parameters to calendar operations and handle duplicate calendar names properly
```

### 5. Test Phase 2 After Implementation

Once Phase 2 is implemented:

```bash
# Run the automated tests
pytest tests/test_calendar_manager_integration.py -v

# Then run manual tests from quick-test-prompts.md
# Specifically Test 2, 3, and 4 which verify calendar_id functionality
```

---

## What Claude Code Should Do

When you ask Claude Code to implement Phase 2, it should:

1. ✅ Add `MultipleCalendarsException` exception class
2. ✅ Add `_find_calendar()` method that handles both ID and name
3. ✅ Update `_find_calendar_by_name()` to detect duplicates
4. ✅ Add `calendar_id` field to `CreateEventRequest` and `UpdateEventRequest`
5. ✅ Update `create_event()`, `update_event()`, `list_events()` in CalendarManager
6. ✅ Update MCP tools to accept and pass through `calendar_id`
7. ✅ Add exception handling for `MultipleCalendarsException`
8. ✅ Add tests for duplicate calendar handling
9. ✅ Run all tests to verify
10. ✅ Commit and push changes

**Estimated time:** 5-6 hours of implementation + testing

---

## Testing Workflow

### Automated Tests (macOS only)

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_calendar_manager_integration.py::test_get_calendars_info -v
```

### Manual MCP Testing

1. **Configure MCP client** (e.g., Claude Desktop):
   - Point to your local development installation
   - Or use `uv run mcp-ical` for testing

2. **Run test prompts** from `quick-test-prompts.md`

3. **Verify behaviors** match expected outcomes

---

## Files You'll Be Modifying (Phase 2)

When implementing Phase 2, you'll modify:

- ✏️ `src/mcp_ical/ical.py` - Add calendar lookup methods
- ✏️ `src/mcp_ical/models.py` - Add calendar_id fields
- ✏️ `src/mcp_ical/server.py` - Update tool signatures
- ✏️ `tests/test_calendar_manager_integration.py` - Add tests

**Tip:** Follow `PHASE2_PLAN.md` section-by-section for a systematic approach.

---

## Current State Summary

### ✅ Phase 1: Visibility (DONE)
- Users can see unique calendar IDs
- Users can see which account each calendar belongs to
- `list_calendars` tool enhanced with detailed info

### ⏳ Phase 2: Operations (TODO)
- Add `calendar_id` parameter to all operations
- Handle duplicate calendar names with clear errors
- Maintain backward compatibility

### 🎯 Goal
Enable users with multiple accounts (e.g., two Exchange accounts) to distinguish and use calendars with identical names.

---

## Need Help?

If you encounter issues:

1. **Check `quick-test-prompts.md`** for test scenarios and expected behaviors
2. **Review `PHASE2_PLAN.md`** for detailed implementation steps
3. **Run git log** to see what's been done: `git log --oneline --graph`
4. **Check the issue**: https://github.com/Omar-V2/mcp-ical/issues/16

---

## Quick Command Reference

```bash
# Pull and setup
git checkout claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
git pull origin claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
pip install -e ".[dev]"

# Test Phase 1
pytest tests/test_calendar_manager_integration.py::test_get_calendars_info -v

# Ask Claude Code to implement Phase 2
# (in Claude Code terminal)
claude-code
> Implement Phase 2 from PHASE2_PLAN.md

# Test Phase 2 (after implementation)
pytest tests/ -v

# Commit changes
git add .
git commit -m "Implement Phase 2: Add calendar_id parameter support"
git push origin claude/investigate-upstream-issue-011CV5NhXVJimjarNMrXqNH8
```

---

## Success Criteria

You'll know it's working when:

✅ `list_calendars` shows unique IDs and sources (Phase 1 - already done)
✅ You can create an event using `calendar_id` parameter
✅ Operations with duplicate `calendar_name` show helpful error messages
✅ All tests pass
✅ Manual test scenarios from `quick-test-prompts.md` all pass
