from core.clients import gemini
from constants import GEMINI_MODEL
from core.retriever import build_context, query_codebase, rerank
from deepeval.tracing import observe

@observe()
async def generate(question: str, context: str) -> str | None:
  prompt = f"""You are a code assistant. Answer the user's question using ONLY the code chunks provided.
For every claim you make, cite the file and line numbers like this: `src/server/http.ts (lines 13–72)`.
If the answer isn't in the provided chunks, say so — do not guess.

<code_context>
{context}
</code_context>

Question: {question}"""

  response = await gemini.aio.models.generate_content(model=GEMINI_MODEL,contents=prompt)
  return response.text

@observe()
async def ask(question: str, repo: str, candidate_k: int = 20, final_k: int = 5):
    results = await query_codebase(question, repo=repo, top_k=candidate_k )
    reranked = await rerank(question, results, top_k=final_k)
    context = build_context(reranked)
    response_text = await generate(question, context)
    return response_text, reranked  