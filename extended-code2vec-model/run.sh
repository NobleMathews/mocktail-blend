#!/usr/bin/env bash
###########################################################
# Change the following values to train and test a new model.
# type: its typically the representations included in the dataset, used in name of the dataset.
# dataset: the name of the dataset.
###########################################################
# These values cannot be changed. 
# This expects the data files with fixed names and in fixed paths based on `type` and `dataset` variables.
# data_dir: main directory in which all train-test-val splits reside.
# data: This is the name prefix of all the train-test-val splits and the dictionary file.
# val_data: points to the validation set. This is the set that will be evaluated after each training iteration.
# test_data: points to the test set

type=ast_cfg_ddg
dataset_name=testdata
data_dir=data/${dataset_name}/${type}
data=${data_dir}/${dataset_name}_${type}
val_data=${data_dir}/${dataset_name}_${type}.val.txt
test_data=${data_dir}/${dataset_name}_${type}.test.txt
model_dir=models/${dataset_name}/${type}

mkdir -p ${model_dir}
set -e
## Training and evaluating the model on training and validation data.
python3 -u main.py --export_code_vectors --task method_naming --num_classes 104 --reps ast cfg ddg --max_contexts '{"ast":"200", "cfg":"10", "ddg":"100"}' --data ${data} --test ${val_data} --save ${model_dir}/saved_model

## Evaluate a trained model on test data (by loading the model)
# python3 -u main.py --export_code_vectors --task method_naming --num_classes 104 --reps ast cfg ddg --max_contexts '{"ast":"200", "cfg":"10", "ddg":"100"}' --load ${model_dir}/saved_model --test ${test_data}
