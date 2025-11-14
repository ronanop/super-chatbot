"""
Query enhancement service for improving knowledge base retrieval.
Expands and rewrites queries to improve semantic search results.
"""

from __future__ import annotations

import logging
from typing import List

from app.services.gemini import get_generation_model

logger = logging.getLogger(__name__)


def expand_query(query: str, use_llm: bool = True) -> List[str]:
    """
    Expand a query into multiple variations to improve retrieval.
    Returns a list of query variations including the original.
    
    Args:
        query: Original user query
        use_llm: Whether to use LLM for expansion (slower but better) or simple rules (faster)
    """
    query_lower = query.lower().strip()
    words = query_lower.split()
    
    # Always start with original query
    expansions = [query]
    
    # Extract key terms (names, important words)
    key_terms = []
    if "who is" in query_lower:
        name = query_lower.replace("who is", "").strip()
        if name:
            key_terms.append(name)
    elif "who are" in query_lower:
        name = query_lower.replace("who are", "").strip()
        if name:
            key_terms.append(name)
    elif "what is" in query_lower:
        term = query_lower.replace("what is", "").strip()
        if term:
            key_terms.append(term)
    else:
        # Extract words longer than 3 chars (likely names/important terms)
        key_terms = [w for w in words if len(w) > 3 and w not in ["about", "information", "details"]]
    
    # Simple rule-based expansion (fast and effective)
    if key_terms:
        for term in key_terms[:2]:  # Limit to first 2 key terms
            expansions.extend([
                f"{term}",
                f"information about {term}",
                f"details about {term}",
                f"{term} leadership",
                f"{term} team",
                f"about {term}",
                f"{term} member"
            ])
    
    # Add question variations
    if "who is" in query_lower:
        name = query_lower.replace("who is", "").strip()
        if name:
            expansions.extend([
                f"who is {name} in the team",
                f"who is {name} in leadership",
                f"{name} role",
                f"{name} position"
            ])
    
    # Use LLM expansion for very short queries if enabled (adds latency but better results)
    if use_llm and len(words) <= 3 and key_terms:
        try:
            model = get_generation_model()
            
            # Quick, focused expansion prompt
            expansion_prompt = f"""Generate 3 alternative search queries for finding information about "{key_terms[0]}" in a knowledge base. 
Return only the queries, one per line, no numbering. Make them specific and varied.

Example for "shraddha":
shraddha leadership team
information about shraddha
shraddha role and position

Now for "{key_terms[0]}":"""

            result = model.generate_content(expansion_prompt)
            expanded_text = getattr(result, "text", "").strip()
            
            if expanded_text:
                llm_variations = [line.strip() for line in expanded_text.split("\n") if line.strip() and len(line.strip()) > 5]
                # Remove any that are too similar to what we already have
                for var in llm_variations[:3]:
                    if var.lower() not in [e.lower() for e in expansions]:
                        expansions.append(var)
        except Exception as e:
            logger.debug(f"LLM query expansion failed: {e}, using rule-based only")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_expansions = []
    for exp in expansions:
        exp_lower = exp.lower().strip()
        if exp_lower and exp_lower not in seen:
            seen.add(exp_lower)
            unique_expansions.append(exp)
    
    return unique_expansions[:8]  # Limit to 8 variations


def enhance_query_for_search(query: str, use_llm: bool = False) -> List[str]:
    """
    Enhance query for better semantic search.
    Returns multiple query variations to try.
    
    Args:
        query: Original user query
        use_llm: Whether to use LLM for expansion (adds ~200-500ms latency)
    """
    # Get expanded queries (rule-based is fast, LLM is better but slower)
    expanded = expand_query(query, use_llm=use_llm)
    
    return expanded

