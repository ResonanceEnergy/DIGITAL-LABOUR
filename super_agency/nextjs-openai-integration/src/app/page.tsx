import Link from "next/link";
import ChatClient from "./components/ChatClient";

export default function Home() {
  return (
    <div className="min-h-screen p-8 bg-zinc-50 dark:bg-black">
      <main className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Next.js OpenAI Integrations</h1>
        <p className="text-lg mb-8 text-center">
          Explore different ways to integrate OpenAI with Next.js.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 bg-white dark:bg-zinc-800 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">1. API Routes (Server-Side)</h2>
            <p className="mb-4">Use API routes to securely call OpenAI from the server.</p>
            <Link href="/api/chat" className="text-blue-500 hover:underline">View API Route</Link>
          </div>
          <div className="p-6 bg-white dark:bg-zinc-800 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">2. Client-Side Integration</h2>
            <p className="mb-4">Directly call OpenAI from React components.</p>
            <ChatClient />
          </div>
          <div className="p-6 bg-white dark:bg-zinc-800 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">3. Streaming Responses</h2>
            <p className="mb-4">Handle streaming responses for real-time updates.</p>
            <Link href="/api/stream-chat" className="text-blue-500 hover:underline">View Streaming API</Link>
          </div>
          <div className="p-6 bg-white dark:bg-zinc-800 rounded-lg shadow">
            <h2 className="text-2xl font-semibold mb-4">4. Server Components</h2>
            <p className="mb-4">Use server components for SSR with OpenAI.</p>
            <Link href="/chat?prompt=Hello" className="text-blue-500 hover:underline">View Server Component</Link>
          </div>
          <div className="p-6 bg-white dark:bg-zinc-800 rounded-lg shadow md:col-span-2">
            <h2 className="text-2xl font-semibold mb-4">5. Edge Runtime Integration</h2>
            <p className="mb-4">Run OpenAI calls on the edge for low latency.</p>
            <Link href="/api/edge-chat" className="text-blue-500 hover:underline">View Edge API</Link>
          </div
