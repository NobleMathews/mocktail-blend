import os
import sys
from shutil import copy, rmtree
from projectPreprocessor.utils import *


# Filter the C/C++ source files and copy to the Dataset folder.
def filter_files(in_path, out_path):
    projectDirs = [name for name in os.listdir(os.path.join(in_path)) if
                   os.path.isdir(os.path.join(in_path, name)) and name != "_temp_file_dir_"]

    # For each project directory, extract all C files and save in corresponding project folder in out_path.
    for dir in projectDirs:
        for root, dirs, files in os.walk(os.path.join(in_path, dir)):
            for file in files:
                if file.endswith(".cpp") or file.endswith(".CPP") or file.endswith(".c++") or file.endswith(
                        ".cp") or file.endswith(".cxx") or \
                        file.endswith(".hpp") or file.endswith(".HPP") or file.endswith(".c") or file.endswith(
                    ".h") or file.endswith(".C") or file.endswith(".cc"):
                    in_file_path = os.path.join(root, file)

                    # Replicate the same folder structure in out_path.
                    # C:\Users\karthik chandra\Downloads\Dataset\C\borg-master\scripts\fuzz-cache-sync\main.c
                    out_file_path = os.path.join(out_path, in_file_path.replace(in_path, "")[1:])
                    os.makedirs(os.path.dirname(out_file_path), exist_ok=True)

                    # Get the path without the file name in the end. (For example, without \main.c in the above path.)
                    # C:\Users\karthik chandra\Downloads\Dataset\C\borg-master\scripts\fuzz-cache-sync
                    out_file_path = os.path.dirname(os.path.abspath(out_file_path))

                    try:
                        copy(in_file_path, out_file_path)
                    except OSError as e:
                        continue


# Splits all the files in in_path directory to functions and outputs them in out_path folder repository wise (each repository has saperate folder).
def split_files_into_functions_multiple(in_path, out_path, maxFileSize):
    projectDirs = [name for name in os.listdir(os.path.join(in_path)) if os.path.isdir(os.path.join(in_path, name))]
    os.makedirs(out_path, exist_ok=True)

    # For each project directory, extract all C functions and save in corresponding project folder in out_path.
    for dir in projectDirs:
        i = 0
        fin_path = os.path.join(out_path, dir)
        if os.path.exists(fin_path):
            rmtree(fin_path)
        os.mkdir(fin_path)

        for root, dirs, files in os.walk(os.path.join(in_path, dir)):
            for file in files:
                in_file_path = os.path.join(root, file)
                code = preprocess_cfile(in_file_path)
                names, functions = extract_functions_from_file(code)
                for function, name in zip(functions, names):
                    # print(i, in_file_path)

                    # Filter files as per the max size requirement.
                    if sys.getsizeof(function) > maxFileSize:
                        continue

                    with open(os.path.join(out_path, dir, name + "_mocktail_" + str(i) + ".c"), "w",
                              encoding='utf-8') as fileW:
                        fileW.write(function)
                    i += 1


# Splits all the files in in_path directory to functions and outputs them in out_path folder.
def split_files_into_functions_single(in_path, out_path, maxFileSize):
    os.makedirs(out_path, exist_ok=True)
    i = 0
    for root, dirs, files in os.walk(in_path):
        for file in files:
            in_file_path = os.path.join(root, file)

            code = preprocess_cfile(in_file_path)
            names, functions = extract_functions_from_file(code)

            for name, function in zip(names, functions):
                # print(i, in_file_path)

                # Filter files as per the max size requirement.
                if sys.getsizeof(function) > maxFileSize:
                    continue

                with open(os.path.join(out_path, name + "_mocktail_" + str(i) + ".c"), "w", encoding='utf-8') as fileW:
                    fileW.write(function)
                i += 1
