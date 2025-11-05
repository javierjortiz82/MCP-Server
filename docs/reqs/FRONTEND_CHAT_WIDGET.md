# Frontend Chat Widget Requirements - Odiseo Web

**Project:** Odiseo Sales AI - Web Chat Widget
**Backend Integration:** Demo Agent API (`/home/javort/alfredo/MCP-Server/demo_agent`)
**Frontend Location:** `/home/javort/odiseo-web/odiseo-sales-ai`
**Reference:** `CHAT.MD` - Base requirements document
**Created:** 2025-11-04
**Status:** Ready for Implementation

---

## 1. Overview

Build a ChatGPT-like chat interface in Odiseo Web that allows authenticated users to interact with the "Odiseo" AI agent. The widget must integrate with the backend Demo Agent API, handle token-based quota management, and provide real-time usage warnings.

### 1.1 Core Features

- ✅ ChatGPT-style conversational interface
- ✅ Token-based usage quota with visual indicators
- ✅ Real-time warning system at 85% usage threshold
- ✅ Typewriter effect for AI responses
- ✅ Loading animations with brand logo
- ✅ Multi-language support (EN, ES, AR)
- ✅ Voice input button (UI only - not functional yet)
- ✅ Document attachment button (UI only - not functional yet)

---

## 2. Technical Stack & Architecture

### 2.1 Frontend Framework

**Framework:** React 18.3.1 + Vite 5.4.19 + TypeScript 5.8.3

**Key Libraries:**
- `@clerk/clerk-react` 5.53.4 - Authentication
- `react-i18next` 16.1.4 - Internationalization
- `@tanstack/react-query` 5.83.0 - API state management
- `tailwindcss` 3.4.17 - Styling
- `@radix-ui/*` - UI primitives

### 2.2 Project Structure

```
/src/
├── pages/
│   └── Chat.tsx                    # NEW: Chat page (protected route)
├── components/
│   ├── chat/                       # NEW: Chat components
│   │   ├── ChatWidget.tsx         # Main chat container
│   │   ├── ChatMessage.tsx        # Individual message bubble
│   │   ├── ChatInput.tsx          # Input area with buttons
│   │   ├── ChatHeader.tsx         # Header with quota display
│   │   ├── UsageWarning.tsx       # Warning overlay
│   │   ├── LoadingAnimation.tsx   # Logo loading animation
│   │   └── TypewriterMessage.tsx  # Typewriter effect component
│   └── ui/                         # Existing shadcn/ui components
├── services/                       # NEW: API services
│   └── demoAgent.ts               # Demo Agent API client
├── hooks/                          # Existing + new hooks
│   ├── useChat.ts                 # NEW: Chat state management
│   ├── useTokenQuota.ts           # NEW: Token quota tracking
│   └── useTypewriter.ts           # NEW: Typewriter effect
├── i18n/locales/
│   ├── en.json                    # ADD: Chat translations
│   ├── es.json                    # ADD: Chat translations
│   └── ar.json                    # ADD: Chat translations
└── types/
    └── chat.ts                    # NEW: TypeScript types
```

---

## 3. Backend API Integration

### 3.1 Environment Configuration

**Add to `.env`:**
```env
# Demo Agent API
VITE_DEMO_AGENT_URL=http://localhost:8082
VITE_DEMO_AGENT_URL_PROD=https://your-production-url.com
```

### 3.2 API Endpoints

#### **POST /v1/demo** - Send Chat Message

**Location:** `main.py:593`

**Request:**
```typescript
interface DemoRequest {
  user_id?: string;      // Legacy (deprecated after Clerk migration)
  session_id: string;    // Generated per session
  input: string;         // User message
  language: string;      // "en" | "es" | "ar"
  metadata: {
    ip?: string;
    user_agent?: string;
    fingerprint?: string;
  };
}
```

**Response (Success - 200):**
```typescript
interface DemoResponse {
  success: true;
  response: string;           // AI response text
  tokens_used: number;        // Tokens consumed this request
  tokens_remaining: number;   // Tokens left today
  warning: {
    is_warning: boolean;      // TRUE when percentage >= 85%
    message: string | null;   // "You've consumed X% of your daily quota"
    percentage_used: number;  // Current usage percentage
  };
  session_id: string;
  created_at: string;         // ISO 8601
}
```

