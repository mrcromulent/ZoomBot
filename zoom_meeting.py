import re
import time
import pickle as pk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from helper_functions import ParticipantNotFoundException, RoomIndexNotFoundException
from urllib3.exceptions import MaxRetryError


class ZoomMeeting(object):
    """
    Container to hold all the main operations of handling a zoom meeting. self.d is the chromedriver and holds all the
    DOM information. This is what you need to manipulate to access the webpage

    user_locs is a dictionary that stores the last known breakout room location of users, indexed by user name
    """

    move_phrase         = "AssignMeTo: "
    broadcast_phrase    = "Broadcast: "
    command_history     = []
    user_locs           = dict()
    broadcast_history   = []
    n_most_recent       = [[], []]
    very_long_wait      = 20  # seconds
    long_wait           = 4  # seconds
    short_wait          = 0  # seconds

    ZOOM_SIGNIN_PATH    = "https://zoom.us/signin"
    ZOOM_START_PATH     = "https://zoom.us/start/webmeeting"
    ZOOM_PROFILE_PATH   = "https://zoom.us/profile"
    ZOOM_MEETINGS_PATH  = "https://zoom.us/meeting"

    def __init__(self, meeting_params):
        self.d              = None
        self.room_names     = meeting_params["room_names"]
        self.SESSION_PATH   = meeting_params["SESSION_PATH"]
        self.CHROME_PATH    = meeting_params["CHROME_PATH"]
        self.username       = meeting_params["username"]
        self.password       = meeting_params["password"]
        self.meeting_docs   = meeting_params["meeting_docs"]

    def set_driver_from_file(self):
        """
        Restarts ZoomBot using session information stored at SESSION_PATH. Sets self.d as driver from file
        """

        with open(self.SESSION_PATH, "rb") as handle:
            session_info = pk.load(handle)

        driver = webdriver.Remote(command_executor=session_info["url"], desired_capabilities={})
        driver.close()  # this prevents the dummy browser
        driver.session_id = session_info["session_id"]

        self.d = driver
        self.set_global_driver_settings()

    def set_global_driver_settings(self):
        """
        Sets the driver implicit wait time and maximises the chrome window
        """

        self.d.implicitly_wait(self.long_wait)
        self.d.maximize_window()

    def set_new_driver(self):
        """
        Initialises a new driver and saves this information to SESSION_PATH in case a restart is required
        """

        # Make a driver and login
        driver = webdriver.Chrome(self.CHROME_PATH)

        # Save session info
        session_info = {"url": driver.command_executor._url,
                        "session_id": driver.session_id}

        with open(self.SESSION_PATH, "wb") as handle:
            pk.dump(session_info, handle)

        self.d = driver
        self.set_global_driver_settings()

    def logged_in(self):
        """
        Returns True if the user is logged in
        """

        self.d.get(self.ZOOM_PROFILE_PATH)
        not_logged_in, _ = self.check_if_exists(By.NAME, "password", self.very_long_wait)

        if not_logged_in:
            return False
        return True

    def login(self):
        """
        Enters the user's login credentials on the login page
        """
        uname = self.d.find_element_by_name("email")
        uname.clear()
        uname.send_keys(self.username)

        pword = self.d.find_element_by_name("password")
        pword.clear()
        pword.send_keys(self.password)
        pword.send_keys(Keys.RETURN)

        print("Handle any CAPTCHAS and popups that appear. You have 10 minutes")
        WebDriverWait(self.d, 600).until(ec.title_is("My Profile - Zoom"), "Waiting for profile page to load")

    def dismiss_audio(self):
        """
        Closes the "Connect to audio" frame
        """

        print("Dismissing audio")
        self.click_if_exists(By.XPATH, '//div[@data-focus-lock-disabled="false"]/div/div/button')

    def open_chat(self):
        """
        Opens the chat
        """
        print("Opening chat")
        self.click_if_exists(By.XPATH, '//button[@aria-label="close the chat pane"]')
        self.d.find_element_by_xpath('//button[@aria-label="open the chat pane"]').click()

    def send_message_to_chat(self, message):
        """
        Sends the string message to chat
        :param message:
        :return:
        """

        self.d.find_element_by_class_name("chat-box__chat-textarea").send_keys(message)
        self.d.find_element_by_class_name("chat-box__chat-textarea").send_keys(Keys.RETURN)

    def get_n_most_recent_chat_messages(self, n):
        """
        Retrieves the n most recent messages from the chat
        :param n:
        :return:
        """

        chat_items = self.d.find_elements_by_class_name("chat-item__chat-info")[-n:]

        authors     = []
        messages    = []

        for item in chat_items:
            authors.append(item.find_element_by_xpath(".//div[1]/span[1]").get_attribute("innerText").strip())
            messages.append(item.find_element_by_xpath(".//pre[1]").get_attribute("innerText"))

        return authors, messages

    def open_participants_pane(self):
        """
        Opens the participants pane
        :return:
        """
        print("Opening participants pane")
        self.click_if_exists(By.XPATH, '//button[starts-with(@aria-label, "close the manage participants list pane")]')
        self.d.find_element_by_xpath(
            '//button[starts-with(@aria-label, "open the manage participants list pane")]').click()

    def open_breakout_room_menu(self):
        """
        Opens the breakout rooms menu
        :return:
        """
        already_open, _ = self.check_if_exists(By.CLASS_NAME, "bo-room-item-container__btn-group")

        if not already_open:
            open_button_visible, button = self.check_if_exists(By.XPATH, '//button[@aria-label="Breakout Rooms"]')

            if open_button_visible:
                button.click()
            else:
                self.d.find_element_by_id("moreButton").click()
                self.d.find_element_by_xpath('//a[@aria-label="Breakout Rooms"]').click()

    def set_up_breakout_rooms(self):
        """
        Sets the number and names of the breakout rooms
        :return:
        """

        print("Setting up breakout rooms")
        # Set up n rooms with manual arrangement
        self.open_breakout_room_menu()
        rooms_not_started, _ = self.check_if_exists(By.CLASS_NAME, 'zmu-number-input', self.long_wait)

        if rooms_not_started:
            self.d.find_element_by_class_name('zmu-number-input').send_keys(Keys.BACKSPACE)
            self.d.find_element_by_class_name('zmu-number-input').send_keys(str(len(self.room_names)))
            self.d.find_element_by_xpath('//div[@aria-label="Manually"]').click()
            self.d.find_element_by_class_name("bo-createwindow-content__actions").\
                find_element_by_xpath('.//button[2]').click()

            # Rename rooms according to room_names
            bo_room_list_container = self.d.find_element_by_class_name("bo-room-list-container")

            for i, name in enumerate(self.room_names):
                bo_room = bo_room_list_container.find_element_by_xpath(f".//ul/li[{i + 1}]")
                content = bo_room.find_element_by_xpath(".//div/div/div")

                # Mouse over correct room and click rename
                ActionChains(self.d).move_to_element(content).click().perform()
                ActionChains(self.d).move_to_element(content.find_element_by_xpath(".//button[1]")).click().perform()

                # Type in new name and confirm
                self.d.find_element_by_class_name('confirm-tip__tip').find_element_by_xpath(".//input").send_keys(name)
                self.d.find_element_by_class_name('confirm-tip__footer').find_element_by_xpath('.//button[1]').click()

    @property
    def d(self):
        """
        Property method for chromedriver
        :return:
        """
        return self._d

    @d.setter
    def d(self, value):
        self._d = value

    def check_if_exists(self, by_tag, link_tag, wait_time=None):
        """
        Checks for the existence of a particular element on the DOM
        :param by_tag:
        :param link_tag:
        :param wait_time:
        :return:
        """

        if wait_time is None:
            wait_time = self.short_wait

        try:
            WebDriverWait(self.d, wait_time).until(ec.presence_of_element_located((by_tag, link_tag)), "")
            return True, self.d.find_element(by_tag, link_tag)
        except TimeoutException:
            return False, None

    def click_if_exists(self, by_tag, link_tag, wait_time=None):
        """
        Clicks a particular element if it exists in the DOM
        :param by_tag:
        :param link_tag:
        :param wait_time:
        :return:
        """

        exists, elem = self.check_if_exists(by_tag, link_tag, wait_time)
        if exists and elem.is_displayed():
            elem.click()

    def join_from_browser(self):
        """
        Clicks the "join from browser" button when starting up a meeting. Also dismisses the existing meeting
        :return:
        """

        print("Joining from browser")
        self.click_if_exists(By.ID, "btn_end_meeting", self.long_wait)
        self.click_if_exists(By.PARTIAL_LINK_TEXT, "join from your browser", self.long_wait)
        self.click_if_exists(By.ID, "btn_end_meeting", self.long_wait)

    def move_is_valid(self, target_user, target_room):
        """
        Determines whether a move is valid. Validity is defined as:
        - the target_user's name is not truncated
        - the target_room is either a valid name and
        - the target_user is not in the target_room already

        :param target_user:
        :param target_room:
        :return:
        """

        if target_user.endswith("..."):
            self.send_message_to_chat(f"{target_user} - Name too long. Please shorten it.")
            return False

        if target_room in self.room_names:
            if target_user not in self.room_participants(target_room):
                return True
            else:
                self.send_message_to_chat(f"{target_user} already in {target_room}")
                return False

        elif target_room.startswith("[CLASS NAME]"):
            pass
        else:
            self.send_message_to_chat(f"{target_user} - {target_room} is not a valid name. Check spelling.")

    def start_new_call(self):
        """
        Starts a new Zoom Meeting if an existing one cannot be resumed
        :return:
        """

        self.d.get(self.ZOOM_START_PATH)
        self.set_up_call()

    def disable_screen_sharing(self):
        """
        Disables sharing to limit data transfer rate
        :return:
        """

        self.d.find_element_by_id("sharePermissionMenu").click()
        adv_sharing_opts = self.d.find_element_by_xpath('//ul[@aria-labelledby="sharePermissionMenu"]/li[3]/a')
        adv_sharing_opts.click()

        only_me_button = self.d.find_element_by_xpath('//div[@aria-labelledby="radio_group_ability"]/div/div')
        only_me_button.click()

        close_button = self.d.find_element_by_class_name('zm-modal-footer-default-actions').\
            find_element_by_xpath('.//button')
        close_button.click()

    def set_up_call(self):
        """
        Sets up call for new or resumed calls, providing time for the user to dismiss popups and performs setup tasks
        such as opening chat, and setting up breakout rooms
        :return:
        """

        self.join_from_browser()

        print(f"Waiting {self.very_long_wait} seconds for page...")
        time.sleep(self.very_long_wait)

        self.dismiss_audio()
        self.disable_video_receiving()
        self.disable_screen_sharing()
        self.open_chat()
        self.open_participants_pane()
        self.set_up_breakout_rooms()
        self.send_message_to_chat(self.meeting_docs)

        # Lower the implicit wait time
        self.d.implicitly_wait(self.short_wait)

    def add_driver(self, existing_meeting_id):
        """
        Determines if an existing meeting is still open and if so, tries to connect to the Chrome instance running that
        meeting
        :param existing_meeting_id:
        :return:
        """

        try:
            self.set_driver_from_file()
            if existing_meeting_id is not None:
                return False
            return True
        except (MaxRetryError, FileNotFoundError) as e:
            print(str(e))
            self.set_new_driver()
            return False

    def start_scheduled_call(self, existing_meeting_id):
        """
        Checks the meetings tab for a scheduled meeting matching existing_meeting_id
        :param existing_meeting_id:
        :return:
        """

        existing_meeting_id = existing_meeting_id.strip()
        print(f"Searching for existing meeting: {existing_meeting_id}")

        self.d.get(self.ZOOM_MEETINGS_PATH)

        meetings = self.d.find_element_by_class_name("mtg-list-content")
        meetings_list = meetings.find_elements_by_class_name("clearfix")

        for meeting in meetings_list:
            meeting_id = meeting.find_element_by_class_name("meetingId").get_attribute("innerText").strip()

            if existing_meeting_id == meeting_id:
                meeting.find_element_by_xpath('.//a[@ui-cmd="Start"]').click()
                self.set_up_call()
                return None

        print(f"Couldn't find meeting matching ID: {existing_meeting_id}")

    def resume_call(self):
        """
        Determines whether setup of a Zoom meeting was complete by checking the window title. If incomplete, a new call
        is started
        :return:
        """

        if "Zoom Meeting" or "Polit University Online" in self.d.title:
            print("Setting up call")
            self.set_up_call()
        else:
            print("Starting new call")
            self.start_new_call()

    def new_messages(self, aut_mess):
        """
        Returns true if [authors, messages] is different than self.n_most_recent
        """

        first_set = set(map(tuple, self.n_most_recent))
        secnd_set = set(map(tuple, aut_mess))

        return bool(first_set ^ secnd_set)
    
    def broadcast_message(self, message):
        """
        Uses Zoom's broadcast feature to send the string message to all breakout rooms
        :param message:
        :return:
        """

        if self.breakout_rooms_started():
            self.open_breakout_room_menu()
            bc_button = self.d.find_element_by_class_name("bo-room-in-progress-footer__actions").\
                find_element_by_xpath(".//button")
            bc_button.click()
            textarea = self.d.find_element_by_class_name("bo-room-broadcast-paper__textarea")
            textarea.send_keys(message)

            send_button = self.d.find_element_by_class_name("bo-room-broadcast-paper__footer").\
                find_element_by_xpath(".//button")
            send_button.click()

            # Add to history to avoid rebroadcast
            self.broadcast_history.append(message)

    def extract_from_message(self, message, keyword):
        """
        Catches messages after a command phrase (Move Phrase or Broadcast Phrase) and zeros out any other command
        phrases in the message
        """

        regexp  = r"(?<=" + keyword + ").+$"
        match   = re.findall(regexp, message, re.MULTILINE)
        message = match[-1]

        clean_msg = message.replace(self.move_phrase, "").replace(self.broadcast_phrase, "").strip()

        return clean_msg

    def move_user_to_room(self, target_user, target_room):
        """
        Attempts to move target_user to target_room. This procedure is different depending on whether or not breakout
        rooms are currently "started"

        This function searches the last known location of a user first to save time. If they are not found, it cycles
        through all the breakout rooms (including the psuedo-room "Unassigned") until the user is found.

        :param target_user:
        :param target_room:
        :return:
        """

        bo_room_list_container  = self.d.find_element_by_class_name("bo-room-list-container")

        # If rooms have not yet been opened
        if not self.breakout_rooms_started():

            # click assign
            bo_room_list_container.find_element_by_xpath(
                '//div[starts-with(@aria-label, "' + target_room + '")]/div[2]/button').click()
            assign_list = self.d.find_element_by_class_name("bo-room-assign-list-scrollbar")

            assignees = []
            avail_assignees = self.d.find_elements_by_class_name("zmu-data-selector-item")
            for assignee in avail_assignees:
                assignees.append(assignee.find_element_by_xpath(".//span/span[2]/span").get_attribute("innerText"))

            target_idx = assignees.index(target_user)
            assign_list.find_element_by_xpath(f".//div/div/div[{target_idx+1}]").click()

            self.start_breakout_rooms()
            self.user_locs[target_user] = target_room

        # If rooms have already been opened
        else:
            try:
                lk_room_name = self.last_known_location(target_user)
                lk_room_participants = self.room_participants(lk_room_name)

                if target_user not in lk_room_participants:
                    lk_room_name = self.search_rooms_for_user(target_user)

                lk_room_idx = self.room_idx(lk_room_name, unassigned_incl=True)
                curr_room = bo_room_list_container.find_element_by_xpath(f".//ul/li[{lk_room_idx}]")
                attendees = curr_room.find_elements_by_class_name("bo-room-item-attendee")
                attendee = attendees[self.attendee_idx(target_user, lk_room_name, start_at_zero=True)]

                self.assign_attendee_to_room(attendee, target_room, lk_room_name)
                self.user_locs[target_user] = target_room

            except (NoSuchElementException, ParticipantNotFoundException) as e:
                msg = f"Tried to move {target_user} to {target_room}. An error occurred. Did they move?"
                self.send_message_to_chat(msg)
                print(str(e))

    def search_rooms_for_user(self, target_user):
        """
        Cycles through rooms to locate target_user. The room where they are located is returned or
        ParticipantNotFoundException is raised
        """

        if target_user in self.room_participants("Unassigned"):
            return "Unassigned"

        for test_room in self.room_names:
            room_part = self.room_participants(test_room)
            if target_user in room_part:
                return test_room

        raise ParticipantNotFoundException(f"Target user: {target_user} not found")

    def room_participants(self, target_room):
        """
        Returns a list of participants of target_room
        :param target_room:
        :return:
        """

        if target_room == "Unassigned" and not self.unassigned_room_open():
            return []

        if self.room_name_valid(target_room):
            xpath = '//div[starts-with(@aria-label, "' + target_room + '")]'
            room_banner = self.d.find_element_by_xpath(xpath)
        else:
            return []

        if not (room_banner.get_attribute("aria-expanded") == 'true'):
            room_banner.find_element_by_xpath('.//parent::div').click()
            
        bo_room = room_banner.find_element_by_xpath('.//parent::div//parent::li')
        attendees = bo_room.find_elements_by_class_name("bo-room-item-attendee")
        participants = []

        for attendee in attendees:
            raw_name = attendee.find_element_by_xpath('.//span[starts-with(@class, "bo-room-item-attendee__name")]')
            participants.append(raw_name.get_attribute('innerText'))

        return participants

    def breakout_rooms_started(self):
        """
        Returns True if breakout rooms have started
        :return:
        """
        self.open_breakout_room_menu()
        exists, _ = self.check_if_exists(By.CLASS_NAME, "bo-room-not-started-footer__btn-wrapper")
        return not exists

    def start_breakout_rooms(self):
        """
        Clicks "Open Breakout Rooms" button
        :return:
        """

        self.d.find_element_by_class_name("bo-room-not-started-footer__actions")\
            .find_element_by_xpath(".//div[4]/button[1]").click()

    def ask_for_help_window_open(self):
        """
        Returns True if the "Ask Host For Help" window is open
        :return:
        """
        exists, _ = self.check_if_exists(By.XPATH, '//div[contains(@aria-label, "asked for help.")]')
        return exists

    def close_ask_for_help(self):
        """
        Closes the "Ask Host for Help" window and sends a message to chat with the details of who asked for help
        :return:
        """

        mod_wind = self.d.find_element_by_xpath('//div[contains(@aria-label, "asked for help.")]')
        help_text = mod_wind.find_element_by_class_name('content').get_attribute("innerText")
        mod_wind.find_element_by_xpath('.//button[@aria-label="close modal"]').click()
        self.send_message_to_chat(help_text)

    def room_idx(self, target_room, start_at_zero=False, unassigned_incl=False, skip=None):
        """
        Returns the index of target_room based on its name

        :param target_room: room name
        :param start_at_zero: indicates whether the list uses Python indexing or DOM indexing
        :param unassigned_incl: indicates whether "Unassigned" appears on the list
        :param skip: Any elements that will be excluded from the list
        :return: Integer index
        """

        uro     = self.unassigned_room_open()
        offset  = 0

        if target_room in self.room_names:
            base_idx = self.room_names.index(target_room)
            if unassigned_incl and uro:
                offset += 1
        elif target_room == "Unassigned" and uro:
            base_idx = 0
        elif target_room == "Unassigned" and not uro:
            return None
        else:
            msg = f"target room: {target_room}, start at zero: {start_at_zero}, " \
                  f"unassigned included: {unassigned_incl}, skip: {skip}"
            raise RoomIndexNotFoundException(msg)

        if not start_at_zero:
            offset += 1

        if skip is not None:
            if "Unassigned" in skip:
                skip.remove("Unassigned")
            
            for room in skip:
                if self.room_names.index(room) < base_idx:
                    offset -= 1

        return base_idx + offset

    def last_known_location(self, target_user):
        """
        Returns the last known location of a user based on the dictionary self.user_locs
        :param target_user:
        :return:
        """

        if target_user in self.user_locs.keys():
            return self.user_locs[target_user]
        else:
            return "Unassigned"

    def attendee_idx(self, target_user, room, start_at_zero=False):
        """
        Returns the index of a particular target user based on their name
        :param target_user: user name
        :param room: room that user is currently in
        :param start_at_zero: indicates whether Python indexing or DOM indexing is used
        :return: Integer index
        """

        if start_at_zero:
            offset = 0
        else:
            offset = 1

        attendees = self.room_participants(room)
        return attendees.index(target_user) + offset

    def unassigned_room_open(self):
        """
        Returns True if Breakout rooms are open and there are unassigned users
        :return:
        """

        first_bo_item_name = self.d.find_element_by_class_name("bo-room-item-container__title")\
            .get_attribute("innerText")
        if first_bo_item_name != self.room_names[0]:
            return True
        return False

    def room_name_valid(self, room_name):
        """
        Returns true if the room name is Unassigned or in the name list
        :param room_name:
        :return:
        """

        return room_name in self.room_names or room_name == "Unassigned"

    def assign_attendee_to_room(self, attendee, target_room, lk_room_name):
        """
        Clcicks the Assign button next to a uaer's name to move them to target_room
        :param attendee:
        :param target_room:
        :param lk_room_name:
        :return:
        """

        # Click Assign To
        ActionChains(self.d).move_to_element(attendee).perform()
        assign_button = self.d.find_element_by_class_name("bo-room-item-attendee__tools").\
            find_element_by_xpath(".//button")

        ActionChains(self.d).move_to_element(assign_button).click().perform()
        assign_box = self.d.find_element_by_class_name("bo-room-item-attendee__moveto-list-scrollbar")

        options = assign_box.find_elements_by_class_name("zmu-data-selector-item")
        options[self.room_idx(target_room, start_at_zero=True, unassigned_incl=False, skip=[lk_room_name])].click()

    def trim_messages(self, messages, authors, num):
        """Trims the most recent message in the chat using the internal memory. This is to prevent re-execution of
        commands which have already been performed.

        The issue here is that Zoom groups together your most recent messages into one message. For example, if you sent
        a message 10 minutes ago and then sent a new message, both of those would be returned as your newest message,
        provided no one else sent anything to the chat in the interim. The goal here is to only grab new content."""

        most_recent_messages        = messages[-num:]
        most_recent_authors         = authors[-num:]
        most_recent_messages_mem    = self.n_most_recent[1][-num:]
        most_recent_authors_mem     = self.n_most_recent[0][-num:]

        msg_copy = messages[:]
        if len(most_recent_messages_mem) > 0:
            for i, msg in enumerate(most_recent_messages):
                if most_recent_authors[i] == most_recent_authors_mem[i]:
                    msg_copy[i] = msg.replace(most_recent_messages_mem[i], "")

        return msg_copy

    def disable_video_receiving(self):
        """
        Disables video receiving
        :return:
        """

        print("Disabling video receiving")
        self.d.find_element_by_id("moreButton").click()
        self.click_if_exists(By.XPATH, '//a[@aria-label="Disable video receiving"]')
