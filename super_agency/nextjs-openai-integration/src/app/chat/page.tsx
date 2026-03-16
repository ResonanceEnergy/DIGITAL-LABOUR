import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export default async function ChatPage({ searchParams }: { searchParams: { prompt?: string } }) {
  const prompt = searchParams.prompt || 'Hello, how can I help you?';
  const completion = await openai.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: prompt }],
  });

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Server Component OpenAI Integration</h1>
      <p><strong>Prompt:</strong> {prompt}</p>
      <p><strong>Response:</strong> {completion.choices[0].message.content}</p>
    </div>
  );
}
