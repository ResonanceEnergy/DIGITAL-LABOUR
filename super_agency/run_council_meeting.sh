#!/bin/bash
# Digital Labour Agent Council Meeting Runner
# Triggered every 15 minutes by launchd

cd "$HOME/repos/DIGITAL LABOUR-Shared"

# Run the council meeting
python3 agent_council_meeting.py >> council_meetings/scheduler.log 2>&1

# Keep scheduler log trimmed (last 2000 lines)
if [ -f council_meetings/scheduler.log ]; then
    tail -2000 council_meetings/scheduler.log > council_meetings/scheduler.log.tmp
    mv council_meetings/scheduler.log.tmp council_meetings/scheduler.log
fi
