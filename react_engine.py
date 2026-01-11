import re
import json
from typing import Dict, Any, Optional


def calculate_escape_velocity(mass: float, radius: float) -> Dict[str, Any]:
    """Calculate escape velocity for a celestial body."""
    G = 6.674e-11
    v_escape = (2 * G * mass / radius) ** 0.5
    
    return {
        "escape_velocity_m_s": round(v_escape, 2),
        "escape_velocity_km_s": round(v_escape / 1000, 2),
        "mass": mass,
        "radius": radius,
        "status": "success"
    }


def scan_sector_hazards(x: int, y: int) -> Dict[str, Any]:
    """Scan a grid sector for navigational hazards."""
    hazard_map = {
        (0, 0): "Clear - Starting position",
        (0, 1): "High Radiation - DANGER",
        (0, 2): "Clear",
        (1, 0): "Clear",
        (1, 1): "Asteroid Field - DANGER",
        (1, 2): "Clear",
        (2, 0): "Clear",
        (2, 1): "Ion Storm - DANGER",
        (2, 2): "Clear - Exit point"
    }
    
    hazard = hazard_map.get((x, y), "Unknown sector - Out of bounds")
    is_safe = "DANGER" not in hazard and "Unknown" not in hazard
    
    return {
        "coordinates": f"({x}, {y})",
        "hazard_description": hazard,
        "safe": is_safe,
        "status": "success"
    }


TOOLS = {
    "calculate_escape_velocity": calculate_escape_velocity,
    "scan_sector_hazards": scan_sector_hazards
}


def simulate_llm_response(conversation_history: list, step: int) -> str:
    """Simulates LLM responses for testing the ReAct loop."""
    responses = [
        """Thought: I am at the starting position (0,0). I need to navigate to the exit at (2,2) while avoiding hazards. Let me first check the sector directly to the right at (1,0).
Action: scan_sector_hazards
Action Input: {"x": 1, "y": 0}""",
        
        """Thought: Sector (1,0) is clear. Before moving, let me also check the upward sector (0,1) to explore my options.
Action: scan_sector_hazards
Action Input: {"x": 0, "y": 1}""",
        
        """Thought: Sector (0,1) has high radiation and is dangerous. Sector (1,0) is clear, so I should move right to (1,0). Let me now check the next sector (1,1).
Action: scan_sector_hazards
Action Input: {"x": 1, "y": 1}""",
        
        """Thought: Sector (1,1) has an asteroid field - I cannot go through there. Let me check sector (2,0) to see if I can go further right first.
Action: scan_sector_hazards
Action Input: {"x": 2, "y": 0}""",
        
        """Thought: Sector (2,0) is clear. Now let me check sector (2,1) to see if I can move up from there.
Action: scan_sector_hazards
Action Input: {"x": 2, "y": 1}""",
        
        """Thought: Sector (2,1) has an ion storm, which is dangerous. However, I can navigate around this. Let me check the final destination (2,2) to confirm it's safe.
Action: scan_sector_hazards
Action Input: {"x": 2, "y": 2}""",
        
        """Thought: Perfect! I have mapped out the hazards. The safe path is:
- Start at (0,0)
- Move right to (1,0) - Clear
- Move right to (2,0) - Clear  
- Move up to (2,2) - Clear (Exit)

This path avoids all hazards: the radiation at (0,1), asteroid field at (1,1), and ion storm at (2,1).

Final Answer: Safe navigation path plotted. Route: (0,0) → (1,0) → (2,0) → (2,2). The ship should move right twice, then up twice to reach the exit while avoiding all hazardous sectors."""
    ]
    
    if step < len(responses):
        return responses[step]
    else:
        return "Final Answer: Maximum steps reached without finding solution."


