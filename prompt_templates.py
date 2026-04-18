from typing import List, Dict, Any, Optional
from models import DataResponse, LLMPromptTemplate, MultiSourceResponse, ConfidenceScore
from datetime import datetime


class AntiHallucinationPrompts:
    """Enhanced prompt templates with multi-level anti-hallucination mechanisms."""
    
    # Confidence threshold levels
    STRICT_THRESHOLD = 0.90
    MODERATE_THRESHOLD = 0.85
    LENIENT_THRESHOLD = 0.75
    
    @staticmethod
    def create_strict_system_prompt() -> str:
        """Create system prompt with STRICT anti-hallucination rules.
        
        Use for: Critical applications, medical, legal, financial data
        """
        return """You are a precision-focused information retrieval assistant with MAXIMUM anti-hallucination protocols.

⚠️  CRITICAL RULES - ZERO TOLERANCE FOR HALLUCINATIONS:

1. DATA SOURCE RESTRICTIONS:
   - ONLY use information explicitly present in the provided retrieved data sources
   - NEVER infer, extrapolate, assume, or generate information beyond the exact data provided
   - DO NOT combine information from sources unless explicitly instructed
   - REJECT any request to speculate or guess

2. CONFIDENCE THRESHOLD ENFORCEMENT:
   - If ANY source has confidence score below threshold: Respond "I don't know"
   - If information_not_found flag is True for ALL sources: Respond "I don't know"
   - If aggregated_confidence < threshold: Respond "I don't know"
   - If NO sources are verified: Respond "I don't know"

3. SOURCE CITATION REQUIREMENTS:
   - EVERY piece of information MUST be cited with [Source: {source_type}-{source_id}]
   - Include timestamp if data freshness is relevant: [Source: {source_type}-{source_id}, Retrieved: {timestamp}]
   - For multi-source information: List ALL sources that confirm the data

4. DATA CONFLICT HANDLING:
   - If sources contradict each other: Acknowledge conflict explicitly
   - Format: "Source A states X [Source: A], while Source B states Y [Source: B]"
   - DO NOT attempt to resolve conflicts - present both with citations
   - Note confidence scores for conflicting sources

5. DATA QUALITY TRANSPARENCY:
   - Explicitly state data limitations and gaps
   - Mention missing fields or incomplete data
   - Report any verification failures
   - Note if data is outdated (use retrieved_at timestamp)

6. RESPONSE STRUCTURE:
   a) Confidence Assessment: State overall confidence and threshold status
   b) Core Information: Provide data with complete citations
   c) Data Quality Notes: Any limitations, conflicts, or concerns
   d) Conclusion: Clear statement if uncertain or data insufficient

7. PROHIBITED ACTIONS:
   ❌ Making up or fabricating information
   ❌ Inferring beyond the explicit data
   ❌ Ignoring low confidence scores
   ❌ Providing uncited information
   ❌ Combining data without clear source separation
   ❌ Answering when confidence is below threshold
   ❌ Using external knowledge not in retrieved data

8. "I DON'T KNOW" REQUIREMENTS:
   When responding "I don't know", ALWAYS provide:
   - Specific reason (e.g., "confidence below threshold", "no data found")
   - List of queried sources and their status
   - What information WAS found (if any)
   - Suggestions for improving the query (if applicable)

RESPONSE FORMAT:
```
[CONFIDENCE: {score}/1.0 | Threshold: {threshold} | Status: {PASS/FAIL}]

{Your response with [Source: ...] citations}

[DATA QUALITY NOTES]
- Source reliability: ...
- Data completeness: ...
- Potential limitations: ...

[CONCLUSION]
{Clear statement about certainty level}
```

Remember: It is ALWAYS better to say "I don't know" than to provide uncertain information."""

    @staticmethod
    def create_moderate_system_prompt() -> str:
        """Create system prompt with MODERATE anti-hallucination rules.
        
        Use for: General applications, informational queries, standard operations
        """
        return """You are a careful information retrieval assistant with strong anti-hallucination protocols.

IMPORTANT RULES:

1. DATA SOURCE USAGE:
   - Primarily use information from the provided retrieved data sources
   - NEVER fabricate or guess information not present in sources
   - Minor reasonable inferences are allowed if clearly marked as such
   - External general knowledge may be used for context ONLY if marked as "[General Knowledge]"

2. CONFIDENCE THRESHOLD COMPLIANCE:
   - If aggregated_confidence < threshold: Respond "I don't know" OR provide heavily qualified answer
   - If ALL sources show information_not_found: Respond "I don't know"
   - If confidence is marginal (within 0.05 of threshold): Add strong disclaimers

3. SOURCE CITATION:
   - MUST cite sources for all factual claims: [Source: {source_type}-{source_id}]
   - General statements may be less strictly cited if based on multiple sources
   - Always cite when presenting numbers, dates, or specific facts

4. DATA CONFLICTS:
   - Acknowledge conflicts between sources
   - May attempt resolution by considering confidence scores
   - Format: "Based on higher confidence source X [0.92]: ..."

5. QUALIFIED RESPONSES:
   - Use qualifiers when confidence is not high: "likely", "appears to", "suggests"
   - Be explicit about certainty level
   - Note any data quality concerns

6. RESPONSE FORMAT:
```
[Confidence: {score} | Threshold: {threshold}]

{Response with appropriate citations}

{Data quality notes if relevant}
```

PROHIBITED:
- Complete fabrication of facts
- Ignoring very low confidence scores (< threshold - 0.10)
- Providing information without any source basis"""

    @staticmethod
    def create_lenient_system_prompt() -> str:
        """Create system prompt with LENIENT anti-hallucination rules.
        
        Use for: Exploratory queries, brainstorming, creative applications
        Note: Still maintains baseline accuracy requirements
        """
        return """You are a helpful information retrieval assistant with baseline anti-hallucination measures.

GUIDELINES:

1. DATA SOURCES:
   - Use provided retrieved data as primary information source
   - May supplement with relevant general knowledge, clearly marked
   - Reasonable inferences are allowed with appropriate qualifiers

2. CONFIDENCE AWARENESS:
   - Monitor confidence scores and note when below threshold
   - Provide warnings for low-confidence information
   - Still respond "I don't know" if ALL sources are unavailable

3. CITATIONS:
   - Cite sources for key facts and specific data points
   - May use general citations for well-supported information: [Sources: multiple]

4. HELPFUL RESPONSES:
   - Balance accuracy with usefulness
   - Provide context and explanations
   - Acknowledge but don't be paralyzed by uncertainty

5. TRANSPARENCY:
   - Note confidence levels
   - Acknowledge data limitations
   - Use qualifiers appropriately

STILL PROHIBITED:
- Deliberate fabrication
- Ignoring critical data quality issues"""

    @staticmethod
    def create_user_prompt(
        query: str, 
        retrieved_data: List[DataResponse], 
        confidence_threshold: float,
        include_detailed_metadata: bool = True,
        include_confidence_analysis: bool = True
    ) -> str:
        """Create comprehensive user prompt with retrieved data context."""
        
        prompt = f"""QUERY: {query}

CONFIDENCE THRESHOLD: {confidence_threshold}
TOTAL SOURCES: {len(retrieved_data)}
TIMESTAMP: {datetime.utcnow().isoformat()}

═══════════════════════════════════════════════════════════
RETRIEVED DATA SOURCES:
═══════════════════════════════════════════════════════════
"""
        
        # Track overall data quality
        sources_with_data = 0
        verified_sources = 0
        total_confidence = 0.0
        
        for idx, data in enumerate(retrieved_data, 1):
            source_id = data.source_metadata.source_id
            source_type = data.source_metadata.source_type.value
            
            # Source header
            prompt += f"\n{'─' * 60}\n"
            prompt += f"SOURCE {idx}: {source_type.upper()}\n"
            prompt += f"{'─' * 60}\n"
            
            # Core metadata
            prompt += f"Source ID: {source_id}\n"
            
            if data.source_metadata.table_name:
                prompt += f"Table/Database: {data.source_metadata.table_name}\n"
            
            # Confidence information
            prompt += f"\n📊 CONFIDENCE ANALYSIS:\n"
            prompt += f"   Score: {data.confidence.score:.3f} / 1.000\n"
            prompt += f"   Status: {'✓ MEETS THRESHOLD' if data.confidence.score >= confidence_threshold else '✗ BELOW THRESHOLD'}\n"
            prompt += f"   Reasoning: {data.confidence.reasoning}\n"
            
            if include_confidence_analysis and data.confidence.factors:
                prompt += f"   Factors:\n"
                for factor_name, factor_value in data.confidence.factors.items():
                    prompt += f"      - {factor_name}: {factor_value:.3f}\n"
            
            # Data status
            prompt += f"\n🔍 DATA STATUS:\n"
            prompt += f"   Information Found: {'NO ❌' if data.information_not_found else 'YES ✓'}\n"
            prompt += f"   Verified: {'YES ✓' if data.verified else 'NO ❌'}\n"
            prompt += f"   Retrieved: {data.source_metadata.retrieved_at.isoformat()}\n"
            
            # The actual data
            if data.information_not_found:
                prompt += f"\n📄 DATA: NONE - No information found in this source\n"
            elif data.data is not None:
                prompt += f"\n📄 DATA:\n"
                # Format data nicely
                if isinstance(data.data, dict):
                    for key, value in data.data.items():
                        prompt += f"   {key}: {value}\n"
                elif isinstance(data.data, list):
                    for item in data.data[:5]:  # Limit to first 5 items
                        prompt += f"   - {item}\n"
                    if len(data.data) > 5:
                        prompt += f"   ... and {len(data.data) - 5} more items\n"
                else:
                    prompt += f"   {data.data}\n"
            else:
                prompt += f"\n📄 DATA: NULL\n"
            
            # Additional context
            if data.additional_context:
                prompt += f"\n⚠️  ADDITIONAL CONTEXT: {data.additional_context}\n"
            
            # Detailed metadata
            if include_detailed_metadata:
                if data.source_metadata.query_params:
                    prompt += f"\n🔧 QUERY PARAMS: {data.source_metadata.query_params}\n"
                if data.source_metadata.raw_data_hash:
                    prompt += f"🔐 DATA HASH: {data.source_metadata.raw_data_hash[:16]}...\n"
            
            # Update tracking
            if not data.information_not_found:
                sources_with_data += 1
            if data.verified:
                verified_sources += 1
            total_confidence += data.confidence.score
        
        # Summary section
        prompt += f"\n{'═' * 60}\n"
        prompt += f"DATA QUALITY SUMMARY:\n"
        prompt += f"{'═' * 60}\n"
        prompt += f"Sources with Data: {sources_with_data}/{len(retrieved_data)}\n"
        prompt += f"Verified Sources: {verified_sources}/{len(retrieved_data)}\n"
        
        if len(retrieved_data) > 0:
            avg_confidence = total_confidence / len(retrieved_data)
            prompt += f"Average Confidence: {avg_confidence:.3f}\n"
            prompt += f"Threshold Status: {'✓ ACCEPTABLE' if avg_confidence >= confidence_threshold else '✗ BELOW THRESHOLD'}\n"
        
        # Instructions
        prompt += f"\n{'═' * 60}\n"
        prompt += f"INSTRUCTIONS:\n"
        prompt += f"{'═' * 60}\n"
        prompt += """
1. ANALYZE the retrieved data carefully
2. CHECK all confidence scores against the threshold
3. VERIFY that at least one source is verified
4. CITE sources using format: [Source: {source_type}-{source_id}]
5. If confidence is below threshold: State "I don't know" with clear reasoning
6. If data conflicts exist: Present all versions with source citations
7. Be explicit about any data limitations or concerns

PROVIDE YOUR RESPONSE:
"""
        
        return prompt

    @staticmethod
    def create_template(
        query: str, 
        retrieved_data: List[DataResponse], 
        confidence_threshold: float = 0.85,
        strictness_level: str = "strict"
    ) -> LLMPromptTemplate:
        """Create complete LLM prompt template with specified strictness level.
        
        Args:
            query: User's query string
            retrieved_data: List of retrieved data responses
            confidence_threshold: Minimum confidence threshold
            strictness_level: "strict", "moderate", or "lenient"
        """
        # Select appropriate system prompt
        if strictness_level == "strict":
            system_prompt = AntiHallucinationPrompts.create_strict_system_prompt()
        elif strictness_level == "moderate":
            system_prompt = AntiHallucinationPrompts.create_moderate_system_prompt()
        elif strictness_level == "lenient":
            system_prompt = AntiHallucinationPrompts.create_lenient_system_prompt()
        else:
            raise ValueError(f"Invalid strictness level: {strictness_level}")
        
        user_prompt = AntiHallucinationPrompts.create_user_prompt(
            query, 
            retrieved_data, 
            confidence_threshold
        )
        
        return LLMPromptTemplate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            retrieved_data=retrieved_data,
            strict_mode=(strictness_level == "strict"),
            confidence_threshold=confidence_threshold
        )

    @staticmethod
    def create_validation_prompt(query: str, llm_response: str, retrieved_data: List[DataResponse]) -> str:
        """Create comprehensive validation prompt for LLM response verification."""
        return f"""TASK: Validate the following LLM response for hallucinations and accuracy.

ORIGINAL QUERY: {query}

LLM RESPONSE TO VALIDATE:
─────────────────────────────────────────────────────────
{llm_response}
─────────────────────────────────────────────────────────

RETRIEVED DATA AVAILABLE ({len(retrieved_data)} sources):
{chr(10).join([
    f"- {data.source_metadata.source_type.value} ({data.source_metadata.source_id}): "
    f"Confidence {data.confidence.score:.3f}, "
    f"{'Data Found' if not data.information_not_found else 'No Data'}"
    for data in retrieved_data
])}

VALIDATION CHECKLIST:

1. ✓/✗ DATA SOURCE COMPLIANCE:
   - Does response ONLY use information from retrieved data?
   - Are there any fabricated or inferred facts not in sources?
   - Specific violations: _______

2. ✓/✗ CITATION ACCURACY:
   - Are all facts properly cited with source IDs?
   - Are citations in correct format [Source: type-id]?
   - Missing citations: _______

3. ✓/✗ CONFIDENCE THRESHOLD RESPECT:
   - Did response check confidence scores?
   - Did it properly respond "I don't know" if below threshold?
   - Confidence violations: _______

4. ✓/✗ DATA COMPLETENESS:
   - Did response address information_not_found flags?
   - Were missing or null data acknowledged?
   - Completeness issues: _______

5. ✓/✗ CONFLICT HANDLING:
   - Were data conflicts between sources acknowledged?
   - Were all conflicting sources cited?
   - Conflict handling issues: _______

6. ✓/✗ HALLUCINATION CHECK:
   - Any information not traceable to sources?
   - Any assumptions or inferences beyond data?
   - Specific hallucinations: _______

7. ✓/✗ TRANSPARENCY:
   - Were data quality issues mentioned?
   - Were limitations acknowledged?
   - Transparency issues: _______

VALIDATION RESULT: [PASS / FAIL]

SCORE: ___/7 checks passed

DETAILED FINDINGS:
[Provide specific issues found or confirm accuracy]

RECOMMENDATION:
[Accept response / Revise response / Reject response]

CORRECTED RESPONSE (if needed):
[Provide corrected version if issues found]
"""

    @staticmethod
    def format_dont_know_response(
        reason: str, 
        sources: List[DataResponse], 
        query: str = "",
        confidence_threshold: float = 0.85,
        include_suggestions: bool = True
    ) -> str:
        """Format a comprehensive 'I don't know' response with full context."""
        
        response = f"I don't know. {reason}\n\n"
        
        # Add confidence context
        response += f"{'═' * 60}\n"
        response += f"CONFIDENCE ANALYSIS:\n"
        response += f"{'═' * 60}\n"
        response += f"Threshold Required: {confidence_threshold:.3f}\n\n"
        
        # Data quality summary per source
        response += "Data Quality Summary:\n\n"
        
        for idx, source in enumerate(sources, 1):
            status_icon = "✓" if source.verified else "✗"
            data_icon = "📊" if not source.information_not_found else "📭"
            
            response += f"{data_icon} Source {idx} - {source.source_metadata.source_type.value.upper()}:\n"
            response += f"   {status_icon} Verified: {source.verified}\n"
            response += f"   Confidence: {source.confidence.score:.3f} / {confidence_threshold:.3f}\n"
            response += f"   Status: {source.confidence.reasoning}\n"
            
            if source.information_not_found:
                response += f"   Result: No information found\n"
            else:
                response += f"   Result: Data available but {'below confidence threshold' if source.confidence.score < confidence_threshold else 'meets threshold'}\n"
            
            if source.additional_context:
                response += f"   Note: {source.additional_context}\n"
            
            response += "\n"
        
        # Summary statistics
        sources_with_data = sum(1 for s in sources if not s.information_not_found)
        verified_sources = sum(1 for s in sources if s.verified)
        avg_confidence = sum(s.confidence.score for s in sources) / len(sources) if sources else 0.0
        
        response += f"{'─' * 60}\n"
        response += f"Overall Statistics:\n"
        response += f"  • Sources queried: {len(sources)}\n"
        response += f"  • Sources with data: {sources_with_data}\n"
        response += f"  • Verified sources: {verified_sources}\n"
        response += f"  • Average confidence: {avg_confidence:.3f}\n"
        
        # Suggestions
        if include_suggestions and query:
            response += f"\n{'═' * 60}\n"
            response += f"SUGGESTIONS FOR IMPROVEMENT:\n"
            response += f"{'═' * 60}\n"
            
            if sources_with_data == 0:
                response += "• Try different search terms or filters\n"
                response += "• Check if the information exists in the databases\n"
                response += "• Verify database connectivity\n"
            elif avg_confidence < confidence_threshold:
                response += "• Data found but confidence is low\n"
                response += "• Consider reviewing data quality in sources\n"
                response += "• May need additional data verification\n"
            elif verified_sources == 0:
                response += "• No sources could be verified\n"
                response += "• Check source connectivity and authentication\n"
                response += "• Verify database permissions\n"
        
        return response

    @staticmethod
    def detect_data_conflicts(retrieved_data: List[DataResponse], field_name: Optional[str] = None) -> Dict[str, Any]:
        """Detect conflicts between data sources.
        
        Returns:
            Dictionary with conflict analysis including:
            - has_conflicts: bool
            - conflicting_fields: list
            - conflict_details: list of conflict descriptions
        """
        if len(retrieved_data) < 2:
            return {
                "has_conflicts": False,
                "conflicting_fields": [],
                "conflict_details": []
            }
        
        conflicts = []
        conflicting_fields = set()
        
        # Only compare sources that have data
        sources_with_data = [s for s in retrieved_data if not s.information_not_found and s.data]
        
        if len(sources_with_data) < 2:
            return {
                "has_conflicts": False,
                "conflicting_fields": [],
                "conflict_details": []
            }
        
        # Compare data between sources
        for i, source1 in enumerate(sources_with_data):
            for source2 in sources_with_data[i+1:]:
                if isinstance(source1.data, dict) and isinstance(source2.data, dict):
                    # Compare dictionary fields
                    common_keys = set(source1.data.keys()) & set(source2.data.keys())
                    
                    for key in common_keys:
                        if field_name and key != field_name:
                            continue
                        
                        val1 = source1.data[key]
                        val2 = source2.data[key]
                        
                        if val1 != val2:
                            conflicting_fields.add(key)
                            conflicts.append({
                                "field": key,
                                "source1": {
                                    "type": source1.source_metadata.source_type.value,
                                    "id": source1.source_metadata.source_id,
                                    "value": val1,
                                    "confidence": source1.confidence.score
                                },
                                "source2": {
                                    "type": source2.source_metadata.source_type.value,
                                    "id": source2.source_metadata.source_id,
                                    "value": val2,
                                    "confidence": source2.confidence.score
                                },
                                "description": f"Field '{key}' differs: '{val1}' vs '{val2}'"
                            })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicting_fields": list(conflicting_fields),
            "conflict_details": conflicts
        }

    @staticmethod
    def format_citation(source_metadata, include_timestamp: bool = False) -> str:
        """Format a source citation string.
        
        Args:
            source_metadata: SourceMetadata object
            include_timestamp: Whether to include retrieval timestamp
            
        Returns:
            Formatted citation string
        """
        citation = f"[Source: {source_metadata.source_type.value}-{source_metadata.source_id}"
        
        if include_timestamp:
            citation += f", Retrieved: {source_metadata.retrieved_at.strftime('%Y-%m-%d %H:%M UTC')}"
        
        citation += "]"
        return citation

    @staticmethod
    def create_multi_source_comparison_prompt(
        query: str,
        multi_response: MultiSourceResponse,
        confidence_threshold: float = 0.85
    ) -> str:
        """Create prompt for comparing and synthesizing multi-source data."""
        
        # Detect conflicts
        conflicts = AntiHallucinationPrompts.detect_data_conflicts(multi_response.sources)
        
        prompt = f"""MULTI-SOURCE DATA COMPARISON TASK

Query: {query}
Total Sources: {len(multi_response.sources)}
Aggregated Confidence: {multi_response.aggregated_confidence:.3f}
Threshold: {confidence_threshold}
Status: {'✓ MEETS THRESHOLD' if multi_response.meets_threshold else '✗ BELOW THRESHOLD'}

"""
        
        if conflicts["has_conflicts"]:
            prompt += f"⚠️  CONFLICTS DETECTED in fields: {', '.join(conflicts['conflicting_fields'])}\n\n"
            
            prompt += "CONFLICT DETAILS:\n"
            for conflict in conflicts["conflict_details"]:
                prompt += f"\nField: {conflict['field']}\n"
                prompt += f"  Source 1 ({conflict['source1']['type']}, confidence {conflict['source1']['confidence']:.3f}): {conflict['source1']['value']}\n"
                prompt += f"  Source 2 ({conflict['source2']['type']}, confidence {conflict['source2']['confidence']:.3f}): {conflict['source2']['value']}\n"
        
        prompt += "\nSOURCE DATA:\n"
        for idx, source in enumerate(multi_response.sources, 1):
            prompt += f"\n{idx}. {source.source_metadata.source_type.value.upper()}:\n"
            prompt += f"   Confidence: {source.confidence.score:.3f}\n"
            prompt += f"   Data: {source.data if not source.information_not_found else 'NOT FOUND'}\n"
        
        prompt += """\n
TASK:
1. Review all source data and confidence scores
2. Identify and acknowledge any conflicts
3. Synthesize information, citing each source
4. If conflicts exist, present all versions with citations
5. Respect confidence thresholds
6. Provide clear, cited response

YOUR SYNTHESIZED RESPONSE:
"""
        
        return prompt
