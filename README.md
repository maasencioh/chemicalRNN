# chemicalRNN

A SMILES random generator using Recurrent Neural Networks using Tensorflow.

### How to use it

For now you have to download [Tensorflow](https://github.com/tensorflow/tensorflow) from github and
then put the ptb_word_lm.py in the tensorflow folder: 

```{path to Tensorflow}/tensorflow/models/rnn/ptb/```

### Compile

In the path to tensorflow, you can compile as following:

``` bazel build -c opt --config=cuda tensorflow/models/rnn/ptb:ptb_word_lm ```

If you don't have cuda, you can remove this: "--config=cuda".

Then for running you can use:

``` bazel-bin/tensorflow/models/rnn/ptb/ptb_word_lm --model {size} --data_path={Path To Folder Data} 
    --load={Path to model}
```

Supported sizes:

* small
* medium
* large
* normal

for our model we use normal. The data_path must have the ptb .txt files for training, cross and test sets, and 
load must be a model file if you want to use a pre-trained model, in our case model.ckpt.
 
# Generating...

For now you have to uncomment the lines from 371 to 374, then you compile it, and run.



