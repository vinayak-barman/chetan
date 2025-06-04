from typing import Callable, Literal, Sequence
import os
import pickle

from chetan.agent.module import AgentLoopModule
from chetan.lm import LMLegibleMessage
from chetan.tools import toolfn
from chetan.types.context.agent import EntityMessage, PrologueItem
from chetan.agent.module import prologue

from chetan.types.context.agent.iteration import AgentContext
from llama_index.core.schema import Document
from llama_index.core import VectorStoreIndex
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import BaseNode
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.base.embeddings.base import BaseEmbedding


from asq import query
from pydantic import BaseModel


class LlamaIndexItem(BaseModel):
    content: str
    source: str


class LlamaIndexResult(PrologueItem):
    items: list[LlamaIndexItem]

    def __str__(self):
        return "\n----------------------------------------n".join(
            f"Document: {item.content}\nSource: {item.source}" for item in self.items
        )

    def to_lm_legible(self):
        if not self.items:
            return []

        return LMLegibleMessage(
            role="system",
            content=str(self),
        )


class LlamaIndexRAGModule(AgentLoopModule):
    tool_namespace: str = "rag"

    def __init__(
        self,
        data_fn: Callable[[], list[Document]],
        mode: Literal["userquery", "iteration"] = "userquery",
        pipeline: IngestionPipeline = IngestionPipeline(
            transformations=[SentenceSplitter(chunk_size=128, chunk_overlap=64)]
        ),
        embed_model_fn: Callable[[], BaseEmbedding] = None,
        cache_path: str = "./temp/rag_cache.pkl",  # New argument for cache file
        **kwargs,
    ):
        """Initialize the LlamaIndexRAGModule with the provided data.

        Args:
            data (list[Document]): A list of documents to be indexed.
        """
        self.data_fn = data_fn
        self.pipeline = pipeline
        self.mode = mode
        self.embed_model_fn = embed_model_fn
        self.cache_path = cache_path
        self._kwargs = kwargs

        super().__init__()

    def setup(self):
        self.log("Loading embedding model...")
        self.embed_model = self.embed_model_fn() if self.embed_model_fn else None
        self.log("Finished loading embedding model.")

        # If cache_path is provided and file exists, load from cache
        if self.cache_path and os.path.exists(self.cache_path):
            self.log(f"Loading RAG pipeline state from cache: {self.cache_path}")
            with open(self.cache_path, "rb") as f:
                cache = pickle.load(f)

            self.nodes: Sequence[BaseNode] = cache["nodes"]
            self.log(f"Loaded {len(self.nodes)} nodes from cache.")
            self.index: VectorStoreIndex = cache["index"]
            self.retriever: BaseRetriever = cache["retriever"]
            self.log("Loaded index, retriever from cache.")
            return

        self.log("Loading data...")
        data = self.data_fn()
        if not data:
            raise ValueError("No data provided to the LlamaIndexRAGModule.")
        self.log(f"Loaded {len(data)} documents.")

        self.log("Running pipeline...")
        self.nodes = self.pipeline.run(documents=self.data_fn())
        self.log(f"Pipeline completed with {len(self.nodes)} nodes.")
        self.log("Creating index...")
        self.index, self.retriever = self.create_index(
            self.nodes, embed_model=self.embed_model, **self._kwargs
        )
        self.log("Finished creating index.")

        # Save to cache if cache_path is provided
        if self.cache_path:
            self.log(f"Saving RAG pipeline state to cache: {self.cache_path}")
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "wb") as f:
                pickle.dump(
                    {
                        "nodes": self.nodes,
                        "index": self.index,
                        "retriever": self.retriever,
                    },
                    f,
                )
            self.log("Saved RAG pipeline state to cache.")

    def create_index(self, nodes, **kwargs):
        """Create an index from the provided nodes.

        Args:
            nodes (Sequence[BaseNode]): A list of nodes to be indexed.

        Returns:
            _type_: _description_
        """
        index = VectorStoreIndex(nodes, **kwargs)
        retriever = index.as_retriever(**kwargs)
        return index, retriever

    def _retrieve(self, query):
        return self.retriever.retrieve(query)

    @toolfn
    def retrieve(self, query: str) -> LlamaIndexResult:
        """Retrieve relevant documents from the index based on the query.

        Args:
            query (str): The query string to search for.

        Returns:
            LlamaIndexResult: A result object containing a list of items with content and source that match the query.
        """
        retrieval = self._retrieve(query)
        return LlamaIndexResult(
            items=[
                LlamaIndexItem(
                    content=item.node.get_content(),
                    source=item.node.metadata["file_name"],
                )
                for item in retrieval
            ]
        )

    @prologue
    def retrieve_prologue(self, context: AgentContext, *args, **kwargs):
        """Retrieve relevant documents from the index based on the query."""
        if self.mode == "userquery":
            retrieve_query = (
                query(context.latest().prologue)
                .where(lambda x: isinstance(x, EntityMessage) and x.role == "user")
                .select(lambda x: x.content)
                .last_or_default(default=None)
            )

            if retrieve_query is None:
                return

        if self.mode == "iteration":
            retrieve_query = context.latest_complete_iteration().flatten()

        retrieval = self._retrieve(retrieve_query)

        context.add_item(
            LlamaIndexResult(
                items=[
                    LlamaIndexItem(
                        content=item.node.get_content(),
                        source=item.node.metadata["file_name"],
                    )
                    for item in retrieval
                ]
            ),
            "prologue",
        )
