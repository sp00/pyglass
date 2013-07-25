import unittest
from glass.mirror import Mirror, Timeline, TimelineAttachment

mirror = Mirror()
mirror.get_my_oauth()


class TestTimeline(unittest.TestCase):
    def test_list_timeline(self):
        pass
