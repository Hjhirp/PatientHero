import os
from browserbase import Browserbase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_and_close_sessions():
    """List and close all active BrowserBase sessions"""
    api_key = os.getenv('BROWSERBASE_API_KEY')
    project_id = os.getenv('BROWSERBASE_PROJECT_ID')
    
    if not api_key or not project_id:
        print("❌ Missing required environment variables in .env file")
        return
    
    try:
        # Initialize client
        client = Browserbase(api_key=api_key)
        
        # List all sessions
        print("📋 Listing active sessions...")
        sessions = client.sessions.list(project_id=project_id)
        
        if not sessions:
            print("✅ No active sessions found")
            return
            
        print(f"\nFound {len(sessions)} active sessions:")
        for i, session in enumerate(sessions, 1):
            print(f"{i}. ID: {session.id} | Created: {session.created_at}")
        
        # Close all sessions
        print("\n🚀 Closing all active sessions...")
        for session in sessions:
            try:
                client.sessions.close(session.id)
                print(f"✅ Closed session: {session.id}")
            except Exception as e:
                print(f"❌ Error closing session {session.id}: {str(e)}")
        
        print("\n✅ Cleanup complete!")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        print("\n💡 If you're seeing rate limit errors, try again in a few minutes.")
        print("   You can also check and close sessions manually at:")
        print(f"   https://browserbase.com/projects/{project_id}/sessions")

if __name__ == "__main__":
    print("🔍 BrowserBase Session Cleanup Tool")
    print("================================")
    list_and_close_sessions()
    
    print("\nNext steps:")
    print("1. Wait a few seconds for sessions to fully close")
    print("2. Run the test script: python test_browserbase.py")
