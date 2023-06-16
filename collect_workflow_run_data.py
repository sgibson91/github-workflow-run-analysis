# TODO: Add input vars to set owner/repo and start date to collect data from

import os
import requests
import pandas as pd

api_url = "https://api.github.com"

# Read in a token from environment
token = os.environ.get("GITHUB_TOKEN", None)
if token is None:
    raise ValueError("GITHUB_TOKEN environment variable must be set")

# Create headers to send with API requests
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
}

repo = "2i2c-org/infrastructure"

# Get list of GitHub Actions workflow runs for repo
url = "/".join([api_url, "repos", repo, "actions", "runs"])
params = {
    "status": "failure",
    "created": ">2023-06-12",
    "per_page": 100,
}
response = requests.get(url, headers=headers, params=params)
workflow_runs = response.json()["workflow_runs"]

# Detect if pagination is required and execute as needed
while "Link" in response.headers.keys():
    response = requests.get(response.headers["Link"], headers=headers)
    workflow_runs.extend(response.json()["workflow_runs"])

# Instantiate empty dataframe
wf_df = pd.DataFrame({})

for workflow_run in workflow_runs:
    # Append an instance of each workflow run to a dataframe
    tmp_wf_df = pd.DataFrame(
        {
            "run_time": workflow_run["run_started_at"],
            workflow_run["path"]: 1,
        },
        index=[0]
    )
    wf_df = pd.concat([wf_df, tmp_wf_df], ignore_index=True)
    wf_df.reset_index(inplace=True, drop=True)

# Post-process dataframes and save copies
wf_df["run_time"] = pd.to_datetime(wf_df["run_time"])
wf_df.fillna(0, inplace=True)
wf_df.to_csv("workflow_run_count_data.csv", index=False)

# Resample data to monthly intervals and save a copy
wf_df = wf_df.resample("M", on="run_time").sum()
wf_df.to_csv("workflow_run_data_monthly_resample.csv")
