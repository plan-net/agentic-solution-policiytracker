# ETL Integration with Airflow

We need to integrate now an ETL Pipeline into the project, which is collecting data from Apify and potentially other data providers, to extract, transform and load the data for getting processed by flow1 and flow2. It is the process to replace the example documents with real data.

- I want to use the latest version of Apache Airflow and run it alongside the other services also in docker
- make sure to update docker compose and the justfile accordingly 
- we need to generate a first job which will collect data from the Apify API as context on the client
- we will get json. part of the json is the full text of the news article. I want to transform this in actual markdown files, preserving some key metadata like url, headline, time of publication etc.
- we then store the md files either local in the data folder and in production we would load them to azure blob storage
- the jobs will run on a daily basis and it should be possible to trigger them manually
- we should also explore options if we can also schedule the execution of flow1 and/or flow2 through apache airflow
- I think there are connectors for ray available or we simply start them through kodosumi. let's think about the best option here

Let's keep this implementation very lean and simple.

Apify has a python client and here is a codensippet on how to collect news.
I want to use this apify actor to collect news on the client which is defined in the client.yaml file in data/context

```
from apify_client import ApifyClient

# Initialize the ApifyClient with your API token
client = ApifyClient("<YOUR_API_TOKEN>")

# Prepare the Actor input
run_input = {
    "query": "Tesla",
    "topics": [],
    "topicsHashed": [],
    "language": "US:en",
    "maxItems": 100,
    "fetchArticleDetails": True,
    "proxyConfiguration": { "useApifyProxy": True },
}

# Run the Actor and wait for it to finish
run = client.actor("eWUEW5YpCaCBAa0Zs").call(run_input=run_input)

# Fetch and print Actor results from the run's dataset (if there are any)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)
```

Here is my api key for apifiy: <YOUR_APIFY_API_TOKEN>

After this data has been collected and prepared as markdown files, this would trigger flow2 (which is not ready yet), when then adds these documents also to our knowledge graph with Graphiti. This will help us to understand what is happening in the context of the client.


