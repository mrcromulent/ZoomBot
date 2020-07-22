# ZoomBot
 Selenium + Zoom Breakout Room Reassigning Tool

## Purpose
ZoomBot was designed for the Society for Creative Anachronism's (SCA's) Polit University Online event, run by the [Barony of Politarchopolis](https://politarchopolis.lochac.sca.org/). This event ran several classrooms in parallel using [Zoom's](https://zoom.us/) Breakout Rooms feature. At time of writing, the Zoom API does not allow users to move themselves between Breakout Rooms either in the UI or programatically, so this program uses the Zoom Chat. Commands should be of the form:

AssignMeTo: RoomName

I'm adding the software to a GitHub after completion of the event because several participants expressed an interest in using and modifying the software further.

## Background

The code is written in Python and it interfaces with Zoom using Selenium and the Chrome Webdriver. Because the ZoomBot works using Selenium, it uses the mouse to click elements on the Zoom.us webpage, so the best way to ensure it works properly is to start it up on the machine you'd like to host the meeting and then leave it alone as much as possible (you'll still need to interact with it for some things through, like assigning co-hosts) for the duration of the meeting. For example, if you were to click into a different window and then fail to click back to the Selenium Chrome Window, you'll get a StaleElementException because the elements the ZoomBot is trying to read are inaccessible. 
It's also worth saying that the ZoomBot can break at any time if Zoom changes their web design. (This happened twice during Polit Uni Online, which really speaks to the need for Zoom to include Breakout Rooms in their API).

### Prerequisites: 
- A Zoom Account (with the Large Meeting addon to support hundreds of attendees). You'll need to run these meetings through the Zoom web portal instead of the zoom app.
- A Google Chrome installation and Chrome Driver. Be sure to match the version at `chrome:\\version`

In your Zoom Settings, you'll also need to enable the "Breakout Rooms" and "Always show meeting control toolbar" options. We also set the "Who Can Share?" option to Host Only because we found that screen sharing would modify the DOM unexpectedly, which could interfere with the ZoomBot's operation. (Participants can still screenshare within breakout rooms). 

## Setup

The file that you'll need to modify is conf.py. You'll need to do several things here:
- Fill in your Zoom credentials in the username and password variables
- Fill in the path to your chrome driver in CHROME_PATH
- If you want to start a pre-scheduled meeting, enter its meeting id as a string in the existing_meeting_id variable

I would recommend leaving the value of N to 1. N is the number of most recent messages that the ZoomBot will look through for commands. I wrote the code so that N could be increased if need be but I have only really tested it at 1 and the speed was sufficient regardless of the number of participants. 

## Running ZoomBot:

Running ZoomBot is relatively easy. 

1. If you are running ZoomBot on Mac, you will need to start the ChromeDriver, which is a Unix Executable. On Windows, this was not needed
2. In the appropriate folder, just run "python3 scaroomassign.py"
3. If the following two steps worked correctly, a new Chrome window should pop up and load a Zoom Webpage and log you in using your credentials. Zoom will then present you with a difficult CAPTCHA. ZoomBot will give you up to 10 minutes to solve this and as soon as you're done, it will take over again.
4. If you set ZoomBot to start a new meeting, it will start one automatically. Otherwise, it will navigate to the Meetings tab and find a meeting matching the id you specified in conf.py. Selenium had trouble handling some of Zoom's popups (specifically "Open this meeting in the Zoom App?" and "Allow Notifications from this webpage?") so you will need to close these manually.

From here, the ZoomBot should set up the meeting for you by opening the chat, setting up the breakout rooms, etc. If the meeting set up correctly, you shouldn't need to do anything else. 

## Error Management

You can test whether the bot is working correctly by using the commands. Have a user send a message through the chat using the "Move Phrase"

AssignMeTo: RoomName

If RoomName is one of the breakout rooms, ZoomBot should detect the message and assign the user to the room. Once breakout rooms have been opened, you can broadcast messages to all breakout rooms using the "Broadcast Phrase"

Broadcast: Message

I've included some common-sense error checks for things like misspelled rooms and users who have names that are too long (so that you can't identify who needs to move based on their name). I've also done some rudimentary commenting in the code and listed known bugs in scaroomassign.py but hopefully you shouldn't have any trouble. If the ZoomBot fails mid-meeting, you can just re-run "python3 scaroomassign.py" and the ZoomBot can pick up from where it left off (as long as you haven't closed the chrome tab). 

All the best!

Pierre

