# Resources
1. https://www.youtube.com/watch?v=RKV8rqOZ63g

# Notes

- text classification(spam, fraud, emergency response, doc classification)
- transfer learning for language models.
    - input model: predict next word using given a sequence(source task).
    - input model fine-tuned to perform text classification(target task).
    - unsupervised.
- discriminative fine-tuning
    - learning rate for each layer of the LM.
    - $\eta^{l} = \frac{\eta^{l-1}}{2.6}$, where $\eta^{l}$ is the learning rate for the l$^{th}$ layer.
- slanted triangular learning rate
    - learning rate increased in initial iterations and decreased gradually after a cutoff of `#iter` is reached.
- gradual unfreezing.
    - 

## Classifier Tuning
1. ReLU + Softmax Blocks
2. feature set for this task = \[$h_T$, maxpool(H), meanpool(H)\], where H = \{$h_1$, $h_2$, $h_3$.....$h_T$\} is the vector output by the language model, T: #iterations.