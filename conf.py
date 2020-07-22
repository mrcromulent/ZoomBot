"""
Variables for configuration of zoom meetings using SCA Room Assign Tool
"""

N               = 1
SESSION_PATH    = "session_info.obj"
CHROME_PATH     = "C:/ChromeDriver/chromedriver.exe"


existing_meeting_id = None  # either a valid meeting ID or None, e.g. "860 1959 8282"
username            = ""
password            = ""
room_names          = ["Calligraphy", "Costume", "Cooking", "Performance", "Construction", "Other", "Chatroom 1",
                       "Chatroom 2"]
meeting_docs        = """Bot started. """

meeting_params = {
    "room_names": room_names,
    "SESSION_PATH": SESSION_PATH,
    "CHROME_PATH": CHROME_PATH,
    "username": username,
    "password": password,
    "meeting_docs": meeting_docs}
