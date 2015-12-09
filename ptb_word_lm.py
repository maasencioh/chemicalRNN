# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Example / benchmark for building a PTB LSTM model.

Trains the model described in:
(Zaremba, et. al.) Recurrent Neural Network Regularization
http://arxiv.org/abs/1409.2329

The data required for this example is in the data/ dir of the
PTB dataset from Tomas Mikolov's webpage:

http://www.fit.vutbr.cz/~imikolov/rnnlm/simple-examples.tgz

There are 3 supported model configurations:
===========================================
| config | epochs | train | valid  | test
===========================================
| small  | 13     | 37.99 | 121.39 | 115.91
| medium | 39     | 48.45 |  86.16 |  82.07
| large  | 55     | 37.87 |  82.62 |  78.29
The exact results may vary depending on the random initialization.

The hyperparameters used in the model:
- init_scale - the initial scale of the weights
- learning_rate - the initial value of the learning rate
- max_grad_norm - the maximum permissible norm of the gradient
- num_layers - the number of LSTM layers
- num_steps - the number of unrolled steps of LSTM
- hidden_size - the number of LSTM units
- max_epoch - the number of epochs trained with the initial learning rate
- max_max_epoch - the total number of epochs for training
- keep_prob - the probability of keeping weights in the dropout layer
- lr_decay - the decay of the learning rate for each epoch after "max_epoch"
- batch_size - the batch size

To compile on CPU:
  bazel build -c opt tensorflow/models/rnn/ptb:ptb_word_lm
To compile on GPU:
  bazel build -c opt tensorflow --config=cuda \
    tensorflow/models/rnn/ptb:ptb_word_lm
To run:
  ./bazel-bin/.../ptb_word_lm --data_path=/tmp/simple-examples/data/

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

import tensorflow.python.platform
from tensorflow.models.rnn import rnn

import numpy as np
import tensorflow as tf

from tensorflow.models.rnn import rnn_cell
from tensorflow.models.rnn import seq2seq
from tensorflow.models.rnn.ptb import reader

flags = tf.flags
logging = tf.logging

flags.DEFINE_string(
    "model", "small",
    "A type of model. Possible options are: small, medium, large.")
flags.DEFINE_string("data_path", None, "data_path")
flags.DEFINE_string("load", None, "load")

FLAGS = flags.FLAGS


class PTBModel(object):
  """The PTB model."""

  def __init__(self, is_training, config, is_eval=False):
    self.batch_size = batch_size = config.batch_size
    self.num_steps = num_steps = config.num_steps
    size = config.hidden_size
    vocab_size = config.vocab_size

    self._input_data = tf.placeholder(tf.int32, [batch_size, num_steps])
    self._targets = tf.placeholder(tf.int32, [batch_size, num_steps])

    # Slightly better results can be obtained with forget gate biases
    # initialized to 1 but the hyperparameters of the model would need to be
    # different than reported in the paper.
    lstm_cell = rnn_cell.BasicLSTMCell(size, forget_bias=0.0)
    if is_training and config.keep_prob < 1:
      lstm_cell = rnn_cell.DropoutWrapper(
          lstm_cell, output_keep_prob=config.keep_prob)
    cell = rnn_cell.MultiRNNCell([lstm_cell] * config.num_layers)

    self._cell = cell

    self._initial_state = cell.zero_state(batch_size, tf.float32)

    with tf.device("/cpu:0"):
      embedding = tf.get_variable("embedding", [vocab_size, size])
      inputs = tf.split(1, num_steps, tf.nn.embedding_lookup(embedding, self._input_data))
      inputs = [tf.squeeze(input_, [1]) for input_ in inputs]

    if is_training and config.keep_prob < 1:
      inputs = [tf.nn.dropout(input_, config.keep_prob) for input_ in inputs]

    # Simplified version of tensorflow.models.rnn.rnn.py's rnn().
    # This builds an unrolled LSTM for tutorial purposes only.
    # In general, use the rnn() or state_saving_rnn() from rnn.py.
    #
    # The alternative version of the code below is:
    # /home/jefferson/tensorflow/tensorflow/models/rnn/ptb/logs
    #

    outputs, states = rnn.rnn(cell, inputs, initial_state=self._initial_state)

    output = tf.reshape(tf.concat(1, outputs), [-1, size])

    logits = tf.nn.xw_plus_b(output,
                             tf.get_variable("softmax_w", [size, vocab_size]),
                             tf.get_variable("softmax_b", [vocab_size]))

    self._outputs = tf.nn.softmax(logits)
    self._final_state = states[-1]
    if is_eval:
      return

    #loss = tf.nn.softmax_cross_entropy_with_logits(logits, tf.to_float(tf.reshape(self._targets, [-1])))

    loss = seq2seq.sequence_loss_by_example([logits],
                                            [tf.reshape(self._targets, [-1])],
                                            [tf.ones([batch_size * num_steps])],
                                            vocab_size)
    self._cost = cost = tf.reduce_sum(loss) / batch_size
    #self._final_state = states[-1]

    if not is_training:
      return

    self._lr = tf.Variable(0.0, trainable=False)
    tvars = tf.trainable_variables()
    grads, _ = tf.clip_by_global_norm(tf.gradients(cost, tvars),
                                      config.max_grad_norm)
    optimizer = tf.train.GradientDescentOptimizer(self.lr)
    self._train_op = optimizer.apply_gradients(zip(grads, tvars))

  def assign_lr(self, session, lr_value):
    session.run(tf.assign(self.lr, lr_value))

  def outputs(self):
    return self._outputs

  @property
  def input_data(self):
    return self._input_data

  @property
  def targets(self):
    return self._targets

  @property
  def initial_state(self):
    return self._initial_state

  @property
  def cost(self):
    return self._cost

  @property
  def final_state(self):
    return self._final_state

  @property
  def lr(self):
    return self._lr

  @property
  def train_op(self):
    return self._train_op

