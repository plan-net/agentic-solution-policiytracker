# Split Graph Processing

## Goals
I want to have three distinct workflows which can work with the underlying graph database
1. Data Ingestions - processing input documents and enrich context with LLMs before we actually build the graph
2. Company Context - taking the current client.yaml simply as starting point and running an LLM driven enrichment process on the client context, which will be added to the same graph database. this will be re-run on a daily basis to update the assessment based on new insights, news and documents provided
3. Relevance Assessment - a process which runs on a daily basis to check if the changes of available data or client context changes something on our policy assessment

Right now we have prototyped a first version of a policy tracker system, but it's now time to move towards an architecture, which matches real-world requirements

## Requirements
- it is really critical that we have an architecture in place, which builds on-top of a temporal aware knowledge-graph, which can handle daily updates to the graph and allows to look at specific timesframe. Data Ingestion and Client Context will update on a daily basis and the relevance assessment needs to be capable to understand whats new and also analyse events in the order in which they happen
- all three processes need to run on the underlaying Ray Cluster Environment, supported by Kodosumi. We should have three distinct Kodosumi Apps appearing in the admin panel, which can be triggered independently

## Temporal-aware Graph RAG system
- so far we have build with the Neo4J Pyton Library for Graph RAG, but now we need to assess the best way forward
- please evaluate if this might be a good option: https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/?utm_source=chatgpt.com
- here is the repository on Github: https://github.com/getzep/graphiti
- here is their documentation for their MCP Server: https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- I find the idea to interact with the Knowledge Graph through this MCP Server quite compelling
- in order to work with the MCP server we would need this adapter for langchain and langgraph: https://github.com/langchain-ai/langchain-mcp-adapters
- we could run the MCP Server alongside the NEO4J database through our Docker Compose Setup

## Really Important:
- let's build this in small steps, which we can validate step-by-step
- don't build a massive codebase and then we spend a full day to make it work
- break it down into small steps

## The three workflows:

### 1. Data Ingestion
- load the files from the data/input folder (a seperate process will update these documents in the future)
- run entity recognition on them with an LLM (I want to be able to specify in a separate config file which entities we want to recongise. like: politicians, laws, legaslative initiatives etc.)
- run web research accross a list of trustes sources (trusted sources need to be configurable) to gain more context about the entities. Rerun the process of entity recognition and research on them again.
- it should be configurable how many times we want to complete this loop to gather more context. by default we just do this one time
- then the rest of the process needs to happen (chunking, embedding etc.) in order to update the knowledge graph with these insights
- it's key that this process already is time sensitive at it runs daily and only processes documents, which it has not seen yet. 
- the output in the end of this workflow which the user sees in the kodosumi interface as a result is just a short report on what has been happening. how many new documents processed, how many entities recongnized, graph update with X notes and y relationship. whatever makes the most sense.

### 2. Client Context
- load the client.yaml file as a kind of briefing for the client context
- run different Web Searches to get more context about the client, which can be used to be ingested into the knowledge base
- so we are collecting again documents on this client and then go through the process to prepare this data for ingestion into the knowledge graph
- this part of the process should be re-usable and be capable to be used by both the data ingestion and the client context alike.
- please develop a good idea on how to structure this and make the core process reusable
- the output of the client context process should again be simply a report on what has been update in the knowledge graph for this client, similiar to the data ingestion process

### 3. Relevance Assesssment
- this process tries to identify for a given timeframe (defaults: last day, last week, last month or all-time) which topics are relevant for the given client
- we need to develop a good query strategy for how to figure this out. we should look at the latest addition to the knowledge-graph and how they change our assessment and whats new.
- our data model should have in the graph for each client linked topics, which have the potential to influence our clients business. we should identify if any news, new laws, talks of politicians or whatever is coming from the data ingestion could potentialls influence those topics to recognize
- to make our lives easier the relevance assessment should always build a memory of what its assessment has been. So after each run it creates a new summary and stores this summary somewhere (keep it simple for the beginning) and it needs to be able to review its passt assessment as context to derive good query strategies
- as a result of this process we want to have a list of items: "whats new" - these are events, whereby an event can be the publication of a news article, a new legislative initiative, a speech of a politician and more - and for each event we provide an assessment of why this event might be relevant.
- the purpose of this process is only to filter events, which are relevant and we would want to have system, which gives a bit more context on relevance. something like: how time-sensitive is this event, how direct or indirect might this affect the company, where could this affect the client
- is NOT our job yet to go into great detail of what the implications might be or what potential scenarios could be. That will happen in the future in a fourth process, which would take this events ranked by relevance and analyse in great depth.

## Additional advise
- we always want LLMs to do the job
- remove any rule based or keyword based approaches. they are not suitable for what we want to do here