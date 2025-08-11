import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI()

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.get("/health/")
async def health_check():
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url="http://localhost:6333")
        qdrant.get_collections()  # Test Qdrant connection
        client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Test"}]
        )  # Test OpenAI connection
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.post("/query/")
async def process_query(request: QueryRequest):
    try:
        query = request.query

        # Embedding
        embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

        # Connect to Qdrant
        try:
            vector_db = QdrantVectorStore.from_existing_collection(
                url="http://localhost:6333",
                collection_name='learn_vector',
                embedding=embedding_model
            )
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant collection: {str(e)}", exc_info=True)
            raise HTTPException(status_code=400, detail="No documents uploaded. Please upload a PDF first.")

        # Search
        search_result = vector_db.similarity_search(query=query)
        if not search_result:
            logger.warning(f"No relevant documents found for query: {query}")
            raise HTTPException(status_code=400, detail="No relevant information found in the uploaded documents.")

        # Format context
        context = "\n\n\n".join([
            f"page_content: {result.page_content} \n page_label: {result.metadata.get('page_label', None)}"
            for result in search_result
        ])

        # System prompt
        SYSTEM_PROMPT = f"""
        YOU ARE AN EXPERT INSURANCE ASSISTANT SPECIALIZED IN SEMANTIC RETRIEVAL FROM POLICY DOCUMENTS.

        YOUR OBJECTIVE:
        To help the user understand if their insurance policy covers a specific situation by:
        1. Rewriting their query into 4–5 formal, semantically diverse search queries.
        2. Retrieving evidence for each query using the knowledge_base tool (vector search).
        3. Answering each query with a formal Yes, No, or Not Sure along with a legal-style justification.
        4. Retrying any query that results in Not Sure due to poor retrieval (max 2 retries).
        5. Producing a final combined answer: Yes or No + justification using all the retrieved context.

        ---

        ### STEP 1: ANALYZE THE USER'S QUESTION

        Extract key dimensions from the plain-English query:
        - Insurance type (health, life, motor)
        - Concern (e.g., surgery, maternity, exclusion, accident)
        - Attributes (age, procedure, city, gender, policy duration)
        - Legal concepts (waiting period, pre-existing disease, network hospital, sub-limit, daycare, permanent exclusion)

        ---

        ### STEP 2: GENERATE 4–5 SEMANTIC SEARCH QUERIES

        Create legally precise, embedding-friendly semantic queries to explore different angles like:
        - Coverage eligibility
        - Waiting periods
        - Exclusion clauses
        - Day care vs hospitalization classification
        - Geographic/network constraints

        **Example Input Query:**
        "46-year-old male, knee surgery in Pune, 3-month-old health insurance policy"

        **Generated Semantic Queries:**
        ```json
        [
        "Does the policy cover arthroscopic knee surgery under day care treatments?",
        "Is knee meniscectomy eligible for claim under a 3-month-old health insurance policy?",
        "Are orthopedic surgeries excluded within the first 90 days of policy inception?",
        "Is a 46-year-old eligible for knee replacement coverage under current waiting period clauses?",
        "Are knee surgeries in Pune hospitals eligible for network hospital reimbursement?"
        ]
        ```

        ### STEP 3: FOR EACH SEMANTIC QUERY

        1. RETRIEVE:
        - Use the `knowledge_base` tool to fetch top 3–5 relevant policy chunks.

        2. EVALUATE:
        - If relevant information is retrieved:
            - Answer: "Yes" or "No"
            - Justify based on actual clauses or logic.
        - If information is insufficient or ambiguous:
            - Answer: "Not sure"
            - Justify that retrieval was vague or lacking

        3. RETRY ON “NOT SURE”:
        - Rephrase the query to be more specific
        - Retry retrieval and evaluation
        - Max 4 attempts per query
        {
        "query": "<semantic_query>",
        "answer": "Yes | No | Not sure",
        "justification": "<short legal-style justification based on retrieved text>"
        }

        ### STEP 4: COMBINE FINAL ANSWER

        After all semantic queries have been resolved:

        1. Synthesize a final judgment: Yes or No
        (based on the majority or most decisive answers from above)

        2. Justify the answer using the retrieved evidence:
        • Refer to waiting period/exclusion clauses
        • Mention any exceptions
        • Be formal and objective

        Final Answer Format:
        {
        "final_answer": {
            "answer": "Yes | No",
            "justification": "<Formal summary combining all findings from individual queries>"
        }
        }

        RULES & SAFETY
        Only say “Not sure” if retrieval was truly insufficient. Otherwise, retry.

        Stop retrying after 4 attempts per query

        Avoid assumptions — rely on retrieved text only.

        Be formal, factual, and contract-aware.

        Never return partial or vague final answers — always return a clear Yes/No + justification.

        GOAL
        Help users confidently understand their insurance rights and claim eligibility using:

        Multiple legal perspectives

        Vector-based retrieval

        Retry on failure

        Clear final outcome

        Context:
        {context}
        """

        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': query}
            ]
        )
        logger.debug(f"OpenAI response: {response.choices[0].message.content}")

        return {"response": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))