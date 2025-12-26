from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from sqlalchemy.sql.expression import func
from core.database import get_async_session
from models.knowledge_doc_model import KnowledgeDoc
from schemas import SearchFilters
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Using OpenAI Embeddings as requested (Size 1536)
# Ensure OPENAI_API_KEY is in .env
def get_embeddings_model():
    return OpenAIEmbeddings(model="text-embedding-3-small")  # or text-embedding-ada-002

class RetrievalService:
    def __init__(self):
        # Initialize LLM for query analysis (using GPT-4o keys from env)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.embeddings = get_embeddings_model()
        
        # Setup Pydantic parser
        self.parser = PydanticOutputParser(pydantic_object=SearchFilters)
        
        # Prompt for extracting filters
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at extracting search filters from natural language queries.\n"
                       "Extract the following fields using the provided schema:\n"
                       "- query_text: The core keyword for search.\n"
                       "- start_date/end_date: If time is mentioned (convert relative dates like 'yesterday' to YYYY-MM-DD).\n"
                       "- source_type: If a source is mentioned (e.g., 'notion', 'slack').\n"
                       "- tags: Any specific tags mentioned.\n"
                       "\n{format_instructions}"),
            ("user", "{query}")
        ]).partial(format_instructions=self.parser.get_format_instructions())
        
        self.chain = self.prompt | self.llm | self.parser

    async def extract_filters(self, query: str) -> SearchFilters:
        """Extract structured filters from natural language query."""
        return await self.chain.ainvoke({"query": query})

    async def search_documents(self, user_query: str, session: AsyncSession, limit: int = 5) -> List[KnowledgeDoc]:
        """
        Perform a search using Metadata Pre-filtering Strategy.
        """
        # 1. Extract Filters
        filters = await self.extract_filters(user_query)
        print(f"DEBUG: Extracted Filters: {filters}")

        # 2. Get Query Embedding
        query_vector = await self.embeddings.aembed_query(filters.query_text)

        # 3. Construct Dynamic SQL Query
        stmt = select(KnowledgeDoc)
        conditions = []

        # Filter: User ID (Example: assuming we have context, passed externally or via filter. 
        # Here we assume the filter *could* contain it, or we rely on the caller to enforce tenancy.
        # For this refactor, we'll focus on the extracted fields. 
        # In a real app, user_id should be passed as an argument to this function for security.)
        
        # Filter: Source Type
        if filters.source_type:
            conditions.append(KnowledgeDoc.source_type == filters.source_type)
        
        # Filter: Date Range
        if filters.start_date:
            conditions.append(KnowledgeDoc.created_at >= filters.start_date)
        if filters.end_date:
            conditions.append(KnowledgeDoc.created_at <= filters.end_date)
            
        # Filter: Tags (using Postgres Array overlap usually, or contains)
        if filters.tags:
            # Assumes tags column is ARRAY(String). 
            # '&&' operator checks for overlap.
            conditions.append(KnowledgeDoc.tags.overlap(filters.tags))

        # Apply WHERE clauses
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # 4. Vector Similarity Search (using pgvector cosine distance: <=>)
        # Order by distance ASC
        stmt = stmt.order_by(KnowledgeDoc.embedding.cosine_distance(query_vector))
        
        # Limit results
        stmt = stmt.limit(limit)

        # 5. Execute
        result = await session.execute(stmt)
        docs = result.scalars().all()
        
        return docs

# Standalone function for easy usage
async def retrieve_with_filters(user_query: str, session: AsyncSession) -> List[KnowledgeDoc]:
    service = RetentionService()
    return await service.search_documents(user_query, session)
