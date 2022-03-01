import glob
import math
from pkgutil import iter_modules
import psutil
import ray
from projectPreprocessor.process_files import *
from pathExtractor.generate_dataset import *
from output_formatter import *
from questionary import Choice
from pathlib import Path
import configparser
import questionary
import os
from shutil import rmtree, which

# find . -name '*.txt' -exec sh -c 'mv "$0" "${0%.txt}.c"' {} \;
# Reading the configuration parameters from config.ini file.
config = configparser.ConfigParser()
dirname = os.path.dirname(os.path.realpath(__file__))
config.read(os.path.join(dirname, "config.ini"))

in_path = "./1_input"
process_path = "./2_processed"
output_dir = "./3_output"

# dot -Tpng 0-ast.dot -o 0-ast.png
numOfProcesses = psutil.cpu_count()
num_cpus = psutil.cpu_count(logical=False)
outputType = config['projectPreprocessor']['outputType']
generateAll = config['pathExtractor'].getboolean('generateAll')
train_split = config['outputFormatter'].getfloat('train_split')
test_split = config['outputFormatter'].getfloat('test_split')
val_split = config['outputFormatter'].getfloat('val_split')
useCheckpoint = config['pathExtractor'].getboolean('useCheckpoint')

def checks():
    # if os.getuid() == 0:
    #     raise Exception("This program requires to be run as root but was called by " + getpass.getuser())
    for dependency in ["joern", "terashuf"]:
        if which(dependency) is None:
            raise Exception("Check whether " + dependency + " is on PATH and marked as executable.")
    modules = set(x[1] for x in iter_modules())
    with open(os.path.join(dirname, './requirements.txt'), 'r') as fr:
        for line in fr:
            requirement = line.split("=")[0].strip()
            if requirement not in modules:
                raise Exception("Missing dependency: " + requirement)
    if not Path.exists(Path(os.path.join(dirname, in_path))):
        raise Exception("Missing input directory, please update config.ini")
    if not Path.exists(Path(os.path.join(dirname, process_path))):
        print("Created missing processing directory")
        os.makedirs(Path(os.path.join(dirname, process_path)))
    if not Path.exists(Path(os.path.join(dirname, output_dir))):
        print("Created missing output directory")
        os.makedirs(Path(os.path.join(dirname, output_dir)))
    if not questionary.confirm(
            "Have you updated config with required details ? Also please manually clear the processed and output folder if fresh run").ask():
        raise Exception("Please update and confirm config file contents")


def divide(lst, n):
    p = len(lst) // n
    if len(lst) - p > 0:
        return [lst[:p]] + divide(lst[p:], n - 1)
    else:
        return [lst]


def get_file_indices(in_path_f, num_of_processes):
    # Divide the work between processes.
    totalFiles = os.listdir(in_path_f)
    return divide(totalFiles, num_of_processes)


def pre_process():
    # print({section: dict(config[section]) for section in config.sections()})
    maxFileSize = config['projectPreprocessor'].getint('maxFileSize')

    intermediate_path = os.path.join(dirname, in_path, "_temp_file_dir_")
    if os.path.exists(intermediate_path):
        rmtree(intermediate_path)
    os.mkdir(intermediate_path)

    try:
        filter_files(in_path, intermediate_path)
        if outputType == "method":
            split_files_into_functions_multiple(intermediate_path, process_path, maxFileSize)
        elif outputType == "file":
            filter_files(in_path, process_path)
        # DEPRECATED - use method instead as it is mostly similar
        elif outputType == "single":
            split_files_into_functions_single(intermediate_path, os.path.join(process_path, "single"), maxFileSize)

    except Exception as e:
        raise Exception(e)

    finally:
        rmtree(intermediate_path)
        for filename in glob.glob("./_temp_*"):
            rmtree(filename)


