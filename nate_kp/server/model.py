import pandas as pd
import requests
import sys
import random
from scipy.spatial import distance
import math

def run(i):
    SERVER_URL = 'http://84.201.135.211:8000/'
    STUDENT_INTERESTS_PATH = 'interests_by_student/'
    TAGS_PATH = 'requirements/'
    PROJECTS_PATH = 'projects/'
    PROJECT_TAGS_PATH = 'requirements_by_project/'
    OUTPUT_PATH = 'suggestions_create/'


    # student_id = sys.argv[1]
    student_id = i

    student_interests = pd.read_json(f'{SERVER_URL}{STUDENT_INTERESTS_PATH}{student_id}')
    tags = pd.read_json(f'{SERVER_URL}{TAGS_PATH}')
    projects = pd.read_json(f'{SERVER_URL}{PROJECTS_PATH}')

    projects = projects[projects['id'] > 13]

    tag_clusters = pd.read_csv('~/nate_kp/nate_kp/server/tags_clustered.csv', encoding='utf-16').drop(columns=['Unnamed: 0'])
    project_clusters = pd.read_csv('~/nate_kp/nate_kp/server/clustered_projects2.csv')
    tag_matrix = pd.read_csv('~/nate_kp/nate_kp/server/tag_matrix_full_new.csv')

    user_tags = student_interests['name'].tolist()
    print(user_tags)

    project_nums = projects['id'].tolist()
    project_names = projects['description'].tolist()
    project_clusters['id'] = [project_nums[project_names.index(name)] for name in project_clusters['name']]
    project_tags = {}

    for num in project_nums:
        pt = pd.read_json(f'{SERVER_URL}{PROJECT_TAGS_PATH}{num}')
        if len(pt):
            pt = pt['name'].tolist()
            project_tags[num] = pt

    tag_similarities = {}

    for key in project_tags:
        cluster_nums = tag_clusters['cluster_num'].unique()
        scores = []

        if 'Прикладной проект' in user_tags:
            user_tags.remove('Прикладной проект')
        if 'Исследовательский проект' in user_tags:
            user_tags.remove('Исследовательский проект')

        for num in cluster_nums:
            tags_in_cluster = tag_clusters[tag_clusters['cluster_num']==num]['tag'].tolist()
            ut = [1 if x in user_tags else 0 for x in tags_in_cluster]
            pt = [1 if x in project_tags[key] else 0 for x in tags_in_cluster]
            intersection = sum([a and b for a, b in zip(ut, pt)])
            if num in [-1, 3]:
                union = sum(pt)
            else:
                union = sum([a or b for a, b in zip(ut, pt)])

            if union:
                scores.append(intersection / union)
            else:
                scores.append(0)

        scores.sort(reverse=True)
        tag_similarities[key] = scores[0]*0.6 + scores[1]*0.3 + scores[2]*0.1
        
        

    max_sim = max(tag_similarities, key=tag_similarities.get)
    del tag_similarities[max_sim]

    if max(tag_similarities.values()) != 0:
        res = {'project_id' : max_sim, 'student_id' : student_id}
#         print(max_sim, max(tag_similarities.values()))
        requests.post(f'{SERVER_URL}{OUTPUT_PATH}', data=res)

    if max(tag_similarities.values()) >= 0.5:
        max_sim_row = project_clusters[project_clusters['id'] == max_sim].iloc[0].values.flatten().tolist()
        max_sim_cluster = max_sim_row[-3]
        max_sim_coords = max_sim_row[:10]

        for key in tag_similarities:
            cur_row = project_clusters[project_clusters['id'] == key].iloc[0].values.flatten().tolist()
            cur_cluster = cur_row[-3]
            cur_coords = cur_row[:10]
            if (max_sim_cluster != -1 and cur_cluster == max_sim_cluster) or max_sim_cluster == -1:
                tag_similarities[key] += 0.5*math.exp(-distance.euclidean(max_sim_coords, cur_coords))

        for key in tag_similarities:
            if tag_similarities[key] > 0.5:
                res = {'project_id' : key, 'student_id' : student_id}
                print(key, tag_similarities[key])
                requests.post(f'{SERVER_URL}{OUTPUT_PATH}', data=res)