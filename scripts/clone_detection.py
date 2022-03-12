import os, random, itertools, math, sys
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import pickle
import time

plt.style.use("seaborn-dark")

def pretty(d, indent=0):
    for key, value in d.items():
        print('\n' + '\t' * indent + str(key))
        if isinstance(value, dict):
            pretty(value, indent+1)
        else:
            print('\t' * (indent+1) + str(value))

def nCr(n, r):
    f = math.factorial
    return f(n) // f(r) // f(n-r)


def read_csv_file(code_vectors_file):
    # Create a dictionary with (class - list of code vectors) mapping.
    data_dict = {}

    with open(code_vectors_file, 'r') as f:
        for line in f:
            label = line.split(' ')[0]
            label = int(label)
            
            if label > NUM_CLASSES:         # This is useful in selecting only initial `NUM_CLASSES` problems (like first 15 in OJClone.)
                continue

            vector = line.split(' ')[1].split(',')[:-1]
            vector = [float(num) for num in vector]
            
            CLASS_SET.append(label)
            if label in data_dict:
                data_dict[label].append(vector)
            else:
                data_dict[label] = [vector]

    # pretty(data_dict)
    return data_dict

def generate_clone_pairs(data_dict):
    print("Extracting clone pairs...")
    clone_pairs_per_class = math.ceil(MAX_CLONE_PAIRS / NUM_CLASSES)
    clone_pairs = []

    for class_label, vectors in data_dict.items():
        pairs = list(itertools.combinations(vectors, 2))

        if len(pairs) > clone_pairs_per_class:
            pairs = random.sample(pairs, clone_pairs_per_class)

        clone_pairs += pairs

    # print(clone_pairs)
    return clone_pairs

def generate_non_clone_pairs(data_dict):
    print("Extracting non-clone pairs...")
    nonclone_pairs_per_class_pair = math.ceil(MAX_NON_CLONE_PAIRS / nCr(NUM_CLASSES, 2))
    non_clone_pairs = []

    # for class_label, vectors in data_dict.items():
    #     for other_label, other_vectors in data_dict.items():
    #         if class_label != other_label:
    #             pairs = list(itertools.product(vectors, other_vectors))
    #             random.shuffle(pairs)

    #             for (v1, v2) in pairs:
    #                 if ((v1, v2) not in non_clone_pairs) and ((v2, v1) not in non_clone_pairs):
    #                     non_clone_pairs.append((v1, v2))
            
    # if len(non_clone_pairs) > MAX_NON_CLONE_PAIRS:
    #     non_clone_pairs = random.sample(non_clone_pairs, MAX_NON_CLONE_PAIRS)

    # for class_label, vectors in data_dict.items():
    #     for other_label, other_vectors in data_dict.items():
    #         if other_label > class_label:
    #             pairs = list(itertools.product(vectors, other_vectors))

    #             if len(pairs) > nonclone_pairs_per_class_pair:
    #                 pairs = random.sample(pairs, nonclone_pairs_per_class_pair)

    #             non_clone_pairs += pairs
    #             print(len(non_clone_pairs))

    num_samples = 500
    included_sample_pairs = []
    timeout = time.time() + 60*5   # 5 minutes from now

    while len(non_clone_pairs) < MAX_NON_CLONE_PAIRS and time.time() < timeout:
        class1, class2 = np.random.choice(NUM_CLASSES, 2, replace=False)    # np.random.choice generates numbers in range [0, NUM_CLASSES)
        class1 += 1
        class2 += 1

        if (class1 not in data_dict) or (class2 not in data_dict):
            continue
        # class1, class2 = random.sample(CLASS_SET, 2)

        num_samples1 = len(data_dict[class1])
        num_samples2 = len(data_dict[class2])

        class1_idx = random.randint(0, num_samples1 - 1)                    # random.randint generates numbers in range [0, num_samples1 - 1] (both included.)
        class2_idx = random.randint(0, num_samples2 - 1)

        pair = (data_dict[class1][class1_idx], data_dict[class2][class2_idx])
        idxs_pair = (class1*num_samples + class1_idx, class2*num_samples + class2_idx)
        if (pair not in non_clone_pairs) and (idxs_pair not in included_sample_pairs):
            non_clone_pairs.append(pair)
            included_sample_pairs.append(idxs_pair)

    # print(non_clone_pairs)
    return non_clone_pairs


