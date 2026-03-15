/**
 * Chatbot-specific Small Features (SF-64 to SF-70)
 * Session memory, partial regeneration, and confidence scoring
 */

'use client';

import { useRef, useCallback, useState, useEffect } from 'react';

// SF-64: Chatbot memory in session
export interface ChatbotSessionMemory {
  courseId: string;
  courseName: string;
  courseCode: string;
  syllabus?: string;
  programOutcomes: string[]; // PO names/codes
  programSpecificOutcomes?: string[]; // PSO names/codes
  currentCO?: string;
  conversationHistory: ChatMessage[];
  timestamp: Date;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const useChatbotMemory = (courseId: string) => {
  const [memory, setMemory] = useState<ChatbotSessionMemory>({
    courseId,
    courseName: '',
    courseCode: '',
    programOutcomes: [],
    conversationHistory: [],
    timestamp: new Date(),
  });

  useEffect(() => {
    setMemory(prev => ({
      ...prev,
      courseId,
      timestamp: new Date(),
    }));
  }, [courseId]);

  const recordMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    setMemory(prev => ({
      ...prev,
      conversationHistory: [
        ...prev.conversationHistory,
        { role, content, timestamp: new Date() },
      ],
      timestamp: new Date(),
    }));
  }, []);

  const setCourseContext = useCallback(
    (courseName: string, courseCode: string, syllabus?: string, pos: string[] = []) => {
      setMemory(prev => ({
        ...prev,
        courseName,
        courseCode,
        syllabus,
        programOutcomes: pos,
      }));
    },
    []
  );

  const clearMemory = useCallback(() => {
    setMemory({
      courseId,
      courseName: '',
      courseCode: '',
      programOutcomes: [],
      conversationHistory: [],
      timestamp: new Date(),
    });
  }, [courseId]);

  return {
    memory,
    recordMessage,
    setCourseContext,
    clearMemory,
  };
};

// SF-65: Partial CO regeneration
export interface COGenerationRequest {
  type: 'full' | 'partial';
  courseId: string;
  courseCode: string;
  courseSyllabus: string;
  existingCOs?: Record<string, string>; // CO1 -> statement
  targetCOs?: string[]; // 'CO1', 'CO3' for partial
  programOutcomes: string[];
  context?: string; // Additional context from conversation
}

export interface GeneratedCO {
  code: string; // 'CO1', 'CO2', etc.
  statement: string;
  bloomLevel: 'K' | 'U' | 'App' | 'An' | 'E' | 'C'; // Knowledge, Understand, Apply, etc.
  confidence: number; // 0-100
  mappedPOs: string[]; // Which POs this CO addresses
}

export const formatCOGenerationPrompt = (request: COGenerationRequest): string => {
  let prompt = `Generate ${request.type === 'full' ? 'Course Outcomes (COs)' : `new CO statements for: ${request.targetCOs?.join(', ')}`}`;

  prompt += `\n\nCourse: ${request.courseCode}`;
  prompt += `\nSyllabus:\n${request.courseSyllabus}`;

  if (request.existingCOs && request.type === 'partial') {
    prompt += `\n\nExisting COs (keep unchanged):`;
    Object.entries(request.existingCOs).forEach(([code, statement]) => {
      if (!request.targetCOs?.includes(code)) {
        prompt += `\n${code}: ${statement}`;
      }
    });
  }

  prompt += `\n\nProgram Outcomes to map to:\n${request.programOutcomes.map(po => `- ${po}`).join('\n')}`;

  if (request.context) {
    prompt += `\n\nAdditional context: ${request.context}`;
  }

  prompt += `\n\nProvide each CO as JSON with: code, statement, bloomLevel, mappedPOs`;

  return prompt;
};

// SF-66: BT (Bloom's Taxonomy) justification on demand
export interface BTJustification {
  co: string;
  bloomLevel: 'K' | 'U' | 'App' | 'An' | 'E' | 'C';
  reasoning: string;
  examples: string[];
}

export const bloomLevelDescriptions: Record<string, string> = {
  K: 'Knowledge - Recall facts and basic concepts',
  U: 'Understand - Explain ideas and concepts',
  App: 'Apply - Use information in a new situation',
  An: 'Analyze - Draw connections among ideas',
  E: 'Evaluate - Justify a stand or decision',
  C: 'Create - Produce new or original work',
};

export const requestBTJustification = (co: string, bloomLevel: string): string => {
  return `Explain why "${co}" is at Bloom's Taxonomy level ${bloomLevel} (${bloomLevelDescriptions[bloomLevel]}). Provide examples of how students demonstrate this level.`;
};

// SF-67: Confidence score display
export const getConfidenceLabel = (confidence: number): string => {
  if (confidence >= 90) return 'Very High Confidence';
  if (confidence >= 75) return 'High Confidence';
  if (confidence >= 60) return 'Moderate Confidence';
  if (confidence >= 40) return 'Low Confidence';
  return 'Very Low Confidence';
};

export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 80) return 'text-attain';
  if (confidence >= 60) return 'text-amber-500';
  return 'text-alert';
};

export const formatConfidenceScore = (confidence: number): string => {
  return `${confidence}% confidence — ${getConfidenceLabel(confidence)}`;
};

// SF-68: Context-specific suggested replies
export interface SuggestedReply {
  text: string;
  action: 'regenerate' | 'refine' | 'accept' | 'reject' | 'clarify' | 'explain';
  params?: Record<string, any>;
}