**Response (Quota Exceeded - 429):**
```typescript
{
  success: false;
  error: "demo_quota_exceeded";
  message: "Demo bloqueada. Límite de 5,000 tokens alcanzado...";
  retry_after_seconds: 64800;
  blocked_until: "2025-11-01T12:30:45Z";
}
```

**Response (Not Authenticated - 401):**
```typescript
{
  success: false;
  error: "authentication_required";
  message: "Please log in with Clerk to use this endpoint.";
}
```

**Response (Account Issues - 403):**
```typescript
{
  success: false;
  error: "account_not_active" | "email_not_verified" | "account_suspended";
  message: string;
}
```

#### **GET /v1/demo/status** - Check Quota Status

**Location:** `main.py:802`

**Query Parameters:**
- `user_id?: string` - Authenticated user ID (Clerk)
- `session_id?: string` - Anonymous session ID
- `fingerprint?: string` - Client fingerprint

**Response:**
```typescript
interface QuotaStatus {
  tokens_used: number;
  tokens_remaining: number;
  percentage_used: number;
  requests_count: number;
  is_blocked: boolean;
  blocked_until: string | null;
  last_reset: string;           // ISO 8601
  next_reset: string;            // ISO 8601
  warning: {                     // NEW: Added in backend implementation
    is_warning: boolean;         // TRUE when percentage >= 85%
    message: string | null;      // Generic English message
    percentage_used: number;
  };
}
```

### 3.3 API Service Implementation

**Create:** `/src/services/demoAgent.ts`