class SmallConfig(object):
  """Small config."""
  init_scale = 0.1
  learning_rate = 1.0
  max_grad_norm = 5
  num_layers = 2
  num_steps = 20
  hidden_size = 200
  max_epoch = 4
  max_max_epoch = 13
  keep_prob = 1.0
  lr_decay = 0.5
  batch_size = 20
  vocab_size = 90


class MediumConfig(object):
  """Medium config."""
  init_scale = 0.05
  learning_rate = 1.0
  max_grad_norm = 5
  num_layers = 2
  num_steps = 35 # number of chars in element
  hidden_size = 800
  max_epoch = 6
  max_max_epoch = 39
  keep_prob = 0.5
  lr_decay = 0.8
  batch_size = 20 # number of elements
  vocab_size = 10000


class LargeConfig(object):
  """Large config."""
  init_scale = 0.04
  learning_rate = 1.0
  max_grad_norm = 10
  num_layers = 2
  num_steps = 35
  hidden_size = 850
  max_epoch = 14
  max_max_epoch = 55
  keep_prob = 0.5
  lr_decay = 1 / 1.15
  batch_size = 20
  vocab_size = 90

class NormalConfig(object):
  init_scale = 0.05
  learning_rate = 0.8
  max_grad_norm = 5
  num_layers = 2
  num_steps = 35 # number of chars in element
  hidden_size = 128
  max_epoch = 6
  max_max_epoch = 39
  keep_prob = 0.6
  lr_decay = 0.97
  batch_size = 20 # number of elements
  vocab_size = 83

