import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

const DOUBAO_KEY = Deno.env.get('DOUBAO_API_KEY') ?? ''
const DOUBAO_MODEL = 'doubao-seed-1-6-251015'
const DOUBAO_URL = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'

const SYSTEM_PROMPT = `你是一名专业文档编辑，负责对文档进行深度质量检查。
请从以下维度逐条输出问题（每条一行，不要加序号或Markdown符号）：
- 逻辑连贯性：段落衔接、论述是否前后矛盾
- 表述清晰度：是否存在歧义、冗余或晦涩表达
- 数据一致性：数字、日期、引用是否自洽
- 语言规范：正式程度、用词是否得体
若某维度无问题可省略。每条问题直接描述具体位置和建议，不超过50字。`

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { content } = await req.json()
    if (!content?.trim()) {
      return new Response(JSON.stringify({ error: '文档内容为空' }), {
        status: 400, headers: { ...CORS, 'Content-Type': 'application/json' }
      })
    }

    const resp = await fetch(DOUBAO_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${DOUBAO_KEY}` },
      body: JSON.stringify({
        model: DOUBAO_MODEL,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: `请检查以下文档内容：\n\n${content}` }
        ],
        temperature: 0.3,
        max_tokens: 1024,
      }),
    })

    const data = await resp.json()
    const text = data.choices?.[0]?.message?.content ?? ''
    return new Response(JSON.stringify({ content: text, usage: data.usage }), {
      headers: { ...CORS, 'Content-Type': 'application/json' }
    })
  } catch (err) {
    return new Response(JSON.stringify({ error: (err as Error).message }), {
      status: 500, headers: { ...CORS, 'Content-Type': 'application/json' }
    })
  }
})
