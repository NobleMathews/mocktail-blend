import configparser
import pickle
import os


# This function is taken from code2vec (https://github.com/tech-srl/code2vec/blob/master/extractor.py)
def java_string_hashcode(s):
    """
        Imitating Java's String#hashCode, because the model is trained on hashed paths but we wish to
        Present the path attention on un-hashed paths.
        """
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def update_freq_dict(freq_dict, word):
    if word in freq_dict:
        freq_dict[word] += 1
    else:
        freq_dict[word] = 1


def create_dictionaries(input_file, output_file, token_freq_dict, path_freq_dict, target_freq_dict,
                        num_training_examples):
    with open(input_file, 'r', encoding='utf-8') as fin:
        for line in fin:
            fields = line.strip('\n').split(' ')

            update_freq_dict(target_freq_dict, fields[0])

            for path_context in fields[1:]:
                if path_context != '':
                    try:
                        start_token, path, end_token = path_context.split(',')
                        update_freq_dict(token_freq_dict, start_token)
                        update_freq_dict(path_freq_dict, path)
                        update_freq_dict(token_freq_dict, end_token)
                    except Exception as e:
                        print(e)
    with open(output_file, 'wb') as f:
        pickle.dump(token_freq_dict, f)
        pickle.dump(path_freq_dict, f)
        pickle.dump(target_freq_dict, f)
        pickle.dump(num_training_examples, f)


# noinspection PyUnusedLocal
def save_dictionaries(output_file, hash_to_string_dict, token_freq_dict, path_freq_dict, target_freq_dict, outputType,
                      num_training_examples):
    if os.path.isfile(output_file) and outputType != "file":
        print("{} already exist!".format(output_file))
        return

    with open(output_file, 'wb') as f:
        token_freq_dict_old = {}
        path_freq_dict_old = {}
        target_freq_dict_old = {}
        count = 0
        #  and outputType == "file"
        if os.path.isfile(output_file):
            if os.stat(output_file).st_size != 0:
                with open(output_file, 'rb') as fo:
                    token_freq_dict_old = pickle.load(fo)
                    path_freq_dict_old = pickle.load(fo)
                    target_freq_dict_old = pickle.load(fo)
                    count = pickle.load(fo)
        # token_freq_dict_old.update(token_freq_dict)
        # path_freq_dict_old.update(path_freq_dict)
        # target_freq_dict_old.update(target_freq_dict)
        # count = count + num_training_examples

        pickle.dump({k: token_freq_dict_old.get(k, 0) + token_freq_dict.get(k, 0) for k in
                     set(token_freq_dict_old) | set(token_freq_dict)}, f)
        pickle.dump({k: token_freq_dict_old.get(k, 0) + path_freq_dict.get(k, 0) for k in
                     set(path_freq_dict_old) | set(path_freq_dict)}, f)
        pickle.dump({k: token_freq_dict_old.get(k, 0) + target_freq_dict.get(k, 0) for k in
                     set(target_freq_dict_old) | set(target_freq_dict)}, f)
        pickle.dump(count + num_training_examples, f)

    # with open("path_dict.txt", 'w', encoding="utf-8") as f:
    #     for hashed_path, context_path in hash_to_string_dict.items():
    #         f.write(hashed_path + '\t' + context_path + '\n')

    print('Dictionaries saved to: {}'.format(output_file))


def split_dataset(output_dir, dataset_name, num_examples, train_split, test_split, val_split):
    full_shuffled_file = os.path.join(output_dir, '{}.full.shuffled.txt'.format(dataset_name))
    train_file = os.path.join(output_dir, '{}.train.txt'.format(dataset_name))
    test_file = os.path.join(output_dir, '{}.test.txt'.format(dataset_name))
    val_file = os.path.join(output_dir, '{}.val.txt'.format(dataset_name))

    if os.path.isfile(train_file) and os.path.isfile(test_file) and os.path.isfile(val_file):
        print("Reusing the existing Train-Test-Val splits to generate dataset ..")
        return
    train_index = round(num_examples * train_split)
    val_index = round(num_examples * val_split) + train_index
    test_index = round(num_examples * test_split) + val_index
    print("Total number of Train Examples: ", train_index)
    print("Total number of Val Examples: ", val_index - train_index)
    print("Total number of Test Examples: ", test_index - val_index)
    line_count = 0
    with open(train_file, 'w') as fo0:
        with open(val_file, 'w') as fo1:
            with open(test_file, 'w') as fo2:
                with open(full_shuffled_file, 'r', encoding="utf-8") as fin:
                    for line in fin:
                        line_count += 1
                        if line_count <= train_index:
                            fo0.write(line)
                        elif train_index < line_count <= val_index:
                            fo1.write(line)
                        elif val_index < line_count <= test_index:
                            fo2.write(line)


