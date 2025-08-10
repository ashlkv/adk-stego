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
import os

# Phrases have to be long even for a short watermark. 15 words average.
general_instructions = "You are an agent who can participate in IT company meetings and speaks corporate lingo. Give abstract answers when asked a question and ask generic questions in return. 15-20 words in average."

# Create different agents with different voices
standalone_agent = Agent(
   name="standalone_agent",
   model="gemini-2.0-flash-exp", 
   description="An agent who speaks corporate lingo",
   instruction=general_instructions,
   tools=[google_search],
)

alice_agent = Agent(
   name="alice_agent",
   model="gemini-2.0-flash-exp",
   description="Alice - corporate meeting participant",
   instruction=f"{general_instructions}. Your name is Alice. You are in a meeting. Do not speak unless you are addressed by name, i.e. Alice. Wait for the person to finish speaking. Bastian is your teammate. After you answer a question, ask Bastian something. Remember to mention his name.",
   tools=[google_search],
)

bastian_agent = Agent(
   name="bastian_agent", 
   model="gemini-2.0-flash-exp",
   description="Bastian - corporate meeting participant who initiates meetings",
   instruction=f"{general_instructions}. Your name is Bastian. When you receive any initial input or greeting, start the meeting by greeting everyone and asking Alice a question to begin discussion. Always address Alice by her name. After that, only respond when addressed by your name.",
   tools=[google_search],
)

agent_name = os.environ.get("AGENT_NAME", "standalone").lower()
print(f"Agent name: {agent_name}")

if agent_name == "alice":
    root_agent = alice_agent
elif agent_name == "bastian":
    root_agent = bastian_agent
else:
    root_agent = standalone_agent
