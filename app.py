"""
Metadata Creator Dash App
A TfL-styled chat application for generating metadata from data files
Connects to Databricks Model Serving (Claude) endpoint
"""

import os
import json
import base64
import io
from pathlib import Path
from typing import Optional, List, Dict

import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH, ctx
import dash_bootstrap_components as dbc
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import pandas as pd

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in production

# Configuration from .env (no hardcoded profile names or URLs)
DATABRICKS_CONFIG_PROFILE = os.getenv('DATABRICKS_CONFIG_PROFILE')
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
SERVING_ENDPOINT = os.getenv('DATABRICKS_SERVING_ENDPOINT')

if DATABRICKS_CONFIG_PROFILE and DATABRICKS_HOST:
    print(f"🔧 Using Databricks profile from .env: {DATABRICKS_CONFIG_PROFILE}")
    print(f"🔧 Using Databricks host from .env: {DATABRICKS_HOST}")
    w = WorkspaceClient(profile=DATABRICKS_CONFIG_PROFILE, host=DATABRICKS_HOST)
else:
    # Running in Databricks Apps: auth and endpoint are set by the platform
    print("🔧 Using Databricks Apps default authentication")
    w = WorkspaceClient()

if not SERVING_ENDPOINT:
    print("⚠️ DATABRICKS_SERVING_ENDPOINT not set (use .env locally or bundle config on Databricks)")

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Metadata Creator"
)

# Server for deployment
server = app.server

# TfL Color Scheme
TFL_BLUE = "#0019A8"
TFL_RED = "#DC241F"
TFL_LIGHT_BLUE = "#EBF1FF"


def _load_system_prompt() -> str:
    """Load the metadata JSON definition and LLM instructions from metadata_prompt.txt."""
    prompt_path = Path(__file__).resolve().parent / "metadata_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Metadata prompt file not found: {prompt_path}. "
            "Ensure metadata_prompt.txt exists in the same directory as app.py."
        )
    return prompt_path.read_text(encoding="utf-8").strip()


SYSTEM_PROMPT = _load_system_prompt()

# Custom CSS for TfL styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(to bottom, #EBF1FF 0%, #F5F5F5 100%);
            }
            .tfl-header {
                background-color: ''' + TFL_BLUE + ''';
                color: white;
                padding: 1rem 2rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .tfl-roundel {
                width: 44px;
                height: 44px;
            }
            .chat-message {
                padding: 1rem;
                margin: 0.5rem 0;
                border-radius: 8px;
                max-width: 80%;
            }
            .chat-message.user {
                background-color: ''' + TFL_LIGHT_BLUE + ''';
                margin-left: auto;
                border: 2px solid ''' + TFL_BLUE + ''';
            }
            .chat-message.assistant {
                background-color: white;
                margin-right: auto;
                border: 1px solid #e0e0e0;
            }
            .chat-input-container {
                background: white;
                border: 2px solid ''' + TFL_BLUE + ''';
                border-radius: 8px;
                padding: 1rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .btn-tfl {
                background-color: ''' + TFL_BLUE + ''';
                color: white;
                border: none;
                padding: 0.5rem 1.5rem;
                border-radius: 4px;
                font-weight: 600;
                cursor: pointer;
            }
            .btn-tfl:hover {
                background-color: ''' + TFL_RED + ''';
            }
            .file-upload-area {
                border: 2px dashed ''' + TFL_BLUE + ''';
                border-radius: 8px;
                padding: 2rem;
                text-align: center;
                background-color: ''' + TFL_LIGHT_BLUE + ''';
                cursor: pointer;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

def create_tfl_roundel():
    """Create TfL roundel logo using HTML/CSS"""
    return html.Div(
        style={
            "position": "relative",
            "width": "44px",
            "height": "44px",
            "borderRadius": "50%",
            "backgroundColor": TFL_RED,
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center"
        },
        children=[
            # White inner circle
            html.Div(
                style={
                    "position": "absolute",
                    "width": "34px",
                    "height": "34px",
                    "borderRadius": "50%",
                    "backgroundColor": "white"
                }
            ),
            # Blue bar with text
            html.Div(
                "METADATA",
                style={
                    "position": "relative",
                    "backgroundColor": TFL_BLUE,
                    "color": "white",
                    "padding": "4px 8px",
                    "borderRadius": "2px",
                    "fontSize": "7px",
                    "fontWeight": "700",
                    "fontFamily": "Arial, Helvetica, sans-serif",
                    "letterSpacing": "0.5px",
                    "textAlign": "center",
                    "zIndex": "1"
                }
            )
        ]
    )

def create_header():
    """Create TfL-styled header"""
    return html.Div(
        className="tfl-header",
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "1rem"},
                children=[
                    create_tfl_roundel(),
                    html.H1("Metadata Creator", style={"margin": 0, "fontSize": "1.5rem"})
                ]
            )
        ]
    )