```typescript
import { useAuth } from '@clerk/clerk-react';

const API_BASE_URL = import.meta.env.VITE_DEMO_AGENT_URL || 'http://localhost:8082';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tokens_used?: number;
}

export class DemoAgentService {
  private sessionId: string;

  constructor() {
    this.sessionId = crypto.randomUUID();
  }

  /**
   * Send chat message to Odiseo AI
   */
  async sendMessage(
    message: string,
    language: string,
    clerkToken?: string
  ): Promise<DemoResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add Clerk authentication token if available
    if (clerkToken) {
      headers['Authorization'] = `Bearer ${clerkToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/v1/demo`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        session_id: this.sessionId,
        input: message,
        language,
        metadata: {
          user_agent: navigator.userAgent,
          fingerprint: await this.generateFingerprint(),
        },
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new DemoAgentError(error, response.status);
    }

    return response.json();
  }

  /**
   * Get current quota status
   */
  async getQuotaStatus(clerkToken?: string): Promise<QuotaStatus> {
    const headers: Record<string, string> = {};

    if (clerkToken) {
      headers['Authorization'] = `Bearer ${clerkToken}`;
    }

    const response = await fetch(
      `${API_BASE_URL}/v1/demo/status?session_id=${this.sessionId}`,
      { headers }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch quota status');
    }

    return response.json();
  }

  private async generateFingerprint(): Promise<string> {
    // Simple fingerprint based on browser properties
    const components = [
      navigator.userAgent,
      navigator.language,
      screen.colorDepth,
      screen.width,
      screen.height,
      new Date().getTimezoneOffset(),
    ];

    const fingerprint = components.join('|');
    const encoder = new TextEncoder();
    const data = encoder.encode(fingerprint);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
}

export class DemoAgentError extends Error {
  constructor(
    public error: any,
    public statusCode: number
  ) {
    super(error.message || 'Unknown error');
    this.name = 'DemoAgentError';
  }
}
```

---

## 4. Component Specifications

### 4.1 Chat Page (`/src/pages/Chat.tsx`)

**Route:** `/chat` (Protected - requires Clerk authentication)

**Responsibilities:**
- Main container for chat interface
- Initialize chat state
- Handle authentication checks
- Render ChatWidget component

```typescript
import { useAuth } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { ChatWidget } from '@/components/chat/ChatWidget';

export const Chat = () => {
  const { isSignedIn, isLoaded } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      navigate('/login');
    }
  }, [isLoaded, isSignedIn, navigate]);

  if (!isLoaded) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <ChatWidget />
    </div>
  );
};
```

### 4.2 ChatWidget (`/src/components/chat/ChatWidget.tsx`)

**Main chat container with full layout**

**Features:**
- Message history display
- Scrollable message area
- Input section at bottom
- Header with quota display
- Warning overlay when >= 85%

**State Management:**
```typescript
interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  quotaStatus: QuotaStatus | null;
  error: string | null;
}
```

**Layout:**
```
┌─────────────────────────────────────┐
│ ChatHeader (Quota Display)          │
├─────────────────────────────────────┤
│                                     │
│  Message History                    │
│  (Scrollable)                       │
│                                     │
│  [User Message]                     │
│  [AI Response with Typewriter]      │
│                                     │
├─────────────────────────────────────┤
│ ChatInput (Text + Buttons)          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ UsageWarning (Fixed Bottom Right)   │ <- Only shows when warning.is_warning = true
└─────────────────────────────────────┘
```

### 4.3 ChatMessage (`/src/components/chat/ChatMessage.tsx`)

**Individual message bubble**

**Props:**
```typescript
interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tokens_used?: number;
  isTyping?: boolean;  // For typewriter effect
}
```

**Styling:**
- User messages: Right-aligned, primary color background
- AI messages: Left-aligned, card background
- Avatar: User avatar from Clerk / "Odiseo" logo for AI
- Timestamp: Subtle, below message
- Token count: Small badge for AI messages

### 4.4 ChatInput (`/src/components/chat/ChatInput.tsx`)

**Input area with buttons**

**Features:**
- Textarea with auto-grow (max 4 lines)
- Send button (enabled only when text entered)
- Voice input button (shows "Function not available" toast)
- Attach document button (shows "Function not available" toast)
- Disabled state when quota exceeded

**Layout:**
```
┌─────────────────────────────────────────┐
│  🎤  📎  [Textarea]  [Send Button ➤]   │
└─────────────────────────────────────────┘
```

**Disabled States:**
- Quota exceeded (`is_blocked: true`)
- Loading response
- No text entered (send button only)

### 4.5 ChatHeader (`/src/components/chat/ChatHeader.tsx`)

**Header with quota display**

**Features:**
- "Odiseo AI" branding
- Token quota progress bar
- Percentage display
- Tooltip with detailed info

**Layout:**
```
┌─────────────────────────────────────────┐
│  🤖 Odiseo AI    [====75%====    ] 75%  │
└─────────────────────────────────────────┘
```

**Color Coding:**
- 0-74%: Green (`--secondary`)
- 75-84%: Yellow/Warning (`--accent`)
- 85-100%: Red (`--destructive`)

### 4.6 UsageWarning (`/src/components/chat/UsageWarning.tsx`)

**Fixed warning banner at bottom right**

**Visibility:** Only shown when `warning.is_warning === true`

**Content:**
- Translated warning message from i18n
- Token usage information
- Next reset time
- Close button

**Layout:**
```
┌─────────────────────────────────────┐
│  ⚠️  Warning Title             [×]  │
│  Translated message here            │
│  Tokens: 4250 / 5000 (85%)          │
│  Resets: Tomorrow at 00:00 UTC      │
└─────────────────────────────────────┘
```

**Position:** Fixed bottom-right, 20px from edges

### 4.7 LoadingAnimation (`/src/components/chat/LoadingAnimation.tsx`)

**Loading state while waiting for AI response**

**Features:**
- Animated Odiseo logo (`/public/logo.png`)
- Pulsing/breathing animation
- "Odiseo is thinking..." text

**Animation:**
- Use existing `animate-logo-pulse-once` or similar
- Smooth fade-in/fade-out

### 4.8 TypewriterMessage (`/src/components/chat/TypewriterMessage.tsx`)

**Typewriter effect for AI responses**

**Props:**
```typescript
interface TypewriterMessageProps {
  text: string;
  speed?: number;  // Characters per second (default: 50)
  onComplete?: () => void;
}
```

**Implementation:**
- Use `useState` + `useEffect` with `setInterval`
- Render character by character
- Support for markdown (optional, future enhancement)

---

## 5. Custom Hooks

### 5.1 useChat (`/src/hooks/useChat.ts`)

**Chat state management hook**

```typescript
export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();
  const { data: quotaStatus, refetch: refetchQuota } = useTokenQuota();
  const demoAgent = useMemo(() => new DemoAgentService(), []);

  const sendMessage = async (content: string, language: string) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await demoAgent.sendMessage(content, language, token);

      // Add AI response
      const aiMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: response.created_at,
        tokens_used: response.tokens_used,
      };
      setMessages(prev => [...prev, aiMessage]);

      // Refresh quota status
      await refetchQuota();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    isLoading,
    error,
    quotaStatus,
    sendMessage,
  };
};
```

### 5.2 useTokenQuota (`/src/hooks/useTokenQuota.ts`)

**Token quota tracking hook**

```typescript
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@clerk/clerk-react';
import { DemoAgentService } from '@/services/demoAgent';

export const useTokenQuota = () => {
  const { getToken } = useAuth();
  const demoAgent = useMemo(() => new DemoAgentService(), []);

  return useQuery({
    queryKey: ['token-quota'],
    queryFn: async () => {
      const token = await getToken();
      return demoAgent.getQuotaStatus(token);
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    refetchOnWindowFocus: true,
  });
};
```

### 5.3 useTypewriter (`/src/hooks/useTypewriter.ts`)

**Typewriter effect hook**

```typescript
export const useTypewriter = (
  text: string,
  speed: number = 50
) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!text) return;

    let index = 0;
    setDisplayedText('');
    setIsComplete(false);

    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, 1000 / speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayedText, isComplete };
};
```

---

## 6. Internationalization (i18n)

### 6.1 Translation Keys

**Add to `/src/i18n/locales/en.json`:**
```json
{
  "chat": {
    "title": "Chat with Odiseo",
    "placeholder": "Type your message...",
    "send": "Send",
    "thinking": "Odiseo is thinking...",
    "voiceInput": "Voice input",
    "attachFile": "Attach document",
    "featureNotAvailable": "Feature not available",
    "quota": {
      "title": "Daily Quota",
      "remaining": "{{remaining}} tokens remaining",
      "used": "{{used}} of {{total}} tokens used",
      "percentage": "{{percentage}}% used",
      "resetsAt": "Resets at {{time}}"
    },
    "warning": {
      "title": "Approaching Daily Limit",
      "message": "You've used {{percentage}}% of your daily quota",
      "tokensRemaining": "{{remaining}} tokens remaining",
      "blocked": "Daily quota exceeded. Please try again after {{time}}."
    },
    "errors": {
      "sendFailed": "Failed to send message",
      "quotaExceeded": "Daily quota exceeded",
      "notAuthenticated": "Please log in to continue",
      "accountIssue": "Account verification required"
    }
  }
}
```

**Add to `/src/i18n/locales/es.json`:**
```json
{
  "chat": {
    "title": "Chat con Odiseo",
    "placeholder": "Escribe tu mensaje...",
    "send": "Enviar",
    "thinking": "Odiseo está pensando...",
    "voiceInput": "Entrada de voz",
    "attachFile": "Adjuntar documento",
    "featureNotAvailable": "Función no disponible",
    "quota": {
      "title": "Cuota Diaria",
      "remaining": "{{remaining}} tokens restantes",
      "used": "{{used}} de {{total}} tokens usados",
      "percentage": "{{percentage}}% usado",
      "resetsAt": "Se reinicia a las {{time}}"
    },
    "warning": {
      "title": "Acercándose al Límite Diario",
      "message": "Has usado {{percentage}}% de tu cuota diaria",
      "tokensRemaining": "{{remaining}} tokens restantes",
      "blocked": "Cuota diaria excedida. Intenta de nuevo después de {{time}}."
    },
    "errors": {
      "sendFailed": "Error al enviar mensaje",
      "quotaExceeded": "Cuota diaria excedida",
      "notAuthenticated": "Por favor inicia sesión para continuar",
      "accountIssue": "Verificación de cuenta requerida"
    }
  }
}
```

**Add to `/src/i18n/locales/ar.json`:**
```json
{
  "chat": {
    "title": "الدردشة مع أوديسيو",
    "placeholder": "اكتب رسالتك...",
    "send": "إرسال",
    "thinking": "أوديسيو يفكر...",
    "voiceInput": "إدخال صوتي",
    "attachFile": "إرفاق مستند",
    "featureNotAvailable": "الميزة غير متاحة",
    "quota": {
      "title": "الحصة اليومية",
      "remaining": "{{remaining}} رمز متبقي",
      "used": "{{used}} من {{total}} رمز مستخدم",
      "percentage": "{{percentage}}٪ مستخدم",
      "resetsAt": "يتم إعادة التعيين في {{time}}"
    },
    "warning": {
      "title": "الاقتراب من الحد اليومي",
      "message": "لقد استخدمت {{percentage}}٪ من حصتك اليومية",
      "tokensRemaining": "{{remaining}} رمز متبقي",
      "blocked": "تم تجاوز الحصة اليومية. يرجى المحاولة مرة أخرى بعد {{time}}."
    },
    "errors": {
      "sendFailed": "فشل إرسال الرسالة",
      "quotaExceeded": "تم تجاوز الحصة اليومية",
      "notAuthenticated": "يرجى تسجيل الدخول للمتابعة",
      "accountIssue": "التحقق من الحساب مطلوب"
    }
  }
}
```

---

## 7. Styling Guidelines

### 7.1 Color Scheme (from existing design system)

```css
/* Chat-specific colors */
.chat-user-message {
  background: hsl(var(--primary));  /* Coral Red */
  color: hsl(var(--foreground));
}

.chat-ai-message {
  background: hsl(var(--card));     /* Deep Blue */
  color: hsl(var(--foreground));
}

.chat-warning {
  background: hsl(var(--destructive)); /* Red */
  color: hsl(var(--foreground));
}

.quota-bar-normal {
  background: hsl(var(--secondary));   /* Green */
}

.quota-bar-warning {
  background: hsl(var(--accent));      /* Teal */
}

.quota-bar-critical {
  background: hsl(var(--destructive)); /* Red */
}
```

### 7.2 Animations

**Use existing animations:**
- `animate-fade-in` - For message appearance
- `animate-fade-in-up` - For message entry
- `animate-logo-pulse-once` - For loading animation

**New animations needed:**
```css
@keyframes typing-indicator {
  0%, 60%, 100% { opacity: 0.4; }
  30% { opacity: 1; }
}

.typing-dot {
  animation: typing-indicator 1.4s infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}
```

### 7.3 Responsive Design

**Breakpoints:**
- Mobile: < 640px (sm)
- Tablet: 640px - 1024px (md, lg)
- Desktop: > 1024px (xl)

**Chat Widget:**
- Mobile: Full screen, fixed header/input
- Tablet: 90% width, centered
- Desktop: Max 800px width, centered

---

## 8. Error Handling & Edge Cases

### 8.1 Error States

| Error | Status | Handling |
|-------|--------|----------|
| Not Authenticated | 401 | Redirect to /login |
| Account Not Active | 403 | Show error message + link to verify email |
| Quota Exceeded | 429 | Disable input, show countdown to reset |
| Network Error | - | Show retry button |
| Server Error | 500 | Show generic error message |

### 8.2 Edge Cases

**Empty Response:**
```typescript
if (!response.response || response.response.trim() === '') {
  throw new Error('Empty response from AI');
}
```

**Long Messages:**
- User input: Limit to 2000 characters
- AI response: No limit, but paginate if > 5000 characters

**Simultaneous Requests:**
- Disable send button while loading
- Queue messages if user sends multiple quickly

**Quota Check:**
- Check before sending (optimistic)
- Handle 429 gracefully if quota changes mid-request

### 8.3 Loading States

1. **Initial Load:** Skeleton UI for messages
2. **Sending Message:** Disable input, show loading indicator
3. **AI Response:** Show typing indicator (3 animated dots)
4. **Quota Refresh:** Background, no UI blocking

---

## 9. Testing Requirements

### 9.1 Unit Tests

**Components to test:**
- `ChatMessage` - Rendering user/AI messages
- `ChatInput` - Input validation, button states
- `UsageWarning` - Visibility based on threshold
- `TypewriterMessage` - Text animation

**Hooks to test:**
- `useChat` - Message sending, state updates
- `useTokenQuota` - Quota fetching, caching
- `useTypewriter` - Character-by-character rendering

### 9.2 Integration Tests

**Scenarios:**
1. **Complete Chat Flow:**
   - User sends message
   - AI responds with typewriter
   - Quota updates
   - Warning appears at 85%

2. **Quota Exceeded:**
   - User at 100% quota
   - Input disabled
   - Error message shown

3. **Authentication:**
   - Unauthenticated user redirected
   - Clerk token passed correctly

### 9.3 E2E Tests

**User Journeys:**
1. Login → Open Chat → Send Message → Receive Response
2. Use Chat until 85% → See Warning → Continue → Hit 100% → Blocked
3. Check Quota Status → Wait for Reset → Use Again

---

## 10. Performance Optimization

### 10.1 React Query Caching

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,      // 30 seconds
      cacheTime: 300000,     // 5 minutes
      refetchOnWindowFocus: true,
    },
  },
});
```

### 10.2 Lazy Loading

```typescript
// Lazy load chat page
const Chat = lazy(() => import('@/pages/Chat'));

