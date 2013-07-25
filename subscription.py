class SubscriptionEvent(object):
    def parse(self, notification, mirror):
        """

        @param notification: dict parsed from JSON from Google POST.
        @param mirror: a Mirror object so the object can preemptively get Timeline and Location objects.
        @return: event_type: The parsed event type, also saved to self.event_type. The rest of the parsed information
        will be saved to object attributes, depending on type.
        SHARE and REPLY will a timeline attribute that is a Timeline object.
        DELETE will have a timeline_id attribute which is the deleted card's id.
        CUSTOM will have a actions attribute that is a dict of the custom userActions the user did and
        a menu_item attribute that is the id for a TimelineMenuItem. It is up to you to find that TimelineMenuItem.
        Location updates will have a location attribute that is a Location object representing the user's latest
        location.
        """
        self._mirror = mirror
        try:
            self.item_id = notification["itemId"]
            self.operation = notification["operation"]
            self.user_token = notification["userToken"]
            if 'verifyToken' in notification:
                self.verify_token = notification["verifyToken"]
            else:
                # No verification token in custom type?
                self.verify_token = None
            self.verify(self.verify_token)
            # Dispatch to individual type handlers based on action type
            if notification["collection"] == "locations":
                self.event_type = "locations"
                self._location_update(notification)
            notification_type = notification["userActions"][0]["type"]

            if notification_type == 'SHARE':
                self.event_type = 'share'
                self._share(notification)
            elif notification_type == 'REPLY':
                self.event_type = "reply"
                self._reply(notification)
            elif notification_type == 'DELETE':
                self.event_type = "delete"
                self._delete(notification)
            elif notification_type == 'CUSTOM':
                self.event_type = "custom"
                self._custom(notification)
            else:
                raise Exception("Unknown notification type from Google: {0}".format(notification_type))
            return self.event_type
        except KeyError as e:
            raise Exception("Malformed subscription message from Google.")

    def verify(self, verify_token):
        """
        Override this if you want built in verification of all steps. Raise an exception if it does not verify.
        """
        return

    def _location_update(self, notification):
        raise NotImplementedError()

    def _share(self, notification):
        print "notification", notification['itemId']
        self.timeline = self._mirror.get_timeline(notification['itemId'])

    def _reply(self, notification):
        self.timeline = self._mirror.get_timeline(notification['itemId'])

    def _delete(self, notification):
        """
        Really nothing to do here. We could verify maybe?
        """
        return

    def _custom(self, notification):
        # self.menu_item = self._mirror.
        self.menu_item = notification['itemId']
        self.actions = notification['userActions']
        # Don't need type, already saved.
        del(self.actions['type'])
