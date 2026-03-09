# LLM Configuration

## Primary: OpenAI GPT-4o
- Best for: Sales Ops copywriting, Support resolution
- Cost: ~$2.50/1M input, ~$10/1M output
- Quality: Highest for nuanced writing tasks
- Set in .env: OPENAI_API_KEY + OPENAI_MODEL=gpt-4o

## Fallback: Groq (Llama 3.3 70B)
- Best for: Research, classification, QA verification
- Cost: Significantly cheaper
- Speed: Faster inference
- Set in .env: GROQ_API_KEY + GROQ_MODEL=llama-3.3-70b-versatile

## Cost Strategy
- Use GPT-4o for client-facing copy (emails, responses)
- Use Groq/cheaper model for internal QA checks
- Monitor cost-per-task weekly — if > 30% of revenue, switch QA to cheaper model

## Local Option: Ollama
- For offline testing only
- Models: llama3.1, mistral, phi-3
- No API cost, but slower and lower quality
- Good for prompt development, not production
