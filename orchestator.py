"""
Main logic of the project.

For one user request:
  1. make_plan()   -> asks the AI to split the request into steps
  2. run_step()    -> runs one step (called once for every step)
  3. synthesize()  -> joins all step outputs into the final answer

A step is a normal dictionary like:
  {"id": 1, "title": "...", "agent_role": "...", "instructions": "..."}
"""

import json

from mistral_client import chat

MAX_STEPS = 10

PLANNER_PROMPT = """You are a planning agent. Break the user's request into an \
ordered list of steps. Each step will be done by a specialist agent.

Use only as many steps as the request really needs:
- simple request: 1-2 steps
- medium request: 3-5 steps
- big request: more steps, but never more than 10
Do not add extra steps just to fill the plan.

Reply with ONLY a JSON array. No markdown, no extra text.
Each item must have these keys:
  "id": number starting from 1
  "title": short title of the step
  "agent_role": specialist name (example: "API Designer")
  "instructions": clear instructions for that specialist

Do not add a final "combine everything" step. That is done separately.
"""

SYNTHESIS_PROMPT = """You are a synthesis agent. You get the original request \
and the outputs of several specialists. Combine them into one clear final \
answer for the user. Do not mention steps, plans or agents. \
Use Markdown formatting.
"""


def get_json_list(text):
    """The AI sometimes adds ```json fences or extra text, so we cut out
    only the part between the first [ and the last ]."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("Could not find a JSON list in the planner reply.")
    return json.loads(text[start:end + 1])


def make_plan(user_input, model=None):
    reply = chat(
        PLANNER_PROMPT,
        "User request:\n" + user_input,
        model=model,
        temperature=0.2,
    )
    data = get_json_list(reply)

    if len(data) == 0:
        raise ValueError("Planner did not return any steps.")

    data = data[:MAX_STEPS]  # keep only the first 10 steps

    steps = []
    number = 1
    for item in data:
        step = {
            "id": number,
            "title": item.get("title", "Step " + str(number)),
            "agent_role": item.get("agent_role", "Specialist Agent"),
            "instructions": item.get("instructions", ""),
        }
        steps.append(step)
        number += 1
    return steps


def run_step(step, user_input, previous_results, model=None):
    """previous_results is a list of {"step": step, "output": text}."""

    # put the outputs of earlier steps in one text
    if len(previous_results) == 0:
        context = "(no previous steps, this is the first step)"
    else:
        context = ""
        for r in previous_results:
            context += "### Output of Step " + str(r["step"]["id"])
            context += " (" + r["step"]["title"] + ")\n"
            context += r["output"] + "\n\n"

    system_prompt = (
        "You are a specialist agent working as: " + step["agent_role"] + ".\n"
        "You must complete only this one step of a bigger plan. "
        "Give a clear and usable output for your step only. "
        "Do not repeat the whole plan and do not do other steps. "
        "Use Markdown formatting."
    )
    user_prompt = (
        "Original user request:\n" + user_input + "\n\n"
        "Your step (" + str(step["id"]) + ") - " + step["title"] + ":\n"
        + step["instructions"] + "\n\n"
        "Context from previous steps:\n" + context + "\n"
        "Now write the output for this step."
    )
    return chat(system_prompt, user_prompt, model=model, temperature=0.4)


def synthesize(user_input, results, model=None):
    all_outputs = ""
    for r in results:
        step = r["step"]
        all_outputs += "### Step " + str(step["id"]) + " - " + step["title"]
        all_outputs += " (" + step["agent_role"] + ")\n"
        all_outputs += r["output"] + "\n\n"

    user_prompt = "Original request:\n" + user_input + "\n\n" + all_outputs
    return chat(SYNTHESIS_PROMPT, user_prompt, model=model, temperature=0.3)