def parse_file_content(contents: str, filename: str) -> str:
    """Parse uploaded file and extract sample data"""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Handle different file types
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            sample = df.head(10).to_string()
            return f"File: {filename}\nSample data (first 10 rows):\n\n{sample}"
        
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(decoded))
            sample = df.head(10).to_string()
            return f"File: {filename}\nSample data (first 10 rows):\n\n{sample}"
        
        elif filename.endswith('.json'):
            data = json.loads(decoded.decode('utf-8'))
            if isinstance(data, list):
                sample = json.dumps(data[:10], indent=2)
            else:
                sample = json.dumps(data, indent=2)
            return f"File: {filename}\nSample data:\n\n{sample}"
        
        else:
            # Plain text
            text = decoded.decode('utf-8')
            lines = text.split('\n')[:10]
            return f"File: {filename}\nSample data (first 10 lines):\n\n{chr(10).join(lines)}"
    
    except Exception as e:
        return f"Error parsing file: {str(e)}"

def call_databricks_model(messages: List[Dict[str, str]]) -> str:
    """Call Databricks Model Serving endpoint"""
    if not SERVING_ENDPOINT:
        return (
            "Error: DATABRICKS_SERVING_ENDPOINT is not set. "
            "Add it to your .env file for local development, or ensure the app is deployed with a serving endpoint resource."
        )
    try:
        # Prepare messages for Databricks API
        chat_messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT)
        ]
        
        for msg in messages:
            role = ChatMessageRole.USER if msg['role'] == 'user' else ChatMessageRole.ASSISTANT
            chat_messages.append(ChatMessage(role=role, content=msg['content']))
        
        # Call the serving endpoint
        response = w.serving_endpoints.query(
            name=SERVING_ENDPOINT,
            messages=chat_messages,
            max_tokens=2000
        )
        
        # Extract response text
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            return "Sorry, I couldn't process that request."
    
    except Exception as e:
        return f"Error calling model: {str(e)}"

