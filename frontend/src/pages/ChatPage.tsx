import { useEffect, useState, useRef } from 'react';
import { chatApi } from '../services/api';
import { ChatMessage } from '../types';
import { CardContent, CardHeader, Button, Badge } from '../components/ui';
import { Send, Bot, User, Copy, Loader2 } from 'lucide-react';
import { cn } from '../utils/cn';
import { Markdown } from '../components/Markdown';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [context] = useState<{ repository_id?: string; scan_id?: string; finding_id?: string }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatApi.send({
        messages: [...messages, userMessage],
        ...context,
      });

      setMessages(prev => [...prev, response.message]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="h-[calc(100vh-200px)] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Chat Assistant</h1>
          <p className="text-dark-500 mt-1">Ask questions about security findings, patches, and best practices</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col card overflow-hidden">
        <CardHeader className="border-b border-dark-200 dark:border-dark-700 px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary-600" />
              <span className="font-medium">AI Security Assistant</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-dark-500">
              {context.repository_id && (
                <Badge variant="default">Repo: {context.repository_id.slice(0, 8)}</Badge>
              )}
              {context.scan_id && (
                <Badge variant="default">Scan: {context.scan_id.slice(0, 8)}</Badge>
              )}
              {context.finding_id && (
                <Badge variant="default">Finding: {context.finding_id.slice(0, 8)}</Badge>
              )}
            </div>
          </div>
        </CardHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="text-center text-dark-500 py-12">
              <Bot className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">How can I help?</h3>
              <p className="max-w-md mx-auto">Ask me about security vulnerabilities, explain findings, generate patches, or learn about secure coding practices.</p>
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
                {[
                  'Why is this SQL injection vulnerable?',
                  'Explain this CWE-79 finding',
                  'How was this patch generated?',
                  'Can I ignore this finding?',
                  'What is the OWASP category for this?',
                  'Show me secure coding examples',
                ].map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(suggestion)}
                    className="text-left p-3 rounded-lg bg-dark-100 dark:bg-dark-800 hover:bg-dark-200 dark:hover:bg-dark-700 transition-colors text-sm"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={cn('flex gap-3', message.role === 'user' ? 'flex-row-reverse' : '')}>
                <div className={cn('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0', message.role === 'user' ? 'bg-primary-600' : 'bg-dark-100 dark:bg-dark-800')}>
                  {message.role === 'user' ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-primary-600" />}
                </div>
                <div className={cn('max-w-[80%]', message.role === 'user' ? 'text-right' : '')}>
                  <div className={cn('inline-block p-4 rounded-2xl', message.role === 'user' ? 'bg-primary-600 text-white' : 'bg-dark-100 dark:bg-dark-800')}>
                    <Markdown content={message.content} />
                  </div>
                  {message.role === 'assistant' && (
                    <div className="flex items-center gap-2 mt-1 text-xs text-dark-400">
                      <button className="flex items-center gap-1 hover:text-primary-600" onClick={() => navigator.clipboard.writeText(message.content)}>
                        <Copy className="h-3 w-3" />
                        Copy
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center flex-shrink-0">
                <Bot className="h-4 w-4 text-primary-600" />
              </div>
              <div className="bg-dark-100 dark:bg-dark-800 rounded-2xl p-4 animate-pulse">
                <div className="h-4 bg-dark-200 dark:bg-dark-700 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-dark-200 dark:bg-dark-700 rounded w-1/2"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <CardContent className="p-4 border-t border-dark-200 dark:border-dark-700">
          <form onSubmit={handleSend} className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about security findings, patches, vulnerabilities..."
              className="flex-1 input min-h-[50px] max-h-40 resize-none pr-10"
              disabled={loading}
              rows={1}
            />
            <Button type="submit" disabled={!input.trim() || loading} className="h-[50px] shrink-0">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>
          <p className="text-xs text-dark-400 mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </CardContent>
      </div>
    </div>
  );
}