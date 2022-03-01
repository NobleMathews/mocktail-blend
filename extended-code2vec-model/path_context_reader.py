import abc
from enum import Enum
import tensorflow as tf
from functools import reduce
from typing import Dict, Tuple, NamedTuple, Union, Optional, Iterable

from config import Config
from vocabularies import MocktailVocabs, _SpecialVocabWords_JoinedOovPad

class EstimatorAction(Enum):
    Train = 'train'
    Evaluate = 'evaluate'
    Predict = 'predict'

    @property
    def is_train(self):
        return self is EstimatorAction.Train

    @property
    def is_evaluate(self):
        return self is EstimatorAction.Evaluate

    @property
    def is_predict(self):
        return self is EstimatorAction.Predict

    @property
    def is_evaluate_or_predict(self):
        return self.is_evaluate or self.is_predict


class ReaderInputTensors(NamedTuple):
    """
    Used mostly for convenient-and-clear access to input parts (by their names).
    """
    input_dict: Dict[str, tf.Tensor]
    target_index: Optional[tf.Tensor] = None
    target_string: Optional[tf.Tensor] = None


class ModelInputTensorsFormer(abc.ABC):
    """
    Should be inherited by the model implementation.
    An instance of the inherited class is passed by the model to the reader in order to help the reader
        to construct the input in the form that the model expects to receive it.
    This class also enables conveniently & clearly access input parts by their field names.
        eg: 'tensors.path_indices' instead if 'tensors[1]'.
    This allows the input tensors to be passed as pure tuples along the computation graph, while the
        python functions that construct the graph can easily (and clearly) access tensors.
    """

    @abc.abstractmethod
    def to_model_input_form(self, input_tensors: ReaderInputTensors):
        ...

    @abc.abstractmethod
    def from_model_input_form(self, input_row) -> ReaderInputTensors:
        ...


