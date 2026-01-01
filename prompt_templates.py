from typing import List
from models import DataResponse, LLMPromptTemplate


class AntiHallucinationPrompts:
    """Prompt templates with anti-hallucination mechanisms."""
    
    @staticmethod
    def create_strict_system_prompt() -> str:
        """Create system prompt with strict anti-hallucination rules."""
        return """You are a precise information retrieval assistant with STRICT anti-hallucination protocols.

CRITICAL RULES:
1. ONLY use information from the provided retrieved data sources
2. NEVER infer, assume, or generate information not explicitly in the sources
3. If confidence score is below threshold, respond with "I don't know"
4. If information_not_found flag is True, respond with "I don't know"
5. ALWAYS cite the source_id for every piece of information
6. If data conflicts between sources, acknowledge the conflict with source IDs
7. Be explicit about data limitations and gaps

RESPONSE FORMAT:
- Start with confidence assessment
- Provide information with [Source: source_type-source_id] citations
- End with data quality notes if applicable
- If uncertain or data insufficient: "I don't know. [Reason: ...]"

NEVER:
- Make up or infer information
- Extrapolate beyond the data
- Ignore low confidence scores
- Provide information without source citations"""
    
    @staticmethod
    def create_user_prompt(query: str, retrieved_data: List[DataResponse], confidence_threshold: float) -> str:
        """Create user prompt with retrieved data context."""
        prompt = f"""Query: {query}

Confidence Threshold: {confidence_threshold}

RETRIEVED DATA SOURCES:
"""
        
        for idx, data in enumerate(retrieved_data, 1):
            prompt += f"""\n--- Source {idx} ---
Source Type: {data.source_metadata.source_type.value}
Source ID: {data.source_metadata.source_id}
Table/Database: {data.source_metadata.table_name}
Confidence Score: {data.confidence.score:.3f}
Confidence Reasoning: {data.confidence.reasoning}
Information Found: {not data.information_not_found}
Verified: {data.verified}
"""
            
            if data.information_not_found:
                prompt += "Data: NONE - Information not found\n"
            elif data.data:
                prompt += f"Data: {data.data}\n"
            else:
                prompt += "Data: NONE\n"
            
            if data.additional_context:
                prompt += f"Additional Context: {data.additional_context}\n"
        
        prompt += """\n--- END OF RETRIEVED DATA ---

INSTRUCTIONS:
1. Analyze ONLY the retrieved data above
2. Check confidence scores against threshold
3. If ANY source has information_not_found=True or confidence below threshold, state limitations
4. Cite sources using [Source: source_type-source_id] format
5. If data is insufficient or confidence too low, respond: "I don't know. [Reason: ...]"

Provide your response:"""
        
        return prompt
    
    @staticmethod
    def create_template(query: str, retrieved_data: List[DataResponse], confidence_threshold: float = 0.85) -> LLMPromptTemplate:
        """Create complete LLM prompt template."""
        return LLMPromptTemplate(
            system_prompt=AntiHallucinationPrompts.create_strict_system_prompt(),
            user_prompt=AntiHallucinationPrompts.create_user_prompt(query, retrieved_data, confidence_threshold),
            retrieved_data=retrieved_data,
            strict_mode=True,
            confidence_threshold=confidence_threshold
        )
    
    @staticmethod
    def create_validation_prompt(query: str, llm_response: str, retrieved_data: List[DataResponse]) -> str:
        """Create prompt to validate LLM response against retrieved data."""
        return f"""Validate the following LLM response against the retrieved data.

Original Query: {query}

LLM Response: {llm_response}

Retrieved Data Sources: {len(retrieved_data)}

Validation Checklist:
1. Does the response ONLY use information from retrieved data?
2. Are all facts properly cited with source IDs?
3. Does the response respect confidence scores?
4. If data was insufficient, did it respond "I don't know"?
5. Are there any hallucinated facts?

Provide validation result (PASS/FAIL) and explanation:"""
    
    @staticmethod
    def format_dont_know_response(reason: str, sources: List[DataResponse]) -> str:
        """Format a proper 'I don't know' response."""
        response = f"I don't know. {reason}\n\n"
        response += "Data Quality Summary:\n"
        
        for idx, source in enumerate(sources, 1):
            response += f"- Source {idx} ({source.source_metadata.source_type.value}): "
            if source.information_not_found:
                response += "No information found\n"
            else:
                response += f"Confidence {source.confidence.score:.3f} - {source.confidence.reasoning}\n"
        
        return response