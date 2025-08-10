# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools import google_search  # Import the tool
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest

root_agent = Agent(
   # A unique name for the agent.
   name="stego_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.0-flash-exp", # if this model does not work, try below
   #model="gemini-2.0-flash-live-001",
   # A short description of the agent's purpose.
   description="Agent to speak corporate lingo",
   # Instructions to set the agent's behavior.
   instruction="You are an agent who can participate in IT company meetings and speaks corporate lingo. Give abstract answers when asked anything and ask generic questions in return. Be short, 7-10 words max.",
   tools=[google_search],
)
