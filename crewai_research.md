# CrewAI Research Notes

## Agent Capabilities

CrewAI agents are autonomous units that can:
- Perform specific tasks
- Make decisions based on role and goal
- Use tools to accomplish objectives
- Communicate and collaborate with other agents
- Maintain memory of interactions
- Delegate tasks when allowed

## Key Agent Attributes

- **Role**: Defines the agent's function and expertise
- **Goal**: Individual objective guiding decision-making
- **Backstory**: Provides context and personality
- **LLM**: Language model powering the agent (default: gpt-4)
- **Tools**: Capabilities or functions available to the agent
- **Memory**: Can maintain short-term, long-term, entity, and contextual memory
- **Allow Delegation**: Can delegate tasks to other agents
- **Max Iterations**: Maximum iterations before providing best answer (default: 20)
- **Verbose**: Enable detailed execution logs

## Configuration Methods

1. **YAML Configuration (Recommended)**: Clean, maintainable way to define agents
2. **Direct Code Definition**: Instantiate Agent class directly

## Agent Collaboration

Agents work together in a Crew, where they can:
- Share context and memory
- Pass information between tasks
- Delegate work to specialized agents
- Maintain state across interactions


## Task Structure

Tasks in CrewAI are specific assignments completed by agents. Key features:

- **Description**: Detailed explanation of what needs to be done
- **Expected Output**: Clear definition of the desired result
- **Agent**: The agent responsible for completing the task
- **Tools**: Optional tools available for the task
- **Context**: Can receive output from previous tasks
- **Output File**: Can save results to a file

## Task Execution Modes

1. **Sequential**: Tasks executed in order they are defined
2. **Hierarchical**: Tasks assigned based on agent roles and expertise

## Task Context Sharing

Tasks can be collaborative, requiring multiple agents to work together. This is managed through:
- Task properties
- Crew's process orchestration
- Context passing between tasks
- Enhanced teamwork and efficiency