// Use Suspense for loading state
<Suspense fallback={<LoadingAnimation />}>
  <Chat />
</Suspense>
```

### 10.3 Memoization

```typescript
// Memoize expensive computations
const formattedMessages = useMemo(
  () => messages.map(formatMessage),
  [messages]
);

// Memoize callbacks
const handleSend = useCallback(
  (message: string) => sendMessage(message, language),
  [sendMessage, language]
);
```

---

## 11. Security Considerations

### 11.1 Input Sanitization

```typescript
// Sanitize user input before sending
const sanitizeInput = (text: string): string => {
  return text
    .trim()
    .slice(0, 2000)  // Max length
    .replace(/[<>]/g, ''); // Remove HTML tags
};
```

### 11.2 XSS Prevention

- Use React's built-in XSS protection
- Never use `dangerouslySetInnerHTML` for user content
- Sanitize AI responses if rendering markdown

### 11.3 Rate Limiting

- Respect backend rate limits
- Client-side debouncing (prevent spam)
- Disable send button during request

---

## 12. Deployment Checklist

### 12.1 Environment Variables

```env
# Production
VITE_DEMO_AGENT_URL=https://production-api.odiseo.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxxxx

# Staging
VITE_DEMO_AGENT_URL=https://staging-api.odiseo.com
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
```

### 12.2 Build Optimization

```bash
# Build with optimizations
npm run build

