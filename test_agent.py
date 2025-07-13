"""Test script to understand CrewAI Agent initialization."""
import os
import logging
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from crewai import Agent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_agent_creation():
    """Test creating a basic CrewAI agent."""
    try:
        # Initialize Claude
        llm = ChatAnthropic(
            model="claude-3-opus-20240229",
            temperature=0.1,
            max_tokens=4000
        )
        
        # Create a minimal agent
        agent = Agent(
            role="Test Agent",
            goal="Test the agent creation",
            backstory="Just a test agent",
            llm=llm,
            allow_delegation=False,
            max_iterations=3
        )
        
        logger.info("Successfully created agent: %s", agent)
        return True
        
    except Exception as e:
        logger.error("Error creating agent: %s", str(e), exc_info=True)
        return False

if __name__ == "__main__":
    test_agent_creation()