def calculate_cossim(pairs):
    print("Calculating cosine similarity...")
    pair1 = []
    pair2 = []
    for p1, p2 in pairs:
        pair1.append(p1)
        pair2.append(p2)

    x = tf.constant(pair1)
    y = tf.constant(pair2)

    # We take Negative of tf.keras.losses.cosine_similarity as it is defined in opposite way (see docs.)
    s = -tf.keras.losses.cosine_similarity(x, y)
    return s

def plot_similarity_scores(clone_sim=[], non_clone_sim=[]):
    # with open('pairs.pickle', 'rb') as f:
    #     clone_sim = pickle.load(f)
    #     non_clone_sim = pickle.load(f)

    fig, axes = plt.subplots(2, 1, figsize=(7, 10), dpi=600)
    titles = [CLASSIFIER_NAME+' - True Clones', CLASSIFIER_NAME+' - False Clones']
    x_labels = ['', 'Cosine similarity score']
    y_labels = ['Number of clone pairs', 'Number of non-clone pairs']
    # y_labels = ['', '']
    text_x_coord = [THRESHOLD-0.42, THRESHOLD+0.04]
    line_text = ['Threshold = ' + str(THRESHOLD), '']
    data = [clone_sim, non_clone_sim]

    axes = axes.ravel()
    for idx, ax in enumerate(axes):
        ax.hist(data[idx], bins=40, edgecolor='white', color='teal')    # color='cadetblue'
        ax.set_title(titles[idx], size=16)
        ax.set_xlabel(x_labels[idx], size=12)
        ax.set_ylabel(y_labels[idx], size=12)
        ax.set_xticks(np.arange(-1, 1.1, 0.25))
        ax.axvline(THRESHOLD, linestyle=':', alpha=0.5, linewidth=2, ymax=1, color='darkred')
        ax.text(text_x_coord[idx], ax.get_ylim()[-1] * 0.75, line_text[idx], color='darkred', size=12)
        ax.grid(False)
    plt.tight_layout()
    plt.savefig(CLASSIFIER_NAME+ '_' + str(NUM_CLASSES) + '_' + str(THRESHOLD)+'.jpg')
    # plt.savefig(CLASSIFIER_NAME+ '_' + str(NUM_CLASSES) + '_' + str(THRESHOLD)+'.eps', format='eps')
    
    # print(np.percentile(non_clone_sim, 85))
    # print(np.percentile(clone_sim, 20))

    ## Code to have separate figures for clone and non_clone pairs. 
    # plt.rcParams.update({'figure.figsize':(7,5), 'figure.dpi':600})

    # plt.hist(clone_sim.numpy(), bins=40, edgecolor = "black")
    # plt.gca().set(title=CLASSIFIER_NAME+' - True Clones', ylabel='Frequency', xlabel='Cosine similarity score', xticks=np.arange(-1, 1.1, 0.25))
    # plt.axvline(THRESHOLD, linestyle=':', alpha=1, linewidth=1)
    # plt.grid(False)
    # plt.savefig(CLASSIFIER_NAME+'_clones.jpg')
    
    # plt.clf()
    
    # plt.hist(non_clone_sim.numpy(), bins=40, edgecolor = "black")
    # plt.gca().set(title=CLASSIFIER_NAME+' - False Clones', ylabel='Frequency', xlabel='Cosine similarity score', xticks=np.arange(-1, 1.1, 0.25))
    # plt.axvline(THRESHOLD, linestyle=':', alpha=1, linewidth=1)
    # plt.grid(False)
    # plt.savefig(CLASSIFIER_NAME+'_non_clones.jpg')