def process(dataset_name, include_paths_l):
    maxPathContexts = config['pathExtractor'].getint('maxPathContexts')
    maxLength = config['pathExtractor'].getint('maxLength')
    maxWidth = config['pathExtractor'].getint('maxWidth')
    maxTreeSize = config['pathExtractor'].getint('maxTreeSize')
    maxFileSize = config['pathExtractor'].getint('maxFileSize')
    separator = config['pathExtractor']['separator']
    splitToken = config['pathExtractor'].getboolean('splitToken')
    upSymbol = config['pathExtractor']['upSymbol']
    downSymbol = config['pathExtractor']['downSymbol']
    labelPlaceholder = config['pathExtractor']['labelPlaceholder']
    useParentheses = config['pathExtractor'].getboolean('useParentheses')

    # Divide the work between processes.
    processFileIndices = get_file_indices(os.path.join(process_path, dataset_name), numOfProcesses)

    # This is used to track what files were processed already by each process. Used in checkpointing.
    initialCount = 0
    checkpointDict = {}
    for processIndex in range(numOfProcesses):
        checkpointDict[processIndex] = set()

    # If the output files already exist, either use it as a checkpoint or don't continue the execution.
    if os.path.isfile(os.path.join(process_path, dataset_name, dataset_name + ".txt")):
        if useCheckpoint:
            print(dataset_name + ".txt file exists. Using it as a checkpoint ...")
            with open(os.path.join(process_path, dataset_name, dataset_name + ".txt"), 'r') as fc:
                for line in fc:
                    if line.startswith("file:"):
                        fileIndex = line.strip('file:\n\t ')
                        for processIndex, filesRange in enumerate(processFileIndices):
                            if fileIndex in filesRange:
                                checkpointDict[processIndex].add(fileIndex)
                                initialCount += 1
                                break
            initialCount += 1

        else:
            print(dataset_name + ".txt file already exist. Exiting ...")
            sys.exit()

    # Create the argument collection, where each element contains the array of parameters for each process.
    # noinspection PyTypeChecker
    ProcessArguments = (
        [process_path, dataset_name, outputType] + [FileIndices] + [checkpointDict[processIndex]] + [maxPathContexts,
                                                                                                     maxLength,
                                                                                                     maxWidth,
                                                                                                     maxTreeSize,
                                                                                                     maxFileSize,
                                                                                                     splitToken,
                                                                                                     separator,
                                                                                                     upSymbol,
                                                                                                     downSymbol,
                                                                                                     labelPlaceholder,
                                                                                                     useParentheses,
                                                                                                     generateAll,
                                                                                                     include_paths_l]
        for
        processIndex, FileIndices in enumerate(processFileIndices))

    # # Start executing multiple processes.
    # with mp.Pool(processes = numOfProcesses) as pool:
    #     pool.map(generate_dataset, ProcessArguments)
    ray.init(num_cpus=num_cpus)
    # , log_to_driver=False
    tasks_pre = [generate_dataset.remote(x) for x in ProcessArguments]
    ray.get(tasks_pre)

    for filename in glob.glob("./_temp_*"):
        # print(filename)
        rmtree(filename)
    ray.shutdown()