def run_epoch(session, m, data, eval_op, verbose=False):
  """Runs the model on the given data."""
  epoch_size = ((len(data) // m.batch_size) - 1) // m.num_steps
  start_time = time.time()
  costs = 0.0
  iters = 0
  state = m.initial_state.eval()

  merged_summary_op = tf.merge_all_summaries()
  summary_writer = tf.train.SummaryWriter('/home/jefferson/tensorflow/tensorflow/models/rnn/ptb/logs', session.graph_def)

  for step, (x, y) in enumerate(reader.ptb_iterator(data, m.batch_size,
                                                    m.num_steps)):

    cost, state, _ = session.run([m.cost, m.final_state, eval_op],
                                 {m.input_data: x,
                                  m.targets: y,
                                  m.initial_state: state})

    # every 10 times we will save a log for the tensorboard program
    if step + 1 % 10 == 0:
      summary_str = session.run(merged_summary_op)
      summary_writer.add_summary(summary_str, step + 1)

    costs += cost
    iters += m.num_steps

    # if verbose is true, report step, perplexity and words per second
    if verbose and step % (epoch_size // 10) == 10:
      print("%.3f perplexity: %.3f speed: %.0f wps" %
            (step * 1.0 / epoch_size, np.exp(costs / iters),
             iters * m.batch_size / (time.time() - start_time)))

  return np.exp(costs / iters)

'''
This function will retrieve a prediction of the model given.

- session: a tensorflow session
- model: the RNN model
- element: the id of the word in the dictionary
- id_to_word: a dictionary to decode the output
- separator: a string to separate between each prediction
'''
def eval_element(session, model, element, id_to_word, separator):
  state = model.initial_state.eval()
  vocab_size = len(id_to_word.keys())
  smile = []
  print(id_to_word[element])
  i = 0
  while id_to_word[element] != '<eos>' and i < 500:
    smile.append(id_to_word[element])

    # This will retrieve the probability of each word in the vocabulary and the internal state for
    # the following forward propagation
    output = session.run([model.outputs(), model.final_state, tf.no_op()],
                                feed_dict={model.input_data: [[element]], model.initial_state: state})
    state = output[1]
    output = output[0][0]

    if s > 1.0:
      output = [elem/s for elem in output]

    #element = np.random.multinomial(1, output)[0]
    lst = np.random.choice(range(len(output)), 1, p=output)
    element = np.argmax(np.bincount(lst))
    i += 1
  smile = separator.join(smile)
  return smile[1:]


def get_config():
  if FLAGS.model == "small":
    return SmallConfig()
  elif FLAGS.model == "medium":
    return MediumConfig()
  elif FLAGS.model == "large":
    return LargeConfig()
  elif FLAGS.model == "normal":
    return NormalConfig()
  else:
    raise ValueError("Invalid model: %s", FLAGS.model)


def main(unused_args):
  if not FLAGS.data_path:
    raise ValueError("Must set --data_path to PTB data directory")

  raw_data = reader.ptb_raw_data(FLAGS.data_path)
  train_data, valid_data, test_data, _, word_to_id, id_to_word = raw_data

  #print(id_to_word[9])

  config = get_config()
  eval_config = get_config()
  eval_config.batch_size = 1
  eval_config.num_steps = 1

  with tf.Graph().as_default(), tf.Session() as session:
    initializer = tf.random_uniform_initializer(-config.init_scale,
                                                config.init_scale)
    with tf.variable_scope("model", reuse=None, initializer=initializer):
      m = PTBModel(is_training=True, config=config)
    with tf.variable_scope("model", reuse=True, initializer=initializer):
      mvalid = PTBModel(is_training=False, config=config)
      mtest = PTBModel(is_training=False, config=eval_config)
      mforward = PTBModel(is_training=False, config=eval_config, is_eval=True)

    tf.initialize_all_variables().run()

    saver = tf.train.Saver()
    if FLAGS.load:
        print("loading model ...")
        saver.restore(session, FLAGS.load)
        print("model loaded.")

    print(word_to_id)
    #f = open("./smilesData.txt", "w")
    #for i in xrange(3000):
    #  f.write(eval_element(session, mforward, word_to_id["|"], id_to_word, "") + "\n")
    #f.close()

    for i in range(config.max_max_epoch):
      lr_decay = config.lr_decay ** max(i - config.max_epoch, 0.0)
      m.assign_lr(session, config.learning_rate * lr_decay)

      print("Epoch: %d Learning rate: %.3f" % (i + 1, session.run(m.lr)))
      train_perplexity = run_epoch(session, m, train_data, m.train_op,
                                   verbose=True)
      print("Epoch: %d Train Perplexity: %.3f" % (i + 1, train_perplexity))
      valid_perplexity = run_epoch(session, mvalid, valid_data, tf.no_op())
      print("Epoch: %d Valid Perplexity: %.3f" % (i + 1, valid_perplexity))
      save_path = saver.save(session, "./" + str(i) + ".ckpt")
      print("Model saved in file:", save_path)

      ## forward step
      #for i in xrange(5):
        #eval_element(session, mforward, word_to_id["|"], id_to_word, "")

    test_perplexity = run_epoch(session, mtest, test_data, tf.no_op())
    print("Test Perplexity: %.3f" % test_perplexity)


if __name__ == "__main__":
  tf.app.run()
