import os
import json
import logging
import numpy as np
from quagga import Model
from urllib import urlretrieve
from quagga.matrix import Matrix
from quagga.context import Context
from collections import defaultdict
from collections import OrderedDict
from quagga.connector import Connector
from quagga.optimizers import SgdOptimizer
from quagga.optimizers.observers import Saver
from quagga.optimizers.observers import ValidLossTracker
from quagga.optimizers.observers import TrainLossTracker
from quagga.optimizers.policies import FixedLearningRatePolicy
from quagga.optimizers.stopping_criteria import MaxIterCriterion


def get_logger(file_name):
    logger = logging.getLogger('train_logger')
    handler = logging.FileHandler(file_name, mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%d-%m-%Y %H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def load_ptb_dataset():
    train_file_path = 'ptb_train.txt'
    valid_file_path = 'ptb_valid.txt'
    test_file_path = 'ptb_test.txt'

    if not os.path.exists(train_file_path):
        urlretrieve('https://github.com/wojzaremba/lstm/raw/master/data/ptb.train.txt', train_file_path)
    if not os.path.exists(valid_file_path):
        urlretrieve('https://github.com/wojzaremba/lstm/raw/master/data/ptb.valid.txt', valid_file_path)
    if not os.path.exists(test_file_path):
        urlretrieve('https://github.com/wojzaremba/lstm/raw/master/data/ptb.tests.txt', test_file_path)

    vocab = {}
    idx_to_word = []
    ptb_train = []
    with open(train_file_path) as f:
        for line in f:
            sentence = ['<S>'] + line.strip().split() + ['</S>']
            for word in sentence:
                if word not in vocab:
                    vocab[word] = len(idx_to_word)
                    idx_to_word.append(word)
            ptb_train.append([vocab[word] for word in sentence])

    ptb_valid = []
    with open(valid_file_path) as f:
        for line in f:
            sentence = ['<S>'] + line.strip().split() + ['</S>']
            ptb_valid.append([vocab[word] for word in sentence])

    ptb_test = []
    with open(test_file_path) as f:
        for line in f:
            sentence = ['<S>'] + line.strip().split() + ['</S>']
            ptb_test.append([vocab[word] for word in sentence])

    return ptb_train, ptb_valid, ptb_test, vocab, idx_to_word


class HomogeneousDataGenerator(object):
    def __init__(self, sentences, batch_size, sentence_max_len, randomize=False, infinite=False):
        sentences = [s for s in sentences if len(s) <= sentence_max_len]
        self.b_size = batch_size
        self.flatten_sentences = [w for s in sentences for w in s]
        self.offsets = defaultdict(list)
        for s_offsets in self.__get_sentence_offsets(sentences):
            self.offsets[s_offsets[1] - s_offsets[0]].append(s_offsets)
        if randomize:
            self.rng = np.random.RandomState(42)
        self.infinite = infinite

    def __iter__(self):
        while True:
            for batch_offsets in self.__iter():
                yield batch_offsets
            if not self.infinite:
                break

    def __iter(self):
        randomize = hasattr(self, 'rng')
        if randomize:
            for s_offsets in self.offsets.itervalues():
                self.rng.shuffle(s_offsets)
        progress = defaultdict(int)
        available_lengths = self.offsets.keys()
        if randomize:
            get_sent_len = lambda: self.rng.choice(available_lengths)
        else:
            get_sent_len = lambda: available_lengths[0]
        batch_offsets = []
        b_size = self.b_size
        k = get_sent_len()
        while available_lengths:
            batch_offsets.extend(self.offsets[k][progress[k]:progress[k]+b_size])
            progress[k] += b_size
            if len(batch_offsets) == self.b_size:
                yield batch_offsets
                batch_offsets = []
                b_size = self.b_size
                k = get_sent_len()
            else:
                b_size = self.b_size - len(batch_offsets)
                i = available_lengths.index(k)
                del available_lengths[i]
                if not available_lengths:
                    break
                if i == 0:
                    k = available_lengths[0]
                elif i >= len(available_lengths) - 1:
                    k = available_lengths[-1]
                else:
                    k = available_lengths[i + self.rng.choice([-1, 1])]
        if batch_offsets:
            yield batch_offsets

    @staticmethod
    def __get_sentence_offsets(sentences):
        sentence_offsets = []
        offset = 0
        for s in sentences:
            sentence_offsets.append((offset, offset + len(s)))
            offset += len(s)
        return sentence_offsets


class PtbMiniBatchesGenerator(object):
    def __init__(self, ptb_train, ptb_valid, batch_size, sentence_max_len, device_id):
        self.blocking_context = None
        self.context = Context(device_id)
        device_id = self.context.device_id
        self.train_offsets = HomogeneousDataGenerator(ptb_train, batch_size, sentence_max_len, randomize=True, infinite=True)
        self.valid_offsets = HomogeneousDataGenerator(ptb_valid, batch_size, sentence_max_len)

        train_sentences = np.array([self.train_offsets.flatten_sentences]).T
        valid_sentences = np.array([self.valid_offsets.flatten_sentences]).T
        self.train_sents = Matrix.from_npa(train_sentences, 'int', device_id)
        self.valid_sents = Matrix.from_npa(valid_sentences, 'int', device_id)
        self._sent_lengths = np.empty((batch_size, 1), dtype=np.int32, order='F')
        self.sent_lengths = Matrix.from_npa(self._sent_lengths, device_id=device_id)

        self._sentence_batch = Matrix.empty(batch_size, sentence_max_len, 'int', device_id)
        self.sentence_batch = Connector(self._sentence_batch, self.context)
        self.sentence_batch.sync_fill(0)
        self.mask = Matrix.empty(batch_size, sentence_max_len, 'float', device_id)
        self.mask = Connector(self.mask, self.context)

        self.train_offsets_iterator = iter(self.train_offsets)
        self.valid_offsets_iterator = iter(self.valid_offsets)
        self.training_mode = True

    def set_training_mode(self):
        self.training_mode = True

    def set_testing_mode(self):
        self.training_mode = False

    def fprop(self):
        if self.training_mode:
            offsets = next(self.train_offsets_iterator)
            sents = self.train_sents
        else:
            try:
                offsets = next(self.valid_offsets_iterator)
                sents = self.valid_sents
            except StopIteration as e:
                self.valid_offsets_iterator = iter(self.valid_offsets)
                raise e
        self._sent_lengths = self._sent_lengths.base[:len(offsets)]
        self.sentence_batch.nrows = len(offsets)
        for k, offset in enumerate(offsets):
            sent = sents[offset[0]:offset[1]]
            batch_chunk = self._sentence_batch[k]
            sent.copy_to(self.context, batch_chunk)
            self._sent_lengths[k] = offset[1] - offset[0]
        self.sent_lengths.to_device(self.context, self._sent_lengths)
        self.sentence_batch.ncols = np.max(self._sent_lengths)
        self.mask.ncols = self.sentence_batch.ncols
        self.mask.mask_column_numbers_row_wise(self.context, self.sent_lengths)
        self.context.wait(self.blocking_context)
        self.sentence_batch.fprop()
        self.mask.fprop()


if __name__ == '__main__':
    ptb_train, ptb_valid, ptb_test, vocab, idx_to_word = load_ptb_dataset()
    print len(ptb_train), len(ptb_valid), len(ptb_test)
    data_block = PtbMiniBatchesGenerator(ptb_train, ptb_valid, batch_size=64, sentence_max_len=200, device_id=0)
    with open('penn_treebank.json') as f:
        model_definition = json.load(f, object_pairs_hook=OrderedDict)
    model = Model(model_definition, data_block)
    logger = get_logger('train.log')
    learning_rate_policy = FixedLearningRatePolicy(0.005)
    sgd_optimizer = SgdOptimizer(MaxIterCriterion(40000), learning_rate_policy, model)
    train_loss_tracker = TrainLossTracker(model, 350, logger)
    valid_loss_tracker = ValidLossTracker(model, 350, logger)
    saver = Saver(model, 700, 'penn_treebank_trained.json', 'penn_treebank_parameters.hdf5', logger)
    sgd_optimizer.add_observer(train_loss_tracker)
    sgd_optimizer.add_observer(valid_loss_tracker)
    sgd_optimizer.add_observer(saver)

    import time
    t = time.time()
    sgd_optimizer.optimize()
    from quagga.cuda import cudart
    cudart.cuda_device_synchronize()
    print time.time() - t