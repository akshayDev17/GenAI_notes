# Janus 1.3B
- lightweight image understanding and generating LLM

## Preface
- multimodal understanding vs visual generation
    - former: understanding a given image, latter: generating an image given instructions
    - former: necessitates maximum information-retention, hence requires high-dimensional encoding; latter: generated image should be coherent(global consistency) + key details of instructions to be followed ===> no need of unnecessary complexities ===> low-dimensional encoding.
- most models: unified, i.e. use the same encoder for both tasks.
    - **performance tradeoff**: multimodal understanding suffers if the encoder is a low-dimensional encoder OR coherence of the generated image suffers if a high-dimensional encoder is used instead.
- Janus resolves this by having a separate encoding pathway for each of these tasks.
    - i.e. it decouples visual encoding from the task at hand.
    - this architectural principle can be extended to other kinds of inputs, such as EEG-signals, point clouds, audio data.

## Reference papers
- easy to understand but lacks detail: [Janus: Decoupling Visual Encoding for Unified Multimodal Understanding and Generation](https://arxiv.org/pdf/2410.13848)
- more complex but details the architecture: [JanusFlow: Harmonizing Autoregression and Rectified Flow for Unified Multimodal Understanding and Generation](https://arxiv.org/pdf/2411.07975)

## Notes
- LLM is the autoregressive transformer used commonly for both tasks.
- the generation decoder is the SDXL-VAE (stable diffusion XL variational autoencoder) as its the one that translates the codeblock-space generated image(by the LLM) back to the latent space(which is continuous in nature).
- velocity vector is the output of the image generation task part of Janus
    - given the prompt, i.e. $x^{con}$(conditioned on the prompt), the velocity(i.e. current timestep LLM output) is $v(z_t, t|x^{con})$, and for the same timestep if a forward pass would've been performed with no condition, the velocity is $v(z_t, t | \phi)$. the final velocity term used ($v(z_t)$) is a weighted sum of these 2 quantities, with the weights being $w$ and $1-w$ respectively.
    - this approach =  *classifier-free guidance*
    - higher w ==> higher <font color="red">semantic alignment</font>. (whatever this means w.r.t. images)
- [perplexity chat session on Janus 1.3B](https://www.perplexity.ai/search/janus-1-3-b-explain-_BCBwkNFSy.epxJvXxLjpQ)

# Project Ideas

## Company-specific potential usecases
### Marketing Content
1. Develop visually appealing promotional graphics and social media content that align with game themes and narratives.([Wooga, Germany](https://www.wooga.com))
2. Develop engaging advertisements that combine compelling visuals and informative text about Tesla's innovations.
3. Create personalized marketing materials that showcase local restaurants and dishes tailored to user preferences. ([Delivery Hero, Germany](https://www.deliveryhero.com))
4. Generate personalized marketing content showcasing local offers and services available through the Gojek app.

