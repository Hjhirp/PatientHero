import os
from browserbase import Browserbase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_browserbase_connection():
    # Get API key from environment
    api_key = os.getenv('BROWSERBASE_API_KEY')
    if not api_key:
        print("❌ BROWSERBASE_API_KEY not found in environment variables")
        return False
    
    print("✅ Found BROWSERBASE_API_KEY in environment")
    
    try:
        # Initialize client
        client = Browserbase(api_key=api_key)
        
        # Test session creation
        print("\nTesting BrowserBase session creation...")
        session = client.sessions.create(
            project_id="412550f9-0b9c-425a-a258-f3d1a3bd4f9e"  # Your BrowserBase Project ID
        )
        print(f"✅ Successfully created session: {session.id}")
        print(f"   Project ID: {session.project_id}")
        print(f"   Session URL: https://browserbase.com/projects/{session.project_id}/sessions/{session.id}")
        
        # Clean up - use close instead of delete
        try:
            client.sessions.close(session.id)
            print("✅ Successfully closed session")
        except Exception as e:
            print(f"⚠️  Warning: Could not close session: {e}")
            print("   The session may time out automatically after a period of inactivity.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing BrowserBase: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing BrowserBase connection...")
    if test_browserbase_connection():
        print("\n✅ BrowserBase test completed successfully!")
    else:
        print("\n❌ BrowserBase test failed. Please check your API key and network connection.")
