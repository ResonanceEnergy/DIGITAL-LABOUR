import { NextRequest } from 'next/server';
import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export const config = { runtime: 'edge' };

export async function POST(req: NextRequest) {
  try {
    const { prompt } = await req.json();
    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [{ role: 'user', content: prompt }],
    });
    return new Response(JSON.stringify({ response: completion.choices[0].message.content }));
  } catch (error) {
    return new Response(JSON.stringify({ error: 'OpenAI API error' }), { status: 500 });
  }
}
