# TODO: Add input vars to set owner/repo and start date to collect data from

import os
import pandas as pd
from ghapi.all import GhApi, paged

# Read in a token from environment
token = os.environ.get("GITHUB_TOKEN", None)
if token is None:
    raise ValueError("GITHUB_TOKEN environment variable must be set")

# Authenticate ghapi
gh = GhApi(token=token)

owner = "2i2c-org"
repo = "infrastructure"

# Get list of GitHub Actions workflow runs for repo
response = gh.actions.list_workflow_runs_for_repo(
    owner, repo, per_page=100, created="2022-06-01..2023-06-01"
)
workflow_runs = response["workflow_runs"]

# Detect if pagination is required and execute as needed
total_pages = (response["total_count"] // 100) + 1
if total_pages > 1:
    for i in range(2, total_pages + 1):
        response = gh.actions.list_workflow_runs_for_repo(
            owner, repo, per_page=100, page=i,
        )
        workflow_runs.extend(response["workflow_runs"])

# Instantiate empty dataframes
wf_df = pd.DataFrame({})

for workflow_run in workflow_runs:
    # Append an instance of the workflow run to a dataframe
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

df["run_time"] = pd.to_datetime(df["run_time"])
df.fillna(0, inplace=True)
df.to_csv("all_workflow_run_data.csv", index=False)

# Resample data to monthly intervals and save a copy
wf_df = wf_df.resample("M", on="run_time").sum()
wf_df.to_csv("workflow_run_data_monthly_resample.csv")
