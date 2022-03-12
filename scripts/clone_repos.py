import os
import json
import subprocess

## Simple script to clone repositories from GitHub.
def clone_repos(filename="repos.json"):
    if not os.path.exists('C_Dataset'):
        os.makedirs('C_Dataset')

    existingRepos = [os.path.join('C_Dataset', folder) for folder in os.listdir('C_Dataset') if os.path.isdir(os.path.join('C_Dataset', folder))]

    with open(filename, "r") as f:
        repo_list = json.load(f)

        for repo_name, repo_link in repo_list.items():
            in_path = os.path.join("C_Dataset", repo_name)
            if in_path not in existingRepos:
                # p = subprocess.Popen("git clone --depth=1 --progress -v " + repo_link + ' ' + in_path, stdout=subprocess.PIPE)
                p = subprocess.Popen(["git", "clone", "--depth=1", "--progress", "-v", repo_link, in_path], stdout=subprocess.PIPE)
                p.wait()

            repoCount += 1

if __name__ == '__main__':
    clone_repos("repos.json")