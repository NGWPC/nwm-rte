import argparse
import functools
import json
import os
import subprocess
import urllib.request

print = functools.partial(print, flush=True)


def run(cmd: str, cwd: str) -> str:
    """Run a command and return stdout"""
    print(f"From {repr(cwd)} running command: {repr(cmd)}")
    p = subprocess.run(
        cmd, cwd=cwd, shell=True, capture_output=True, text=True, check=False
    )
    try:
        p.check_returncode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ERROR: failed to run cmd: {cmd}\n\nSTDERR={p.stderr}\n\nSTDOUT={p.stdout}\n\nERROR"
        )
    return p.stdout.rstrip()  # remove trailing whitespace


def get_repo_name(gh_org: str, local_repo_path: str) -> str:
    cmd = "git config --get remote.origin.url"
    raw = run(cmd, cwd=local_repo_path)

    startswith_ssh = f"git@github.com:{gh_org}/"
    startswith_https = f"https://github.com/{gh_org}/"

    if raw.startswith(startswith_ssh):
        repo_name = raw[len(startswith_ssh) :]
    elif raw.startswith(startswith_https):
        repo_name = raw[len(startswith_https) :]
    else:
        raise ValueError(f"Unexpected result from cmd {cmd}: {raw}")

    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]
    return repo_name


def fetch_github_commit_info(gh_org: str, repo_name: str, branch: str) -> dict:
    """Fetch commit information from GitHub API for a given repo and branch/tag/commit"""
    if not gh_org:
        raise ValueError("gh_org must be provided")
    # GitHub API endpoint for commits
    api_url = f"https://api.github.com/repos/{gh_org}/{repo_name}/commits/{branch}"

    print(f"Fetching commit info from: {api_url}")

    try:
        req = urllib.request.Request(api_url)
        # Add user agent to avoid GitHub API rate limiting issues
        req.add_header("User-Agent", "nwm-rte-build-script")

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        return data
    except urllib.error.HTTPError as e:
        print(f"ERROR: Failed to fetch from GitHub API: {e}")
        print(f"Response body: {e.read().decode() if hasattr(e, 'read') else 'N/A'}")
        raise


class GitInfoBuilder:
    def __init__(
        self,
        gh_org: str = None,
        local_repo_path: str = None,
        remote_repo_name: str = None,
        remote_branch: str = None,
        output_dir: str = None,
    ):
        d = {}

        if local_repo_path:
            d["repo_name"] = get_repo_name(gh_org, local_repo_path)
            d["commit_hash"] = run("git rev-parse HEAD", cwd=local_repo_path)
            d["branch"] = run("git rev-parse --abbrev-ref HEAD", cwd=local_repo_path)
            d["tags"] = run(
                "git tag --points-at HEAD | tr '\n' ' '", cwd=local_repo_path
            )
            d["author"] = run("git log -1 --pretty=format:'%an'", cwd=local_repo_path)
            d["commit_date"] = run(
                "date -u -d @$(git log -1 --pretty=format:'%ct') +'%Y-%m-%d %H:%M:%S UTC'",
                cwd=local_repo_path,
            )
            d["message"] = run(
                "git log -1 --pretty=format:'%s' | tr '\n' ';'", cwd=local_repo_path
            )
            d["build_date"] = run(
                "date -u +'%Y-%m-%d %H:%M:%S UTC'", cwd=local_repo_path
            )

        elif remote_repo_name and remote_branch:
            # Fetch commit info from GitHub API
            commit_data = fetch_github_commit_info(
                gh_org, remote_repo_name, remote_branch
            )

            # Extract relevant information from the API response
            d["repo_name"] = remote_repo_name
            d["commit_hash"] = commit_data["sha"]
            d["branch"] = remote_branch  # The branch/tag/ref that was requested
            d["tags"] = ""  # Tags not easily available from this API endpoint
            d["author"] = commit_data["commit"]["author"]["name"]
            d["commit_date"] = commit_data["commit"]["author"]["date"]
            d["message"] = commit_data["commit"]["message"].split("\n")[
                0
            ]  # First line only
            d["build_date"] = subprocess.run(
                ["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.rstrip()
        else:
            raise ValueError("Incompatible args combo")

        self.d = d
        self.output_dir = output_dir

    def write_json_file(self):
        json_file = os.path.join(
            self.output_dir, f"{self.d['repo_name']}_git_info.json"
        )

        print(f"Writing: {json_file}")
        with open(json_file, "w") as f:
            json.dump(self.d, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gh_org", required=False)
    parser.add_argument("--local_repo_path", required=False)
    parser.add_argument("--remote_repo_name", required=False)
    parser.add_argument("--remote_branch", required=False)
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory to write the gitinfo json file into",
    )
    args = parser.parse_args()

    builder = GitInfoBuilder(**vars(args))
    builder.write_json_file()


if __name__ == "__main__":
    main()
