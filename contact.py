class Contact(object):
    """
    Represents something users can share to.
    Requires either display_name or json_data.
    """
    def __init__(self, display_name=None, id=None, image_urls=[], type="INDIVIDUAL", accept_types=[], phone_number=None,
                 priority=1, json_data=None):
        if json_data is not None:
            for k, v in json_data.items():
                setattr(self, k, v)
            return
        if display_name is None or display_name == "":
            raise Exception("Contacts must have display names.")
        self.display_name = display_name
        if id is None:
            self.id = display_name.replace(' ', '_')
        else:
            self.id = id
        if image_urls == []:
            raise Exception("Contacts must have image urls.")
        elif len(image_urls) > 8:
            raise Exception("Contacts cannot have more than 8 image URLs.")
        self.image_urls = image_urls
        if type not in ("INDIVIDUAL", "GROUP"):
            raise Exception("Contact type must be either INDIVIDUAL or GROUP")
        self.type = type
        self.accept_types = accept_types
        self.phone_number = phone_number
        self.priority = priority

    def contact_body(self):
        body = {
            'displayName': self.display_name,
            'imageUrls': self.image_urls,
            'type': self.type,
            'id': self.id
        }
        if self.accept_types:
            body['acceptTypes'] = self.accept_types
        if self.phone_number:
            body['phoneNumber'] = self.phone_number
        if self.priority:
            body['priority'] = self.priority
        print "body", body
        return body
