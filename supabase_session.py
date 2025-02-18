# supabase_session.py

import uuid
import json
from flask.sessions import SessionInterface, SessionMixin
from datetime import datetime
from werkzeug.datastructures import CallbackDict


class SupabaseSession(CallbackDict, SessionMixin):
    """
    Simple wrapper around a dict-like session object that
    also tracks whether the session was modified.
    """
    def __init__(self, initial=None, session_id=None, user_id=None):
        def on_update(_self):
            _self.modified = True
        super().__init__(initial, on_update)
        self.session_id = session_id
        self.user_id = user_id
        self.modified = False


class SupabaseSessionInterface(SessionInterface):
    """
    Custom session interface that reads/writes session data into a Supabase table.
    """
    def __init__(self, supabase_client, table_name="flask_sessions"):
        self.supabase = supabase_client
        self.table_name = table_name

    def open_session(self, app, request):
        """
        This gets called at the start of each request. 
        We look up the user_id in Flask’s session cookie (if any).
        If no user is logged in, we just return a new empty session.
        """
        # For demonstration: we look if there's a user_id in the existing session cookie.
        # If none, then we create a blank session object with no user_id.
        user_id = None
        stored_user_id = request.cookies.get("user_id_cookie", None)
        if stored_user_id:
            # You might store it in the cookie or in the session, up to you.
            user_id = stored_user_id

        # If there's no user_id, just return an empty session.
        if not user_id:
            return SupabaseSession(session_id=None, user_id=None)

        # Otherwise, attempt to load the most recent session data from Supabase for that user.
        try:
            response = self.supabase.table(self.table_name) \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            rows = response.data
            if rows:
                row = rows[0]
                session_data = row.get("data", {})
                session_id = str(row.get("id"))  # or any other unique id
                return SupabaseSession(initial=session_data, session_id=session_id, user_id=user_id)
        except Exception as e:
            app.logger.error(f"Error opening Supabase session: {e}")

        # If no row found or error, return empty session
        return SupabaseSession(session_id=None, user_id=user_id)

    def save_session(self, app, session, response):
        """
        Called after the request is processed, to persist the session data.
        """
        # If the session is empty or not modified, we can decide not to save it
        if not session:
            return

        # If there's no user_id (anonymous user), skip or handle differently
        user_id = getattr(session, 'user_id', None)
        if not user_id:
            # You could store a truly anonymous session by generating a new user_id or session_id
            # but typically sessions are associated with a logged-in user in this approach.
            return

        # Convert session data to dict
        session_dict = dict(session)  # from the CallbackDict

        # If we already have a session_id, we could update. Otherwise, insert a new row.
        session_id = getattr(session, 'session_id', None)
        if session_id:
            # Example: update existing session row
            try:
                self.supabase.table(self.table_name).update({
                    "data": session_dict,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", session_id).execute()
            except Exception as e:
                app.logger.error(f"Error updating Supabase session: {e}")
        else:
            # Insert a new row
            try:
                new_uuid = str(uuid.uuid4())
                result = self.supabase.table(self.table_name).insert({
                    "id": new_uuid,
                    "user_id": user_id,
                    "data": session_dict
                }).execute()
                if result and result.data:
                    session.session_id = new_uuid  # store the newly inserted ID
            except Exception as e:
                app.logger.error(f"Error inserting Supabase session: {e}")

        # Optionally, set a user_id cookie or other cookie to track the user
        # (Depending on how you want to handle session cookies / user_id)
        response.set_cookie("user_id_cookie", str(user_id))