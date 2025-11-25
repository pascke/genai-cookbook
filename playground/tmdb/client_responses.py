import os
import json
import gradio
import logging

from prance import ResolvingParser
from openai import OpenAI

from dotenv import load_dotenv
from tools import call_http, build_tools

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
tools = build_tools(spec, isResponseAPI=True)

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
    Handles the execution of a tool by parsing its arguments, invoking the corresponding HTTP call,
    and returning the output in a standardized format.

    Args:
        tool: An object containing the tool's information, including its arguments (as a JSON string),
              name, and call_id.

    Returns:
        dict: A dictionary with the following structure:
            - type (str): Indicates the type of response, always "function_call_output".
            - call_id: The unique identifier for the tool call.
            - output: The content returned from the HTTP call.
    """
    arguments = json.loads(tool.arguments)    
    content = call_http(spec, tool.name, arguments, before_request=before_request)
    return {
        "type": "function_call_output",
        "call_id": tool.call_id,
        "output": content
    }

def chat(user_prompt, _):
    """
    Handles a chat interaction with the OpenAI GPT-4.1 model, maintaining conversation context and supporting tool calls.

    Args:
        user_prompt (str): The user's input message to be sent to the model.
        _ (Any): Unused parameter, kept for interface compatibility.

    Yields:
        str: The assistant's response content as it is generated.

    Global Variables:
        messages (list): A list maintaining the conversation history, including user and assistant messages.

    Workflow:
        1. Appends the user's prompt to the global messages list.
        2. Initiates a streaming response from the OpenAI model with the current conversation context.
        3. Iterates over streamed events:
            - If the event is a text delta, appends it to the response content and yields it.
            - If the event is a function call, stores the tool call for later processing.
            - If the event is a function call argument delta, appends arguments to the corresponding tool call.
        4. If tool calls are present, processes each tool call and appends both the call and its result to the messages list.
        5. If no tool calls are present, appends the assistant's response to the messages list and exits the loop.
    """
    global messages
    messages.append({ "role": "user", "content": user_prompt })
    while True:
        stream = openai.responses.create(
            model="gpt-4.1", 
            instructions=system_prompt,
            input=messages, 
            temperature=0, 
            tools=tools,
            stream=True
        )
        tool_calls = {}
        content = ""
        for event in stream:
            if event.type == 'response.output_text.delta':
                content += event.delta
                yield content
            elif event.type == 'response.output_item.added' and event.item.type == 'function_call':
                tool_calls[event.output_index] = event.item
            elif event.type == 'response.function_call_arguments.delta':
                index = event.output_index
                if tool_calls[index]:
                    tool_calls[index].arguments += event.delta
        if tool_calls:
            for tool_call in tool_calls.values():
                result = handle_tool(tool_call)
                messages.append(tool_call)
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