# noinspection PyUnusedLocal
def filter_paths(input_file, output_file, collate_file, include_paths, max_path_count, outputType):
    # if os.path.isfile(output_file):
    #     print("{} already exists!".format(output_file))
    #     return

    total_valid_examples = 0
    with open(collate_file, 'a', encoding="utf-8") as cout:
        with open(output_file, 'a', encoding="utf-8") as fout:
            with open(input_file, 'r', encoding="utf-8") as fin:
                for line in fin:
                    fields = line.strip('\n').split(' ')
                    label = fields[0]
                    ast_paths = fields[1: (max_path_count['ast'] + 1)]
                    cfg_paths = fields[(max_path_count['ast'] + 1): (max_path_count['ast'] + max_path_count['cfg'] + 1)]
                    cdg_paths = fields[(max_path_count['ast'] + max_path_count['cfg'] + 1): (
                            max_path_count['ast'] + max_path_count['cfg'] + max_path_count['cdg'] + 1)]
                    ddg_paths = fields[(max_path_count['ast'] + max_path_count['cfg'] + max_path_count['cdg'] + 1): (
                            max_path_count['ast'] + max_path_count['cfg'] + max_path_count['cdg'] + max_path_count['ddg'] + 1)]

                    valid_example = True
                    output = label
                    if include_paths['ast']:
                        output += (' ' + ' '.join(ast_paths))
                    if include_paths['cfg'] and valid_example:
                        output += (' ' + ' '.join(cfg_paths))
                    if include_paths['cdg'] and valid_example:
                        output += (' ' + ' '.join(cdg_paths))
                    if include_paths['ddg'] and valid_example:
                        output += (' ' + ' '.join(ddg_paths))

                    fout.write(output + '\n')
                    # if outputType == "file":
                    cout.write(output + '\n')
                    if output.strip():
                        total_valid_examples += 1

    print("Number of Valid Examples in {file}: {count}".format(file=output_file, count=total_valid_examples))


def convert_to_model_input_format(input_file, output_file, max_paths, not_include_methods, hash_to_string_dict):
    if os.path.isfile(output_file):
        print("{} already exists!".format(output_file))
        return sum(1 for line in open(output_file, 'r', encoding='utf-8') if line.strip() != '')

    total_valid_examples = 0  # Total valid examples (valid --> example with valid non-empty label)
    empty_examples = 0
    startToken = ''
    path = ''
    endToken = ''
    flag = 0
    current_row = ''
    first_example = True
    valid_example = False

    total_path_count = {'ast': 0, 'cfg': 0, 'cdg': 0, 'ddg': 0}
    current_path_count = {'ast': 0, 'cfg': 0, 'cdg': 0, 'ddg': 0}
    current_counter = 'ast'

    with open(output_file, 'a', encoding="utf-8") as fout:
        with open(input_file, 'r', encoding="utf-8") as f:
            for line in f:
                if line.startswith("label:"):
                    if current_counter == 'ddg' and valid_example:
                        current_row += (' ' * (max_paths['ddg'] - current_path_count['ddg'] - 1))
                        fout.write(current_row)
                        total_valid_examples += 1

                        total_path_count['ddg'] += current_path_count['ddg']
                        current_path_count['ddg'] = 0

                    current_row = ''
                    label = line[6:].strip('\n\t ')
                    if (not label) or (label in not_include_methods):
                        valid_example = False
                        empty_examples += 1
                        continue
                    else:
                        valid_example = True
                        if first_example:
                            current_row += (label + ' ')
                            first_example = False
                        else:
                            current_row += ('\n' + label + ' ')  # \t or ' '

                elif not line.strip() or line.startswith("#") or line.startswith("file:"):
                    continue

                elif line.startswith("path: ast") and valid_example:
                    current_counter = 'ast'

                elif (line.startswith("path: cfg") or line.startswith("path: cdg") or line.startswith(
                        "path: ddg")) and valid_example:
                    current_row += (' ' * (max_paths[current_counter] - current_path_count[current_counter] - 1))
                    total_path_count[current_counter] += current_path_count[current_counter]
                    current_path_count[current_counter] = 0

                    current_counter = line.lstrip('path: \n\t').rstrip(' \n\t')
                    current_row += ' '  # \t or ' '

                else:
                    if (not valid_example) or (current_path_count[current_counter] >= max_paths[current_counter]):
                        continue

                    pathContext = line.split('\t')

                    # Special Case.
                    if len(pathContext) == 2:
                        if flag == 0:
                            startToken = pathContext[0].strip()
                            path = pathContext[1].strip()
                            flag = 1
                            continue
                        elif flag == 1:
                            path = path + pathContext[0].replace('\\n', '').strip()
                            endToken = pathContext[1].strip()
                            print(startToken, path, endToken)
                            print()
                            flag = 0

                    elif len(pathContext) == 3:
                        startToken = pathContext[0].strip()
                        path = pathContext[1].strip()
                        endToken = pathContext[2].strip()

                    else:
                        continue

                    if (not startToken) or (not path) or (not endToken):
                        continue

                    hashed_path = str(java_string_hashcode(path))
                    hash_to_string_dict[hashed_path] = path
                    current_row += (startToken + ',' + hashed_path + ',' + endToken)
                    current_path_count[current_counter] += 1

                    if current_path_count[current_counter] < max_paths[current_counter]:
                        current_row += ' '

        if valid_example:
            current_row += (' ' * (max_paths[current_counter] - current_path_count[current_counter] - 1))
            total_path_count[current_counter] += current_path_count[current_counter]
            current_path_count[current_counter] = 0

            fout.write(current_row + '\n')
            total_valid_examples += 1

    print('File: ' + input_file)
    print('Valid examples: ' + str(total_valid_examples))
    print('Empty/Bad Label examples: ' + str(empty_examples))
    print('Average Path Count: ')
    for rep, count in total_path_count.items():
        print(rep, count / total_valid_examples)

    return total_valid_examples

