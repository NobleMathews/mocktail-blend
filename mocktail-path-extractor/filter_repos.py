import os
import json
import requests
import subprocess

def get_top_repos(minPage = 1, maxpage = 20):
    repo_details = []
    for i in range(minPage, maxpage + 1):
        try:
            public_repos = requests.get('https://api.github.com/search/repositories?page=' + str(i) + '&q=language:C&sort=stars&order=desc').json()['items']
        except:
            print("Exited at {}. Use it as minPage next time".format(i))
            return repo_details

        for repo in public_repos:
            repo_name = repo['name']
            repo_link = repo['html_url']
            repo_stars = repo['stargazers_count']
            repo_forks = repo['forks_count']
            repo_size = repo['size']
            # print(repo_name, repo_link, repo_stars)
            repo_details.append({ 'name': repo_name,
                                    'link': repo_link,
                                    'stars': repo_stars,
                                    'forks': repo_forks,
                                    'size': repo_size})

    return repo_details


def clone_repos(filename="repos.json", repoStartIndex=0, repoEndIndex=9):
    existingRepos = [os.path.join('CppDataset', folder) for folder in os.listdir('CppDataset') if os.path.isdir(os.path.join('CppDataset', folder))]

    with open(filename, "r") as f:
        repo_list = json.load(f)
        repoCount = 0

        for repo_name, repo_link in repo_list.items():
            if repoCount < repoStartIndex:
                repoCount += 1
                continue
            if repoCount > repoEndIndex:
                break

            in_path = os.path.join("CppDataset", repo_name)
            if in_path not in existingRepos:
                # p = subprocess.Popen("git clone --depth=1 --progress -v " + repo_link + ' ' + in_path, stdout=subprocess.PIPE)
                p = subprocess.Popen(["git", "clone", "--depth=1", "--progress", "-v", repo_link, in_path], stdout=subprocess.PIPE)
                p.wait()

            repoCount += 1


# if __name__ == '__main__':
    # Stars C:
    # print(json.dumps(get_top_repos(35, 200), indent=4))


    # Stars Cpp:
    # print(get_top_repos(33, 200))

    # Forks C:
    # pretty(get_top_repos(0, 200))
    # print(json.dumps(get_top_repos(34, 200), indent=4))


    # clone_repos("repos.json", repoStartIndex=0, repoEndIndex=998)       # 0 Indexing



    ####### Combine repos_c_stars.json repos_c_forks.json into repos_c.json 
    # new_repos = []
    # with open('repos_c_stars.json', 'r') as f:
    #     with open('repos_c_forks.json', 'r') as f1:
    #         repos_stars = json.load(f)
    #         repos_forks = json.load(f1)

    #         for repo in repos_stars:
    #             curr_link = repo['link']

    #             flag = False
    #             for repo1 in new_repos:
    #                 if repo1['link'] == curr_link:
    #                     flag = True
    #                     break
    #                 else:
    #                     continue
                
    #             if flag == False:
    #                 new_repos.append(repo)

    #         for repo in repos_forks:
    #             curr_link = repo['link']

    #             flag = False
    #             for repo1 in new_repos:
    #                 if repo1['link'] == curr_link:
    #                     flag = True
    #                     break
    #                 else:
    #                     continue
                
    #             if flag == False:
    #                 new_repos.append(repo)
        
    # with open('repos_c.json', 'w') as f:
    #     json.dump(new_repos, f, indent=4)




    ####### Find the difference between repos_c_stars.json and repos_c_forks.json.
    # extra_repos = []
    # with open('repos_c_forks.json', 'r') as f:
    #     with open('repos_c_stars.json', 'r') as f1:
    #         forks = json.load(f)
    #         stars = json.load(f1)

    #         forks_names = []
    #         for fork in forks:
    #             forks_names.append(fork['name'])

    #         print("Repos in forks, but not in stars: ")
    #         for repo in forks_names:
    #             if repo not in stars:
    #                 print(repo)
    #                 extra_repos.append(repo)

    #         print("Repos in stars, but not in forks: ")
    #         for repo in stars:
    #             if repo not in forks_names:
    #                 print(repo)



    ####### Calculate z-scores, sort repos as per z-scores and rewrite file.
    # import numpy
    # from scipy import stats

    # repos = []
    # with open('repos_c.json', 'r') as f:
    #     repos = json.load(f)
    #     repo_stars = []
    #     repo_forks = []

    #     for repo in repos:
    #         repo_stars.append(repo['stars'])
    #         repo_forks.append(repo['forks'])

    #     # stars_mean = numpy.mean(repo_stars)
    #     # forks_mean = numpy.mean(repo_forks)
    #     # print(stars_mean)
    #     # print(forks_mean)

    #     # stars_std = numpy.std(repo_stars)
    #     # forks_std = numpy.std(repo_forks)
    #     # print(stars_std)
    #     # print(forks_std)

    #     stars_zscores = stats.zscore(repo_stars)
    #     forks_zscores = stats.zscore(repo_forks)
    #     total_zscores = stars_zscores + forks_zscores
    #     print(total_zscores)


    # for index, repo in enumerate(repos):
    #     repo['z-score'] = total_zscores[index]

    # repos = sorted(repos, key=lambda repo: repo['z-score'], reverse=True) 

    # with open('repos_c_mod.json', 'w') as f:
    #     json.dump(repos, f, indent=4)



    ####### From repos_count.json, inserting method counts for all repos into repos_c_mod.json
    # with open('repos_c_mod.json', 'r') as f:
    #     with open('repos_count.json', 'r') as f1:
    #         repos = json.load(f)
    #         repos_count = json.load(f1)

    #         for repo in repos:
    #             if repo['name'] in repos_count:
    #                 repo['method_count'] = repos_count[repo['name']]
    #             else:
    #                 repo['method_count'] = -1

    #         with open('repos_c_mod2.json', 'w') as f2:
    #             json.dump(repos, f2, indent=4)


    # with open('repos_c_mod2.json', 'r') as f:
    #     repos = json.load(f)

    #     total_count = 0
    #     for index, repo in enumerate(repos):
    #         if repo['method_count'] > 25000:
    #             total_count += repo['method_count']
    #             print(repo['name'], repo['method_count'])

    #         # if total_count > 1500000:
    #         #     print(index, repo['name'])
    #         #     break