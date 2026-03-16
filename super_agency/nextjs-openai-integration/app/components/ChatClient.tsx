'use client';

import OpenAI from 'openai';
import { useState } from 'react';

const openai = new OpenAI({ apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY, dangerouslyAllowBrowser: true });

export default function ChatClient() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const completion = await openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [{ role: 'user', content: prompt }],
      });
      setResponse(completion.choices[0].message.content || '');
    } catch (error: any) {
      setResponse('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Client-Side OpenAI Integration</h2>
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Enter your prompt"
        className="border p-2 w-full mb-2"
      />
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="bg-blue-500 text-white p-2 disabled:opacity-50"
      >
        {loading ? 'Sending...' : 'Send'}
      </button>
      <p className="mt-4">{response}</p>
    </div>
  );
}
