'use client';

import { Bot, Loader2 } from 'lucide-react';

export default function LoadingMessage() {
  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start space-x-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-white" />
        </div>
        
        {/* Loading Content */}
        <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md shadow-lg border border-gray-100">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-purple-500" />
            <span className="text-sm text-gray-600">Thinking...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
