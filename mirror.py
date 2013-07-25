from oauth2client.tools import run
from oauth2client.client import OAuth2WebServerFlow, OAuth2Credentials
from oauth2client import multistore_file
from oauth2client.file import Storage
import json
import os
import gflags
import sys
import httplib2
from apiclient.discovery import build
import io
from apiclient.http import MediaIoBaseUpload
from timeline import Timeline, TimelineMenuItem
from contact import Contact
from subscription import SubscriptionEvent


DEFAULT_SCOPE = [
    'https://www.googleapis.com/auth/glass.timeline',
]
FLAGS = gflags.FLAGS
CREDENTIAL_STORAGE_FILE = 'credentials.json'
DEFAULT_MENU_ACTIONS = (
    'REPLY', 'REPLY_ALL', 'DELETE', 'SHARE', 'READ_ALOUD', 'VOICE_CALL', 'NAVIGATE', 'TOGGLE_PINNED')


class Mirror(object):
    """
    An object that assists with all the connections between you and the Mirror API for a single client.
    Similar to boto's "Connection". Most times you need to query or post to the API, it goes through Mirror,
    usually returning various objects such as Timeline objects.
    You will need one Mirror per user.
    """
    def __init__(self, scopes=None):
        """
        Initialize the scopes this Mirror instance will be able to access on behalf of the user.
        """
        if scopes is None:
            self.scopes = DEFAULT_SCOPE
        else:
            self.scopes = scopes

    def get_my_oauth(self, scope=None, hostname='localhost', port="8000"):
        """
        For testing only!!!!!!!
        Used to get an oauth token for yourself (or test user)
        Will pop up a browser request to allow access.
        """
        # Wow! Look at this hack!
        sys.argv.append('--auth_host_port')
        sys.argv.append(port)
        sys.argv.append('--auth_host_name')
        sys.argv.append(hostname)
        try:
            argv = FLAGS(sys.argv)  # parse flags
        except gflags.FlagsError, e:
            print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
            sys.exit(1)
        # print "ARGV", argv
        flow = self._get_flow(scope)
        storage = self._get_storage()
        credentials = None
        try:
            credentials = storage.get()
        except Exception:
            pass
            # credentials = None
        if credentials is None:
            credentials = run(flow, storage)
        # print credentials
        self._get_service(credentials)
        return credentials

    def post_timeline(self, timeline):
        """
        Posts the timeline object to the user's Timeline
        return status.
        """
        if timeline.attachment:
            return self.service.timeline().insert(body=timeline.timeline_body(), media_body=timeline.attachment).execute()
        else:
            return self.service.timeline().insert(body=timeline.timeline_body()).execute()
            # return self.service.timeline().insert(body=timeline.timeline_body()).execute()

    def update_timeline(self, timeline):
        """
        Updates an existing timeline object in place.
        """
        if timeline.attachment:
            return self.service.timeline().update(id=timeline.id, body=timeline.timeline_body(), media_body=timeline.attachment).execute()
        else:
            return self.service.timeline().update(id=timeline.id, body=timeline.timeline_body()).execute()

    def list_timeline(self):
        """
        Returns the list of Timeline objects.
        """
        timeline = self.service.timeline().list().execute()
        timeline_list = []
        for t in timeline['items']:
            timeline_list.append(Timeline(json_data=t))
        return timeline_list

    def get_timeline(self, id):
        """
        Returns a single timeline object
        """
        print "timeline id", id
        ##
        print "service", self.service
        print self.service.timeline()
        print self.service.timeline().list().execute()
        ##
        timeline_json = self.service.timeline().get(id=id).execute()
        return Timeline(json_data=timeline_json)

    def clear_timeline(self):
        for timeline in self.list_timeline():
            self.delete_timeline(timeline.id)

    def delete_timeline(self, id):
        return self.service.timeline().delete(id=id).execute()

    def get_timeline_attachment(self, timeline_item):
        print "attachment id", timeline_item.attachment
        args = {'itemId': timeline_item.id, 'attachmentId': timeline_item.attachments}
        # response, content =
        # self.http.request('https://www.googleapis.com/mirror/v1/timeline/{itemId}/attachments/{attachmentId}'.format(**args))
        response, content = self.http.request(timeline_item.attachment_url)
        # timeline_item.attachment = content
        return content

    def insert_timeline_attachement(self, timeline_item, filename):
        img = open(filename, 'r').read()
        media_body = MediaIoBaseUpload(
            io.BytesIO(img), mimetype="image/jpg", resumable=True)
        self.service.timeline().attachments().insert(
            itemId=timeline_item.id, media_body=media_body).execute()

    def post_contact(self, contact):
        """
        Posts a contact/service that the user will be able to share with
        """
        print contact
        print contact.contact_body()
        return self.service.contacts().insert(body=contact.contact_body()).execute()

    def list_contacts(self):
        """
        Returns a list of Contact objects
        """
        contact = self.service.contacts().list().execute()
        contact_list = []
        for c in contact['items']:
            contact_list.append(Contact(json_data=c))
        return contact_list

    def clear_contacts(self):
        for contact in self.list_contacts():
            self.delete_contact(contact.id)

    def delete_contact(self, id):
        return self.service.contacts().delete(id=id).execute()

    # Subscription handler
    def subscribe(self, callback_url, subscription_type="all", user_token=None, verify_token=None, ):
        """
        Creates a new subscription to user actions or location.
        @param callback_url: the url Google will POST the subscription updates to. (HTTP required) You can then use
        Mirror.parse_notification on the update.
        @param subscription_type: Type of actions to list for. One of "all", "share", "reply", "delete", "custom",
        "location"
        @param user_token: Unique user token for app. Can be basically anything.
        @param verify_token: Unique verification token to ensure posts are coming from Google.
        @return: JSON from Google in response to the subscription.
        """
        subscription_to_operation = {
            "share": "UPDATE",
            "reply": "INSERT",
            "delete": "DELETE",
            "custom": "UPDATE",
            "all": None,
            "location": "UPDATE",
        }
        if subscription_type not in ["all", "share", "reply", "delete", "custom", "location"]:
            raise Exception(
                'Subscription type must be one of ["all", "share", "reply", "delete", "custom", "location"] ')
        # build subscription dict to send to Google
        subscription = {}
        if subscription_type == "location":
            subscription['collection'] = "locations"
        else:
            subscription['collection'] = "timeline"
        subscription['operation'] = subscription_to_operation[subscription_type]
        if user_token:
            subscription['userToken'] = user_token
        if verify_token:
            subscription['verifyToken'] = verify_token
        subscription['callbackUrl'] = callback_url

        return self.service.subscriptions().insert(body=subscription).execute()

    def unsubscribe(self, collection="timeline"):
        if collection not in ["timeline", "locations"]:
            raise Exception('Collection must be one of ["timeline", "locations"].')
        return self.service.subscriptions().delete(collection).execute()

    def list_subscriptions(self):
        return self.service.subscriptions().list().execute().get('items', [])

    def parse_notification(self, request_body, subscription_object=None):
        """Parse a request body into a notification dict.
        Params:
          request_body: The notification payload sent by the Mirror API as a string.
          subscription_object: Allows for overriding subscription objects to have built in handling.
        Returns:
          Dict representing the notification payload.
        """
        notification = json.loads(request_body)
        if subscription_object:
            sub = subscription_object()
        else:
            sub = SubscriptionEvent()
        sub.parse(notification, self)
        return sub

    def _get_service(self, credentials):
        """
        Builds a service object using the API discovery document. Sets self.service
        """
        if credentials is None:
            raise Exception("Invalid credentials")
        http = httplib2.Http()
        http = credentials.authorize(http)
        self.http = http
        service = build('mirror', 'v1', http=http)
        self.service = service
        return service

    def get_service_from_token(self, access_token, client_secrets_filename=None):
        client_id, client_secret = self._get_client_secrets(client_secrets_filename)
        credentials = OAuth2Credentials(access_token=access_token, client_id=client_id, client_secret=client_secret,
                                        refresh_token=None, token_expiry=None, token_uri=None, user_agent=None)
        return self._get_service(credentials)

    def _get_client_secrets(self, filename=None):
        """
        Gets client secrets from the provided filename.
        If filename is none, goes through the default list of places to find a set of client secrets for this app.
        TODO Also throws up an error if client secrets is world readable.
        Default list:
        ./client_secrets.json
        /etc/client_secrets.json

        Returns a tuple of (client_id, client_secret)
        """
        # Ensure provide filename works.
        if filename is not None and not os.path.exists(filename):
            raise Exception("Provided client_secrets file {0} does not exist.".format(filename))
        # Try to find client_secrets file by going through defaults list.
        if filename is not None and os.path.exists(filename):
            json_file = filename
        elif os.path.exists('client_secrets.json'):
            json_file = 'client_secrets.json'
        elif os.path.exists('/etc/client_secrets.json'):
            json_file = '/etc/client_secrets.json'
        else:
            raise Exception("Could not find client secrets.")
        # Read in the file as JSON and try to get the client id and secret.
        try:
            f = open(json_file).read()
        except Exception as e:
            raise Exception("Could not open client secrets file: {0} because {1}".format(json_file, e))
        try:
            data = json.loads(f)
        except Exception as e:
            raise Exception("Could not read JSON data from client secrets file: {0} because {1}".format(json_file, e))
        try:
            print data
            client_id = data['web']['client_id']
            client_secret = data['web']['client_secret']
        except ValueError:
            raise Exception("Clients secret file must have client_id and client_secret.")
        return client_id, client_secret

    def _get_flow(self, redirect_uri=None, client_secrets_filename=None):
        """
        Generates a server flow to obtain an oauth secret.
        Scope is a list of scopes required for this oauth key. Defaults to
        """
        client_id, client_secret = self._get_client_secrets()

        if redirect_uri is None:
            redirect_uri = 'https://localhost:8000'
        print "redir_uri", redirect_uri
        flow = OAuth2WebServerFlow(client_id=client_id,
                                   client_secret=client_secret,
                                   scope=self.scopes,
                                   redirect_uri=redirect_uri,
                                   access_type='offline')
        print flow.redirect_uri
        return flow

    def _get_storage(self):
        return Storage(CREDENTIAL_STORAGE_FILE)


# class TimelineAttachment(object):
#     def __init__(self, filename, content_type):
#         if not os.path.exists(filename):
#             raise ValueError("File does not exist: {0}".format(filename))
#         self.filename = filename
#         media = open(filename).read()
#         self.media_body = MediaIoBaseUpload(io.BytesIO(media), mimetype=content_type, resumable=True)
if __name__ == '__main__':
    mirror = Mirror()
    mirror.get_my_oauth()
