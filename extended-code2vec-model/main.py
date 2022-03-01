import os
from vocabularies import VocabType
from config import Config
# from interactive_predict import InteractivePredictor
from keras_model import MocktailModel

if __name__ == '__main__':
    config = Config(set_defaults=True, load_from_args=True, verify=True)

    model = MocktailModel(config)
    config.log('Done creating mocktail model')

    if config.is_training:
        model.train()
    if config.SAVE_W2V is not None:
        model.save_word2vec_format(config.SAVE_W2V, VocabType.Token)
        config.log('Origin word vectors saved in word2vec text format in: %s' % config.SAVE_W2V)
    if (config.SAVE_T2V is not None) and (config.DOWNSTREAM_TASK == 'method_naming'):       # for classification task, target vocab is None.
        model.save_word2vec_format(config.SAVE_T2V, VocabType.Target)
        config.log('Target word vectors saved in word2vec text format in: %s' % config.SAVE_T2V)
    if (config.is_testing and not config.is_training) or config.RELEASE:
        eval_results = model.evaluate()
        if eval_results is not None:
            if config.DOWNSTREAM_TASK == 'method_naming':
                config.log(str(eval_results).replace('topk', 'top{}'.format(config.TOP_K_WORDS_CONSIDERED_DURING_PREDICTION)))
            else:
                config.log(
                    '    loss: {loss:.4f}, accuracy: {accuracy:.4f}'.format(
                    loss=eval_results.loss, accuracy=eval_results.accuracy))
    if config.EXPORT_CODE_VECTORS and (config.is_training or config.is_loading):
        code_vectors = model.export_code_vectors(config.is_training)
        file_name = '_'.join(os.path.basename(config.data_path(not config.is_training)).split('.')[:-1]) + '_embeddings.csv'
        with open(file_name, 'w') as f:
            model._write_code_vectors(f, code_vectors)
        config.log('Code vectors saved in csv format in: {}'.format(file_name))
    # if config.PREDICT:
    #     predictor = InteractivePredictor(config, model)
    #     predictor.predict()
    model.close_session()
