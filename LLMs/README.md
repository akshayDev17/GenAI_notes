# Temperature
- is a non-negative number said to "enhance creativity"
    - this can be thought of as a dial that controls *exploration vs exploitation*
    - `temperature < 1`: exploiting patterns learnt by the model in training data.
    - `temperature > 1`: exploring patterns not so characteristic of the training data, yielding *diverse* outputs.
- under the hood, the *manner* in which the *output tokens are selected* using their generation-probability is *changed by* using *temperature*.
- for reference, in the Llama3 model, when `temperature <= 0`, argmax is used, i.e. token with max. probability is selected as output.
    > say that `probs = [0 .1 .2 .3 .4]`, then the token selected is the 5th token(index = 4) as it has the highest probability.
- conversely, when temperature(> 1) is used:
    - the tokens selected as output-tokens using their generated probabilities are selected using the [`sample_top_p`](https://github.com/meta-llama/llama3/blob/main/llama/generation.py#L343) function
    - this uses `torch.multinomial` whose outputs are truly stochastic, regardless of usage of the same temperature value(provided its > 1).
        > Top-p sampling selects the smallest set of tokens whose cumulative probability mass exceeds the threshold p. The distribution is renormalized based on the selected tokens. \
        For `temperature = 1`, `probs = [0 .1 .2 .3 .4]`, `p(threshold) = 0.25` --> `probs_sort = [.4 .3 .2 .1 0]`, `probs_sum = [.4 .7 .9 1 1]`, [0 .4 .7 .9 1], `mask = [F T T T T]`, `probs_sort = [.4 0 0 0 0]`, `next_token = [4]`(ultimately)
    - on using `temperature = 2`
        ```python
        probs, p = [0 .05 .1 .15 .2], 0.25
        probs_sort, probs_idx = [.2 .15 .1 .05 0], [4 3 2 1 0]
        probs_sum = [.2 .35 .45 .5 .5]
        # probs_sum - probs_sort = [0 0.2 0.35 0.45 0.5]
        mask = probs_sum - probs_sort > p # [F F T T T]
        probs_sort[mask] = 0.0 # [.2 .15 0 0 0] 
        probs_sort.div_(probs_sort.sum(dim=-1, keepdim=True)) # [4/7 3/7 0 0 0]
        next_token = torch.multinomial(probs_sort, num_samples = 1) # [1] (or could be [0])
        next_token = torch.gather(probs_idx, -1, next_token) # if prev. step was [0], output = [4], for [1] its [3]
        ```