# App layout
app.layout = html.Div([
    # Header
    create_header(),
    
    # Main content
    dbc.Container([
        dbc.Row([
            dbc.Col([
                # File upload area
                html.Div(
                    id="upload-container",
                    children=[
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                '📎 Drag and Drop or ',
                                html.A('Select Files', style={"color": TFL_BLUE, "fontWeight": "bold"}),
                                html.Br(),
                                html.Small('CSV, Excel, JSON, TXT (max 100MB)')
                            ]),
                            className="file-upload-area",
                            multiple=False,
                            max_size=100 * 1024 * 1024  # 100MB
                        ),
                    ],
                    style={"marginTop": "2rem", "marginBottom": "1rem"}
                ),
                
                # Chat messages with loading indicator
                # The loading spinner automatically shows "Processing file..." while waiting for LLM
                dcc.Loading(
                    id="loading-chat",
                    type="circle",
                    color=TFL_BLUE,
                    parent_className="loading-wrapper",
                    children=html.Div(
                        id="chat-messages",
                        style={
                            "minHeight": "400px",
                            "maxHeight": "600px",
                            "overflowY": "auto",
                            "padding": "1rem",
                            "marginBottom": "1rem"
                        }
                    ),
                    # Custom loading message
                    custom_spinner=html.Div([
                        html.Div(
                            style={
                                "width": "60px",
                                "height": "60px",
                                "border": f"5px solid {TFL_LIGHT_BLUE}",
                                "borderTop": f"5px solid {TFL_BLUE}",
                                "borderRadius": "50%",
                                "animation": "spin 1s linear infinite",
                                "margin": "0 auto 1rem auto"
                            }
                        ),
                        html.Div(
                            "⏳ Processing file...",
                            style={
                                "color": TFL_BLUE,
                                "fontWeight": "600",
                                "fontSize": "1.1rem",
                                "textAlign": "center"
                            }
                        )
                    ], style={
                        "padding": "2rem",
                        "backgroundColor": TFL_LIGHT_BLUE,
                        "borderRadius": "12px",
                        "margin": "2rem auto",
                        "maxWidth": "300px"
                    })
                ),
                
                # Input area
                html.Div(
                    className="chat-input-container",
                    children=[
                        dbc.Row([
                            dbc.Col([
                                dcc.Textarea(
                                    id="message-input",
                                    placeholder="Type your message here...",
                                    style={"width": "100%", "border": "none", "resize": "none"},
                                    rows=2
                                )
                            ], width=10),
                            dbc.Col([
                                html.Button(
                                    "Send",
                                    id="send-button",
                                    className="btn-tfl",
                                    n_clicks=0,
                                    style={"width": "100%", "height": "100%"}
                                )
                            ], width=2)
                        ])
                    ]
                )
            ], width=12, lg=10, xl=8)
        ], justify="center")
    ], fluid=True, style={"padding": "2rem"}),
    
    # Hidden div to store conversation history
    dcc.Store(id='conversation-history', data=[]),
    dcc.Store(id='uploaded-file-data', data=None)
])

@callback(
    Output('uploaded-file-data', 'data'),
    Output('chat-messages', 'children', allow_duplicate=True),
    Output('conversation-history', 'data', allow_duplicate=True),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('conversation-history', 'data'),
    prevent_initial_call=True
)
def handle_file_upload(contents, filename, conversation):
    if contents is None:
        return None, dash.no_update, dash.no_update
    
    # Parse file content
    file_content = parse_file_content(contents, filename)
    
    # Add to conversation
    if conversation is None:
        conversation = []
    
    conversation.append({
        'role': 'user',
        'content': f"[File uploaded: {filename}]\n\n{file_content}"
    })
    
    # Get AI response (loading indicator with "Processing file..." will show automatically)
    ai_response = call_databricks_model(conversation)
    conversation.append({
        'role': 'assistant',
        'content': ai_response
    })
    
    # Create message components with final response
    messages = []
    for msg in conversation:
        if msg['role'] == 'user':
            messages.append(
                html.Div(
                    msg['content'],
                    className="chat-message user",
                    style={"whiteSpace": "pre-wrap"}
                )
            )
        else:
            messages.append(
                html.Div(
                    dcc.Markdown(msg['content']),
                    className="chat-message assistant"
                )
            )
    
    return file_content, messages, conversation

@callback(
    Output('chat-messages', 'children'),
    Output('message-input', 'value'),
    Output('conversation-history', 'data'),
    Input('send-button', 'n_clicks'),
    State('message-input', 'value'),
    State('conversation-history', 'data'),
    prevent_initial_call=True
)
def send_message(n_clicks, message, conversation):
    if not message or not message.strip():
        return dash.no_update, dash.no_update, dash.no_update
    
    if conversation is None:
        conversation = []
    
    # Add user message
    conversation.append({
        'role': 'user',
        'content': message
    })
    
    # Get AI response (loading indicator with "Processing file..." will show automatically)
    ai_response = call_databricks_model(conversation)
    conversation.append({
        'role': 'assistant',
        'content': ai_response
    })
    
    # Create message components with final response
    messages = []
    for msg in conversation:
        if msg['role'] == 'user':
            messages.append(
                html.Div(
                    msg['content'],
                    className="chat-message user",
                    style={"whiteSpace": "pre-wrap"}
                )
            )
        else:
            messages.append(
                html.Div(
                    dcc.Markdown(msg['content']),
                    className="chat-message assistant"
                )
            )
    
    return messages, "", conversation

if __name__ == '__main__':
    # For local development
    app.run_server(debug=True, host='0.0.0.0', port=8050)
