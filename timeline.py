import io
from apiclient.http import MediaIoBaseUpload
import os
DEFAULT_MENU_ACTIONS = (
    'REPLY', 'REPLY_ALL', 'DELETE', 'SHARE', 'READ_ALOUD', 'VOICE_CALL', 'NAVIGATE', 'TOGGLE_PINNED')


class Timeline(object):
    attachment = None
    text = None
    html = None
    pinned = False
    title = None
    notify = None

    menu_items = []

    def __init__(self, text=None, html=None, json_data=None, notify=False, menu_items=None):
        if json_data is not None:
            for k, v in json_data.items():
                if k == 'attachments':
                    for a in v:
                        print "A", a
                        if 'contentUrl' in a:
                            self.attachment_url = a['contentUrl']
                print "Setting timeline val", k, v
                setattr(self, k, v)
            return
        if text:
            self.text = text
        if html:
            self.html = html
        self.notify = notify
        if menu_items:
            self.menu_items = menu_items

    def add_attachment(self, filename, content_type):
        """
        Add the file at filename identified by content_type. content_type should be something like 'image/jpeg'
        """
        if not os.path.exists(filename):
            raise ValueError("File does not exist: {0}".format(filename))
        self.attachment_filename = filename
        self.attachment_content_type = content_type
        media = open(filename).read()
        self.attachment = MediaIoBaseUpload(io.BytesIO(media), mimetype=content_type, resumable=True)

    def timeline_body(self):
        timeline_body = {}
        if self.text:
            timeline_body['text'] = self.text
        if self.html:
            timeline_body['html'] = self.html
        if self.notify:
            timeline_body['notification'] = {'level': 'DEFAULT'}
        print "Timeline body", timeline_body
        return timeline_body

    def add_menu_item(self, item):
        """
        Adds a menu item to the timeline card.
        Accepts either a string for a default menu item (must be in DEFAULT_MENU_ITEMS), or a TimelineMenuItem.
        """

    def __str__(self):
        return str(self.id)


class TimelineMenuItem(object):
    action = None

    def __init__(self, action, values, id=None, remove_when_selected=False,):
        # Check that string items are in default menu items. Non string items should be TimelineMenuItems.
        if action not in DEFAULT_MENU_ACTIONS or action == "CUSTOM":
            raise Exception("{0} not in default menu items or CUSTOM".format(action))
        self.action = action
        if self.action == "CUSTOM":
            # Make sure we have a default value in values
            default = 0
            for value in values:
                if 'displayName' not in value or 'iconUrl' not in value or 'state' not in value:
                    raise Exception("Custom menu actions need displayName, iconUrl, and state.")
                if value['state'] == "DEFAULT":
                    default += 1
            if default != 1:
                raise Exception("Custom menu actions need exactly one menu item with 'state' set to DEFAULT")
            self.values = values