class PathContextReader:
    def __init__(self,
                 vocabs: MocktailVocabs,
                 config: Config,
                 model_input_tensors_former: ModelInputTensorsFormer,
                 estimator_action: EstimatorAction,
                 repeat_endlessly: bool = False):
        self.vocabs = vocabs
        self.config = config
        self.model_input_tensors_former = model_input_tensors_former
        self.estimator_action = estimator_action
        self.repeat_endlessly = repeat_endlessly
        self.CONTEXT_PADDING = ','.join([self.vocabs.token_vocab.special_words.PAD,
                                         self.vocabs.path_vocab.special_words.PAD,
                                         self.vocabs.token_vocab.special_words.PAD])

        # Default value of an example. ex: [['OOV'], ['PAD,PAD,PAD'], ['PAD,PAD,PAD'], ...., ['PAD,PAD,PAD']]
        self.csv_record_defaults = [[self.vocabs.target_vocab.special_words.OOV]] if self.vocabs.target_vocab is not None else [[_SpecialVocabWords_JoinedOovPad.OOV]]
        for rep in self.config.CODE_REPRESENTATIONS:
            self.csv_record_defaults += ([[self.CONTEXT_PADDING]] * self.config.MAX_CONTEXTS[rep])

        # initialize the needed lookup tables (if not already initialized).
        self.create_needed_vocabs_lookup_tables(self.vocabs)

        self._dataset: Optional[tf.data.Dataset] = None

    @classmethod
    def create_needed_vocabs_lookup_tables(cls, vocabs: MocktailVocabs):
        vocabs.token_vocab.get_word_to_index_lookup_table()
        vocabs.path_vocab.get_word_to_index_lookup_table()
        if vocabs.target_vocab is not None:     # vocabs.target_vocab is None for classification.
            vocabs.target_vocab.get_word_to_index_lookup_table()

    @tf.function
    def process_input_row(self, row_placeholder):
        parts = tf.io.decode_csv(
            row_placeholder, record_defaults=self.csv_record_defaults, field_delim=' ', use_quote_delim=False)
        # Note: we DON'T apply the filter `_filter_input_rows()` here.
        tensors = self._map_raw_dataset_row_to_input_tensors(*parts)

        # make it batched (first batch axis is going to have dimension 1)
        reader_input_tensors = {}
        for name, tensor in tensors._asdict().items():
            if name == "input_dict":
                temp_dict = {}
                for name1, tensor1 in tensor.items():
                    temp_dict[name1] = None if tensor1 is None else tf.expand_dims(tensor1, axis=0)
                
                reader_input_tensors[name] = temp_dict
            else:
                reader_input_tensors[name] = None if tensor is None else tf.expand_dims(tensor, axis=0)

        tensors_expanded = ReaderInputTensors(**{name: tensor for name, tensor in reader_input_tensors.items()})

        return self.model_input_tensors_former.to_model_input_form(tensors_expanded)

    def process_and_iterate_input_from_data_lines(self, input_data_lines: Iterable) -> Iterable:
        for data_row in input_data_lines:
            processed_row = self.process_input_row(data_row)
            yield processed_row

    def get_dataset(self, input_data_rows: Optional = None, is_training: bool = True, shuffle: bool = True) -> tf.data.Dataset:
        if self._dataset is None:
            self._dataset = self._create_dataset_pipeline(input_data_rows, is_training, shuffle)
        return self._dataset

    def _create_dataset_pipeline(self, input_data_rows: Optional = None, is_training: bool = True, shuffle: bool = True) -> tf.data.Dataset:
        if input_data_rows is None:
            # assert not self.estimator_action.is_predict
            dataset = tf.data.experimental.CsvDataset(
                self.config.data_path(is_evaluating=not is_training),
                record_defaults=self.csv_record_defaults, field_delim=' ', use_quote_delim=False,
                buffer_size=self.config.CSV_BUFFER_SIZE)
        else:
            # This is similar to process_input_row function
            dataset = tf.data.Dataset.from_tensor_slices(input_data_rows)
            dataset = dataset.map(
                lambda input_line: tf.io.decode_csv(
                    tf.reshape(tf.cast(input_line, tf.string), ()),
                    record_defaults=self.csv_record_defaults,
                    field_delim=' ', use_quote_delim=False))

        if shuffle:
            dataset = dataset.shuffle(self.config.SHUFFLE_BUFFER_SIZE, reshuffle_each_iteration=True)
        if self.repeat_endlessly:
            dataset = dataset.repeat()
        if self.estimator_action.is_train:
            if not self.repeat_endlessly and self.config.NUM_TRAIN_EPOCHS > 1:
                dataset = dataset.repeat(self.config.NUM_TRAIN_EPOCHS)

        # For every row, we get a pair of inputs, targets.
        dataset = dataset.map(self._map_raw_dataset_row_to_expected_model_input_form,
                              num_parallel_calls=self.config.READER_NUM_PARALLEL_BATCHES)
        batch_size = self.config.batch_size(is_evaluating=self.estimator_action.is_evaluate)
        if self.estimator_action.is_predict:
            dataset = dataset.batch(1)
        else:
            dataset = dataset.filter(self._filter_input_rows)
            dataset = dataset.batch(batch_size)
        
        dataset = dataset.prefetch(buffer_size=40)
        return dataset

    def _filter_input_rows(self, *row_parts) -> tf.bool:
        row_parts = self.model_input_tensors_former.from_model_input_form(row_parts)

        any_contexts_is_valid = False
        for rep in self.config.CODE_REPRESENTATIONS:
            any_word_valid_mask_per_context_part = [
                tf.not_equal(tf.reduce_max(row_parts.input_dict[rep + '_path_source_token_indices'], axis=0),
                            self.vocabs.token_vocab.word_to_index[self.vocabs.token_vocab.special_words.PAD]),
                tf.not_equal(tf.reduce_max(row_parts.input_dict[rep + '_path_target_token_indices'], axis=0),
                            self.vocabs.token_vocab.word_to_index[self.vocabs.token_vocab.special_words.PAD]),
                tf.not_equal(tf.reduce_max(row_parts.input_dict[rep + '_path_indices'], axis=0),
                            self.vocabs.path_vocab.word_to_index[self.vocabs.path_vocab.special_words.PAD])]
            any_contexts_is_valid = tf.math.logical_or(any_contexts_is_valid, reduce(tf.logical_or, any_word_valid_mask_per_context_part))

        if self.estimator_action.is_evaluate:
            cond = any_contexts_is_valid  # scalar
        else:  # training
            if self.config.DOWNSTREAM_TASK == 'method_naming':
                word_is_valid = tf.greater(
                    row_parts.target_index, self.vocabs.target_vocab.word_to_index[self.vocabs.target_vocab.special_words.OOV])  # scalar
                cond = tf.logical_and(word_is_valid, any_contexts_is_valid)  # scalar
            else: # classification
                cond = (row_parts.target_index >= 0) and (row_parts.target_index < self.config.NUM_CLASSES)

        return cond

    def _map_raw_dataset_row_to_expected_model_input_form(self, *row_parts) -> \
            Tuple[Union[tf.Tensor, Tuple[tf.Tensor, ...], Dict[str, tf.Tensor]], ...]:
        tensors = self._map_raw_dataset_row_to_input_tensors(*row_parts)
        return self.model_input_tensors_former.to_model_input_form(tensors)

    def _map_raw_dataset_row_to_input_tensors(self, *row_parts) -> ReaderInputTensors:
        row_parts = list(row_parts)

        target_str = row_parts[0]
        if self.config.DOWNSTREAM_TASK == 'method_naming':
            target_index = self.vocabs.target_vocab.lookup_index(target_str)
        else:
            target_index = int(row_parts[0])

        start_index = 1
        input_dict = {}
        for rep in self.config.CODE_REPRESENTATIONS:
            contexts_str = tf.stack(row_parts[start_index : (start_index + self.config.MAX_CONTEXTS[rep])], axis=0)
            split_contexts = tf.compat.v1.string_split(contexts_str, sep=',', skip_empty=False)
            sparse_split_contexts = tf.sparse.SparseTensor(
                indices=split_contexts.indices, values=split_contexts.values, dense_shape=[self.config.MAX_CONTEXTS[rep], 3])
            dense_split_contexts = tf.reshape(
                tf.sparse.to_dense(sp_input=sparse_split_contexts, default_value=self.vocabs.token_vocab.special_words.PAD),
                shape=[self.config.MAX_CONTEXTS[rep], 3])  # (max_contexts, 3)

            path_source_token_strings = tf.squeeze(
                tf.slice(dense_split_contexts, begin=[0, 0], size=[self.config.MAX_CONTEXTS[rep], 1]), axis=1)  # (max_contexts,)
            path_strings = tf.squeeze(
                tf.slice(dense_split_contexts, begin=[0, 1], size=[self.config.MAX_CONTEXTS[rep], 1]), axis=1)  # (max_contexts,)
            path_target_token_strings = tf.squeeze(
                tf.slice(dense_split_contexts, begin=[0, 2], size=[self.config.MAX_CONTEXTS[rep], 1]), axis=1)  # (max_contexts,)

            path_source_token_indices = self.vocabs.token_vocab.lookup_index(path_source_token_strings)  # (max_contexts, )
            path_indices = self.vocabs.path_vocab.lookup_index(path_strings)  # (max_contexts, )
            path_target_token_indices = self.vocabs.token_vocab.lookup_index(path_target_token_strings)  # (max_contexts, )

            valid_word_mask_per_context_part = [
                tf.not_equal(path_source_token_indices, self.vocabs.token_vocab.word_to_index[self.vocabs.token_vocab.special_words.PAD]),
                tf.not_equal(path_target_token_indices, self.vocabs.token_vocab.word_to_index[self.vocabs.token_vocab.special_words.PAD]),
                tf.not_equal(path_indices, self.vocabs.path_vocab.word_to_index[self.vocabs.path_vocab.special_words.PAD])]  # [(max_contexts, )]
            context_valid_mask = tf.cast(reduce(tf.logical_or, valid_word_mask_per_context_part), dtype=tf.float32)  # (max_contexts, )


            input_dict[rep + '_path_source_token_indices'] = path_source_token_indices
            input_dict[rep + '_path_indices'] = path_indices
            input_dict[rep + '_path_target_token_indices'] = path_target_token_indices
            input_dict[rep + '_path_source_token_strings'] = path_source_token_strings
            input_dict[rep + '_path_strings'] = path_strings
            input_dict[rep + '_path_target_token_strings'] = path_target_token_strings
            input_dict[rep + '_context_valid_mask'] = context_valid_mask

            start_index += self.config.MAX_CONTEXTS[rep]

        return ReaderInputTensors(
            input_dict=input_dict,
            target_index=target_index,
            target_string=target_str,
        )