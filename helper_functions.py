"""
Classes to hold the most common types of errors
"""


class ParticipantNotFoundException(Exception):
    def __init__(self, msg):
        print(msg)


class RoomIndexNotFoundException(Exception):

    def __init__(self, msg):
        print(msg)
