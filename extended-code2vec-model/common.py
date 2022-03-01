import re
import numpy as np
import tensorflow as tf
from itertools import takewhile, repeat
from typing import List, Optional, Tuple, Iterable
from datetime import datetime
from collections import OrderedDict


class common:

    @staticmethod
    def normalize_word(word):
        stripped = re.sub(r'[^a-zA-Z]', '', word)
        if len(stripped) == 0:
            return word.lower()
        else:
            return stripped.lower()

    @staticmethod
    def save_word2vec_file(output_file, index_to_word, vocab_embedding_matrix: np.ndarray):
        assert len(vocab_embedding_matrix.shape) == 2
        vocab_size, embedding_dimension = vocab_embedding_matrix.shape
        output_file.write('%d %d\n' % (vocab_size, embedding_dimension))
        for word_idx in range(0, vocab_size):
            assert word_idx in index_to_word
            word_str = index_to_word[word_idx]
            output_file.write(word_str + ' ')
            output_file.write(' '.join(map(str, vocab_embedding_matrix[word_idx])) + '\n')

    @staticmethod
    def binary_to_string(binary_string):
        return binary_string.decode("utf-8")

    @staticmethod
    def binary_to_string_list(binary_string_list):
        return [common.binary_to_string(w) for w in binary_string_list]

    @staticmethod
    def binary_to_string_matrix(binary_string_matrix):
        return [common.binary_to_string_list(l) for l in binary_string_matrix]

    @staticmethod
    def load_file_lines(path):
        with open(path, 'r') as f:
            return f.read().splitlines()

    @staticmethod
    def split_to_batches(data_lines, batch_size):
        for x in range(0, len(data_lines), batch_size):
            yield data_lines[x:x + batch_size]

    @staticmethod
    def legal_method_names_checker(special_words, name):
        return name != special_words.OOV and re.match(r'^[a-zA-Z|]+$', name)

    @staticmethod
    def filter_impossible_names(special_words, top_words):
        result = list(filter(lambda word: common.legal_method_names_checker(special_words, word), top_words))
        return result

    @staticmethod
    def get_subtokens(str):
        return str.split('|')

    @staticmethod
    def parse_prediction_results(raw_prediction_results, unhash_dict, special_words, topk: int = 5) -> List['MethodPredictionResults']:
        prediction_results = []
        for single_method_prediction in raw_prediction_results:
            current_method_prediction_results = MethodPredictionResults(single_method_prediction.original_name)
            for i, predicted in enumerate(single_method_prediction.topk_predicted_words):
                if predicted == special_words.OOV:
                    continue
                suggestion_subtokens = common.get_subtokens(predicted)
                current_method_prediction_results.append_prediction(
                    suggestion_subtokens, single_method_prediction.topk_predicted_words_scores[i].item())
            topk_attention_per_context = [
                (context, single_method_prediction.attention_per_context[context])
                for context in sorted(single_method_prediction.attention_per_context,
                                  key=single_method_prediction.attention_per_context.get, reverse=True)
            ][:topk]
            for context, attention in topk_attention_per_context:
                token1, hashed_path, token2 = context
                if hashed_path in unhash_dict:
                    unhashed_path = unhash_dict[hashed_path]
                    current_method_prediction_results.append_attention_path(attention.item(), token1=token1,
                                                                            path=unhashed_path, token2=token2)
            prediction_results.append(current_method_prediction_results)
        return prediction_results

    # Returns a vector where the first true in input vector has True, and all others zeroes. i.e [0, 0, ..., 1, 0, 0, ...]
    @staticmethod
    def tf_get_first_true(bool_tensor: tf.Tensor) -> tf.Tensor:
        bool_tensor_as_int32 = tf.cast(bool_tensor, dtype=tf.int32)
        cumsum = tf.cumsum(bool_tensor_as_int32, axis=-1, exclusive=False)
        return tf.logical_and(tf.equal(cumsum, 1), bool_tensor)

    @staticmethod
    def count_lines_in_file(file_path: str):
        with open(file_path, 'rb') as f:
            bufgen = takewhile(lambda x: x, (f.raw.read(1024 * 1024) for _ in repeat(None)))
            return sum(buf.count(b'\n') for buf in bufgen)

    @staticmethod
    def squeeze_single_batch_dimension_for_np_arrays(arrays):
        assert all(array is None or isinstance(array, np.ndarray) or isinstance(array, tf.Tensor) for array in arrays)
        return tuple(
            None if array is None else np.squeeze(array, axis=0)
            for array in arrays
        )

    @staticmethod
    def get_first_match_word_from_top_predictions(special_words, original_name, top_predicted_words) -> Optional[Tuple[int, str]]:
        normalized_original_name = common.normalize_word(original_name)
        for suggestion_idx, predicted_word in enumerate(common.filter_impossible_names(special_words, top_predicted_words)):
            normalized_possible_suggestion = common.normalize_word(predicted_word)
            if normalized_original_name == normalized_possible_suggestion:
                return suggestion_idx, predicted_word
        return None

    @staticmethod
    def now_str():
        return datetime.now().strftime("%Y%m%d-%H%M%S: ")

    @staticmethod
    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @staticmethod
    def get_unique_list(lst: Iterable) -> list:
        return list(OrderedDict(((item, 0) for item in lst)).keys())


class MethodPredictionResults:
    def __init__(self, original_name):
        self.original_name = original_name
        self.predictions = list()
        self.attention_paths = list()

    def append_prediction(self, name, probability):
        self.predictions.append({'name': name, 'probability': probability})

    def append_attention_path(self, attention_score, token1, path, token2):
        self.attention_paths.append({'score': attention_score,
                                     'path': path,
                                     'token1': token1,
                                     'token2': token2})