def parse_action(llm_output: str) -> Optional[Dict[str, Any]]:
    """Parse LLM output to extract action and parameters."""
    action_match = re.search(r'Action:\s*(\w+)', llm_output)
    if not action_match:
        return None
    
    tool_name = action_match.group(1)
    
    input_match = re.search(r'Action Input:\s*({.*?})', llm_output, re.DOTALL)
    if not input_match:
        return None
    
    try:
        parameters = json.loads(input_match.group(1))
    except json.JSONDecodeError:
        return None
    
    return {
        "tool_name": tool_name,
        "parameters": parameters
    }


def execute_tool(action: Dict[str, Any]) -> str:
    """Execute a tool and return the observation."""
    tool_name = action["tool_name"]
    parameters = action["parameters"]
    
    if tool_name not in TOOLS:
        return f"Error: Tool '{tool_name}' not found. Available tools: {list(TOOLS.keys())}"
    
    try:
        result = TOOLS[tool_name](**parameters)
        return f"Observation: {json.dumps(result, indent=2)}"
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def run_agent(query: str, max_iterations: int = 10, use_simulator: bool = True) -> Dict[str, Any]:
    """
    Main ReAct loop that orchestrates agent behavior.
    
    The loop:
    1. Send conversation to LLM
    2. Parse response for Action
    3. Execute tool if action found
    4. Append observation to conversation
    5. Repeat until Final Answer or max iterations
    """
    print("\nReAct Agent Initialized")
    print(f"Query: {query}\n")
    
    conversation_history = []
    step = 0
    final_answer = None
    
    system_prompt = f"""You are AURA, an AI agent navigating the Nebula of Uncertainty. You have access to tools that help you gather information and make decisions.

Available Tools:
1. scan_sector_hazards(x, y) - Scan a grid sector for hazards
2. calculate_escape_velocity(mass, radius) - Calculate escape velocity

Your task: {query}

Use the following format:
Thought: [Your reasoning about what to do next]
Action: [Tool name]
Action Input: {{"param": "value"}}

OR when you have enough information:
Final Answer: [Your complete answer]"""
    
    conversation_history.append({"role": "system", "content": system_prompt})
    
    while step < max_iterations:
        print(f"\n--- Iteration {step + 1} ---")
        
        if use_simulator:
            llm_output = simulate_llm_response(conversation_history, step)
        else:
            llm_output = "Final Answer: Real LLM integration not implemented."
        
        print(f"\n{llm_output}")
        
        conversation_history.append({"role": "assistant", "content": llm_output})
        
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[1].strip()
            print(f"\nFinal Answer Reached:\n{final_answer}\n")
            break
        
        action = parse_action(llm_output)
        
        if action is None:
            step += 1
            continue
        
        print(f"\nExecuting: {action['tool_name']}({action['parameters']})")
        
        observation = execute_tool(action)
        print(f"{observation}")
        
        conversation_history.append({"role": "user", "content": observation})
        
        step += 1
    
    if step >= max_iterations and final_answer is None:
        final_answer = "Agent terminated due to iteration limit. No final answer produced."
        print(f"\nWarning: Maximum iterations reached")
    
    print("\nAgent Execution Complete\n")
    
    return {
        "final_answer": final_answer,
        "iterations": step,
        "conversation_history": conversation_history,
        "success": final_answer is not None and "iteration limit" not in final_answer
    }


def main():
    """Demonstrate the ReAct agent in action."""
    print("\n" + "=" * 60)
    print("TEST CASE: Nebula Navigation")
    print("=" * 60)
    
    query = "Plot a safe course from starting position (0,0) to the Exit at (2,2). Scan sectors to avoid hazards."
    
    result = run_agent(query, max_iterations=10)
    
    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Total Iterations: {result['iterations']}")
    print(f"Final Answer: {result['final_answer'][:150]}..." if len(result['final_answer']) > 150 else f"Final Answer: {result['final_answer']}")
    
    print("\n" + "=" * 60)
    print("BONUS: Testing Escape Velocity Calculator")
    print("=" * 60)
    
    earth_result = calculate_escape_velocity(mass=5.972e24, radius=6.371e6)
    print(f"Earth Escape Velocity: {earth_result['escape_velocity_km_s']} km/s\n")


if __name__ == "__main__":
    main()