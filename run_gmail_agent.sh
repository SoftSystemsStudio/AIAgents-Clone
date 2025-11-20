#!/bin/bash
# Gmail Cleanup Agent Runner
# Automatically loads .env and runs the Gmail cleanup agent

cd "$(dirname "$0")"

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Run the agent
python -m examples.gmail_cleanup_agent
