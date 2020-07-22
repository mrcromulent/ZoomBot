"""

SCA Room Assign Tool

Known Bugs:

User Input to chat box:
AssignMeTo:
AssignMeTo: <Valid Room Name>

Expected Result:
User assigned to <Valid Room>, error message displayed for first command

Result:
Command ignored

Notes:
I suspect this is because zoom_meeting.trim_message() is incorrectly trimming this message, causing the keyword to be
stripped out. The easiest fix is to just ask people to enter their command again
"""

from zoom_meeting import ZoomMeeting
from conf import meeting_params, N, existing_meeting_id

# Initialise a Zoom meeting and check if a driver exists
zm = ZoomMeeting(meeting_params)
resume_meeting_successful = zm.add_driver(existing_meeting_id)

if resume_meeting_successful:
    zm.resume_call()

else:  # Make new meeting or start a scheduled one

    if not zm.logged_in():
        zm.login()

    if existing_meeting_id is not None:  # scheduled
        zm.start_scheduled_call(existing_meeting_id)
    else:  # new
        zm.start_new_call()

# Main loop
while True:

    # Close help windows
    if zm.ask_for_help_window_open():
        zm.close_ask_for_help()

    # Get N most recent messages. If any new messages, trim them and check for keywords (broadcast phrase and
    # move phrase)
    authors, messages = zm.get_n_most_recent_chat_messages(N)
    if zm.new_messages([authors, messages]):

        trimmed_messages = zm.trim_messages(messages, authors, N)
        for message_idx, message in enumerate(trimmed_messages):

            # Broadcast to all rooms
            if zm.broadcast_phrase in message:
                bc_message = zm.extract_from_message(message, zm.broadcast_phrase)
                if bc_message not in zm.broadcast_history:
                    print(f"Broadcasting : {bc_message}")
                    zm.broadcast_message(bc_message)

            # Move people around
            if zm.move_phrase in message:
                target_room = zm.extract_from_message(message, zm.move_phrase)
                target_user = authors[message_idx]

                if zm.move_is_valid(target_user, target_room):
                    print(f"Moving {target_user} to {target_room}")
                    zm.move_user_to_room(target_user, target_room)

    zm.n_most_recent = [authors, messages]
