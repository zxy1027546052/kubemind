import { create } from 'zustand';
import type { ChatOpsMessageResponse } from '../schemas/chatops';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  result?: ChatOpsMessageResponse;
}

interface ChatOpsState {
  sessionId: string;
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  error: string;
  expanded: Set<number>;
  useStream: boolean;
}

interface ChatOpsActions {
  setInput: (input: string) => void;
  addMessage: (message: ChatMessage) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string) => void;
  toggleExpand: (index: number) => void;
  setUseStream: (useStream: boolean) => void;
  reset: () => void;
}

function makeSessionId() {
  return `chat-${Date.now().toString(36)}`;
}

const initialState: ChatOpsState = {
  sessionId: makeSessionId(),
  messages: [],
  input: '',
  loading: false,
  error: '',
  expanded: new Set(),
  useStream: true,
};

export const useChatOpsStore = create<ChatOpsState & ChatOpsActions>((set) => ({
  ...initialState,

  setInput: (input) => set({ input }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  toggleExpand: (index) =>
    set((s) => {
      const next = new Set(s.expanded);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return { expanded: next };
    }),

  setUseStream: (useStream) => set({ useStream }),

  reset: () => set({ ...initialState, sessionId: makeSessionId(), expanded: new Set() }),
}));
