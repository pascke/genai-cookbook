import os
import json
import gradio
import logging

from prance import ResolvingParser
from openai import OpenAI

from dotenv import load_dotenv
from playground.tmdb.tools import call_http, build_tools

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
access_token = os.getenv("TMDB_ACCESS_TOKEN")

logging.basicConfig(
    level=logging._levelToName.get(log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

with open('./system_prompt.md', 'r', encoding='utf-8') as file:
    system_prompt = file.read()

# List of messages in memory used for conversation context.
# Each dictionary contains:
#   - "role": The role of the message sender (e.g., "system", "user", "assistant").
#   - "content": The content of the message.
messages = [
    { "role": "system", "content": system_prompt }
]

# Create an OpenAI client instance using the provided API key.
openai = OpenAI(api_key=api_key)

# Initialize a ResolvingParser to parse the OpenAPI specification from the given file path.
parser = ResolvingParser("./openapi.yaml")

# Retrieve the parsed OpenAPI specification from the parser.
spec = parser.specification

# Build tool definitions based on the parsed OpenAPI specification.
tools = build_tools(spec)

def before_request(method, url, headers, query, body):
    """
    A callback function to modify HTTP request details before sending it.
    
    This function appends an authorization token to the headers of the request.
    Can be used to handle authentication or other preprocessing tasks.
    
    Args:
     method (str): The HTTP method (e.g., "GET", "POST").
        url (str): The URL for the HTTP request.
        headers (dict): The headers for the HTTP request.
        query (dict): The query parameters for the HTTP request.
        body (dict): The body of the HTTP request if applicable.
    
    Returns:
        tuple: A tuple containing the modified method, URL, headers, query parameters, and body.
    """
    headers["Authorization"] = f"Bearer {access_token}"
    return method, url, headers, query, body

def handle_tool(tool):
    """
    Handles the execution of a tool call from a chat completion message.

    Args:
        tool: The tool call object containing function details and arguments.

    Returns:
        dict: A dictionary with the following keys:
            - "role": The role of the responder, set to "tool".
            - "name": The name of the function being called.
            - "content": The result of the HTTP call to the specified function.
            - "tool_call_id": The unique identifier of the tool call.
    """
    arguments = json.loads(tool.function.arguments)
    content = call_http(spec, tool.function.name, arguments, before_request=before_request)
    return {
        "role": "tool",
        "name": tool.function.name,
        "content": content,
        "tool_call_id": tool.id
    }

def chat(user_prompt, _):
    """
    Handles a chat interaction with the OpenAI API, streaming responses and managing tool calls.

    This function appends the user's prompt to the global message history, streams the assistant's response,
    and processes any tool calls returned by the model. If tool calls are present, it handles them and updates
    the message history accordingly. Otherwise, it appends the assistant's response to the message history.

    Args:
        user_prompt (str): The prompt or message from the user.
        _ : Unused parameter, included for interface compatibility.

    Yields:
        str: The current content of the assistant's streamed response.
    """

    global messages
    messages.append({ "role": "user", "content": user_prompt })
    while True:
        stream = openai.chat.completions.create(
            model="gpt-4.1", 
            messages=messages, 
            temperature=0, 
            tools=tools,
            stream=True
        )
        content = ""
        tool_calls = {}
        for event in stream:
            delta = event.choices[0].delta
            if hasattr(delta, 'content') and delta.content:
                content += delta.content
                yield content
            elif hasattr(delta, 'tool_calls') and delta.tool_calls:
                for chunk in delta.tool_calls:
                    index = chunk.index
                    if index not in tool_calls:
                        tool_calls[index] = {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }
                    if chunk.id:
                        tool_calls[index]["id"] = chunk.id
                    if hasattr(chunk, 'function'):
                        if chunk.function.name:
                            tool_calls[index]["function"]["name"] = chunk.function.name
                        if chunk.function.arguments:
                            tool_calls[index]["function"]["arguments"] += chunk.function.arguments
        if tool_calls:
            for data in tool_calls.values():
                class ToolCall:
                    """
                    Represents a tool call event with associated function metadata.
                    """
                    def __init__(self, data):
                        """
                        Initializes a ToolCall instance.

                        Args:
                            data (dict): Tool call data containing id, type, and function details.
                        """
                        self.id = data["id"]
                        self.type = data["type"]
                        self.function = type('obj', (object,), {
                            'name': data["function"]["name"],
                            'arguments': data["function"]["arguments"]
                        })()
                tool_call = ToolCall(data)
                result = handle_tool(tool_call)
                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }],
                })
                messages.append(result)
        else:
            messages.append({ "role": "assistant", "content": content })
            break

if __name__ == "__main__":
    """
    Entry point of the script. Initializes and launches a Gradio chat interface.
    """
    gradio.ChatInterface(fn=chat, type="messages").launch(server_port=7860)
    """
    Creates a Gradio ChatInterface using the 'chat' function to handle messages.
    The interface is launched and made available for user interaction.
    """