def post_process(options):
    hash_to_string_dict = {}
    token_freq_dict = {}
    path_freq_dict = {}
    target_freq_dict = {}

    include_paths_dict = {'ast': "AST" in options, 'cfg': "CFG" in options, 'cdg': "CDG" in options,
                          'ddg': "DDG" in options}
    max_path_count = {'ast': 0, 'cfg': 0, 'cdg': 0, 'ddg': 0}
    dataset_name_ext = '_'.join(options)
    datasets = [folder.name for folder in os.scandir("./2_processed") if folder.is_dir()]
    not_include_methods = config['outputFormatter']['notIncludeMethods']
    not_include_methods = [method.strip() for method in not_include_methods.split(',')]

    max_path_count['ast'] = config['outputFormatter'].getint('maxASTPaths')
    max_path_count['cfg'] = config['outputFormatter'].getint('maxCFGPaths')
    max_path_count['cdg'] = config['outputFormatter'].getint('maxCDGPaths')
    max_path_count['ddg'] = config['outputFormatter'].getint('maxDDGPaths')

    # For normal Train-Test-Val split.
    for dataset_name in datasets:
        try:
            destination_dir = os.path.join(output_dir, dataset_name, dataset_name_ext)
            data_path = os.path.join(process_path, dataset_name, dataset_name + ".txt")
            os.makedirs(destination_dir, exist_ok=True)

            # Convert the input data file into model input format. Takes only "max_path_count" number of paths for each type. Removes the "not_include_methods" methods.
            num_examples = convert_to_model_input_format(data_path, os.path.join(output_dir, dataset_name,
                                                                                 "{}.txt".format(
                                                                                     dataset_name + '.full')),
                                                         max_path_count, not_include_methods, hash_to_string_dict)

            # Shuffle the output file of above step.
            if os.path.isfile(os.path.join(output_dir, dataset_name, '{}.full.shuffled.txt'.format(dataset_name))):
                # print("{} already exists!".format(
                os.path.join(output_dir, dataset_name, '{}.full.shuffled.txt'.format(dataset_name))
                #     ))
            else:
                os.system(
                    'terashuf < {output_dir}/{dataset_name}/{dataset_name}.full.txt 1> {output_dir}/{dataset_name}/{dataset_name}.full.shuffled.txt 2> /dev/null'.format(
                        output_dir=output_dir, dataset_name=dataset_name))

            # Splitting the joined and shuffled file into Train-Test-Val sets.
            split_dataset(os.path.join(output_dir, dataset_name), dataset_name, num_examples, train_split, test_split, val_split)

            # Use "include_paths" to select specific type of paths.
            filter_paths(os.path.join(output_dir, dataset_name, '{}.train.txt'.format(dataset_name)),
                         os.path.join(destination_dir, '{}.train.txt'.format(dataset_name + '_' + dataset_name_ext)),
                         os.path.join(output_dir, '{}.train.txt'.format(dataset_name_ext)),
                         include_paths_dict, max_path_count, outputType)
            filter_paths(os.path.join(output_dir, dataset_name, '{}.test.txt'.format(dataset_name)),
                         os.path.join(destination_dir, '{}.test.txt'.format(dataset_name + '_' + dataset_name_ext)),
                         os.path.join(output_dir, '{}.test.txt'.format(dataset_name_ext)),
                         include_paths_dict, max_path_count, outputType)
            filter_paths(os.path.join(output_dir, dataset_name, '{}.val.txt'.format(dataset_name)),
                         os.path.join(destination_dir, '{}.val.txt'.format(dataset_name + '_' + dataset_name_ext)),
                         os.path.join(output_dir, '{}.val.txt'.format(dataset_name_ext)),
                         include_paths_dict, max_path_count, outputType)

            # Create dictionaries using training data.
            create_dictionaries(
                os.path.join(destination_dir, '{}.train.txt'.format(dataset_name + '_' + dataset_name_ext)),
                os.path.join(destination_dir, '{}.dict.txt'.format(dataset_name + '_' + dataset_name_ext)),
                token_freq_dict, path_freq_dict, target_freq_dict, round(num_examples * train_split))

            # Save the dictionary file.
            # if outputType == "file":
            save_dictionaries(os.path.join(output_dir, '{}.dict.txt'.format(dataset_name_ext)),
                              hash_to_string_dict, token_freq_dict, path_freq_dict, target_freq_dict, outputType,
                              round(num_examples * train_split))
        except Exception as e:
            print(e)


if __name__ == "__main__":
    try:
        checks()
    except Exception as err:
        raise SystemExit(err)
    joblist = questionary.checkbox(
        "Select actions to perform",
        choices=[Choice("Preprocess project", checked=True), Choice("Path extraction", checked=True),
                 Choice("Format output", checked=True)],
    ).ask()
    include_paths = questionary.checkbox(
        "Select paths to include",
        choices=[Choice("AST", checked=True), Choice("CFG", checked=True), Choice("CDG", checked=False),
                 Choice("DDG", checked=True)],
    ).ask()
    if "Preprocess project" in joblist:
        if os.path.exists("time_summary.txt"):
            with open("time_summary.txt", 'w') as f2:
                pass
        if useCheckpoint:
            if len(os.listdir(process_path)) == 0:
                pre_process()
            else:
                print("Processing directory is not empty and useCheckpoint is True, preprocess is being skipped to prevent loss of checkpoints!")
        else:
            if os.path.exists("time.txt"):
                with open("time.txt", 'w') as f1:
                    pass
            pre_process()
    if "Path extraction" in joblist:
        for f in os.scandir("./2_processed"):
            if f.is_dir():
                process(f.name, include_paths)
            if os.path.exists("time.txt"):
                with open("time.txt", 'r') as f1:
                    fpm = 0
                    total_time = 0
                    for time_used in f1:
                        time_used = time_used.strip()
                        fpm = fpm + (1 / float(time_used))
                        # total time for a dataset
                        total_time = total_time + float(time_used)
                    pass
                with open(output_dir + '/' + 'time_summary.txt', 'a+') as fileO:
                    fileO.write(str(total_time) + " per_dataset->fpm " + str(fpm) + "\n")
                os.rename('time.txt', output_dir + '/' + f.name + '_time.txt')

    if "Format output" in joblist:
        post_process(include_paths)
