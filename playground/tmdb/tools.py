import os
import json
import logging
import requests

from dotenv import load_dotenv
from typing import Callable, Optional, Dict, Any, Tuple

load_dotenv()

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=logging._levelToName.get(log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

"""
Defines a type alias 'BeforeRequest' representing a callable that modifies HTTP request properties like method, URL, headers, query, and body.

Args:
    str: HTTP method as a string (e.g., "GET", "POST").
    str: The URL of the request.
    Dict[str, str]: HTTP headers as a dictionary.
    Dict[str, Any]: Query parameters as a dictionary.
    Optional[Dict[str, Any]]: The request body as an optional dictionary.

Returns:
    Tuple: A tuple containing modified method, URL, headers, query parameters, and optional body in the same order.
"""
BeforeRequest = Callable[
    [str, str, Dict[str, str], Dict[str, Any], Optional[Dict[str, Any]]],
    Tuple[str, str, Dict[str, str], Dict[str, Any], Optional[Dict[str, Any]]]
]

def build_schema(item: dict, operation: dict) -> dict:
    """
    Builds a JSON schema dictionary based on OpenAPI path item and operation definitions.

    Args:
        item (dict): The OpenAPI path item object containing parameters.
        operation (dict): The OpenAPI operation object containing parameters and requestBody.

    Returns:
        dict: A JSON schema representing the combined parameters and request body.
            - "type": Always "object".
            - "properties": Dictionary of parameter/request body schemas.
            - "required": List of required property names.
    """
    required = []
    properties = {}
    parameters = (item.get("parameters") or []) + (operation.get("parameters") or [])
    for parameter in parameters:
        name = parameter["name"]
        schema = parameter.get("schema") or { "type": "string" }
        properties[name] = schema
        if parameter.get("required"):
            required.append(name)
    if "requestBody" in operation:
        content = operation["requestBody"].get("content", {})
        body_schema = content.get("application/json", {}).get("schema")
        if body_schema:
            properties["body"] = body_schema
            if operation["requestBody"].get("required"):
                required.append("body")
        else:
            properties.setdefault("body", { "type": "object" })
    return {
        "type": "object", 
        "properties": properties, 
        "required": required
    }

def build_tools(spec: dict, isResponseAPI: bool = False) -> list:
    """
    Builds a list of tool definitions from an OpenAPI specification.

    Args:
        spec (dict): The OpenAPI specification as a dictionary.
        isResponseAPI (bool, optional): If True, the tool definition will not nest the function details under a "function" key. 
            If False, the function details will be nested under a "function" key. Defaults to False.

    Returns:
        list: A list of tool definitions, each represented as a dictionary.
    """
    tools = []
    paths = spec.get("paths", {})
    for path, item in paths.items():
        for method in ["get", "post", "put", "patch", "delete", "head", "options", "trace"]:
            if method not in item:
                continue
            operation = item[method]
            name = operation["operationId"]
            description = operation.get("summary") or operation.get("description") or f"{method.upper()} {path}"
            schema = build_schema(item, operation)
            if isResponseAPI:
                tools.append({
                    "type": "function",
                    "name": name,
                    "description": description,
                    "parameters": schema
                })
            else:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": schema
                    }
                })
    return tools

def call_http(
    spec: dict, 
    tool_name: str, 
    arguments: dict,
    *,
    before_request: Optional[BeforeRequest] = None) -> str:
    """
    Calls an HTTP endpoint defined in an OpenAPI specification using the provided tool name and arguments.

    Args:
        spec (dict): The OpenAPI specification as a dictionary.
        tool_name (str): The operationId of the endpoint to call.
        arguments (dict): Arguments to be passed to the endpoint, including path, query, header parameters, and request body.

    Returns:
        str: The JSON response from the endpoint as a string.

    Raises:
        ValueError: If the tool_name is not mapped to any endpoint in the specification.
        Exception: If an error occurs during the HTTP request, returns the response text.
    """
    paths = spec["paths"]
    for path, methods in paths.items():
        for method, item in methods.items():
            if method.lower() not in { "get", "post", "put", "patch", "delete", "head", "options" }:
                continue
            candidate = item.get("operationId")
            if candidate == tool_name:
                base_url = spec["servers"][0]["url"].rstrip("/")
                url_path = path
                if "{" in url_path:
                    for k, v in list(arguments.items()):
                        token = "{%s}" % k
                        if token in url_path:
                            url_path = url_path.replace(token, str(v))
                url = f"{base_url}/{url_path.lstrip('/')}"
                body = None
                query = {}
                headers = {"Accept": "application/json"}
                all_params = item.get("parameters", []) + methods.get("parameters", [])
                for param in all_params:
                    name = param["name"]
                    pin = param.get("in")
                    if name not in arguments:
                        continue
                    if pin == "query":
                        query[name] = arguments[name]
                    elif pin == "header":
                        headers[name] = str(arguments[name])
                if "requestBody" in item:
                    if "body" in arguments:
                        body = arguments["body"]
                        headers["Content-Type"] = "application/json"
                
                if before_request:
                    method, url, headers, query, body = before_request(method.upper(), url, headers, query, body)
                logging.info(f"Calling the '{tool_name}' function with the arguments:\n{json.dumps(arguments, indent=4, ensure_ascii=False)}")
                try:
                    response = requests.request(method.upper(), url, params=query, headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    logging.info(f"Response from the '{tool_name}' function:\n{json.dumps(data, indent=4, ensure_ascii=False)}")
                    return json.dumps(data)
                except Exception:
                    logging.exception(f"Error calling the '{tool_name}' function")
                    return response.text
    raise ValueError(f"Tool {tool_name} not mapped to an endpoint.")
