import os
import io
import re
import requests
import pandas as pd
import zipfile
import shutil

# Create a set of the current files in the directory
current_files = set(os.listdir(os.getcwd()))

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

# Get list of failed GitHub Actions workflow runs for repo after a set date
url = "/".join([api_url, "repos", repo, "actions", "runs"])
params = {
    "status": "failure",
    "created": ">2023-06-12",
    "per_page": 100,
}
response = requests.get(url, headers=headers, params=params)
workflow_runs = response.json()["workflow_runs"]

# Detect if pagination is required and execute as needed
while ("Link" in response.headers.keys()) and ('rel="next"' in response.headers["Link"]):
    next_url = re.search(r'(?<=<)([\S]*)(?=>; rel="next")', response.headers["Link"])
    response = requests.get(next_url.group(0), headers=headers)
    workflow_runs.extend(response.json()["workflow_runs"])

# Define regex pattern to search the logs for
pattern = re.compile("API rate limit exceeded for installation ID")

# Instantiate empty dataframe
wf_df = pd.DataFrame({})

for workflow_run in workflow_runs:
    # Download the logs
    response = requests.get(workflow_run["logs_url"], headers=headers, stream=True)
    
    try:
        # Extract the logs
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(os.getcwd())
    except zipfile.BadZipFile:
        # This usually means the logs have been deleted, so we break the loop as
        # we have hit the limit of the retention policy
        break

    # Establish which files have been downloaded
    updated_files = set(os.listdir(os.getcwd()))
    new_files = updated_files.difference(current_files)

    # Loop through downloaded files, read them, and search for relevant error message
    for ifile in new_files:
        if not os.path.isfile(ifile):
            for jfile in os.listdir(ifile):
                with open(os.path.join(ifile, jfile)) as f:
                    content = f.read()
                match = pattern.search(content)
                if match is not None:
                    # Append the failed workflow to a dataframe
                    tmp_wf_df = pd.DataFrame(
                        {
                            "run_time": workflow_run["run_started_at"],
                            workflow_run["path"]: 1,
                        },
                        index=[0],
                    )
                    wf_df = pd.concat([wf_df, tmp_wf_df], ignore_index=True)
                    wf_df.reset_index(inplace=True, drop=True)

            shutil.rmtree(ifile)
        else:
            os.remove(ifile)

# Post-process dataframes and save copies
try:
    wf_df["run_time"] = pd.to_datetime(wf_df["run_time"])
    wf_df.fillna(0, inplace=True)
except KeyError:
    pass

if len(wf_df) > 0:
    wf_df.to_csv("failed_workflow_run_count_data.csv", index=False)

try:
    # Resample data to daily intervals and save a copy
    wf_df = wf_df.resample("D", on="run_time").sum()
    wf_df.to_csv("failed_workflow_run_data_daily_resample.csv")
except KeyError:
    pass
