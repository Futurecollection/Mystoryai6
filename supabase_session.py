import json
from uuid import uuid4
from datetime import datetime, timedelta
from flask.sessions import SessionInterface, SessionMixin

class SupabaseSession(dict, SessionMixin):
    def __init__(self, initial=None, session_id=None):
        super().__init__(initial or {})
        self.session_id = session_id

class SupabaseSessionInterface(SessionInterface):
    """
    A custom Flask SessionInterface that stores session data in a Supabase table
    called 'flask_sessions'. This prevents large data from bloating the cookie.

    Table schema needed:
        CREATE TABLE public.flask_sessions (
            session_id uuid PRIMARY KEY,
            user_id UUID,
            data jsonb,
            expiry timestamptz
        );
    Disable RLS or create a policy for inserts/updates.
    """

    def __init__(self, supabase_client, table_name="flask_sessions", session_lifetime=timedelta(days=1)):
        self.supabase = supabase_client
        self.table_name = table_name
        self.session_lifetime = session_lifetime

    def open_session(self, app, request):
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
        session_id = request.cookies.get(cookie_name)

        if not session_id:
            # No cookie -> create a new session
            session_id = str(uuid4())
            return SupabaseSession(session_id=session_id)

        # Try to load from Supabase
        result = self.supabase.table(self.table_name) \
                              .select("data, expiry, user_id") \
                              .eq("session_id", session_id) \
                              .execute()
        if result.data:
            row = result.data[0]
            expiry_str = row.get("expiry")
            if expiry_str:
                expiry = datetime.fromisoformat(expiry_str)
                # Convert to naive if needed
                expiry = expiry.replace(tzinfo=None)
                if expiry < datetime.utcnow():
                    # Expired => new session
                    return SupabaseSession(session_id=session_id)

            data = row.get("data") or {}
            return SupabaseSession(initial=data, session_id=session_id)
        else:
            # No record => new session
            return SupabaseSession(session_id=session_id)

    def save_session(self, app, session, response):
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
        domain = self.get_cookie_domain(app)

        # If session is empty, remove from DB + clear cookie
        if not session:
            if getattr(session, 'session_id', None):
                self.supabase.table(self.table_name) \
                             .delete() \
                             .eq("session_id", session.session_id) \
                             .execute()
            response.delete_cookie(cookie_name, domain=domain)
            return

        # Otherwise, upsert the session record in DB
        expiry = datetime.utcnow() + self.session_lifetime
        session_data = dict(session)

        self.supabase.table(self.table_name).upsert({
            "session_id": session.session_id,
            "data": session_data,
            "expiry": expiry.isoformat()
        }).execute()

        # Set a small cookie with only the session_id
        response.set_cookie(
            cookie_name,
            session.session_id,
            expires=expiry,
            httponly=True,
            domain=domain
        )