# Analyze bundle size
npm run build -- --analyze
```

### 12.3 Pre-deployment Tests

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual QA on staging
- [ ] Accessibility audit (a11y)
- [ ] Performance audit (Lighthouse)

---

## 13. Code Quality Standards

### 13.1 Airbnb Style Guide

Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript):
- Use ES6+ features
- Prefer `const` over `let`
- Use arrow functions
- Destructure props
- Use meaningful variable names

### 13.2 TypeScript Best Practices

```typescript
// ✅ Good: Explicit types
interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
}

// ❌ Bad: Any types
interface ChatMessageProps {
  role: any;
  content: any;
}
```

### 13.3 Component Structure

```typescript
// 1. Imports
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

// 2. Types/Interfaces
interface Props { ... }

// 3. Component
export const Component = ({ prop }: Props) => {
  // 4. Hooks
  const { t } = useTranslation();
  const [state, setState] = useState();

  // 5. Effects
  useEffect(() => { ... }, []);

  // 6. Event Handlers
  const handleClick = () => { ... };

  // 7. Render
  return ( ... );
};
```

---

## 14. Documentation Requirements

### 14.1 Component Documentation

```typescript
/**
 * ChatWidget - Main chat interface component
 *
 * Displays conversation history, handles message sending,
 * and shows quota warnings when threshold is reached.
 *
 * @example
 * ```tsx
 * <ChatWidget />
 * ```
 */
