import argparse
import functools
import json
import os
import subprocess

print = functools.partial(print, flush=True)


GH_ORG = "NGWPC"


def run(cmd: str, cwd: str) -> str:
    """Run a command and return stdout"""
    print(f"Running command {repr(cmd)} from {repr(cwd)}")
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, check=False)
    try:
        p.check_returncode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ERROR: failed to run cmd: {cmd}\n\nSTDERR={p.stderr}\n\nSTDOUT={p.stdout}\n\nERROR")
    return p.stdout.rstrip()  # remove trailing whitespace


def get_repo_name(local_repo_path: str) -> str:
    raw = run("git config --get remote.origin.url", cwd=local_repo_path)
    assert raw.startswith(f"git@github.com:{GH_ORG}/")
    repo_name = raw[len(f"git@github.com:{GH_ORG}/") :]
    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]
    return repo_name


class GitInfoBuilder:
    def __init__(
        self,
        local_repo_path: str = None,
        remote_repo_name: str = None,
        remote_branch: str = None,
        output_dir: str = None,
    ):
        d = {}

        if local_repo_path:
            d["repo_name"] = get_repo_name(local_repo_path)
            d["commit_hash"] = run("git rev-parse HEAD", cwd=local_repo_path)
            d["branch"] = run("git rev-parse --abbrev-ref HEAD", cwd=local_repo_path)
            d["tags"] = run("git tag --points-at HEAD | tr '\n' ' '", cwd=local_repo_path)
            d["author"] = run("git log -1 --pretty=format:'%an'", cwd=local_repo_path)
            d["commit_date"] = run(
                "date -u -d @$(git log -1 --pretty=format:'%ct') +'%Y-%m-%d %H:%M:%S UTC'", cwd=local_repo_path
            )
            d["message"] = run("git log -1 --pretty=format:'%s' | tr '\n' ';'", cwd=local_repo_path)
            d["build_date"] = run("date -u +'%Y-%m-%d %H:%M:%S UTC'", cwd=local_repo_path)

        elif remote_repo_name and remote_branch:
            raise NotImplementedError("Remote mode not implemented yet")
        else:
            raise ValueError("Incompatible args combo")

        self.d = d
        self.output_dir = output_dir

    def write_json_file(self):
        json_file = os.path.join(self.output_dir, f"{self.d['repo_name']}_git_info.json")

        print(f"Writing: {json_file}")
        with open(json_file, "w") as f:
            json.dump(self.d, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_repo_path", required=False)
    parser.add_argument("--remote_repo_name", required=False)
    parser.add_argument("--remote_branch", required=False)
    parser.add_argument("--output_dir", required=True, help="Directory to write the gitinfo json file into")
    args = parser.parse_args()

    builder = GitInfoBuilder(**vars(args))
    builder.write_json_file()


if __name__ == "__main__":
    main()
