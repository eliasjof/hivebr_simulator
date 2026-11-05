"""
simulator_worker.py
-------------------
Main entry point for the Pyodide Web Worker.

This runs in a separate thread in the browser and communicates with the main
thread via postMessage. It handles all simulation logic without blocking the UI.
"""

# Pyodide provides these globals
import sys
import json

# Make sure we can import from the hivebr package
sys.path.insert(0, "/home/pyodide/lib/python3.12/site-packages")

from web_simulator import handle_message


def main():
    """Main worker loop - handles messages from main thread."""
    # In Pyodide, we receive messages via the `onmessage` handler
    # This is set up by the JavaScript side
    pass


# Message handler for postMessage from main thread
def onmessage(event):
    """Handle incoming message from main thread."""
    try:
        msg = event.data
        result = handle_message(msg)
        
        # Send result back to main thread
        # We need to ensure the result is JSON serializable
        # Pyodide's postMessage handles basic types automatically
        import js
        js.postMessage(result)
    except Exception as e:
        # Send error back
        import js
        js.postMessage({
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        })


# In Pyodide, we need to expose the handler to JavaScript
# This will be called from the JS side to set up the message handler
def set_message_handler():
    """Called from JavaScript to set up the message handler."""
    import js
    js.self.onmessage = onmessage


# For testing in Node/Pyodide shell
if __name__ == "__main__":
    print("Simulator worker loaded")
    print("Waiting for messages...")