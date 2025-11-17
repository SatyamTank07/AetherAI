import os
import json
from dotenv import load_dotenv

def load_config():
    """Load environment variables and static settings from config.json, then return combined configuration dictionary."""
    # Load environment variables
    load_dotenv()
    env_vars = {key: value for key, value in os.environ.items() if value}
    
    # Validate required API keys
    required_keys = ["GROQ_API_KEY", "PINECONE_API_KEY"]
    missing_keys = [key for key in required_keys if key not in env_vars or not env_vars[key]]
    if missing_keys:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
    
    # Load static settings from config.json
    try:
        with open("config.json", "r") as f:
            static_config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config.json file not found.")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in config.json.")
    
    # Combine environment variables with static settings
    return {**env_vars, **static_config}