export const generateSuggestedReplies = (
  lastBotMessage: string,
  context: 'co_generation' | 'mapping' | 'btm_justification' | 'feedback'
): SuggestedReply[] => {
  const replies: SuggestedReply[] = [];

  switch (context) {
    case 'co_generation':
      replies.push(
        { text: 'Regenerate all COs', action: 'regenerate', params: { type: 'full' } },
        { text: 'Refine wording', action: 'refine' },
        { text: 'Accept these COs', action: 'accept' },
        { text: 'Explain reasoning', action: 'explain' }
      );
      break;

    case 'mapping':
      replies.push(
        { text: 'Show mapping details', action: 'clarify' },
        { text: 'Suggest different mapping', action: 'regenerate' },
        { text: 'Accept this mapping', action: 'accept' }
      );
      break;

    case 'btm_justification':
      replies.push(
        { text: 'Move to higher level', action: 'refine' },
        { text: 'Move to lower level', action: 'refine' },
        { text: 'Accept this level', action: 'accept' },
        { text: 'Show more examples', action: 'clarify' }
      );
      break;

    case 'feedback':
      replies.push(
        { text: 'Generate again', action: 'regenerate' },
        { text: 'Keep this version', action: 'accept' },
        { text: 'Provide feedback', action: 'clarify' }
      );
      break;
  }

  return replies;
};

// SF-69: Chatbot fallback for unclear input
export const CHATBOT_FALLBACK_RESPONSES = {
  unclear: `I did not understand that. Would you like to:
    • Generate new Course Outcomes
    • Map COs to Program Outcomes
    • Get Bloom's Taxonomy justification
    • View conversation history
    • Clear session and start over`,

  error: `I encountered an error processing your request. Please:
    • Try rephrasing your question
    • Provide specific CO codes (e.g., "CO1", "CO2")
    • Save your work and refresh the page if the issue persists`,

  timeout: `The request took too long. Let's try again:
    • Ask a more specific question
    • Generate fewer COs at once
    • Check your internet connection`,
};

export const shouldUseFallback = (response: string): boolean => {
  // Detect low-confidence or error responses
  return (
    response.includes('unclear') ||
    response.includes('error') ||
    response.length < 20 ||
    response.toLowerCase().includes('i am not sure')
  );
};

// SF-70: Save draft mid-workflow
export interface ChatbotWorkflowDraft {
  courseId: string;
  workflow: 'co_generation' | 'mapping' | 'validation';
  step: number; // 1, 2, 3 etc.
  data: Record<string, any>;
  memory: ChatbotSessionMemory;
  savedAt: Date;
  expiresAt: Date;
}

export const WORKFLOW_DRAFT_EXPIRY_DAYS = 30;

export const saveChatbotDraft = async (draft: ChatbotWorkflowDraft): Promise<void> => {
  try {
    // Save to localStorage for instant recovery
    localStorage.setItem(
      `chatbot_draft_${draft.courseId}_${draft.workflow}`,
      JSON.stringify(draft)
    );

    // Save to server
    await fetch('/api/chatbot/drafts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    });
  } catch (error) {
    console.error('Failed to save chatbot draft:', error);
  }
};

export const retrieveChatbotDraft = async (
  courseId: string,
  workflow: string
): Promise<ChatbotWorkflowDraft | null> => {
  const storageKey = `chatbot_draft_${courseId}_${workflow}`;
  try {
    const localDraft = localStorage.getItem(storageKey);
    if (localDraft) {
      return JSON.parse(localDraft);
    }

    const response = await fetch(`/api/chatbot/drafts/${courseId}/${workflow}`);
    return response.ok ? response.json() : null;
  } catch {
    try {
      const localDraft = localStorage.getItem(storageKey);
      return localDraft ? JSON.parse(localDraft) : null;
    } catch {
      return null;
    }
  }
};

export const useChatbotWorkflowDraft = (courseId: string, workflow: 'co_generation' | 'mapping' | 'validation') => {
  const [draft, setDraft] = useState<ChatbotWorkflowDraft | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    retrieveChatbotDraft(courseId, workflow)
      .then(setDraft)
      .finally(() => setIsLoading(false));
  }, [courseId, workflow]);

  const saveDraft = useCallback(
    (step: number, data: Record<string, any>, memory: ChatbotSessionMemory) => {
      const newDraft: ChatbotWorkflowDraft = {
        courseId,
        workflow,
        step,
        data,
        memory,
        savedAt: new Date(),
        expiresAt: new Date(Date.now() + WORKFLOW_DRAFT_EXPIRY_DAYS * 24 * 60 * 60 * 1000),
      };
      setDraft(newDraft);
      saveChatbotDraft(newDraft);
    },
    [courseId, workflow]
  );

  const clearDraft = useCallback(async () => {
    setDraft(null);
    localStorage.removeItem(`chatbot_draft_${courseId}_${workflow}`);
    try {
      await fetch(`/api/chatbot/drafts/${courseId}/${workflow}`, {
        method: 'DELETE',
      });
    } catch (error) {
      console.error('Failed to clear draft:', error);
    }
  }, [courseId, workflow]);

  return { draft, isLoading, saveDraft, clearDraft };
};

// Helper: Format chat message for display
export const formatChatMessage = (message: ChatMessage): string => {
  const time = message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return `[${time}] ${message.role === 'user' ? 'You' : 'Bot'}: ${message.content}`;
};
