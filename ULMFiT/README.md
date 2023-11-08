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
    - $\eta^{l} = \frac{\eta^{l-1}}{2.6}$, where $\eta^{l}$ is the learning rate for the l $^{th}$ layer.
- slanted triangular learning rate
    - learning rate increased in initial iterations and decreased gradually after a cutoff of `#iter` is reached.
    - correlate this with how in MD (PEM) intially SD was used and then conjugate gradient to pin-point the minima, 
      - higher learning rates are required to locate points in the close vicinity of the minima/optima.
      - lower learning rates are required to control the *jumps* so that the minima/optima is perfectly/near-perfectly located.
- gradual unfreezing.
    - 

## Classifier Tuning
1. ReLU + Softmax Blocks
2. feature set for this task = \[$h_T$, maxpool(H), meanpool(H)\], where H = \{$h_1$, $h_2$, $h_3$.....$h_T$\} is the vector output by the language model, T: #iterations.

## Preprocessing
1. this is how the input documents were pre-processed
2. along with the characters `abcdefghijklmnopqrstuvwxyz0123456 789-,;.!?:’"/| #$%ˆ&* ̃‘+=<>()[]{}`, special tokens for padding , space , unknown were used.
    1. the input sequence was padded till length is 1014, and sequences longer than 1014 were trimmed at 1014'th token.
    2. unlike previous papers by the same authors(upper case to lower case), tokens to represent upper-case letters were also used, along with tokens for *elongation* and *repetition*.
3. 