def calculate_metrics(clone_sim, non_clone_sim):
    num_clone_pairs = clone_sim.shape[0] if len(clone_sim.shape) > 0 else 0
    num_non_clone_pairs = non_clone_sim.shape[0] if len(non_clone_sim.shape) > 0 else 0
    total_examples = num_clone_pairs + num_non_clone_pairs

    clone_preds = tf.math.greater(clone_sim, THRESHOLD)
    true_positives = tf.reduce_sum(tf.cast(clone_preds, tf.int32)).numpy()
    print("True Positives", true_positives)

    false_negatives = num_clone_pairs - true_positives
    print("False Negatives", false_negatives)

    non_clone_preds = tf.math.less(non_clone_sim, THRESHOLD)
    # non_clone_preds = tf.math.less_equal(non_clone_sim, THRESHOLD)
    true_negatives = tf.reduce_sum(tf.cast(non_clone_preds, tf.int32)).numpy()
    print("True Negatives", true_negatives)

    false_positives = num_non_clone_pairs - true_negatives
    print("False Positives: ", false_positives)

    accuracy = (true_positives + true_negatives) / total_examples
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\nAccuracy: ", accuracy)
    print("Precision: ", precision)
    print("Recall: ", recall)
    print("F1: ", f1)

    return {'acc': accuracy, 'prec': precision, 'recall': recall, 'f1': f1}


# Script expects a .csv file that has (label, vector) pair on each line. label and vector separated with a space.
# Each label is the class (id) to which code snippet belongs to. Expects 1-indexed class numbers - [1, NUM_CLASSES].
# python3 clone_detection.py
if __name__ == '__main__':
    args = dict(arg.split('=') for arg in sys.argv[1:])

    # Upper case constants are defined at module-level.
    code_vectors_file = args['path'] if 'path' in args else 'code_vectors.csv'
    CLASSIFIER_NAME = args['name'] if 'name' in args else 'AST + CFG + PDG'
    NUM_RUNS = int(args['iters']) if 'iters' in args else 3
    THRESHOLD = float(args['threshold']) if 'threshold' in args else 0.5
    NUM_CLASSES = int(args['num_classes']) if 'num_classes' in args else 104
    MAX_CLONE_PAIRS = int(args['max_clone_pairs']) if 'max_clone_pairs' in args else 50000
    MAX_NON_CLONE_PAIRS = int(args['max_non_clone_pairs']) if 'max_non_clone_pairs' in args else 50000

    # plot_similarity_scores()
    # exit(0)

    CLASS_SET = []      # This contains the set of all classes that are part of dataset.
    data_dict = read_csv_file(code_vectors_file)

    # Calculate metrics for NUM_RUNS iterations, and calculate the average scores.
    metrics = {'acc': 0, 'prec': 0, 'recall': 0, 'f1': 0}
    for i in range(NUM_RUNS):
        print("\nITERATION {}:".format(i+1))
        clone_pairs = generate_clone_pairs(data_dict)
        non_clone_pairs = generate_non_clone_pairs(data_dict)

        clone_sim = calculate_cossim(clone_pairs)
        non_clone_sim = calculate_cossim(non_clone_pairs)

        plot_similarity_scores(clone_sim.numpy(), non_clone_sim.numpy())

        curr_metrics = calculate_metrics(clone_sim, non_clone_sim)
        for metric, val in curr_metrics.items():
            metrics[metric] += val

    # Calculate the average scores.
    for metric, val in metrics.items():
        metrics[metric] /= NUM_RUNS

    print("\nAVERAGE METRICS OVER {} ITERATIONS:".format(NUM_RUNS))
    print("Accuracy: ", metrics['acc'])
    print("Precision: ", metrics['prec'])
    print("Recall: ", metrics['recall'])
    print("F1: ", metrics['f1'])