# if __name__ == '__main__':
#     hash_to_string_dict = {}
#     token_freq_dict = {}
#     path_freq_dict = {}
#     target_freq_dict = {}

#     include_paths = {'ast':False, 'cfg':False, 'cdg':False, 'ddg':False}
#     max_path_count = {'ast':0, 'cfg':0, 'cdg':0, 'ddg':0}

#     config = configparser.ConfigParser()
#     config.read("config.ini")
#     input_dir = config['outputFormatter']['inputDirectory']
#     datasets = config['outputFormatter']['datasets']
#     datasets = [dataset.strip() for dataset in datasets.split(',')]
#     output_dir = config['outputFormatter']['outputDirectory']
#     dataset_name_ext = config['outputFormatter']['datasetNameExtension']
#     not_include_methods = config['outputFormatter']['notIncludeMethods']
#     not_include_methods = [method.strip() for method in not_include_methods.split(',')]

#     include_paths['ast'] = config['outputFormatter'].getboolean('includeASTPaths')
#     include_paths['cfg'] = config['outputFormatter'].getboolean('includeCFGPaths')
#     include_paths['cdg'] = config['outputFormatter'].getboolean('includeCDGPaths')
#     include_paths['ddg'] = config['outputFormatter'].getboolean('includeDDGPaths')

#     max_path_count['ast'] = config['outputFormatter'].getint('maxASTPaths')
#     max_path_count['cfg'] = config['outputFormatter'].getint('maxCFGPaths')
#     max_path_count['cdg'] = config['outputFormatter'].getint('maxCDGPaths')
#     max_path_count['ddg'] = config['outputFormatter'].getint('maxDDGPaths')

#     ## For normal Train-Test-Val split.
#     for dataset_name in datasets:
#         destination_dir = os.path.join(output_dir, dataset_name, dataset_name_ext)
#         data_path = os.path.join(input_dir, dataset_name + ".txt")
#         os.makedirs(destination_dir, exist_ok=True)

#         ## Convert the input data file into model input format. Takes only "max_path_count" number of paths for each type. Removes the "not_include_methods" methods.
#         num_examples = convert_to_model_input_format(data_path, os.path.join(output_dir, dataset_name, "{}.txt".format(dataset_name + '.full')), max_path_count, not_include_methods, hash_to_string_dict)

#         ## Shuffle the output file of above step.
#         if os.path.isfile(os.path.join(output_dir, dataset_name, '{}.full.shuffled.txt'.format(dataset_name))):
#             print("{} already exists!".format(os.path.join(output_dir, dataset_name, '{}.full.shuffled.txt'.format(dataset_name))))
#         else:
#             os.system('./terashuf < {output_dir}/{dataset_name}/{dataset_name}.full.txt > {output_dir}/{dataset_name}/{dataset_name}.full.shuffled.txt'.format(output_dir=output_dir, dataset_name=dataset_name))

#         ## Splitting the joined and shuffled file into Train-Test-Val sets.
#         split_dataset(os.path.join(output_dir, dataset_name), dataset_name, num_examples)

#         ## Use "include_paths" to select specific type of paths.
#         filter_paths(os.path.join(output_dir, dataset_name, '{}.train.txt'.format(dataset_name)), os.path.join(destination_dir, '{}.train.txt'.format(dataset_name + '_' + dataset_name_ext)), include_paths, max_path_count)
#         filter_paths(os.path.join(output_dir, dataset_name, '{}.test.txt'.format(dataset_name)), os.path.join(destination_dir, '{}.test.txt'.format(dataset_name + '_' + dataset_name_ext)), include_paths, max_path_count)
#         filter_paths(os.path.join(output_dir, dataset_name, '{}.val.txt'.format(dataset_name)), os.path.join(destination_dir, '{}.val.txt'.format(dataset_name + '_' + dataset_name_ext)), include_paths, max_path_count)

#         ## Create dictionaries using training data.
#         create_dictionaries(os.path.join(destination_dir, '{}.train.txt'.format(dataset_name + '_' + dataset_name_ext)), token_freq_dict, path_freq_dict, target_freq_dict)

#         ## Save the dictionary file.
#         save_dictionaries(os.path.join(destination_dir, '{}.dict.txt'.format(dataset_name + '_' + dataset_name_ext)), hash_to_string_dict, token_freq_dict, path_freq_dict, target_freq_dict, round(num_examples * 0.89))

#         # os.remove(os.path.join(output_dir, dataset_name + '.full.txt'))
#         # os.remove(os.path.join(output_dir, dataset_name + '.full.shuffled.txt'))
