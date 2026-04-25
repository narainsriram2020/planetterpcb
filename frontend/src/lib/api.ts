const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

export interface ChatMessage {
  prompt: string;
}

export interface ChatResponse {
  reply: string;
}

export class PlanetTerpAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async sendMessage(message: string): Promise<string> {
    const endpoints = Array.from(new Set([this.baseUrl, '/api']));
    let lastError: unknown = null;

    for (const endpoint of endpoints) {
      try {
        const response = await fetch(`${endpoint}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ prompt: message }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: ChatResponse = await response.json();
        return data.reply;
      } catch (error) {
        lastError = error;
        console.error(`Error sending message via ${endpoint}:`, error);
      }
    }

    throw new Error('Failed to send message. Please try again.');
  }

  async healthCheck(): Promise<boolean> {
    const endpoints = Array.from(new Set([this.baseUrl, '/api']));

    for (const endpoint of endpoints) {
      try {
        const response = await fetch(`${endpoint}/health`);
        if (response.ok) {
          return true;
        }
      } catch (error) {
        console.error(`Health check failed via ${endpoint}:`, error);
      }
    }

    return false;
  }
}

export const api = new PlanetTerpAPI();
