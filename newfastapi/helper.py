from langchain_qdrant import QdrantVectorStore
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()


def reciprocal_rank_fusion(ranked_lists:list[list[any]], k: float = 60.0):     
    score_map = defaultdict(float)
    doc_map = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            # Use metadata _id if available, otherwise hash page_content
            doc_id = doc.metadata.get("_id") if "_id" in doc.metadata else hash(doc.page_content)
            
            score_map[doc_id] += 1.0 / (k + rank)
            doc_map[doc_id] = doc   # keep the doc itself

    # Sort by descending fused score
    sorted_docs = sorted(score_map.items(), key=lambda x: x[1], reverse=True)

    # Return the actual documents with their scores
    return [(doc_map[doc_id], score) for doc_id, score in sorted_docs]



def fanout(collection_name:str,query:str,embedder,k,client):
    
        retriever = QdrantVectorStore.from_existing_collection(
                url=os.environ.get("QDRANT_URL"),
                api_key=os.environ.get("QDRANT_KEY"),
                collection_name=collection_name,
                embedding=embedder,
            )   
        
        FanOut_SYSTEM_PROMPT="""
        you are Ai assistant. you have to generate 3 similar questions based on the question:{search_query}

        rules:
        - every generate question should be differentiate using "\\\n"
        - the questions should be related to the original question.
        - generate 3 similar questions based on the question.
        - don't include the 'question' word in your answer.
        """
        
        parallel_questions=client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": FanOut_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        )
        
        unique_chunks=[]
        for question in (parallel_questions.choices[0].message.content).split("\\\n"):
            relevant_chunks = retriever.similarity_search(question)
            print("relevant chunk",relevant_chunks)
            unique_chunks.append(relevant_chunks)
        
        ranked_chunks=reciprocal_rank_fusion(unique_chunks)
        print(ranked_chunks)
        final_context_docs = [doc.page_content for doc, _ in ranked_chunks[:k]]
       
        final_context = ",".join(final_context_docs)
        
        return final_context
    