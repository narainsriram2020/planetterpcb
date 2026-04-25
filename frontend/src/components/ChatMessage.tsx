'use client';

import { useState, useEffect } from 'react';
import { Bot, User, Clock } from 'lucide-react';
import { Message } from '@/types/chat';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [isClient, setIsClient] = useState(false);
  const isUser = message.role === 'user';

  useEffect(() => {
    setIsClient(true);
  }, []);
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
        {/* Avatar */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser 
            ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white' 
            : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
        }`}>
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
        </div>
        
        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`px-4 py-3 rounded-2xl max-w-full ${
            isUser
              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-md'
              : 'bg-white text-gray-900 shadow-lg border border-gray-100 rounded-bl-md'
          }`}>
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </div>
          </div>
          
          {/* Timestamp */}
          <div className={`flex items-center space-x-1 mt-1 ${
            isUser ? 'text-blue-100' : 'text-gray-500'
          }`}>
            <Clock className="w-3 h-3" />
            <span className="text-xs">
              {isClient ? message.timestamp.toLocaleTimeString([], { 
                hour: '2-digit', 
                minute: '2-digit' 
              }) : '--:--'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
