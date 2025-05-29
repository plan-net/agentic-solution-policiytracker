As part of the political monitorimg solution I would like to add a chat interface for user to explore the data sitting in the underying neo4j knowledge graph.

- i want to use open webui as the frontend
- and build a react agent with langchain and langgraph wo responds to users request
- this agent should run with ray serve (NOT Kodosumi) and expose a chat endpoint for open webui
- this agent should have basic memory provided through langchain library to remember the chat during the session
- the agent should have several tools to choose from to explore the data in neo4j / graphiti
- we use graphiti on top of neo4j and it provides many different search features
- they are documented here: https://help.getzep.com/graphiti/graphiti/searching
- we need to come up with a good plan on how to turn the search feature into tools
- use the graphiti client directly and do not build a wrapper around it
- the agent should run in multiple loops in which he understand the request by the user, plan on how to explore the data with which tools the best, read the results and have the ability to come up with new search queries, based on what he learned
- we need to have a mechanism in place to evaluate at which point the agent can give the best possible answer back to the user
- all prompts use by the agent need to be loaded from md files in the /src/prompts directory, as how we do it accross the codebase
- langfuse integration is not yet a priority, but will be added later

Our goal is to build now the best possible langchain + langraph agent who reasons, uses tools to explore the graph and evaluate his answer, bevor he responds back to the user.

Please think of how to evolve the src folder structure for this to keep things clean and well organized.



