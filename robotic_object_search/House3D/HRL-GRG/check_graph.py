import scipy.io as sio
import numpy as np
import os
import json
import matplotlib
import matplotlib.pyplot as plt

gamma = 0.99

cfg = json.load(open('../../config.json', 'r'))
id2class = json.load(open(os.path.join(cfg['codeDir'], 'Environment', 'id2class.json'), 'r'))


def show_heatmap(label, value, title, save_path):
    fig, ax = plt.subplots(figsize=(10,10))
    im = ax.imshow(value)
    ax.set_xticks(np.arange(len(label)))
    ax.set_yticks(np.arange(len(label)))

    ax.set_xticklabels(label)
    ax.set_yticklabels(label)

    #ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    plt.setp(ax.get_xticklabels(), rotation=30, ha='right', rotation_mode='anchor')

    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(value.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(value.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)

    for i in range(len(label)):
        for j in range(len(label)):
            text = ax.text(j, i, '{:.1f}'.format(value[i,j]), ha='center', va='center', color='w')

    ax.set_title(title)
    fig.tight_layout()
    plt.show()
    fig.savefig(save_path)


def get_discounted_reward(graph):
    (x, y, z) = graph.shape
    reward = np.zeros((x,y))
    for i in range(x):
        for j in range(y):
            prob = graph[i, j]
            value = [gamma**k for k in range(z-1)]
            value.append(0)
            reward[i, j] = sum(prob*value)
    return reward


def get_scenes_targets(scenes):
    scenes_targets = []
    for scene in scenes:
        scene_dir = '%s/Environment/houses/%s/' % (cfg['codeDir'], scene)
        targets_info = json.load(open('%s/targets_info_all_pred.json' % scene_dir, 'r'))
        scenes_targets = np.union1d(scenes_targets,targets_info.keys())
    return list(scenes_targets)


def get_relevant_info(info, original_index, relevant_index):
    index = []
    for ri in relevant_index:

        index.append(original_index.index(ri))
    return info[:, index][index, :]

def print_relations(reward, targets):
    mean_reward = np.mean(reward)
    reward_threshold = 0.5
    # print mean_reward
    m, n = reward.shape
    for i in range(m):
        for j in range(n):
            if i!=j and reward[i][j] > reward_threshold:
                print (targets[i], targets[j], reward[i][j])



if __name__ == '__main__':
    # with open('pred_option_info.txt', 'w') as f:
    #     for i in range(36):
    #         option = id2class[str(local2global[str(i)])]
    #         f.write("%3d %s\n"%(i, option))
    #     f.write("%3d background" % (36))


    num_options = 77

    options = [id2class[str(i)] for i in range(num_options)]
    options.append('background')

    graph_path = 'result3_ms_pretrain/model/graph99000.mat'
    graph = sio.loadmat(graph_path)['graph']
    # print graph[32][32]
    reward = get_discounted_reward(graph)

    # scenes_targets = options

    scenes = ['5cf0e1e9493994e483e985c436b9d3bc']
    scenes_targets = get_scenes_targets(scenes)
    scenes_targets.append('background')

    scenes_targets = ['sofa', 'television', 'tv_stand', 'table', 'music',
                      'bed', 'dressing_table', 'ottoman',
                      'shower', 'bathtub', 'toilet']



    relevant_reward = get_relevant_info(reward, options, scenes_targets)
    print_relations(relevant_reward, scenes_targets)
    # show_heatmap(scenes_targets, relevant_reward, graph_path.split('.')[0], graph_path.split('.')[0]+'.png')







