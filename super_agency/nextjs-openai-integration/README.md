# Next.js OpenAI Integrations

This project demonstrates various ways to integrate OpenAI with Next.js, including API routes, client-side calls, streaming, server components, and edge runtime.

## Setup

1. Clone or copy this project.
2. Install dependencies: `npm install`
3. Add your OpenAI API key to `.env.local`:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   For client-side integration, also add:
   ```
   NEXT_PUBLIC_OPENAI_API_KEY=your_openai_api_key_here
   ```
   (Note: Exposing keys client-side is insecure; use only for demos.)

4. Run the development server: `npm run dev`

Open [http://localhost:3000](http://localhost:3000) to explore the integrations.

## Integrations

1. **API Routes (Server-Side)**: Secure server-side calls via `/api/chat`.
2. **Client-Side Integration**: Direct browser calls using a React component.
3. **Streaming Responses**: Real-time streaming via `/api/stream-chat`.
4. **Server Components**: SSR with OpenAI at `/chat`.
5. **Edge Runtime**: Low-latency calls via `/api/edge-chat`.

## Best Practices

- Keep API keys secure on the server.
- Implement rate limiting and error handling.
- Monitor usage and costs.
- Use caching for repeated queries.

## Learn More

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