export const ChatWidget = () => { ... };
```

### 14.2 Storybook

Create Storybook stories for all components:
```typescript
// ChatMessage.stories.tsx
export default {
  title: 'Chat/ChatMessage',
  component: ChatMessage,
};

export const UserMessage = () => (
  <ChatMessage
    role="user"
    content="Hello Odiseo!"
    timestamp={new Date().toISOString()}
  />
);

export const AIMessage = () => (
  <ChatMessage
    role="assistant"
    content="Hello! How can I help you today?"
    timestamp={new Date().toISOString()}
    tokens_used={25}
  />
);
```

---

## 15. Implementation Timeline

### Phase 1: Foundation (Week 1)
- [ ] Set up API service layer (`demoAgent.ts`)
- [ ] Create custom hooks (`useChat`, `useTokenQuota`, `useTypewriter`)
- [ ] Add i18n translations
- [ ] Create TypeScript types

### Phase 2: Core Components (Week 2)
- [ ] ChatWidget (layout)
- [ ] ChatMessage (user/AI bubbles)
- [ ] ChatInput (textarea + buttons)
- [ ] LoadingAnimation (logo animation)
- [ ] TypewriterMessage (text effect)

### Phase 3: Advanced Features (Week 3)
- [ ] ChatHeader (quota display)
- [ ] UsageWarning (threshold warning)
- [ ] Error handling
- [ ] Edge case handling

### Phase 4: Polish & Testing (Week 4)
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Performance optimization
- [ ] Accessibility audit
- [ ] Documentation

### Phase 5: Deployment (Week 5)
- [ ] Staging deployment
- [ ] QA testing
- [ ] Production deployment
- [ ] Monitoring & analytics

---

## 16. Success Criteria

### 16.1 Functional Requirements

✅ **Core Features:**
- [ ] User can send messages and receive AI responses
- [ ] Typewriter effect works smoothly
- [ ] Loading animation displays during AI processing
- [ ] Quota tracking updates in real-time
- [ ] Warning appears at 85% threshold
- [ ] Input disabled at 100% quota
- [ ] Multi-language support (EN, ES, AR)

### 16.2 Non-Functional Requirements

✅ **Performance:**
- [ ] Initial load < 2 seconds
- [ ] Message send latency < 500ms
- [ ] Typewriter effect smooth (no jank)
- [ ] Quota check < 300ms

✅ **Quality:**
- [ ] 90%+ test coverage
- [ ] 0 critical bugs
- [ ] Lighthouse score > 90
- [ ] Accessibility (WCAG 2.1 AA)

✅ **User Experience:**
- [ ] Intuitive interface
- [ ] Clear error messages
- [ ] Responsive on all devices
- [ ] Smooth animations

---

## 17. References

- **Base Requirements:** `CHAT.MD`
- **Backend API:** `/home/javort/alfredo/MCP-Server/demo_agent/main.py`
- **Backend Implementation:** `docs/NOTAS_CLAUDE.md` (2025-11-04 entry)
- **Frontend Repo:** `/home/javort/odiseo-web/odiseo-sales-ai`
- **Airbnb Style Guide:** https://github.com/airbnb/javascript
- **React Best Practices:** https://react.dev/learn

---

## 18. Appendix

### A. Example API Responses

**Success Response (85% threshold):**
```json
{
  "success": true,
  "response": "Los laptops varían entre $500 y $3000 dependiendo de las especificaciones...",
  "tokens_used": 250,
  "tokens_remaining": 750,
  "warning": {
    "is_warning": true,
    "message": "You've consumed 85% of your daily quota",
    "percentage_used": 85
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-04T12:30:45Z"
}
```

### B. Component Hierarchy

```
Chat (Page)
└── ChatWidget
    ├── ChatHeader
    │   └── QuotaProgressBar
    ├── MessageList
    │   └── ChatMessage[]
    │       └── TypewriterMessage (for AI)
    ├── LoadingAnimation (conditional)
    ├── ChatInput
    │   ├── VoiceButton
    │   ├── AttachButton
    │   ├── Textarea
    │   └── SendButton
    └── UsageWarning (conditional)
```

### C. State Flow Diagram

```
User Types Message
      ↓
Clicks Send
      ↓
API Call (POST /v1/demo)
      ↓
Loading Animation
      ↓
Response Received
      ↓
Typewriter Effect
      ↓
Quota Updated (warning check)
      ↓
Warning Shown (if >= 85%)
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-04
**Status:** ✅ Ready for Implementation
**Approved By:** Claude Code (Sonnet 4.5)
