import bs4
from langchain_community.document_loaders import WebBaseLoader

# Only keep post title, headers, and content from the full HTML.
bs4_strainer = bs4.SoupStrainer(class_=("post-title", "post-header", "post-content"))
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs={"parse_only": bs4_strainer},
)

# # eager load
# docs = loader.load()
# print(len(docs[0].page_content), "\n", docs[0].metadata)

# # eager async load
# aload_docs = loader.aload()
# print(len(aload_docs[0].page_content), "\n", aload_docs[0].metadata)

import re

escaped_string = re.escape("\n\n")
print(escaped_string)
