
from supabase import Client, create_client
import os
from datetime import datetime
from typing import Optional, Dict, Any

class SupabaseSessionManager:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.client: Optional[Client] = None
        
    def initialize(self) -> Client:
        if not self.client:
            self.client = create_client(self.supabase_url, self.supabase_key)
        return self.client
        
    def store_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        if not self.client:
            self.initialize()
            
        try:
            self.client.table("user_sessions").upsert({
                "user_id": user_id,
                "session_data": session_data,
                "last_activity": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print(f"Failed to store session: {str(e)}")
            
    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            self.initialize()
            
        try:
            response = self.client.table("user_sessions").select("*").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Failed to retrieve session: {str(e)}")
        return None
            
    def delete_session(self, user_id: str) -> None:
        if not self.client:
            self.initialize()
            
        try:
            self.client.table("user_sessions").delete().eq("user_id", user_id).execute()
        except Exception as e:
            print(f"Failed to delete session: {str(e)}")

# Create a singleton instance
supabase_manager = SupabaseSessionManager()
